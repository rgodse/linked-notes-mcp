"""Pytest configuration."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# Add project root for evals and optimize modules
sys.path.insert(0, str(Path(__file__).parent.parent))
