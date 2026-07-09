from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

from .url_utils import clean_url, safe_path_part


class FileStorage:
    """Maps URLs to deterministic local file paths and writes files."""

    CONTENT_TYPE_EXTENSIONS = {
        "text/html": ".html",
        "text/css": ".css",
        "application/javascript": ".js",
        "text/javascript": ".js",
        "application/json": ".json",
        "image/svg+xml": ".svg",
        "font/woff2": ".woff2",
        "font/woff": ".woff",
        "model/gltf-binary": ".glb",
        "model/gltf+json": ".gltf",
    }

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.url_to_file: dict[str, Path] = {}

    def extension_from_content_type(self, content_type: str | None) -> str:
        if not content_type:
            return ""
        normalized = content_type.split(";", 1)[0].strip().lower()
        if normalized in self.CONTENT_TYPE_EXTENSIONS:
            return self.CONTENT_TYPE_EXTENSIONS[normalized]
        return mimetypes.guess_extension(normalized) or ""

    def path_for_url(self, url: str, content_type: str | None = None, force_html: bool = False) -> Path:
        url = clean_url(url)
        parsed = urlparse(url)

        host = safe_path_part(parsed.netloc)
        raw_path = parsed.path or "/"

        if raw_path.endswith("/"):
            raw_path += "index.html" if force_html else "index"

        parts = [safe_path_part(part) for part in raw_path.strip("/").split("/") if part]
        if not parts:
            parts = ["index.html" if force_html else "index"]

        filename = parts[-1]
        name, ext = os.path.splitext(filename)

        if force_html:
            if ext.lower() not in {".html", ".htm"}:
                filename = f"{filename}.html" if ext else "index.html"
        elif not ext:
            guessed = self.extension_from_content_type(content_type)
            if guessed:
                filename += guessed

        if parsed.query:
            query_hash = hashlib.md5(parsed.query.encode("utf-8")).hexdigest()[:10]
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{query_hash}{ext}"

        parts[-1] = filename
        return self.output_dir / host / Path(*parts)

    def remember(self, url: str, local_path: Path) -> None:
        self.url_to_file[clean_url(url)] = local_path

    def get(self, url: str) -> Path | None:
        return self.url_to_file.get(clean_url(url))

    def save_bytes(self, url: str, body: bytes, content_type: str | None = None, force_html: bool = False) -> Path:
        local_path = self.path_for_url(url, content_type=content_type, force_html=force_html)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(body)
        self.remember(url, local_path)
        return local_path

    def save_text(self, url: str, text: str, content_type: str = "text/html", force_html: bool = True) -> Path:
        local_path = self.path_for_url(url, content_type=content_type, force_html=force_html)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(text, encoding="utf-8", errors="ignore")
        self.remember(url, local_path)
        return local_path
