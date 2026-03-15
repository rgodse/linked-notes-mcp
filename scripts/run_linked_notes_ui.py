#!/usr/bin/env python3
# ruff: noqa: I001
"""Launch linked-notes-ui from a local clone without relying on editable installs."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


if __name__ == "__main__":
    from linked_notes_mcp.visualizer import main

    main()
