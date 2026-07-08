from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MirrorConfig:
    """Runtime configuration for the mirror process."""

    start_url: str
    output_dir: Path = Path("mirror")
    max_pages: int | None = 30
    include_external_assets: bool = False
    respect_robots: bool = True
    delay_seconds: float = 0.5
    timeout_ms: int = 45_000
    max_asset_mb: int = 80
    auth_state: Path | None = None
    headed: bool = False
    user_agent: str = "AuthorizedStaticMirror/1.0"

    @property
    def max_asset_bytes(self) -> int:
        return self.max_asset_mb * 1024 * 1024

    @property
    def unlimited_pages(self) -> bool:
        return self.max_pages is None
