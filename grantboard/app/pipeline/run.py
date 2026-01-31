from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List

from dateparser.search import search_dates

from ..config import get_settings
from ..db import get_conn, init_db
from ..models import Opportunity, RunRecord
from ..notify.emailer import send_email
from ..storage.sheets import append_rows
from ..sources.feeds import DEFAULT_FEEDS
from ..sources.grants_gov import GrantsGovSource
from ..sources.rss_feed import RssFeedSource
from .dedupe import dedupe
from .filter import hard_filter
from .normalize import canonical_url, limit_length, make_opportunity_id, normalize_text
from .score import heuristic_score

logger = logging.getLogger(__name__)

KEYWORDS = ["pain", "education", "awareness", "mind-body", "neuroplastic", "community"]


def run_pipeline() -> RunRecord:
    init_db()
    settings = get_settings()
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    errors = []

    sources = [GrantsGovSource()] + [RssFeedSource(feed["name"], feed["url"]) for feed in DEFAULT_FEEDS]
    candidates: List[Opportunity] = []

    for source in sources:
        try:
            results = source.fetch()
        except Exception as exc:
            logger.exception("Source %s failed", source.name)
            errors.append(f"{source.name}: {exc}")
            continue
        for result in results:
            opp = _build_opportunity(result, started)
            candidates.append(opp)

    filtered_in = []
    with get_conn() as conn:
        for opp in candidates:
            allowed, reason = hard_filter(opp)
            if not allowed:
                opp.status = "rejected"
                opp.rejection_reason = reason
            else:
                score, notes = heuristic_score(opp)
                opp.fit_score = score
                opp.notes = limit_length(notes, 150)
                filtered_in.append(opp)
            _upsert_opportunity(conn, opp)
        conn.commit()

    deduped = list(dedupe(filtered_in))
    for opp in deduped:
        opp.status = "new"

    with get_conn() as conn:
        for opp in filtered_in:
            if opp.status == "duplicate":
                _upsert_opportunity(conn, opp)
        conn.commit()

    rows_to_append = []
    for opp in deduped[: settings.max_append_per_run]:
        rows_to_append.append(_sheet_row(opp))
        opp.status = "added_to_sheet"
        opp.last_seen_utc = started.isoformat()
        with get_conn() as conn:
            _upsert_opportunity(conn, opp)
            conn.commit()

    if rows_to_append:
        append_rows(rows_to_append)

    if rows_to_append:
        _notify(rows_to_append)

    finished = datetime.now(timezone.utc)
    run_record = RunRecord(
        run_id=run_id,
        started_utc=started.isoformat(),
        finished_utc=finished.isoformat(),
        n_candidates=len(candidates),
        n_filtered_in=len(filtered_in),
        n_added=len(rows_to_append),
        errors="; ".join(errors),
    )
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs (run_id, started_utc, finished_utc, n_candidates, n_filtered_in, n_added, errors) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run_record.run_id,
                run_record.started_utc,
                run_record.finished_utc,
                run_record.n_candidates,
                run_record.n_filtered_in,
                run_record.n_added,
                run_record.errors,
            ),
        )
        conn.commit()

    return run_record


def _build_opportunity(result, started_time: datetime) -> Opportunity:
    title = normalize_text(result.title)
    link = canonical_url(result.link)
    raw_text = normalize_text(result.raw_text)
    deadline = result.deadline or _extract_deadline(raw_text)
    amount = result.amount or _extract_amount(raw_text)
    focus_area = result.focus_area or _extract_focus(raw_text)
    eligibility = result.eligibility_criteria or _extract_eligibility(raw_text)
    evidence_snippets = result.evidence_snippets or _extract_snippets(raw_text)

    return Opportunity(
        opportunity_id=make_opportunity_id(link),
        title=limit_length(title, 120),
        link=link,
        source=result.source,
        focus_area=limit_length(focus_area, 60),
        eligibility_criteria=limit_length(eligibility, 80),
        deadline=deadline,
        amount=amount,
        notes="",
        evidence_snippets=evidence_snippets,
        raw_text=raw_text,
        first_seen_utc=started_time.isoformat(),
        last_seen_utc=started_time.isoformat(),
        status="new",
        rejection_reason="",
    )


