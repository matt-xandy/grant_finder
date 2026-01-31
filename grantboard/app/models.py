from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Opportunity:
    opportunity_id: str
    title: str
    link: str
    source: str
    focus_area: str = ""
    eligibility_criteria: str = ""
    deadline: str = ""
    amount: str = ""
    fit_score: int = 0
    notes: str = ""
    evidence_snippets: List[str] = field(default_factory=list)
    raw_text: str = ""
    first_seen_utc: str = ""
    last_seen_utc: str = ""
    status: str = "new"
    rejection_reason: str = ""


@dataclass
class RunRecord:
    run_id: str
    started_utc: str
    finished_utc: str
    n_candidates: int
    n_filtered_in: int
    n_added: int
    errors: str = ""


@dataclass
class SourceResult:
    title: str
    link: str
    source: str
    raw_text: str
    deadline: str = ""
    amount: str = ""
    focus_area: str = ""
    eligibility_criteria: str = ""
    evidence_snippets: Optional[List[str]] = None
