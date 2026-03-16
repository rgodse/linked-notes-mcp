"""Note CRUD and memory node tools (6 tools)."""

import json
from typing import Callable

from mcp.types import Tool

from ..graph import KnowledgeGraph
from .helpers import format_note_brief, format_note_full, _template_guidance


def _handle_create_note(args: dict, graph: KnowledgeGraph) -> str:
    try:
        note = graph.create_note(
            title=args["title"],
            content=args["content"],
            tags=args.get("tags"),
            filename=args.get("filename"),
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Created note: {note.title}",
                "note": format_note_brief(note),
                "guidance": _template_guidance(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_update_note(args: dict, graph: KnowledgeGraph) -> str:
    try:
        note = graph.update_note(
            identifier=args["identifier"],
            content=args.get("content"),
            title=args.get("title"),
            tags=args.get("tags"),
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Updated note: {note.title}",
                "note": format_note_brief(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_append_to_note(args: dict, graph: KnowledgeGraph) -> str:
    try:
        note = graph.append_to_note(
            identifier=args["identifier"], content=args["content"]
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Appended to note: {note.title}",
                "note": format_note_brief(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_delete_note(args: dict, graph: KnowledgeGraph) -> str:
    deleted = graph.delete_note(args["identifier"])
    if deleted:
        return json.dumps(
            {"status": "success", "message": f"Deleted note: {args['identifier']}"}
        )
    else:
        return json.dumps({"error": f"Note not found: {args['identifier']}"})


def _handle_upsert_memory_node(args: dict, graph: KnowledgeGraph) -> str:
    try:
        note = graph.upsert_memory_node(
            title=args["title"],
            summary=args["summary"],
            entity_type=args["entity_type"],
            project=args.get("project"),
            status=args.get("status"),
            aliases=args.get("aliases"),
            tags=args.get("tags"),
            relationships=args.get("relationships"),
            body=args.get("body"),
            filename=args.get("filename"),
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Upserted memory node: {note.title}",
                "note": format_note_full(note),
                "guidance": _template_guidance(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_update_relationships(args: dict, graph: KnowledgeGraph) -> str:
    try:
        note = graph.update_relationships(
            identifier=args["identifier"],
            add=args.get("add"),
            remove=args.get("remove"),
            replace=args.get("replace"),
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Updated relationships for: {note.title}",
                "note": format_note_full(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


HANDLERS: dict[str, Callable[[dict, KnowledgeGraph], str]] = {
    "create_note": _handle_create_note,
    "update_note": _handle_update_note,
    "append_to_note": _handle_append_to_note,
    "delete_note": _handle_delete_note,
    "upsert_memory_node": _handle_upsert_memory_node,
    "update_relationships": _handle_update_relationships,
}

TOOL_DEFS: list[Tool] = [
    Tool(
        name="create_note",
        description="Create a new note in the vault. This is a fallback for free-form notes when no template fits. For most new notes, call `list_templates` first and prefer `create_from_template` so memory starts with a consistent, graph-friendly shape. The note will be automatically indexed and linked.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the note"},
                "content": {
                    "type": "string",
                    "description": "Markdown content (without frontmatter). Use [[Note Name]] to link to other notes. Prefer `create_from_template` instead when a template fits the note type.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to categorize the note (e.g., ['project', 'meeting', 'idea'])",
                },
                "filename": {
                    "type": "string",
                    "description": "Optional filename (without .md). Defaults to normalized title.",
                },
            },
            "required": ["title", "content"],
        },
    ),
    Tool(
        name="update_note",
        description="Update an existing note's content, title, or tags. Use this to refine or correct information.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Note ID or title to update"},
                "content": {
                    "type": "string",
                    "description": "New markdown content (replaces existing body)",
                },
                "title": {"type": "string", "description": "New title (optional)"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags (replaces existing tags)",
                },
            },
            "required": ["identifier"],
        },
    ),
    Tool(
        name="append_to_note",
        description="Append content to an existing note. Useful for adding updates, follow-ups, or new sections without replacing existing content.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Note ID or title"},
                "content": {
                    "type": "string",
                    "description": "Content to append (will be added with a blank line separator)",
                },
            },
            "required": ["identifier", "content"],
        },
    ),
    Tool(
        name="delete_note",
        description="Delete a note from the vault. Use with caution - this permanently removes the file.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Note ID or title to delete"}
            },
            "required": ["identifier"],
        },
    ),
    Tool(
        name="upsert_memory_node",
        description="Create or update a structured memory node optimized for agent retrieval. For a brand new note, prefer `list_templates` plus `create_from_template` first, then use this tool to refine or normalize machine-friendly frontmatter such as `entity_type`, `summary`, `status`, and typed relationships.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Canonical note title"},
                "summary": {"type": "string", "description": "Short machine-friendly summary"},
                "entity_type": {
                    "type": "string",
                    "description": "Type like project, service, decision, issue, or session",
                },
                "project": {"type": "string", "description": "Associated project or workstream"},
                "status": {
                    "type": "string",
                    "description": "Status like active, blocked, done, draft, or stale",
                },
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative lookup names",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for the note",
                },
                "relationships": {
                    "type": "array",
                    "description": "Typed relationships to other notes",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "target": {"type": "string"},
                        },
                        "required": ["type", "target"],
                    },
                },
                "body": {"type": "string", "description": "Optional supporting body content"},
                "filename": {"type": "string", "description": "Optional filename override"},
            },
            "required": ["title", "summary", "entity_type"],
        },
    ),
    Tool(
        name="update_relationships",
        description="Add, remove, or replace typed frontmatter relationships for a note without rewriting the whole note body.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Note ID or title"},
                "add": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "target": {"type": "string"},
                        },
                        "required": ["type", "target"],
                    },
                },
                "remove": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "target": {"type": "string"},
                        },
                        "required": ["type", "target"],
                    },
                },
                "replace": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "target": {"type": "string"},
                        },
                        "required": ["type", "target"],
                    },
                },
            },
            "required": ["identifier"],
        },
    ),
]
