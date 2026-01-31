from __future__ import annotations

import base64
import logging
import smtplib
from email.message import EmailMessage
from typing import List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..config import get_settings

logger = logging.getLogger(__name__)


def send_email(subject: str, body: str, recipients: List[str]) -> None:
    settings = get_settings()
    if not settings.email_enabled:
        logger.warning("Email disabled; skipping notification")
        return

    if settings.gmail_credentials_file and settings.gmail_token_file:
        try:
            _send_gmail_api(subject, body, recipients)
            return
        except Exception as exc:
            logger.warning("Gmail API failed, falling back to SMTP: %s", exc)

    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        _send_smtp(subject, body, recipients)
    else:
        logger.warning("SMTP credentials not configured; skipping email")


def _send_gmail_api(subject: str, body: str, recipients: List[str]) -> None:
    settings = get_settings()
    creds = Credentials.from_authorized_user_file(settings.gmail_token_file)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    message = EmailMessage()
    message["To"] = ", ".join(recipients)
    message["From"] = settings.email_from or settings.email_to
    message["Subject"] = subject
    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()


def _send_smtp(subject: str, body: str, recipients: List[str]) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
