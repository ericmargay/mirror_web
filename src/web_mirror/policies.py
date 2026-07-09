from __future__ import annotations

from urllib.robotparser import RobotFileParser

from .url_utils import clean_url, domain, is_http_url, origin


class CrawlPolicy:
    """Decides whether pages/assets are allowed to be visited or stored.

    The default policy keeps page crawling inside the initial domain while still
    allowing external assets when include_external=True.
    """

    def __init__(self, start_url: str, include_external: bool, respect_robots: bool, user_agent: str) -> None:
        self.start_url = clean_url(start_url)
        self.start_domain = domain(self.start_url)
        self.include_external = include_external
        self.respect_robots = respect_robots
        self.user_agent = user_agent
        self._robots = self._load_robots() if respect_robots else None

    def _load_robots(self) -> RobotFileParser | None:
        rp = RobotFileParser()
        try:
            rp.set_url(f"{origin(self.start_url)}/robots.txt")
            rp.read()
            return rp
        except Exception:
            return None

    def can_fetch(self, url: str) -> bool:
        if not self._robots:
            return True
        try:
            return self._robots.can_fetch(self.user_agent, clean_url(url))
        except Exception:
            return True

    def is_internal(self, url: str) -> bool:
        return domain(clean_url(url)) == self.start_domain

    def should_visit_page(self, url: str) -> bool:
        url = clean_url(url)
        return is_http_url(url) and self.is_internal(url) and self.can_fetch(url)

    def should_save_asset(self, url: str) -> bool:
        url = clean_url(url)
        if not is_http_url(url):
            return False
        if not self.can_fetch(url):
            return False
        return self.include_external or self.is_internal(url)
