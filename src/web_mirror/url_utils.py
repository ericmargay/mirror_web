from __future__ import annotations

import re
from urllib.parse import urldefrag, urljoin, urlparse


class UrlTools:
    """Small URL normalization helper used across the project."""

    @staticmethod
    def normalize(url: str, base_url: str | None = None) -> str:
        value = (url or "").strip()

        if base_url:
            value = urljoin(base_url, value)

        if not urlparse(value).scheme:
            value = "https://" + value

        value, _fragment = urldefrag(value)
        return value.rstrip("/") if value.endswith("/") and urlparse(value).path == "/" else value

    @staticmethod
    def origin(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def domain(url: str) -> str:
        return urlparse(url).netloc

    @staticmethod
    def is_http(url: str) -> bool:
        return urlparse(url).scheme in {"http", "https"}

    @staticmethod
    def is_same_domain(left: str, right: str) -> bool:
        return UrlTools.domain(left) == UrlTools.domain(right)

    @staticmethod
    def is_ignored_scheme(url: str) -> bool:
        return bool(re.match(r"^(data|blob|javascript|mailto|tel):", url.strip(), re.I))
