from __future__ import annotations

import logging
from typing import List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from ..config import get_settings

logger = logging.getLogger(__name__)


def _get_service():
    settings = get_settings()
    if not settings.google_service_account_file:
        logger.warning("GOOGLE_SERVICE_ACCOUNT_FILE not set; Google Sheets disabled")
        return None
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(settings.google_service_account_file, scopes=scopes)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_sheet_links() -> List[str]:
    settings = get_settings()
    service = _get_service()
    if not service:
        return []
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=settings.spreadsheet_id, range=f"{settings.sheet_tab}!A:I")
            .execute()
        )
    except Exception as exc:
        logger.warning("Failed to read sheet: %s", exc)
        return []
    values = result.get("values", [])
    links = []
    for row in values[1:]:
        if len(row) >= 3:
            links.append(row[2])
    return links


def append_rows(rows: List[List[str]]) -> None:
    settings = get_settings()
    if not rows:
        return
    service = _get_service()
    if not service:
        logger.warning("Google Sheets disabled; skipping append")
        return
    body = {"values": rows}
    service.spreadsheets().values().append(
        spreadsheetId=settings.spreadsheet_id,
        range=f"{settings.sheet_tab}!A:I",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
