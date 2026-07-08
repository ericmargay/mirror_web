from __future__ import annotations

from urllib.robotparser import RobotFileParser

from .url_utils import UrlTools


class ScopePolicy:
    """Decides whether URLs are inside the crawler/resource scope.

    Pattern: Policy Object. The crawler delegates scope decisions here instead of
    scattering domain checks across the codebase.
    """

    def __init__(self, start_url: str, include_external_assets: bool = False) -> None:
        self.start_url = UrlTools.normalize(start_url)
        self.start_domain = UrlTools.domain(self.start_url)
        self.include_external_assets = include_external_assets

    def can_visit_page(self, url: str) -> bool:
        """Pages are intentionally limited to the initial domain."""
        return UrlTools.is_http(url) and UrlTools.domain(url) == self.start_domain

    def can_save_asset(self, url: str) -> bool:
        """Assets may include external URLs when explicitly enabled."""
        if not UrlTools.is_http(url):
            return False
        return self.include_external_assets or UrlTools.domain(url) == self.start_domain


class RobotsPolicy:
    """robots.txt adapter.

    Pattern: Adapter. `urllib.robotparser` has a low-level API; this class exposes
    the single decision the rest of the app needs.
    """

    def __init__(self, start_url: str, user_agent: str, enabled: bool = True) -> None:
        self.enabled = enabled
        self.user_agent = user_agent
        self.parser: RobotFileParser | None = None

        if not enabled:
            return

        robots_url = f"{UrlTools.origin(start_url)}/robots.txt"
        parser = RobotFileParser()

        try:
            parser.set_url(robots_url)
            parser.read()
            self.parser = parser
        except Exception:
            self.parser = None

    def can_fetch(self, url: str) -> bool:
        if not self.enabled or self.parser is None:
            return True

        try:
            return self.parser.can_fetch(self.user_agent, url)
        except Exception:
            return True
