import hashlib
import re
from urllib.parse import urlparse, urlunparse


def canonical_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/+$", "", parsed.path)
    canonical = urlunparse((scheme, netloc, path, "", "", ""))
    return canonical


def make_opportunity_id(url: str) -> str:
    canonical = canonical_url(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    if not value:
        return ""
    replacements = {
        "“": '"',
        "”": '"',
        "’": "'",
        "‘": "'",
        "–": "-",
        "—": "-",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def limit_length(value: str, max_len: int) -> str:
    value = normalize_text(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "…"


def sanitize_csv_field(value: str) -> str:
    value = normalize_text(value)
    if "," in value:
        return f'"{value}"'
    return value
