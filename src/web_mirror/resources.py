from __future__ import annotations

from pathlib import Path

import requests

from .policies import CrawlPolicy
from .storage import FileStorage
from .url_utils import clean_url


class ResourceDownloader:
    """Downloads assets outside the browser pipeline when a rewriter discovers them."""

    def __init__(
        self,
        storage: FileStorage,
        policy: CrawlPolicy,
        max_asset_bytes: int,
        user_agent: str,
    ) -> None:
        self.storage = storage
        self.policy = policy
        self.max_asset_bytes = max_asset_bytes
        self.saved_urls: set[str] = set()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def save_response_body(self, url: str, body: bytes, content_type: str | None) -> Path | None:
        url = clean_url(url)
        if not self.policy.should_save_asset(url):
            return None
        if len(body) > self.max_asset_bytes:
            print(f"[large] skipped: {url}")
            return None

        local_path = self.storage.save_bytes(url, body, content_type=content_type)
        self.saved_urls.add(url)
        print(f"[asset] {url}")
        return local_path

    def fetch_if_missing(self, url: str) -> Path | None:
        url = clean_url(url)
        existing = self.storage.get(url)
        if existing:
            return existing

        if not self.policy.should_save_asset(url):
            return None

        try:
            response = self.session.get(url, timeout=25)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            return self.save_response_body(url, response.content, content_type)
        except Exception as exc:
            print(f"[error] asset failed: {url} ({exc})")
            return None
