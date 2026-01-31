from __future__ import annotations

from typing import Iterable, Set

from ..db import get_conn
from ..models import Opportunity
from ..storage.sheets import read_sheet_links
from .normalize import canonical_url


def existing_sheet_links() -> Set[str]:
    links = read_sheet_links()
    return {canonical_url(link) for link in links if link}


def existing_db_links() -> Set[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT link FROM opportunities").fetchall()
    return {canonical_url(row["link"]) for row in rows if row["link"]}


def dedupe(opportunities: Iterable[Opportunity]) -> Iterable[Opportunity]:
    sheet_links = existing_sheet_links()
    db_links = existing_db_links()
    seen = set()
    for opp in opportunities:
        link = canonical_url(opp.link)
        if not link:
            continue
        if link in seen or link in sheet_links or link in db_links:
            opp.status = "duplicate"
            opp.rejection_reason = "Duplicate link"
            continue
        seen.add(link)
        yield opp
