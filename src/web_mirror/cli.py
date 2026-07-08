from __future__ import annotations

import argparse
from pathlib import Path

from .browser import save_auth_state
from .config import MirrorConfig
from .crawler import MirrorCrawler
from .url_utils import UrlTools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="web-mirror",
        description="Authorized static website mirror built with Playwright.",
    )

    parser.add_argument("url", help="Initial URL. Example: https://example.com")
    parser.add_argument("-o", "--output", default="mirror", help="Output directory")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=30,
        help="Maximum number of internal pages to crawl. Use 0 for unlimited.",
    )
    parser.add_argument(
        "--include-external",
        action="store_true",
        help="Save external assets from CDNs, font providers, image hosts, etc.",
    )
    parser.add_argument(
        "--no-robots",
        action="store_true",
        help="Disable robots.txt checks. Use only for sites you own/control.",
    )
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between page visits")
    parser.add_argument("--timeout-ms", type=int, default=45_000, help="Page timeout in ms")
    parser.add_argument("--max-asset-mb", type=int, default=80, help="Max size per asset")
    parser.add_argument("--auth", default=None, help="Path to a Playwright auth state JSON")
    parser.add_argument("--headed", action="store_true", help="Run Chromium in visible mode")
    parser.add_argument(
        "--save-auth",
        default=None,
        help="Open a visible browser, sign in manually, and save auth state to this JSON file.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()
    normalized_url = UrlTools.normalize(args.url)

    if args.save_auth:
        save_auth_state(normalized_url, Path(args.save_auth))
        return

    config = MirrorConfig(
        start_url=normalized_url,
        output_dir=Path(args.output),
        max_pages=None if args.max_pages == 0 else args.max_pages,
        include_external_assets=args.include_external,
        respect_robots=not args.no_robots,
        delay_seconds=args.delay,
        timeout_ms=args.timeout_ms,
        max_asset_mb=args.max_asset_mb,
        auth_state=Path(args.auth) if args.auth else None,
        headed=args.headed,
    )

    MirrorCrawler(config).run()
