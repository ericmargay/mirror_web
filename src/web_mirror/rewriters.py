from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .resources import ResourceDownloader
from .storage import FileStorage
from .url_utils import absolute_url, clean_url, is_http_url, relative_path, should_skip_scheme

CSS_URL_RE = re.compile(r'url\((["\']?)(.*?)\1\)', re.IGNORECASE)
CSS_IMPORT_RE = re.compile(r'@import\s+(?:url\()?(["\']?)([^"\')\s;]+)\1', re.IGNORECASE)

HTML_ASSET_ATTRS: dict[str, list[str]] = {
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
    """Rewrites CSS url(...) and @import references to local files."""

    def __init__(self, storage: FileStorage, downloader: ResourceDownloader) -> None:
        self.storage = storage
        self.downloader = downloader

    def rewrite_file(self, css_file: Path, css_url: str) -> None:
        try:
            css_text = css_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        rewritten = self.rewrite_text(css_text, base_url=css_url, source_file=css_file)
        css_file.write_text(rewritten, encoding="utf-8", errors="ignore")

    def rewrite_text(self, css_text: str, base_url: str, source_file: Path) -> str:
        def replace_css_url(match: re.Match[str]) -> str:
            raw = match.group(2).strip()
            if not raw or should_skip_scheme(raw):
                return match.group(0)

            asset_url = absolute_url(base_url, raw)
            local = self.storage.get(asset_url) or self.downloader.fetch_if_missing(asset_url)
            if not local:
                return match.group(0)

            return f"url({relative_path(local, source_file)})"

        css_text = CSS_URL_RE.sub(replace_css_url, css_text)

        def replace_import(match: re.Match[str]) -> str:
            raw = match.group(2).strip()
            if not raw or should_skip_scheme(raw):
                return match.group(0)

            asset_url = absolute_url(base_url, raw)
            local = self.storage.get(asset_url) or self.downloader.fetch_if_missing(asset_url)
            if not local:
                return match.group(0)

            return match.group(0).replace(raw, relative_path(local, source_file))

        return CSS_IMPORT_RE.sub(replace_import, css_text)


class HtmlRewriter:
    """Rewrites an HTML document so saved assets/pages point to local paths."""

    def __init__(self, storage: FileStorage, downloader: ResourceDownloader, css_rewriter: CssRewriter) -> None:
        self.storage = storage
        self.downloader = downloader
        self.css_rewriter = css_rewriter

    def rewrite_srcset(self, value: str, base_url: str, page_file: Path) -> str:
        items: list[str] = []
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue

            parts = item.split()
            if not parts or should_skip_scheme(parts[0]):
                items.append(item)
                continue

            asset_url = absolute_url(base_url, parts[0])
            local = self.storage.get(asset_url) or self.downloader.fetch_if_missing(asset_url)
            if local:
                parts[0] = relative_path(local, page_file)
            items.append(" ".join(parts))
        return ", ".join(items)

    def rewrite_asset_attr(self, tag, attr: str, page_url: str, page_file: Path) -> None:
        value = tag.get(attr)
        if not value or should_skip_scheme(value):
            return

        if attr == "srcset":
            tag[attr] = self.rewrite_srcset(value, page_url, page_file)
            return

        asset_url = absolute_url(page_url, value)
        local = self.storage.get(asset_url) or self.downloader.fetch_if_missing(asset_url)
        if local:
            tag[attr] = relative_path(local, page_file)

    def rewrite_html(self, html: str, page_url: str) -> tuple[str, list[str]]:
        page_url = clean_url(page_url)
        page_file = self.storage.path_for_url(page_url, content_type="text/html", force_html=True)
        soup = BeautifulSoup(html, "html.parser")
        links_to_visit: list[str] = []

        for tag_name, attrs in HTML_ASSET_ATTRS.items():
            for tag in soup.find_all(tag_name):
                for attr in attrs:
                    self.rewrite_asset_attr(tag, attr, page_url, page_file)

        for tag in soup.find_all(style=True):
            tag["style"] = self.css_rewriter.rewrite_text(tag["style"], page_url, page_file)

        for style_tag in soup.find_all("style"):
            text = style_tag.string
            if text:
                style_tag.string.replace_with(self.css_rewriter.rewrite_text(text, page_url, page_file))

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if should_skip_scheme(href):
                continue

            link_url = clean_url(urljoin(page_url, href))
            if not is_http_url(link_url):
                continue

            # The crawler decides later if this page is visitable. Here we only
            # point same-domain pages to the location where they would be saved.
            local_page = self.storage.path_for_url(link_url, content_type="text/html", force_html=True)
            a["href"] = relative_path(local_page, page_file)
            links_to_visit.append(link_url)

        return str(soup), links_to_visit
