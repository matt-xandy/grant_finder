from __future__ import annotations

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import get_settings
from .db import get_conn, init_db
from .pipeline.run import run_pipeline
from .pipeline.normalize import sanitize_csv_field
from .scheduler import start_scheduler

logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="grantboard/app/ui/static"), name="static")

templates = Jinja2Templates(directory="grantboard/app/ui/templates")


@app.on_event("startup")
def startup() -> None:
    init_db()
    start_scheduler()


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    min_score: int = Query(1, alias="fit_score"),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    deadline_from: Optional[str] = Query(None),
    deadline_to: Optional[str] = Query(None),
):
    query = "SELECT * FROM opportunities WHERE fit_score >= ?"
    params: List[object] = [min_score]
    if source:
        query += " AND source = ?"
        params.append(source)
    if search:
        query += " AND (title LIKE ? OR notes LIKE ? OR raw_text LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if deadline_from:
        query += " AND deadline >= ?"
        params.append(deadline_from)
    if deadline_to:
        query += " AND deadline <= ?"
        params.append(deadline_to)
    query += " ORDER BY last_seen_utc DESC"

    with get_conn() as conn:
        opps = conn.execute(query, params).fetchall()
        sources = conn.execute("SELECT DISTINCT source FROM opportunities").fetchall()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "opportunities": opps,
            "sources": [row[0] for row in sources],
            "filters": {
                "fit_score": min_score,
                "source": source,
                "search": search or "",
                "deadline_from": deadline_from or "",
                "deadline_to": deadline_to or "",
            },
        },
    )


@app.get("/opportunity/{opportunity_id}", response_class=HTMLResponse)
def opportunity_detail(request: Request, opportunity_id: str):
    with get_conn() as conn:
        opp = conn.execute(
            "SELECT * FROM opportunities WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    evidence_snippets = []
    if opp["evidence_snippets"]:
        try:
            evidence_snippets = json.loads(opp["evidence_snippets"])
        except json.JSONDecodeError:
            evidence_snippets = [opp["evidence_snippets"]]
    return templates.TemplateResponse(
        "detail.html",
        {"request": request, "opportunity": opp, "evidence_snippets": evidence_snippets},
    )


@app.get("/runs", response_class=HTMLResponse)
def run_history(request: Request):
    with get_conn() as conn:
        runs = conn.execute("SELECT * FROM runs ORDER BY started_utc DESC").fetchall()
    return templates.TemplateResponse("runs.html", {"request": request, "runs": runs})


@app.post("/admin/run")
def run_now(token: str = Form(...)):
    settings = get_settings()
    if not settings.admin_token or token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    run_pipeline()
    return RedirectResponse(url="/runs", status_code=303)


@app.get("/runs/last.csv")
def download_last_run_csv():
    with get_conn() as conn:
        last_run = conn.execute("SELECT * FROM runs ORDER BY finished_utc DESC LIMIT 1").fetchone()
        if not last_run:
            return PlainTextResponse("No runs yet", status_code=404)
        opps = conn.execute(
            "SELECT * FROM opportunities WHERE status = 'added_to_sheet' AND last_seen_utc = ?",
            (last_run["started_utc"],),
        ).fetchall()

    if not opps:
        row = [
            datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S"),
            "NO ELIGIBLE GRANTS FOUND THIS CYCLE",
            "",
            "",
            "",
            "",
            "",
            "0",
            "",
        ]
        csv_row = ",".join(sanitize_csv_field(str(value)) for value in row)
        return PlainTextResponse(csv_row, media_type="text/csv")

    rows = []
    for opp in opps:
        row = [
            opp["first_seen_utc"],
            opp["title"],
            opp["link"],
            opp["focus_area"],
            opp["eligibility_criteria"],
            opp["deadline"],
            opp["amount"],
            opp["fit_score"],
            opp["notes"],
        ]
        rows.append(",".join(sanitize_csv_field(str(value)) for value in row))

    return PlainTextResponse("\n".join(rows), media_type="text/csv")
