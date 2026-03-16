"""Graph health and relationship review tools (9 tools)."""

import json
from datetime import datetime
from typing import Callable

from mcp.types import Tool

from ..graph import KnowledgeGraph
from .helpers import (
    _infer_entity_type,
    _infer_summary,
    _load_reviews,
    _review_confidence,
    _save_reviews,
    _suggestion_key,
    format_note_full,
)


def _handle_lint_memory_graph(args: dict, graph: KnowledgeGraph) -> str:
    issues = graph.lint_graph()
    return json.dumps(
        [
            {
                "note_id": issue.note_id,
                "severity": issue.severity,
                "issue_type": issue.issue_type,
                "message": issue.message,
            }
            for issue in issues
        ],
        indent=2,
    )


def _handle_suggest_relationships(args: dict, graph: KnowledgeGraph) -> str:
    suggestions = graph.suggest_relationships(args.get("limit", 20))
    return json.dumps(
        [
            {
                "source_id": suggestion.source_id,
                "target_id": suggestion.target_id,
                "suggested_type": suggestion.suggested_type,
                "score": suggestion.score,
                "reasons": suggestion.reasons,
            }
            for suggestion in suggestions
        ],
        indent=2,
    )


def _handle_merge_memory_nodes(args: dict, graph: KnowledgeGraph) -> str:
    try:
        note = graph.merge_memory_nodes(
            source_identifier=args["source_identifier"],
            target_identifier=args["target_identifier"],
            archive_source=args.get("archive_source", True),
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Merged into: {note.title}",
                "note": format_note_full(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_get_memory_health(args: dict, graph: KnowledgeGraph) -> str:
    identifier = args.get("identifier")
    if identifier:
        health = graph.get_note_health(identifier)
        if health is None:
            return json.dumps({"error": f"Note not found: {identifier}"})
        return json.dumps(
            {
                "note_id": health.note_id,
                "score": health.score,
                "max_score": health.max_score,
                "issues": health.issues,
            },
            indent=2,
        )
    health_items = graph.get_graph_health(args.get("limit", 50))
    return json.dumps(
        [
            {
                "note_id": item.note_id,
                "score": item.score,
                "max_score": item.max_score,
                "issues": item.issues,
            }
            for item in health_items
        ],
        indent=2,
    )


def _handle_promote_to_memory_node(args: dict, graph: KnowledgeGraph) -> str:
    entity_type = _infer_entity_type(args["raw_text"], args.get("entity_type"))
    summary = _infer_summary(args["raw_text"], args.get("summary"))
    note = graph.upsert_memory_node(
        title=args["title"],
        summary=summary,
        entity_type=entity_type,
        project=args.get("project"),
        status=args.get("status"),
        aliases=args.get("aliases"),
        tags=args.get("tags"),
        relationships=args.get("relationships"),
        body=args["raw_text"],
    )
    return json.dumps(
        {
            "status": "success",
            "message": f"Promoted to memory node: {note.title}",
            "note": format_note_full(note),
        },
        indent=2,
    )


def _handle_review_relationship_suggestions(args: dict, graph: KnowledgeGraph) -> str:
    state = args.get("state", "pending")
    suggestions = graph.suggest_relationships(args.get("limit", 20))
    reviews = _load_reviews(graph)
    result = []
    for suggestion in suggestions:
        key = _suggestion_key(
            suggestion.source_id,
            suggestion.target_id,
            suggestion.suggested_type,
        )
        review = reviews.get(key, {"state": "pending"})
        if state != "all" and review.get("state", "pending") != state:
            continue
        confidence = _review_confidence(review, suggestion.score)
        result.append(
            {
                "source_id": suggestion.source_id,
                "target_id": suggestion.target_id,
                "suggested_type": suggestion.suggested_type,
                "score": suggestion.score,
                "confidence": confidence,
                "reasons": suggestion.reasons,
                "review": review,
            }
        )
    return json.dumps(result, indent=2)


def _handle_accept_relationship_suggestion(args: dict, graph: KnowledgeGraph) -> str:
    source_id = args["source_id"]
    target_id = args["target_id"]
    suggested_type = args["suggested_type"]
    note = graph.update_relationships(
        identifier=source_id,
        add=[{"type": suggested_type, "target": target_id}],
    )
    reviews = _load_reviews(graph)
    key = _suggestion_key(source_id, target_id, suggested_type)
    prior = reviews.get(key, {})
    reviews[key] = {
        "state": "accepted",
        "accepted_count": int(prior.get("accepted_count", 0)) + 1,
        "rejected_count": int(prior.get("rejected_count", 0)),
        "updated_at": datetime.now().isoformat(),
    }
    _save_reviews(graph, reviews)
    return json.dumps(
        {
            "status": "success",
            "message": f"Accepted relationship suggestion for {source_id} -> {target_id}",
            "note": format_note_full(note),
        },
        indent=2,
    )


def _handle_reject_relationship_suggestion(args: dict, graph: KnowledgeGraph) -> str:
    source_id = args["source_id"]
    target_id = args["target_id"]
    suggested_type = args["suggested_type"]
    reviews = _load_reviews(graph)
    key = _suggestion_key(source_id, target_id, suggested_type)
    prior = reviews.get(key, {})
    reviews[key] = {
        "state": "rejected",
        "accepted_count": int(prior.get("accepted_count", 0)),
        "rejected_count": int(prior.get("rejected_count", 0)) + 1,
        "reason": args.get("reason"),
        "updated_at": datetime.now().isoformat(),
    }
    _save_reviews(graph, reviews)
    return json.dumps(
        {
            "status": "success",
            "message": f"Rejected relationship suggestion for {source_id} -> {target_id}",
            "review": reviews[key],
        },
        indent=2,
    )


def _handle_memory_dashboard(args: dict, graph: KnowledgeGraph) -> str:
    health_limit = args.get("health_limit", 10)
    suggestion_limit = args.get("suggestion_limit", 10)
    stale_limit = args.get("stale_limit", 10)
    stats = graph.get_stats()
    health_items = graph.get_graph_health(health_limit)
    stale_notes = graph.list_stale_notes()[:stale_limit]
    reviews = _load_reviews(graph)
    suggestions = graph.suggest_relationships(suggestion_limit)
    pending_suggestions = []
    for suggestion in suggestions:
        key = _suggestion_key(
            suggestion.source_id,
            suggestion.target_id,
            suggestion.suggested_type,
        )
        review = reviews.get(key, {"state": "pending"})
        if review.get("state", "pending") != "pending":
            continue
        pending_suggestions.append(
            {
                "source_id": suggestion.source_id,
                "target_id": suggestion.target_id,
                "suggested_type": suggestion.suggested_type,
                "score": suggestion.score,
                "confidence": _review_confidence(review, suggestion.score),
                "reasons": suggestion.reasons,
            }
        )
    return json.dumps(
        {
            "summary": {
                "total_notes": stats.total_notes,
                "total_links": stats.total_links,
                "total_relationships": stats.total_relationships,
                "orphan_notes": stats.orphan_notes,
                "pending_suggestions": len(pending_suggestions),
                "reviewed_suggestions": len(reviews),
                "stale_notes": len(graph.list_stale_notes()),
            },
            "weak_notes": [
                {
                    "note_id": item.note_id,
                    "score": item.score,
                    "max_score": item.max_score,
                    "issues": item.issues,
                }
                for item in health_items
            ],
            "pending_suggestions": pending_suggestions,
            "stale_notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "expires": str(note.frontmatter.get("expires", "")),
                }
                for note in stale_notes
            ],
        },
        indent=2,
    )


