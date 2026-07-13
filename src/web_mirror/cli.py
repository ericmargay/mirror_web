from __future__ import annotations

import argparse
from pathlib import Path

from .browser import save_auth_state
from .config import MirrorConfig
from .crawler import MirrorCrawler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="web-mirror",
        description="Authorized static website mirroring tool powered by Playwright.",
    )
    parser.add_argument("url", help="Initial URL. Example: https://example.com")
    parser.add_argument("-o", "--output", default="mirror", help="Output folder")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=30,
        help="Maximum number of internal pages to visit. Use 0 for unlimited.",
    )
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Do NOT save assets from CDNs/third-party domains (external assets are saved by default; page crawling always stays internal).",
    )
    parser.add_argument(
        "--include-external",
        action="store_true",
        help=argparse.SUPPRESS,  # deprecated: external assets are now the default
    )
    parser.add_argument(
        "--no-best-images",
        action="store_true",
        help="Skip downloading the largest srcset variant of each image.",
    )
    parser.add_argument("--no-robots", action="store_true", help="Disable robots.txt checks")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between pages in seconds")
    parser.add_argument("--timeout-ms", type=int, default=45_000, help="Page load timeout in milliseconds")
    parser.add_argument("--max-asset-mb", type=int, default=80, help="Maximum size per asset in MB")
    parser.add_argument("--auth", default=None, help="Use a Playwright storage_state JSON file")
    parser.add_argument("--headed", action="store_true", help="Show the browser while crawling")
    parser.add_argument("--save-auth", default=None, help="Open browser and save session to this JSON file")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.save_auth:
        save_auth_state(args.url, args.save_auth)
        return

    config = MirrorConfig(
        start_url=args.url,
        output_dir=Path(args.output),
        max_pages=args.max_pages,
        include_external=not args.internal_only,
        respect_robots=not args.no_robots,
        delay_seconds=args.delay,
        timeout_ms=args.timeout_ms,
        max_asset_mb=args.max_asset_mb,
        auth_state=args.auth,
        headed=args.headed,
        fetch_best_images=not args.no_best_images,
    )

    crawler = MirrorCrawler(config)
    crawler.crawl()


if __name__ == "__main__":
    main()
