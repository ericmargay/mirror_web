from __future__ import annotations

import time
from collections import deque

from .browser import BrowserSession
from .config import MirrorConfig
from .policies import CrawlPolicy
from .resources import ResourceDownloader
from .rewriters import CssRewriter, HtmlRewriter
from .storage import FileStorage
from .url_utils import clean_url


class MirrorCrawler:
    """Coordinates browser rendering, asset capture, rewriting, and crawling."""

    USER_AGENT = "Mozilla/5.0 AuthorizedStaticMirror/0.2"

    def __init__(self, config: MirrorConfig) -> None:
        self.config = config
        self.storage = FileStorage(config.output_dir)
        self.policy = CrawlPolicy(
            start_url=config.start_url,
            include_external=config.include_external,
            respect_robots=config.respect_robots,
            user_agent=self.USER_AGENT,
        )
        self.downloader = ResourceDownloader(
            storage=self.storage,
            policy=self.policy,
            max_asset_bytes=config.max_asset_bytes,
            user_agent=self.USER_AGENT,
        )
        self.css_rewriter = CssRewriter(self.storage, self.downloader)
        self.html_rewriter = HtmlRewriter(self.storage, self.downloader, self.css_rewriter)
        self.visited_pages: set[str] = set()

    def unlimited(self) -> bool:
        return self.config.max_pages == 0

    def under_limit(self, queued_count: int = 0) -> bool:
        return self.unlimited() or len(self.visited_pages) + queued_count < self.config.max_pages

    def handle_browser_response(self, response) -> None:
        url = clean_url(response.url)
        if not self.policy.should_save_asset(url):
            return

        if self.storage.get(url):
            return

        try:
            body = response.body()
            content_type = response.headers.get("content-type", "")
            local_path = self.downloader.save_response_body(url, body, content_type)
            if local_path and ("text/css" in content_type.lower() or local_path.suffix.lower() == ".css"):
                self.css_rewriter.rewrite_file(local_path, url)
        except Exception:
            # Some browser responses cannot expose body data, for example redirects
            # or opaque responses. They are safe to ignore.
            return

    def crawl(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        queue: deque[str] = deque([clean_url(self.config.start_url)])

        with BrowserSession(
            headed=self.config.headed,
            timeout_ms=self.config.timeout_ms,
            auth_state=self.config.auth_state,
            user_agent=self.USER_AGENT,
            on_response=self.handle_browser_response,
        ) as browser:
            while queue and (self.unlimited() or len(self.visited_pages) < self.config.max_pages):
                current_url = clean_url(queue.popleft())

                if current_url in self.visited_pages:
                    continue

                if not self.policy.should_visit_page(current_url):
                    print(f"[policy] skipped page: {current_url}")
                    continue

                print(f"\n[page] {current_url}")
                html = browser.goto_and_get_content(current_url)
                if html is None:
                    continue

                self.visited_pages.add(current_url)
                rewritten_html, discovered_links = self.html_rewriter.rewrite_html(html, current_url)
                self.storage.save_text(current_url, rewritten_html, content_type="text/html", force_html=True)

                for link in discovered_links:
                    link = clean_url(link)
                    if link in self.visited_pages or link in queue:
                        continue
                    if not self.policy.should_visit_page(link):
                        continue
                    if self.under_limit(len(queue)):
                        queue.append(link)

                if self.config.delay_seconds > 0:
                    time.sleep(self.config.delay_seconds)

        print("\nDone.")
        print(f"Pages saved: {len(self.visited_pages)}")
        print(f"Assets saved: {len(self.downloader.saved_urls)}")
        print(f"Output: {self.config.output_dir.resolve()}")
