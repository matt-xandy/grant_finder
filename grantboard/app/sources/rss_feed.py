from __future__ import annotations

from typing import List

import feedparser

from ..config import get_settings
from ..models import SourceResult
from .base import SourceAdapter
from .html_extract import Requester, extract_text_and_snippets


class RssFeedSource(SourceAdapter):
    def __init__(self, name: str, url: str) -> None:
        self.name = name
        self.url = url
        self.settings = get_settings()
        self.requester = Requester()

    def fetch(self) -> List[SourceResult]:
        feed = feedparser.parse(self.url)
        items = []
        for entry in feed.entries[: self.settings.max_candidates_per_source]:
            link = entry.get("link", "")
            title = entry.get("title", "")
            if not link:
                continue
            raw_text, snippets = self._fetch_detail(link)
            items.append(
                SourceResult(
                    title=title,
                    link=link,
                    source=self.name,
                    raw_text=raw_text,
                    evidence_snippets=snippets,
                )
            )
        return items

    def _fetch_detail(self, link: str) -> tuple[str, list[str]]:
        response = self.requester.get(link)
        keywords = ["grant", "deadline", "apply", "eligibility", "nonprofit"]
        return extract_text_and_snippets(response.text, keywords)
