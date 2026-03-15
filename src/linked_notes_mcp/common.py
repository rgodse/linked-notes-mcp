"""Shared helpers for small, reusable linked-notes behaviors."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_json_file(path: Path, default: Any) -> Any:
    """Load JSON content from disk, returning a default on missing/invalid files."""

    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def save_json_file(path: Path, data: Any, *, sort_keys: bool = False) -> None:
    """Persist JSON content with stable formatting."""

    path.write_text(
        json.dumps(data, indent=2, sort_keys=sort_keys),
        encoding="utf-8",
    )


def infer_entity_type(text: str, explicit_entity_type: str | None = None) -> str:
    """Infer a compact memory-node type from text, unless explicitly provided."""

    if explicit_entity_type:
        return explicit_entity_type

    lowered = text.lower()
    if "decision" in lowered or "decided" in lowered:
        return "decision"
    if "meeting" in lowered or "attendees" in lowered:
        return "meeting"
    if "research" in lowered or "findings" in lowered or "finding" in lowered:
        return "research"
    if "stakeholder" in lowered or "owner" in lowered:
        return "stakeholder"
    if "service" in lowered or "api" in lowered:
        return "service"
    if "issue" in lowered or "blocker" in lowered or "bug" in lowered:
        return "issue"
    if "workstream" in lowered or "process" in lowered:
        return "workstream"
    return "project"


def normalize_space(text: str) -> str:
    """Collapse repeated whitespace for compact summaries/snippets."""

    return re.sub(r"\s+", " ", text).strip()


def infer_summary(text: str, explicit_summary: str | None = None, max_chars: int = 160) -> str:
    """Build a short one-line summary unless explicitly provided."""

    if explicit_summary:
        return explicit_summary

    compact = normalize_space(text)
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def candidate_recommendation_label(candidate: dict[str, Any]) -> str:
    """Map a dedupe strategy to the compact review recommendation label."""

    strategy = (candidate.get("dedupe", {}) or {}).get("strategy", "new")
    if strategy == "duplicate":
        return "merge_likely"
    if strategy == "merge_into_existing":
        return "ambiguous"
    return "create_new"
