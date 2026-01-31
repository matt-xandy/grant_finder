from __future__ import annotations

from typing import Tuple

from .normalize import normalize_text
from ..models import Opportunity

HIGH_MATCH = [
    "chronic pain",
    "pain awareness",
    "pain education",
    "neuroplastic",
    "mind-body",
    "mind body",
]

STRONG_MATCH = [
    "behavioral health",
    "mental health education",
    "community education",
    "public awareness",
]

PARTIAL_MATCH = [
    "public health",
    "health education",
    "community engagement",
    "patient education",
]


def heuristic_score(opportunity: Opportunity) -> Tuple[int, str]:
    text = normalize_text(" ".join([
        opportunity.title,
        opportunity.raw_text,
        opportunity.notes,
    ])).lower()

    if any(term in text for term in HIGH_MATCH):
        return 5, "Direct alignment with pain awareness / neuroplastic pain"
    if any(term in text for term in STRONG_MATCH):
        return 4, "Strong alignment with community education"
    if any(term in text for term in PARTIAL_MATCH):
        return 3, "Partial alignment with broader public health education"
    return 2, "Adjacent opportunity; review required"