HANDLERS: dict[str, Callable[[dict, KnowledgeGraph], str]] = {
    "lint_memory_graph": _handle_lint_memory_graph,
    "suggest_relationships": _handle_suggest_relationships,
    "merge_memory_nodes": _handle_merge_memory_nodes,
    "get_memory_health": _handle_get_memory_health,
    "promote_to_memory_node": _handle_promote_to_memory_node,
    "review_relationship_suggestions": _handle_review_relationship_suggestions,
    "accept_relationship_suggestion": _handle_accept_relationship_suggestion,
    "reject_relationship_suggestion": _handle_reject_relationship_suggestion,
    "memory_dashboard": _handle_memory_dashboard,
}

TOOL_DEFS: list[Tool] = [
    Tool(
        name="lint_memory_graph",
        description="Analyze the vault for weak memory nodes such as missing entity_type, missing summary, orphan notes, and missing confidence or review metadata.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="suggest_relationships",
        description="Suggest likely graph relationships based on shared tags, project membership, and summary overlap.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum number of suggestions to return",
                }
            },
        },
    ),
    Tool(
        name="merge_memory_nodes",
        description="Merge one memory node into another, preserving aliases and relationships and optionally archiving the source node.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_identifier": {"type": "string", "description": "Source note ID or title"},
                "target_identifier": {"type": "string", "description": "Target note ID or title"},
                "archive_source": {
                    "type": "boolean",
                    "default": True,
                    "description": "Archive the source note instead of deleting it",
                },
            },
            "required": ["source_identifier", "target_identifier"],
        },
    ),
    Tool(
        name="get_memory_health",
        description="Score memory-node health based on structure, connectivity, and freshness metadata so the agent can improve weak notes.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Optional note ID or title"},
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "description": "Maximum nodes to return when listing graph health",
                },
            },
        },
    ),
    Tool(
        name="promote_to_memory_node",
        description="Turn loosely structured work output into a structured memory node with agent-first frontmatter.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Canonical title for the memory node"},
                "raw_text": {
                    "type": "string",
                    "description": "Loose content to convert into structured memory",
                },
                "entity_type": {
                    "type": "string",
                    "description": "Optional explicit type like project, workstream, stakeholder, research, decision, service, or issue",
                },
                "project": {
                    "type": "string",
                    "description": "Optional project or workstream grouping",
                },
                "status": {"type": "string", "description": "Optional status"},
                "aliases": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string", "description": "Optional explicit summary override"},
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"type": {"type": "string"}, "target": {"type": "string"}},
                        "required": ["type", "target"],
                    },
                },
            },
            "required": ["title", "raw_text"],
        },
    ),
    Tool(
        name="review_relationship_suggestions",
        description="List relationship suggestions together with their review state so the agent can process them systematically.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum suggestions to return",
                },
                "state": {
                    "type": "string",
                    "enum": ["pending", "accepted", "rejected", "all"],
                    "default": "pending",
                    "description": "Filter suggestions by review state",
                },
            },
        },
    ),
    Tool(
        name="accept_relationship_suggestion",
        description="Accept a suggested relationship and apply it to the graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_id": {"type": "string"},
                "target_id": {"type": "string"},
                "suggested_type": {"type": "string"},
            },
            "required": ["source_id", "target_id", "suggested_type"],
        },
    ),
    Tool(
        name="reject_relationship_suggestion",
        description="Reject a suggested relationship and record that decision so it does not keep resurfacing as pending.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_id": {"type": "string"},
                "target_id": {"type": "string"},
                "suggested_type": {"type": "string"},
                "reason": {"type": "string", "description": "Optional rejection reason"},
            },
            "required": ["source_id", "target_id", "suggested_type"],
        },
    ),
    Tool(
        name="memory_dashboard",
        description="Return a compact operational dashboard for the memory graph: weak notes, pending suggestions, stale notes, and summary counts.",
        inputSchema={
            "type": "object",
            "properties": {
                "health_limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum weak notes to return",
                },
                "suggestion_limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum suggestions to return",
                },
                "stale_limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum stale notes to return",
                },
            },
        },
    ),
]
