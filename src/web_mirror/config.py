from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MirrorConfig:
    """Runtime configuration for the crawler.

    max_pages=0 means unlimited internal pages. Use with care.
    """

    start_url: str
    output_dir: Path
    max_pages: int = 30
    include_external: bool = False
    respect_robots: bool = True
    delay_seconds: float = 0.5
    timeout_ms: int = 45_000
    max_asset_mb: int = 80
    auth_state: str | None = None
    headed: bool = False

    @property
    def max_asset_bytes(self) -> int:
        return self.max_asset_mb * 1024 * 1024
