"""Graph health and maintenance tools."""

import json
from typing import Callable

from mcp.types import Tool

from ..common import infer_entity_type, infer_summary
from ..graph import KnowledgeGraph
from .helpers import format_note_full


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


def _handle_promote_to_memory_node(args: dict, graph: KnowledgeGraph) -> str:
    entity_type = infer_entity_type(args["raw_text"], explicit_entity_type=args.get("entity_type"))
    summary = infer_summary(args["raw_text"], explicit_summary=args.get("summary"))
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


HANDLERS: dict[str, Callable[[dict, KnowledgeGraph], str]] = {
    "lint_memory_graph": _handle_lint_memory_graph,
    "suggest_relationships": _handle_suggest_relationships,
    "merge_memory_nodes": _handle_merge_memory_nodes,
    "promote_to_memory_node": _handle_promote_to_memory_node,
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
]