def _extract_deadline(text: str) -> str:
    matches = search_dates(text, settings={"PREFER_DATES_FROM": "future"})
    if not matches:
        return ""
    _, date = matches[0]
    return date.date().isoformat()


def _extract_amount(text: str) -> str:
    for token in ["$", "USD", "US$"]:
        if token in text:
            start = text.find(token)
            snippet = text[start : start + 40]
            return normalize_text(snippet)
    return ""


def _extract_focus(text: str) -> str:
    for keyword in KEYWORDS:
        if keyword in text.lower():
            return keyword
    return "public health"


def _extract_eligibility(text: str) -> str:
    lower = text.lower()
    if "501(c)(3)" in lower or "501c3" in lower:
        return "501(c)(3) nonprofits"
    if "nonprofit" in lower:
        return "US nonprofits"
    return "See guidelines"


def _extract_snippets(text: str) -> List[str]:
    snippets = []
    for keyword in KEYWORDS:
        idx = text.lower().find(keyword)
        if idx != -1:
            start = max(idx - 80, 0)
            end = min(idx + 80, len(text))
            snippet = text[start:end].strip()
            if snippet and snippet not in snippets:
                snippets.append(snippet)
        if len(snippets) >= 3:
            break
    return snippets


def _sheet_row(opp: Opportunity) -> List[str]:
    now_et = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")
    return [
        now_et,
        limit_length(opp.title, 120),
        opp.link,
        limit_length(opp.focus_area, 60),
        limit_length(opp.eligibility_criteria, 80),
        opp.deadline or "TBA",
        opp.amount,
        str(opp.fit_score),
        limit_length(opp.notes, 150),
    ]


def _upsert_opportunity(conn, opp: Opportunity) -> None:
    conn.execute(
        """
        INSERT INTO opportunities (
            opportunity_id, title, link, source, focus_area, eligibility_criteria, deadline, amount,
            fit_score, notes, evidence_snippets, raw_text, first_seen_utc, last_seen_utc, status, rejection_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(opportunity_id) DO UPDATE SET
            title=excluded.title,
            link=excluded.link,
            source=excluded.source,
            focus_area=excluded.focus_area,
            eligibility_criteria=excluded.eligibility_criteria,
            deadline=excluded.deadline,
            amount=excluded.amount,
            fit_score=excluded.fit_score,
            notes=excluded.notes,
            evidence_snippets=excluded.evidence_snippets,
            raw_text=excluded.raw_text,
            last_seen_utc=excluded.last_seen_utc,
            status=excluded.status,
            rejection_reason=excluded.rejection_reason
        """,
        (
            opp.opportunity_id,
            opp.title,
            opp.link,
            opp.source,
            opp.focus_area,
            opp.eligibility_criteria,
            opp.deadline,
            opp.amount,
            opp.fit_score,
            opp.notes,
            json.dumps(opp.evidence_snippets),
            opp.raw_text,
            opp.first_seen_utc,
            opp.last_seen_utc,
            opp.status,
            opp.rejection_reason,
        ),
    )


def _notify(rows: List[List[str]]) -> None:
    settings = get_settings()
    if not settings.email_to:
        logger.warning("EMAIL_TO not set; skipping email")
        return
    subject = f"New ATNS grant opportunities added ({len(rows)})"
    summary_lines = []
    for row in rows[:5]:
        summary_lines.append(f"- {row[1]} (Score {row[7]}) Deadline {row[5]}")
    summary = "\n".join(summary_lines)
    body = f"New opportunities were added to the sheet.\n\nSheet: {settings.sheet_url}\n\n{summary}"
    send_email(subject, body, [settings.email_to])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
