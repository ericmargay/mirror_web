from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from .url_utils import UrlTools

if TYPE_CHECKING:
    from .resources import ResourceManager
    from .storage import FileStore


CSS_URL_RE = re.compile(r'url\((["\']?)(.*?)\1\)', re.IGNORECASE)
CSS_IMPORT_RE = re.compile(r'@import\s+(?:url\()?(["\']?)([^"\')\s;]+)\1', re.IGNORECASE)

HTML_ASSET_ATTRIBUTES = {
    "img": ["src", "srcset", "data-src", "data-lazy-src"],
    "script": ["src"],
    "link": ["href"],
    "source": ["src", "srcset"],
    "video": ["src", "poster"],
    "audio": ["src"],
    "iframe": ["src"],
    "embed": ["src"],
    "object": ["data"],
    "track": ["src"],
}


class CssRewriter:
    """Rewrites CSS `url(...)` and `@import` references to local files."""

    def __init__(self, store: FileStore, resources: ResourceManager) -> None:
        self.store = store
        self.resources = resources

    def rewrite_file(self, css_path: Path, css_url: str) -> None:
        try:
            css = css_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        css = self.rewrite_text(css, base_url=css_url, source_path=css_path)
        css_path.write_text(css, encoding="utf-8", errors="ignore")

    def rewrite_text(self, css: str, *, base_url: str, source_path: Path) -> str:
        css = CSS_URL_RE.sub(lambda match: self._replace_css_url(match, base_url, source_path), css)
        css = CSS_IMPORT_RE.sub(
            lambda match: self._replace_css_import(match, base_url, source_path), css
        )
        return css

    def _replace_css_url(self, match: re.Match[str], base_url: str, source_path: Path) -> str:
        raw_url = match.group(2).strip()

        if not raw_url or raw_url.startswith(("data:", "blob:", "#")):
            return match.group(0)

        absolute_url = UrlTools.normalize(raw_url, base_url=base_url)
        local_path = self.resources.ensure_asset(absolute_url)

        if not local_path:
            return match.group(0)

        return f"url({self.store.relative_path(local_path, source_path)})"

    def _replace_css_import(self, match: re.Match[str], base_url: str, source_path: Path) -> str:
        raw_url = match.group(2).strip()

        if not raw_url or raw_url.startswith(("data:", "blob:", "#")):
            return match.group(0)

        absolute_url = UrlTools.normalize(raw_url, base_url=base_url)
        local_path = self.resources.ensure_asset(absolute_url)

        if not local_path:
            return match.group(0)

        return match.group(0).replace(raw_url, self.store.relative_path(local_path, source_path))


class HtmlRewriter:
    """Rewrites a rendered HTML document and returns internal links to crawl."""

    def __init__(self, store: FileStore, resources: ResourceManager) -> None:
        self.store = store
        self.resources = resources
        self.css_rewriter = CssRewriter(store, resources)

    def rewrite(self, html: str, page_url: str) -> tuple[str, list[str]]:
        page_path = self.store.path_for_url(page_url, content_type="text/html", force_html=True)
        soup = BeautifulSoup(html, "html.parser")

        self._rewrite_html_assets(soup, page_url, page_path)
        self._rewrite_inline_styles(soup, page_url, page_path)
        links_to_visit = self._rewrite_page_links(soup, page_url, page_path)

        return str(soup), links_to_visit

    def _rewrite_html_assets(self, soup: BeautifulSoup, page_url: str, page_path: Path) -> None:
        for tag_name, attributes in HTML_ASSET_ATTRIBUTES.items():
            for tag in soup.find_all(tag_name):
                for attribute in attributes:
                    value = tag.get(attribute)
                    if not value or UrlTools.is_ignored_scheme(value):
                        continue

                    if attribute == "srcset":
                        tag[attribute] = self._rewrite_srcset(value, page_url, page_path)
                        continue

                    absolute_url = UrlTools.normalize(value, base_url=page_url)
                    local_path = self.resources.ensure_asset(absolute_url)

                    if local_path:
                        tag[attribute] = self.store.relative_path(local_path, page_path)

    def _rewrite_srcset(self, srcset: str, page_url: str, page_path: Path) -> str:
        rewritten_items = []

        for item in srcset.split(","):
            parts = item.strip().split()
            if not parts:
                continue

            if UrlTools.is_ignored_scheme(parts[0]):
                rewritten_items.append(" ".join(parts))
                continue

            absolute_url = UrlTools.normalize(parts[0], base_url=page_url)
            local_path = self.resources.ensure_asset(absolute_url)

            if local_path:
                parts[0] = self.store.relative_path(local_path, page_path)

            rewritten_items.append(" ".join(parts))

        return ", ".join(rewritten_items)

    def _rewrite_inline_styles(self, soup: BeautifulSoup, page_url: str, page_path: Path) -> None:
        for tag in soup.find_all(style=True):
            tag["style"] = self.css_rewriter.rewrite_text(
                tag["style"],
                base_url=page_url,
                source_path=page_path,
            )

        for style_tag in soup.find_all("style"):
            if style_tag.string:
                style_tag.string.replace_with(
                    self.css_rewriter.rewrite_text(
                        style_tag.string,
                        base_url=page_url,
                        source_path=page_path,
                    )
                )

    def _rewrite_page_links(self, soup: BeautifulSoup, page_url: str, page_path: Path) -> list[str]:
        links_to_visit: list[str] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")

            if not href or href.startswith("#") or UrlTools.is_ignored_scheme(href):
                continue

            absolute_url = UrlTools.normalize(href, base_url=page_url)

            if self.resources.scope.can_visit_page(absolute_url):
                local_page_path = self.store.path_for_url(
                    absolute_url,
                    content_type="text/html",
                    force_html=True,
                )
                anchor["href"] = self.store.relative_path(local_page_path, page_path)
                links_to_visit.append(absolute_url)

        return links_to_visit
