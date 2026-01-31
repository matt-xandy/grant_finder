from __future__ import annotations

import json
from typing import List

import requests
from bs4 import BeautifulSoup

from ..config import get_settings
from ..models import SourceResult
from .base import SourceAdapter
from .html_extract import Requester, extract_text_and_snippets


SEARCH_TERMS = [
    "pain", "education", "awareness", "community", "behavioral health", "public health"
]


class GrantsGovSource(SourceAdapter):
    name = "Grants.gov"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.requester = Requester()

    def fetch(self) -> List[SourceResult]:
        results = []
        try:
            results = self._fetch_api()
        except Exception:
            results = []
        if not results:
            try:
                results = self._fetch_html()
            except Exception:
                return []
        return results[: self.settings.max_candidates_per_source]

    def _fetch_api(self) -> List[SourceResult]:
        url = "https://api.grants.gov/v1/api/search2"
        payload = {
            "keyword": " OR ".join(SEARCH_TERMS),
            "oppStatuses": ["posted"],
            "rows": self.settings.max_candidates_per_source,
            "start": 0,
        }
        response = self.requester.session.post(url, json=payload, timeout=self.settings.request_timeout)
        response.raise_for_status()
        data = response.json()
        opps = data.get("opportunities", []) or data.get("oppHits", [])
        items = []
        for opp in opps:
            title = opp.get("opportunityTitle") or opp.get("title") or ""
            link = opp.get("opportunityLink") or opp.get("link") or ""
            deadline = opp.get("closeDate") or opp.get("closeDateDesc") or ""
            amount = opp.get("awardCeiling") or ""
            if not link:
                continue
            raw_text, snippets = self._fetch_detail(link)
            items.append(
                SourceResult(
                    title=title,
                    link=link,
                    source=self.name,
                    raw_text=raw_text,
                    deadline=deadline,
                    amount=str(amount) if amount else "",
                    evidence_snippets=snippets,
                )
            )
        return items

    def _fetch_html(self) -> List[SourceResult]:
        search_url = "https://www.grants.gov/search-grants?keyword=pain"
        response = self.requester.get(search_url)
        soup = BeautifulSoup(response.text, "html.parser")
        items = []
        for card in soup.select("a[href*='/search-grants?']"):
            href = card.get("href")
            title = card.get_text(strip=True)
            if not href or not title:
                continue
            if not href.startswith("http"):
                link = f"https://www.grants.gov{href}"
            else:
                link = href
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
        keywords = ["nonprofit", "eligibility", "deadline", "application"]
        return extract_text_and_snippets(response.text, keywords)
