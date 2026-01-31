from __future__ import annotations

import datetime as dt
import re
from typing import Tuple

import dateparser

from .normalize import normalize_text
from ..models import Opportunity

EXCLUSION_TERMS = [
    "biomedical",
    "pharmaceutical",
    "drug development",
    "device development",
    "bench research",
    "clinical trial",
    "basic science",
]


INCLUSION_TERMS = [
    "nonprofit",
    "501(c)(3)",
    "501c3",
    "public charity",
    "community",
    "education",
    "awareness",
]


def deadline_is_valid(deadline: str) -> bool:
    deadline = deadline.strip()
    if not deadline:
        return True
    if deadline.lower() in {"rolling", "tba"}:
        return True
    parsed = dateparser.parse(deadline, settings={"TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True})
    if not parsed:
        return True
    now = dt.datetime.now(dt.timezone.utc)
    return parsed >= now


def hard_filter(opportunity: Opportunity) -> Tuple[bool, str]:
    text = normalize_text(" ".join([
        opportunity.title,
        opportunity.raw_text,
        opportunity.eligibility_criteria,
    ])).lower()

    if any(term in text for term in EXCLUSION_TERMS):
        return False, "Excluded: biomedical/pharma/device focus"

    if "non-u.s" in text or "non us" in text or "outside the united states" in text:
        return False, "Excluded: non-U.S. applicants"

    if "only" in text and "university" in text and "campus" in text:
        return False, "Excluded: single university"

    if not deadline_is_valid(opportunity.deadline):
        return False, "Excluded: deadline passed"

    if not any(term in text for term in INCLUSION_TERMS):
        return False, "Excluded: eligibility unclear for nonprofits"

    return True, ""
