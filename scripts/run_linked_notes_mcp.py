#!/usr/bin/env python3
"""Launch linked-notes-mcp from a local clone without relying on editable installs."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from linked_notes_mcp.server import main


if __name__ == "__main__":
    main()
