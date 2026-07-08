from __future__ import annotations

import time
from collections import deque

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .browser import BrowserSession
from .config import MirrorConfig
from .policies import RobotsPolicy, ScopePolicy
from .resources import ResourceManager
from .rewriters import HtmlRewriter
from .storage import FileStore
from .url_utils import UrlTools


class MirrorCrawler:
    """Coordinates crawling, rendering, rewriting and persistence.

    Pattern: Orchestrator. This class owns the high-level flow and delegates each
    specialized responsibility to collaborators.
    """

    def __init__(self, config: MirrorConfig) -> None:
        self.config = config
        self.start_url = UrlTools.normalize(config.start_url)
        self.visited_pages: set[str] = set()

        self.scope = ScopePolicy(
            start_url=self.start_url,
            include_external_assets=config.include_external_assets,
        )
        self.robots = RobotsPolicy(
            start_url=self.start_url,
            user_agent=config.user_agent,
            enabled=config.respect_robots,
        )
        self.store = FileStore(config.output_dir)
        self.resources = ResourceManager(
            config=config,
            store=self.store,
            scope=self.scope,
            robots=self.robots,
        )
        self.html_rewriter = HtmlRewriter(self.store, self.resources)

    def run(self) -> None:
        queue: deque[str] = deque([self.start_url])

        with BrowserSession(self.config) as browser:
            browser.on_response(self.resources.handle_browser_response)

            while queue and not self._page_limit_reached():
                current_url = UrlTools.normalize(queue.popleft())

                if current_url in self.visited_pages:
                    continue

                if not self.scope.can_visit_page(current_url):
                    continue

                if not self.robots.can_fetch(current_url):
                    print(f"[robots] skipped page: {current_url}")
                    continue

                print(f"\n[page] opening: {current_url}")

                try:
                    rendered_html = browser.goto_and_get_html(current_url)
                except PlaywrightTimeoutError:
                    print("[warn] timed out waiting for network idle; saving loaded content.")
                    if browser.page is None:
                        continue
                    rendered_html = browser.page.content()
                except Exception as error:
                    print(f"[error] failed to open {current_url}: {error}")
                    continue

                rewritten_html, found_links = self.html_rewriter.rewrite(rendered_html, current_url)
                self.store.save_text(
                    current_url,
                    rewritten_html,
                    content_type="text/html",
                    force_html=True,
                )
                self.visited_pages.add(current_url)
                print(f"[saved-page] {current_url}")

                self._enqueue_links(queue, found_links)
                time.sleep(self.config.delay_seconds)

        self._print_summary()

    def _enqueue_links(self, queue: deque[str], links: list[str]) -> None:
        for link in links:
            normalized = UrlTools.normalize(link)

            if normalized in self.visited_pages or normalized in queue:
                continue

            if self._would_exceed_limit(extra_queued=1, current_queue_size=len(queue)):
                continue

            queue.append(normalized)

    def _page_limit_reached(self) -> bool:
        return self.config.max_pages is not None and len(self.visited_pages) >= self.config.max_pages

    def _would_exceed_limit(self, *, extra_queued: int, current_queue_size: int) -> bool:
        if self.config.max_pages is None:
            return False

        projected = len(self.visited_pages) + current_queue_size + extra_queued
        return projected > self.config.max_pages

    def _print_summary(self) -> None:
        print("\nDone.")
        print(f"Pages saved: {len(self.visited_pages)}")
        print(f"Assets saved: {len(self.resources.saved_asset_urls)}")
        print(f"Output: {self.store.output_dir.resolve()}")
