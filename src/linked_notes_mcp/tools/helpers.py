"""Shared utility functions used across tool modules."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..common import load_json_file, save_json_file
from ..graph import KnowledgeGraph, Note

if TYPE_CHECKING:
    pass


def format_note_brief(note: Note) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "aliases": note.aliases,
        "tags": note.tags,
        "path": str(note.path),
        "entity_type": note.frontmatter.get("entity_type"),
        "project": note.frontmatter.get("project"),
        "status": note.frontmatter.get("status"),
        "summary": note.frontmatter.get("summary"),
    }


def format_note_full(note: Note) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "aliases": note.aliases,
        "tags": note.tags,
        "path": str(note.path),
        "frontmatter": note.frontmatter,
        "content": note.content,
        "outgoing_links": [
            {"target": link.target, "display": link.display_text, "type": link.link_type}
            for link in note.outgoing_links
        ],
        "explicit_relationships": [
            {
                "target": relationship.target,
                "type": relationship.relation_type,
                "source_field": relationship.source_field,
            }
            for relationship in note.explicit_relationships
        ],
    }


def _template_guidance(note: Note | None = None) -> str:
    if note is None:
        return (
            "Prefer `create_from_template(...)` for new notes. Start with `list_templates()` "
            "and choose a shape like `repo_project`, `service`, `issue`, `decision`, or `session`."
        )

    if not note.frontmatter.get("entity_type") or not note.frontmatter.get("summary"):
        return (
            "This note was created free-form. For stronger retrieval and graph maintenance, "
            "prefer `create_from_template(...)` for new notes or refine this one with "
            "`upsert_memory_node(...)` so it has structured frontmatter like "
            "`entity_type` and `summary`."
        )

    return (
        "This note already has structured frontmatter. For future notes, prefer "
        "`create_from_template(...)` so new memory starts in a consistent shape."
    )


def _extract_excerpt(note: Note, query: str, max_chars: int = 175) -> str:
    body = note.body
    if not body:
        return ""
    idx = body.lower().find(query.lower())
    if idx == -1:
        raw = body[:max_chars]
        excerpt = raw.strip()
        if len(raw) == max_chars:
            excerpt += "..."
        return excerpt
    half = max_chars // 2
    start = max(0, idx - half)
    end = min(len(body), start + max_chars)
    start = max(0, end - max_chars)
    raw = body[start:end].strip()
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(body) else ""
    return prefix + raw + suffix


def _followups_path(graph: KnowledgeGraph) -> Path:
    return Path(graph.vault_path) / ".linked_notes_followups.json"


def _load_followups(graph: KnowledgeGraph) -> list[dict]:
    return load_json_file(_followups_path(graph), [])


def _save_followups(graph: KnowledgeGraph, followups: list[dict]) -> None:
    save_json_file(_followups_path(graph), followups)


def _recent_session_notes(
    graph: KnowledgeGraph,
    project: str | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    project_tag = f"project-{project.lower()}" if project else None
    candidates = []
    for note in graph.list_all_notes():
        if "session" not in note.tags:
            continue
        if project_tag and project_tag not in note.tags:
            continue
        candidates.append(note)

    candidates.sort(
        key=lambda item: (
            str(item.frontmatter.get("modified") or item.frontmatter.get("created") or ""),
            item.title,
        ),
        reverse=True,
    )
    return [format_note_brief(note) for note in candidates[:limit]]


def _touched_note_summaries(
    graph: KnowledgeGraph,
    touched_notes: list[str],
) -> list[dict[str, Any]]:
    resolved = []
    for identifier in touched_notes:
        note = graph.get_note(identifier)
        if note is None:
            resolved.append({"identifier": identifier, "error": "Note not found"})
            continue
        resolved.append(format_note_brief(note))
    return resolved


def _session_next_steps(
    context_notes: list[dict[str, Any]],
    followups: list[dict[str, Any]],
    stale_notes: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
) -> list[str]:
    steps: list[str] = []
    if context_notes:
        steps.append(f"Start from `{context_notes[0]['title']}` as the current anchor note")
    if followups:
        steps.append(f"Review {len(followups)} followup item(s) before making new changes")
    if stale_notes:
        steps.append(f"Refresh {len(stale_notes)} stale note(s) if they are still active")
    if recent_sessions:
        steps.append("Scan the most recent session summary to recover in-flight context quickly")
    return steps[:4]
