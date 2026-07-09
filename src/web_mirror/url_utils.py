from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse


def clean_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if not urlparse(url).scheme:
        url = "https://" + url
    url, _ = urldefrag(url)
    return url


def absolute_url(base_url: str, value: str) -> str:
    return clean_url(urljoin(base_url, value))


def is_http_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}


def origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def domain(url: str) -> str:
    return urlparse(url).netloc


def safe_path_part(text: str, max_len: int = 120) -> str:
    text = text.strip()
    text = re.sub(r"[^a-zA-Z0-9._-]+", "_", text)
    return text[:max_len] or "file"


def relative_path(target: Path, source: Path) -> str:
    return os.path.relpath(target, source.parent).replace("\\", "/")


def should_skip_scheme(value: str) -> bool:
    value = (value or "").strip().lower()
    return value.startswith(("data:", "blob:", "javascript:", "mailto:", "tel:", "#"))
