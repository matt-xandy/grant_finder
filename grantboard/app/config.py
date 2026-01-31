import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]


@dataclass
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "grantboard.db"))
    admin_token: str = os.getenv("ADMIN_TOKEN", "")
    run_timezone: str = os.getenv("RUN_TIMEZONE", "America/New_York")
    run_hour: int = int(os.getenv("RUN_HOUR", "9"))
    run_minute: int = int(os.getenv("RUN_MINUTE", "0"))

    spreadsheet_id: str = os.getenv("SPREADSHEET_ID", "")
    sheet_tab: str = os.getenv("SHEET_TAB", "Sheet1")
    sheet_url: str = os.getenv("SHEET_URL", "")
    google_service_account_file: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")

    email_enabled: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    email_to: str = os.getenv("EMAIL_TO", "")
    email_from: str = os.getenv("EMAIL_FROM", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")

    gmail_credentials_file: str = os.getenv("GMAIL_CREDENTIALS_FILE", "")
    gmail_token_file: str = os.getenv("GMAIL_TOKEN_FILE", "")

    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "20"))
    request_delay_seconds: float = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))
    request_max_retries: int = int(os.getenv("REQUEST_MAX_RETRIES", "3"))
    request_backoff_factor: float = float(os.getenv("REQUEST_BACKOFF_FACTOR", "1.5"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        "GrantTriageBoard/1.0 (+https://example.org; contact@example.org)",
    )

    max_candidates_per_source: int = int(os.getenv("MAX_CANDIDATES_PER_SOURCE", "20"))
    max_append_per_run: int = int(os.getenv("MAX_APPEND_PER_RUN", "10"))

    llm_scoring_enabled: bool = os.getenv("LLM_SCORING_ENABLED", "false").lower() == "true"


def get_settings() -> Settings:
    return Settings()
