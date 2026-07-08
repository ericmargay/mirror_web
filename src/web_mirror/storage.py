from __future__ import annotations

import hashlib
import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from .url_utils import UrlTools


class FileStore:
    """Maps remote URLs to local filesystem paths and persists content.

    Pattern: Repository. The rest of the app does not care how paths are built
    or where files are written; it asks this class to save/read resources.
    """

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
        self.output_dir = Path(output_dir)
        self.url_to_path: dict[str, Path] = {}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def has(self, url: str) -> bool:
        return UrlTools.normalize(url) in self.url_to_path

    def get(self, url: str) -> Path | None:
        return self.url_to_path.get(UrlTools.normalize(url))

    def save_bytes(
        self,
        url: str,
        content: bytes,
        *,
        content_type: str | None = None,
        force_html: bool = False,
    ) -> Path:
        local_path = self.path_for_url(url, content_type=content_type, force_html=force_html)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        self.url_to_path[UrlTools.normalize(url)] = local_path
        return local_path

    def save_text(
        self,
        url: str,
        content: str,
        *,
        content_type: str = "text/html",
        force_html: bool = True,
    ) -> Path:
        local_path = self.path_for_url(url, content_type=content_type, force_html=force_html)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding="utf-8", errors="ignore")
        self.url_to_path[UrlTools.normalize(url)] = local_path
        return local_path

    def path_for_url(
        self,
        url: str,
        *,
        content_type: str | None = None,
        force_html: bool = False,
    ) -> Path:
        normalized = UrlTools.normalize(url)
        parsed = urlparse(normalized)

        domain = self._safe_part(parsed.netloc)
        url_path = parsed.path or "/"

        if url_path.endswith("/"):
            url_path += "index.html" if force_html else "index"

        parts = [self._safe_part(part) for part in url_path.strip("/").split("/") if part]
        if not parts:
            parts = ["index.html" if force_html else "index"]

        if force_html:
            name, extension = os.path.splitext(parts[-1])
            if not extension:
                # `/about` becomes `/about/index.html` instead of colliding with `/index.html`.
                parts.append("index.html")
            elif extension.lower() not in {".html", ".htm"}:
                parts[-1] = f"{parts[-1]}.html"
        else:
            parts[-1] = self._ensure_extension(
                parts[-1],
                content_type=content_type,
                force_html=False,
            )

        if parsed.query:
            query_hash = hashlib.md5(parsed.query.encode("utf-8")).hexdigest()[:10]
            name, extension = os.path.splitext(parts[-1])
            parts[-1] = f"{name}_{query_hash}{extension}"

        return self.output_dir / domain / Path(*parts)

    def relative_path(self, target_path: Path, source_path: Path) -> str:
        return os.path.relpath(target_path, source_path.parent).replace("\\", "/")

    def _ensure_extension(
        self,
        filename: str,
        *,
        content_type: str | None,
        force_html: bool,
    ) -> str:
        name, extension = os.path.splitext(filename)

        if force_html:
            if extension.lower() not in {".html", ".htm"}:
                return f"{filename}.html" if extension else "index.html"
            return filename

        if extension:
            return filename

        guessed_extension = self._extension_from_content_type(content_type)
        return filename + guessed_extension if guessed_extension else filename

    def _extension_from_content_type(self, content_type: str | None) -> str:
        if not content_type:
            return ""

        clean_content_type = content_type.split(";")[0].strip().lower()
        if clean_content_type in self.CONTENT_TYPE_EXTENSIONS:
            return self.CONTENT_TYPE_EXTENSIONS[clean_content_type]

        return mimetypes.guess_extension(clean_content_type) or ""

    def _safe_part(self, text: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", text.strip())
        return safe[:120] or "file"
