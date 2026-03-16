"""Shared utility functions used across tool modules."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..common import (
    candidate_recommendation_label,
    infer_entity_type,
    infer_summary,
    load_json_file,
    save_json_file,
)
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


def _reviews_path(graph: KnowledgeGraph) -> Path:
    return Path(graph.vault_path) / ".linked_notes_reviews.json"


def _load_reviews(graph: KnowledgeGraph) -> dict[str, dict]:
    return load_json_file(_reviews_path(graph), {})


def _save_reviews(graph: KnowledgeGraph, reviews: dict[str, dict]) -> None:
    save_json_file(_reviews_path(graph), reviews, sort_keys=True)


def _suggestion_key(source_id: str, target_id: str, suggested_type: str) -> str:
    return f"{source_id}|{target_id}|{suggested_type}"


def _review_confidence(review: dict, suggestion_score: int) -> float:
    accepted = int(review.get("accepted_count", 0))
    rejected = int(review.get("rejected_count", 0))
    base = min(0.95, 0.25 + suggestion_score * 0.08)
    adjustment = accepted * 0.07 - rejected * 0.08
    confidence = max(0.0, min(0.99, base + adjustment))
    return round(confidence, 2)


def _infer_entity_type(raw_text: str, explicit_entity_type: str | None) -> str:
    return infer_entity_type(raw_text, explicit_entity_type=explicit_entity_type)


def _infer_summary(raw_text: str, explicit_summary: str | None) -> str:
    return infer_summary(raw_text, explicit_summary=explicit_summary)


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


def _candidate_recommendation(candidate: dict[str, Any]) -> str:
    return candidate_recommendation_label(candidate)


def _candidate_reason(candidate: dict[str, Any]) -> str:
    dedupe = candidate.get("dedupe", {}) or {}
    strategy = dedupe.get("strategy", "new")
    reasons = dedupe.get("reasons", [])
    matched = dedupe.get("matched_note_id")
    if strategy == "duplicate" and matched:
        return f"clear title-level match to existing note `{matched}`"
    if strategy == "merge_into_existing" and matched:
        suffix = f" ({'; '.join(reasons)})" if reasons else ""
        return f"possible merge into `{matched}`{suffix}"
    entity_type = candidate.get("entity_type", "memory node")
    return f"new {entity_type} candidate from staged source"


def _format_review_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence = candidate.get("evidence", []) or []
    top_evidence = evidence[0] if evidence else {}
    return {
        "id": candidate.get("id"),
        "title": candidate.get("title"),
        "entity_type": candidate.get("entity_type"),
        "summary": candidate.get("summary"),
        "project": candidate.get("project"),
        "review_state": candidate.get("review_state"),
        "confidence": candidate.get("confidence"),
        "recommendation": _candidate_recommendation(candidate),
        "reason": _candidate_reason(candidate),
        "matched_note_id": (candidate.get("dedupe", {}) or {}).get("matched_note_id"),
        "relationships": candidate.get("relationships", []),
        "evidence_preview": top_evidence.get("snippet"),
        "source_ref": top_evidence.get("loc"),
        "created_at": candidate.get("created_at"),
    }


def _recommended_actions(
    weak_notes: list[dict[str, Any]],
    pending_suggestions: list[dict[str, Any]],
    pending_candidates: list[dict[str, Any]],
    stale_notes: list[dict[str, Any]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    for candidate in pending_candidates:
        recommendation = candidate.get("recommendation")
        score = (
            100 if recommendation == "merge_likely" else 85 if recommendation == "ambiguous" else 75
        )
        actions.append(
            {
                "kind": "ingestion_candidate",
                "priority": score,
                "title": candidate.get("title"),
                "action": recommendation,
                "reason": candidate.get("reason"),
                "candidate_id": candidate.get("id"),
            }
        )

    for note in weak_notes:
        score = max(0, 70 - int(note.get("score", 0)) * 5)
        actions.append(
            {
                "kind": "weak_note",
                "priority": score,
                "title": note.get("note_id"),
                "action": "improve_note",
                "reason": ", ".join(note.get("issues", [])[:2]),
                "note_id": note.get("note_id"),
            }
        )

    for suggestion in pending_suggestions:
        actions.append(
            {
                "kind": "relationship_suggestion",
                "priority": 65 + int(suggestion.get("score", 0)),
                "title": f"{suggestion.get('source_id')} -> {suggestion.get('target_id')}",
                "action": "review_relationship",
                "reason": "; ".join(suggestion.get("reasons", [])[:2]),
                "source_id": suggestion.get("source_id"),
                "target_id": suggestion.get("target_id"),
                "suggested_type": suggestion.get("suggested_type"),
            }
        )

    for note in stale_notes:
        actions.append(
            {
                "kind": "stale_note",
                "priority": 60,
                "title": note.get("title"),
                "action": "refresh_note",
                "reason": f"expired on {note.get('expires', '')}",
                "note_id": note.get("id"),
            }
        )

    actions.sort(key=lambda item: (-item["priority"], item["kind"], item["title"]))
    return actions[:limit]


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
