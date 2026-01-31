# Grant Triage Board

A ready-to-run grant discovery + triage tool for ATNS. It fetches real opportunities, filters, scores, deduplicates against your Google Sheet, appends new rows, shows results in a web UI, and logs every run.

## Quickstart (Day 1)

1) **Create a virtual environment + install dependencies**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) **Create a Google Service Account + share your Sheet**
- Create a Google Cloud service account with **Google Sheets API** enabled.
- Download the JSON key file.
- Share the sheet **“ATNS funding opportunities”** with the service account email.

3) **Configure environment variables**
```bash
cp .env.example .env
```
Set the values in `.env` (see checklist below).

4) **Run the pipeline once (fetch + filter + score + dedupe + append)**
```bash
python -m grantboard.app.pipeline.run
```

5) **Start the web UI**
```bash
uvicorn grantboard.app.main:app --reload --port 8000
```
Visit http://localhost:8000

---

## Day 1 Guarantee
- Two sources are enabled by default:
  - **Grants.gov** (API first, HTML fallback)
  - **RSS feed source** (Philanthropy News Digest RFPs + Federal Register grants search)
- If Grants.gov blocks or is unavailable, the RSS sources still provide results.
- Every opportunity row is backed by fetched page text and a working link.

---

## Configuration Checklist (must set)
- `SPREADSHEET_ID` – Google Sheet ID.
- `SHEET_TAB` – Tab name (default `Sheet1`).
- `SHEET_URL` – For email + UI display.
- `GOOGLE_SERVICE_ACCOUNT_FILE` – Absolute path to service account JSON.
- `ADMIN_TOKEN` – Required for `/admin/run`.

Optional email settings:
- `EMAIL_ENABLED=true`
- `EMAIL_TO`, `EMAIL_FROM`
- Either SMTP (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`) **or** Gmail API (`GMAIL_CREDENTIALS_FILE`, `GMAIL_TOKEN_FILE`).

---

## Pipeline Summary
Each run:
1) **Discovery**: fetch from Grants.gov + RSS feeds.
2) **Filter**: removes biomedical/pharma/bench-only, non-US-only, expired.
3) **Score**: heuristic 1–5.
4) **Dedupe**: canonical URL vs Google Sheet + DB.
5) **Write**: append 1–10 rows to Google Sheet.
6) **Notify**: optional email if rows added.
7) **Log**: run record in SQLite.

---

## UI
- `/` – Opportunities with filters + search.
- `/opportunity/{id}` – Detail view with evidence snippets + raw text.
- `/runs` – Run history + “Run now” + CSV download.
- `/admin/run` – POST with `ADMIN_TOKEN`.

---

## Troubleshooting

### Google auth errors
- Confirm the Google Sheets API is enabled in the Cloud project.
- Make sure the service account email is **shared** on the sheet.
- Confirm `GOOGLE_SERVICE_ACCOUNT_FILE` path is absolute.

### “No results found”
- Verify outbound network access (Grants.gov and RSS sources).
- Raise `MAX_CANDIDATES_PER_SOURCE` to pull more items.
- Adjust filters in `app/pipeline/filter.py` if too strict.

### RSS source failures
- Check that the feed URLs in `app/sources/feeds.py` are accessible.
- Replace with a new feed if necessary (see adapter guide below).

---

## Adding a New Source Adapter
1) Create a new adapter in `app/sources/` implementing `SourceAdapter`:
```python
from grantboard.app.sources.base import SourceAdapter
from grantboard.app.models import SourceResult

class MySource(SourceAdapter):
    name = "My Source"

    def fetch(self) -> list[SourceResult]:
        return [
            SourceResult(
                title="Example Grant",
                link="https://example.org/grant",
                source=self.name,
                raw_text="Full page text...",
            )
        ]
```
2) Add it to the list in `app/pipeline/run.py`.

---

## Repo Tree
```
grantboard/
  app/
    main.py
    scheduler.py
    db.py
    models.py
    config.py
    pipeline/
      run.py
      filter.py
      score.py
      dedupe.py
      normalize.py
    sources/
      base.py
      grants_gov.py
      rss_feed.py
      feeds.py
      html_extract.py
    storage/
      sheets.py
    notify/
      emailer.py
    ui/
      templates/
      static/
  scripts/
    init_db.py
  tests/
    test_canonical_url.py
    test_dedupe.py
    test_scoring.py
  requirements.txt
  README.md
  .env.example
```
