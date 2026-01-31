from __future__ import annotations

import time
from collections import defaultdict
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

from ..config import get_settings
from ..pipeline.normalize import normalize_text


class Requester:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.settings.user_agent})
        self.last_request_time = defaultdict(float)

    def get(self, url: str) -> requests.Response:
        domain = requests.utils.urlparse(url).netloc
        elapsed = time.time() - self.last_request_time[domain]
        if elapsed < self.settings.request_delay_seconds:
            time.sleep(self.settings.request_delay_seconds - elapsed)

        backoff = self.settings.request_backoff_factor
        for attempt in range(self.settings.request_max_retries):
            try:
                response = self.session.get(url, timeout=self.settings.request_timeout)
                self.last_request_time[domain] = time.time()
                response.raise_for_status()
                return response
            except Exception:
                if attempt == self.settings.request_max_retries - 1:
                    raise
                time.sleep(backoff)
                backoff *= self.settings.request_backoff_factor
        raise RuntimeError("Request failed")


def extract_text_and_snippets(html: str, keywords: List[str]) -> Tuple[str, List[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
    text = normalize_text(soup.get_text(" "))
    snippets = []
    lower = text.lower()
    for keyword in keywords:
        idx = lower.find(keyword.lower())
        if idx != -1:
            start = max(idx - 120, 0)
            end = min(idx + 120, len(text))
            snippet = text[start:end].strip()
            if snippet and snippet not in snippets:
                snippets.append(snippet)
        if len(snippets) >= 3:
            break
    return text, snippets
