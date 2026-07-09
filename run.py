"""Run Web Mirror Pro directly from the repository root.

This file lets you use the project without installing it as a package:

    python.exe run.py https://example.com -o mirror --max-pages 50

It adds ./src to sys.path and delegates execution to web_mirror.cli.main().
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from web_mirror.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
