import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY,
    title TEXT,
    link TEXT,
    source TEXT,
    focus_area TEXT,
    eligibility_criteria TEXT,
    deadline TEXT,
    amount TEXT,
    fit_score INTEGER,
    notes TEXT,
    evidence_snippets TEXT,
    raw_text TEXT,
    first_seen_utc TEXT,
    last_seen_utc TEXT,
    status TEXT,
    rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_utc TEXT,
    finished_utc TEXT,
    n_candidates INTEGER,
    n_filtered_in INTEGER,
    n_added INTEGER,
    errors TEXT
);
"""


def init_db() -> None:
    settings = get_settings()
    with sqlite3.connect(settings.database_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
