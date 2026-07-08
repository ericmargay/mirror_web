from __future__ import annotations

from pathlib import Path

import requests
from playwright.sync_api import Response

from .config import MirrorConfig
from .policies import RobotsPolicy, ScopePolicy
from .storage import FileStore
from .url_utils import UrlTools


class ResourceManager:
    """Saves network resources and fetches missing assets on demand.

    Pattern: Facade. HTML/CSS rewriters interact with this one class instead of
    knowing about Playwright responses, Requests, robots.txt, or filesystem paths.
    """

    def __init__(
        self,
        *,
        config: MirrorConfig,
        store: FileStore,
        scope: ScopePolicy,
        robots: RobotsPolicy,
    ) -> None:
        self.config = config
        self.store = store
        self.scope = scope
        self.robots = robots
        self.saved_asset_urls: set[str] = set()

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

    def handle_browser_response(self, response: Response) -> None:
        """Capture resources loaded by the browser."""
        url = UrlTools.normalize(response.url)

        if not self._should_save(url):
            return

        if url in self.saved_asset_urls:
            return

        try:
            body = response.body()
        except Exception:
            return

        if len(body) > self.config.max_asset_bytes:
            print(f"[large] skipped asset: {url}")
            return

        content_type = response.headers.get("content-type", "")

        # The active page HTML is saved after rewriting by MirrorCrawler.
        # Skipping text/html here avoids counting raw pages as assets.
        if "text/html" in content_type.lower():
            return

        local_path = self.store.save_bytes(url, body, content_type=content_type)
        self.saved_asset_urls.add(url)

        if self._is_css(url, content_type, local_path):
            self._rewrite_css(local_path, url)

        print(f"[asset] {url}")

    def ensure_asset(self, url: str) -> Path | None:
        """Return local path for an asset, fetching it if the browser did not capture it."""
        normalized = UrlTools.normalize(url)

        existing = self.store.get(normalized)
        if existing:
            return existing

        if not self._should_save(normalized):
            return None

        try:
            response = self.session.get(normalized, timeout=25)
            response.raise_for_status()
        except requests.RequestException:
            return None

        if len(response.content) > self.config.max_asset_bytes:
            print(f"[large] skipped asset: {normalized}")
            return None

        content_type = response.headers.get("content-type", "")
        local_path = self.store.save_bytes(normalized, response.content, content_type=content_type)
        self.saved_asset_urls.add(normalized)

        if self._is_css(normalized, content_type, local_path):
            self._rewrite_css(local_path, normalized)

        print(f"[asset] {normalized}")
        return local_path

    def _should_save(self, url: str) -> bool:
        return self.scope.can_save_asset(url) and self.robots.can_fetch(url)

    def _is_css(self, url: str, content_type: str, local_path: Path) -> bool:
        return "text/css" in content_type.lower() or local_path.suffix.lower() == ".css"

    def _rewrite_css(self, local_path: Path, url: str) -> None:
        # Lazy import avoids a circular import between rewriters and resource manager.
        from .rewriters import CssRewriter

        CssRewriter(self.store, self).rewrite_file(local_path, url)
