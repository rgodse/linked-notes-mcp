"""
MCP Server for linked-notes-mcp.

Exposes tools for navigating markdown knowledge graphs via the Model Context Protocol.
"""

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .graph import KnowledgeGraph, Note
from .templates import (
    list_templates as get_templates,
    render_template,
    create_session_summary,
    create_decision_log,
)


# Global graph instance
_graph: Optional[KnowledgeGraph] = None


def get_graph() -> KnowledgeGraph:
    """Get the global graph instance."""
    if _graph is None:
        raise RuntimeError("Graph not initialized. Call init_graph first.")
    return _graph


def init_graph(vault_path: Path) -> KnowledgeGraph:
    """Initialize the global graph."""
    global _graph
    _graph = KnowledgeGraph(vault_path)
    return _graph


def format_note_brief(note: Note) -> dict[str, Any]:
    """Format a note for brief display."""
    return {
        "id": note.id,
        "title": note.title,
        "tags": note.tags,
        "path": str(note.path),
    }


def format_note_full(note: Note) -> dict[str, Any]:
    """Format a note with full content."""
    return {
        "id": note.id,
        "title": note.title,
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


def _extract_excerpt(note: Note, query: str, max_chars: int = 175) -> str:
    """Extract a relevant excerpt from a note's body around the query match."""
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


def _followups_path() -> Path:
    return Path(_graph.vault_path) / ".linked_notes_followups.json"


def _load_followups() -> list[dict]:
    fp = _followups_path()
    if not fp.exists():
        return []
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_followups(followups: list[dict]) -> None:
    _followups_path().write_text(json.dumps(followups, indent=2), encoding="utf-8")


# Define tools
TOOLS = [
    Tool(
        name="get_note",
        description="Get the full content of a note by its ID or title. Returns the complete markdown content, frontmatter, tags, and outgoing links.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Note ID (filename without .md) or title"
                }
            },
            "required": ["identifier"]
        }
    ),
    Tool(
        name="list_links",
        description="Get the outgoing and/or incoming links for a note. Useful for understanding how a note connects to others in the knowledge graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "Note ID or title"
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both",
                    "description": "Which links to return: outgoing (this note links to), incoming (link to this note), or both"
                }
            },
            "required": ["note_id"]
        }
    ),
    Tool(
        name="search",
        description="Full-text search across all notes. Searches titles, content, and tags. Returns matching notes sorted by relevance.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="traverse",
        description="Traverse the knowledge graph starting from a note, finding all connected notes within N hops. Useful for exploring related concepts and building context.",
        inputSchema={
            "type": "object",
            "properties": {
                "start_id": {
                    "type": "string",
                    "description": "Starting note ID or title"
                },
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Maximum number of hops from the starting note"
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both",
                    "description": "Direction to traverse"
                },
                "relation_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional relationship types to keep during traversal, for example depends_on, blocks, or related_to"
                }
            },
            "required": ["start_id"]
        }
    ),
    Tool(
        name="find_path",
        description="Find the shortest path between two notes in the knowledge graph. Useful for understanding how concepts connect.",
        inputSchema={
            "type": "object",
            "properties": {
                "start_id": {
                    "type": "string",
                    "description": "Starting note ID or title"
                },
                "end_id": {
                    "type": "string",
                    "description": "Ending note ID or title"
                }
            },
            "required": ["start_id", "end_id"]
        }
    ),
    Tool(
        name="list_relationships",
        description="List typed graph relationships for a note, including frontmatter relationships and inline link edges. Use this when you want explicit memory edges instead of raw note search.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Note ID or title"
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both",
                    "description": "Which direction of relationships to inspect"
                },
                "relation_type": {
                    "type": "string",
                    "description": "Optional relationship type filter"
                }
            },
            "required": ["identifier"]
        }
    ),
    Tool(
        name="get_graph_context",
        description="Get graph-first context around a note. This expands nearby nodes and edges, scores them by distance and relationship density, and is more useful than raw note search when your memory is structured as a graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Anchor note ID or title"
                },
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Maximum graph distance from the anchor note"
                },
                "limit": {
                    "type": "integer",
                    "default": 12,
                    "description": "Maximum number of related nodes to return"
                },
                "relation_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional relationship types to prioritize or restrict"
                }
            },
            "required": ["identifier"]
        }
    ),
    Tool(
        name="list_tags",
        description="List all tags used across notes, with counts. Useful for understanding the structure of the knowledge base.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="notes_by_tag",
        description="Get all notes with a specific tag.",
        inputSchema={
            "type": "object",
            "properties": {
                "tag": {
                    "type": "string",
                    "description": "Tag to filter by"
                }
            },
            "required": ["tag"]
        }
    ),
    Tool(
        name="graph_summary",
        description="Get an overview of the knowledge graph: total notes, links, tags, orphan notes, and most connected notes. Useful for orientation.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="list_notes",
        description="List all notes in the knowledge base. Returns brief info (id, title, tags, path) for each note.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of notes to return"
                }
            }
        }
    ),
    Tool(
        name="rebuild",
        description="Rebuild the knowledge graph index. Use this after adding, editing, or deleting notes to refresh the graph.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    # ==================== Write Tools ====================
    Tool(
        name="create_note",
        description="Create a new note in the vault. Use this to save insights, summaries, meeting notes, or any information worth remembering. The note will be automatically indexed and linked.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the note"
                },
                "content": {
                    "type": "string",
                    "description": "Markdown content (without frontmatter). Use [[Note Name]] to link to other notes."
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to categorize the note (e.g., ['project', 'meeting', 'idea'])"
                },
                "filename": {
                    "type": "string",
                    "description": "Optional filename (without .md). Defaults to normalized title."
                }
            },
            "required": ["title", "content"]
        }
    ),
    Tool(
        name="update_note",
        description="Update an existing note's content, title, or tags. Use this to refine or correct information.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Note ID or title to update"
                },
                "content": {
                    "type": "string",
                    "description": "New markdown content (replaces existing body)"
                },
                "title": {
                    "type": "string",
                    "description": "New title (optional)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags (replaces existing tags)"
                }
            },
            "required": ["identifier"]
        }
    ),
    Tool(
        name="append_to_note",
        description="Append content to an existing note. Useful for adding updates, follow-ups, or new sections without replacing existing content.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Note ID or title"
                },
                "content": {
                    "type": "string",
                    "description": "Content to append (will be added with a blank line separator)"
                }
            },
            "required": ["identifier", "content"]
        }
    ),
    Tool(
        name="delete_note",
        description="Delete a note from the vault. Use with caution - this permanently removes the file.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Note ID or title to delete"
                }
            },
            "required": ["identifier"]
        }
    ),
    # ==================== Template Tools ====================
    Tool(
        name="list_templates",
        description="List all available note templates. Templates provide consistent structure for common note types like session summaries, decisions, meetings, etc.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="create_from_template",
        description="Create a note using a predefined template. Use list_templates to see available templates.",
        inputSchema={
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "enum": ["session", "decision", "project", "meeting", "idea", "bug", "learning"],
                    "description": "Template to use"
                },
                "title": {
                    "type": "string",
                    "description": "Note title (optional - will auto-generate if not provided)"
                },
                "fields": {
                    "type": "object",
                    "description": "Template fields to fill in (varies by template)"
                },
                "extra_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional tags beyond template defaults"
                }
            },
            "required": ["template", "fields"]
        }
    ),
    Tool(
        name="save_session_summary",
        description="Save a summary at the end of a work session. Captures what was accomplished, decisions made, and what's next. USE THIS before ending significant conversations.",
        inputSchema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief 1-2 sentence summary of the session"
                },
                "accomplished": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of things accomplished this session"
                },
                "decisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key decisions made (optional)"
                },
                "open_items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Items still pending or blocked (optional)"
                },
                "next_session": {
                    "type": "string",
                    "description": "What to pick up next time (optional)"
                },
                "project": {
                    "type": "string",
                    "description": "Project name for tagging (optional)"
                },
                "topic": {
                    "type": "string",
                    "description": "Topic/focus of this session for the title (optional)"
                }
            },
            "required": ["summary", "accomplished"]
        }
    ),
    Tool(
        name="save_decision",
        description="Record an important decision with full context and reasoning. Use this when a significant choice is made so it can be referenced later.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the decision (e.g., 'JWT vs Sessions')"
                },
                "context": {
                    "type": "string",
                    "description": "Background - why was this decision needed?"
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Options that were considered"
                },
                "decision": {
                    "type": "string",
                    "description": "What was decided"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why this option was chosen"
                },
                "implications": {
                    "type": "string",
                    "description": "What this means going forward (optional)"
                },
                "project": {
                    "type": "string",
                    "description": "Project name for tagging (optional)"
                }
            },
            "required": ["title", "context", "options", "decision", "reasoning"]
        }
    ),
    # ==================== Agent Memory Tools ====================
    Tool(
        name="get_context",
        description="Search notes and return excerpts with relevance info, plus any matching followup reminders and graph-local context. Use this at session start to bootstrap context on a topic.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic or keywords to build context around"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of notes to return"
                },
                "graph_depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "How far to expand from the best matching note in the graph"
                },
                "graph_limit": {
                    "type": "integer",
                    "default": 8,
                    "description": "Maximum number of graph-neighbor notes to include"
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_note_summary",
        description="Get a note's metadata and a truncated body preview without loading the full content. Useful for deciding whether to load a note in full.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Note ID or title"
                },
                "max_chars": {
                    "type": "integer",
                    "default": 500,
                    "description": "Maximum characters to return from the body"
                }
            },
            "required": ["identifier"]
        }
    ),
    Tool(
        name="list_stale_notes",
        description="List notes whose 'expires' frontmatter date is in the past. Useful for identifying outdated information.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="add_followup",
        description="Add a persistent followup reminder to the vault. Reminders survive across sessions and can be retrieved with list_followups.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Short topic label for the reminder"
                },
                "reminder": {
                    "type": "string",
                    "description": "The reminder text"
                }
            },
            "required": ["topic", "reminder"]
        }
    ),
    Tool(
        name="list_followups",
        description="List all persistent followup reminders stored in the vault.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="dismiss_followup",
        description="Dismiss (delete) a followup reminder by its ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Followup ID to dismiss"
                }
            },
            "required": ["id"]
        }
    ),
]


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """Handle a tool call and return the result as JSON."""
    graph = get_graph()
    
    if name == "get_note":
        note = graph.get_note(arguments["identifier"])
        if note is None:
            return json.dumps({"error": f"Note not found: {arguments['identifier']}"})
        return json.dumps(format_note_full(note), indent=2)
    
    elif name == "list_links":
        direction = arguments.get("direction", "both")
        links = graph.get_links(arguments["note_id"], direction)
        
        # Enrich with titles
        result = {}
        for dir_name, link_ids in links.items():
            result[dir_name] = []
            for lid in link_ids:
                note = graph.get_note(lid)
                if note:
                    result[dir_name].append({"id": lid, "title": note.title})
                else:
                    result[dir_name].append({"id": lid, "title": lid})
        
        return json.dumps(result, indent=2)
    
    elif name == "search":
        query = arguments["query"]
        limit = arguments.get("limit", 20)
        notes = graph.search(query, limit)
        results = []
        for note in notes:
            brief = format_note_brief(note)
            brief["excerpt"] = _extract_excerpt(note, query)
            results.append(brief)
        return json.dumps(results, indent=2)
    
    elif name == "traverse":
        depth = min(arguments.get("depth", 2), 5)  # Cap at 5
        direction = arguments.get("direction", "both")
        relation_types = arguments.get("relation_types")
        result = graph.traverse(arguments["start_id"], depth, direction, relation_types)
        
        # Enrich nodes with titles
        nodes_with_titles = []
        for nid in result.nodes:
            note = graph.get_note(nid)
            if note:
                nodes_with_titles.append({"id": nid, "title": note.title})
            else:
                nodes_with_titles.append({"id": nid, "title": nid})
        
        return json.dumps({
            "start": result.start_id,
            "depth": result.depth,
            "nodes": nodes_with_titles,
            "edges": [{"from": e[0], "to": e[1]} for e in result.edges],
            "total_nodes": len(result.nodes)
        }, indent=2)
    
    elif name == "find_path":
        path = graph.find_path(arguments["start_id"], arguments["end_id"])
        if path is None:
            return json.dumps({"error": "No path found between the notes"})

        detailed_path = graph.get_path_details(arguments["start_id"], arguments["end_id"]) or []
        path_with_titles = []
        for step in detailed_path:
            note = graph.get_note(step["id"])
            entry = {
                "id": step["id"],
                "title": note.title if note else step["id"],
            }
            if "to_next" in step:
                entry["to_next"] = step["to_next"]
            path_with_titles.append(entry)

        return json.dumps({"path": path_with_titles, "length": len(path)}, indent=2)

    elif name == "list_relationships":
        direction = arguments.get("direction", "both")
        relation_type = arguments.get("relation_type")
        relationships = graph.get_relationships(arguments["identifier"], direction, relation_type)

        enriched = {}
        for bucket, items in relationships.items():
            enriched[bucket] = []
            for item in items:
                source_note = graph.get_note(item["from"])
                target_note = graph.get_note(item["to"])
                enriched[bucket].append(
                    {
                        **item,
                        "from_title": source_note.title if source_note else item["from"],
                        "to_title": target_note.title if target_note else item["to"],
                    }
                )

        return json.dumps(enriched, indent=2)

    elif name == "get_graph_context":
        depth = min(arguments.get("depth", 2), 5)
        limit = arguments.get("limit", 12)
        relation_types = arguments.get("relation_types")
        context = graph.graph_context(
            arguments["identifier"],
            depth=depth,
            relation_types=relation_types,
            limit=limit,
        )
        if "error" in context:
            return json.dumps(context)
        anchor_note = graph.get_note(context["anchor"])
        context["anchor_title"] = anchor_note.title if anchor_note else context["anchor"]
        return json.dumps(context, indent=2)
    
    elif name == "list_tags":
        tags = graph.list_tags()
        return json.dumps([{"tag": t, "count": c} for t, c in tags], indent=2)
    
    elif name == "notes_by_tag":
        notes = graph.notes_by_tag(arguments["tag"])
        return json.dumps([format_note_brief(n) for n in notes], indent=2)
    
    elif name == "graph_summary":
        stats = graph.get_stats()
        
        # Enrich most connected with titles
        most_connected = []
        for nid, count in stats.most_connected:
            note = graph.get_note(nid)
            title = note.title if note else nid
            most_connected.append({"id": nid, "title": title, "connections": count})
        
        return json.dumps({
            "total_notes": stats.total_notes,
            "total_links": stats.total_links,
            "total_tags": stats.total_tags,
            "orphan_notes": stats.orphan_notes,
            "most_connected": most_connected,
            "total_relationships": stats.total_relationships,
            "relationship_counts": [
                {"type": relation_type, "count": count}
                for relation_type, count in stats.relationship_counts
            ],
        }, indent=2)
    
    elif name == "list_notes":
        limit = arguments.get("limit", 100)
        notes = graph.list_all_notes()[:limit]
        return json.dumps([format_note_brief(n) for n in notes], indent=2)
    
    elif name == "rebuild":
        count = graph.rebuild()
        return json.dumps({"status": "success", "notes_indexed": count})

    # ==================== Write Tool Handlers ====================
    elif name == "create_note":
        try:
            note = graph.create_note(
                title=arguments["title"],
                content=arguments["content"],
                tags=arguments.get("tags"),
                filename=arguments.get("filename")
            )
            return json.dumps({
                "status": "success",
                "message": f"Created note: {note.title}",
                "note": format_note_brief(note)
            }, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)})

    elif name == "update_note":
        try:
            note = graph.update_note(
                identifier=arguments["identifier"],
                content=arguments.get("content"),
                title=arguments.get("title"),
                tags=arguments.get("tags")
            )
            return json.dumps({
                "status": "success",
                "message": f"Updated note: {note.title}",
                "note": format_note_brief(note)
            }, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)})

    elif name == "append_to_note":
        try:
            note = graph.append_to_note(
                identifier=arguments["identifier"],
                content=arguments["content"]
            )
            return json.dumps({
                "status": "success",
                "message": f"Appended to note: {note.title}",
                "note": format_note_brief(note)
            }, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)})

    elif name == "delete_note":
        deleted = graph.delete_note(arguments["identifier"])
        if deleted:
            return json.dumps({
                "status": "success",
                "message": f"Deleted note: {arguments['identifier']}"
            })
        else:
            return json.dumps({"error": f"Note not found: {arguments['identifier']}"})

    # ==================== Template Tool Handlers ====================
    elif name == "list_templates":
        templates = get_templates()
        return json.dumps(templates, indent=2)

    elif name == "create_from_template":
        try:
            title, content, tags = render_template(
                template_name=arguments["template"],
                fields=arguments.get("fields", {}),
                title=arguments.get("title"),
                extra_tags=arguments.get("extra_tags")
            )
            note = graph.create_note(title=title, content=content, tags=tags)
            return json.dumps({
                "status": "success",
                "message": f"Created note from template: {note.title}",
                "note": format_note_brief(note)
            }, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)})

    elif name == "save_session_summary":
        try:
            title, content, tags = create_session_summary(
                summary=arguments["summary"],
                accomplished=arguments["accomplished"],
                decisions=arguments.get("decisions"),
                open_items=arguments.get("open_items"),
                next_session=arguments.get("next_session"),
                project_tag=arguments.get("project"),
                topic=arguments.get("topic")
            )
            note = graph.create_note(title=title, content=content, tags=tags)
            return json.dumps({
                "status": "success",
                "message": f"Saved session summary: {note.title}",
                "note": format_note_brief(note)
            }, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)})

    elif name == "save_decision":
        try:
            title, content, tags = create_decision_log(
                decision_title=arguments["title"],
                context=arguments["context"],
                options=arguments["options"],
                decision=arguments["decision"],
                reasoning=arguments["reasoning"],
                implications=arguments.get("implications"),
                project_tag=arguments.get("project")
            )
            note = graph.create_note(title=title, content=content, tags=tags)
            return json.dumps({
                "status": "success",
                "message": f"Saved decision: {note.title}",
                "note": format_note_brief(note)
            }, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)})

    elif name == "get_context":
        query = arguments["query"]
        limit = arguments.get("limit", 10)
        graph_depth = min(arguments.get("graph_depth", 2), 5)
        graph_limit = arguments.get("graph_limit", 8)
        notes = graph.search(query, limit)
        followups = _load_followups()
        query_lower = query.lower()
        matching_followups = [
            f for f in followups
            if query_lower in f.get("topic", "").lower()
            or query_lower in f.get("reminder", "").lower()
        ]
        context_notes = []
        for note in notes:
            brief = format_note_brief(note)
            brief["excerpt"] = _extract_excerpt(note, query)
            brief["relevance"] = 1
            context_notes.append(brief)

        graph_context = None
        if notes:
            graph_context = graph.graph_context(
                notes[0].id,
                depth=graph_depth,
                limit=graph_limit,
            )
            if "error" not in graph_context:
                anchor_note = graph.get_note(graph_context["anchor"])
                graph_context["anchor_title"] = (
                    anchor_note.title if anchor_note else graph_context["anchor"]
                )
        return json.dumps({
            "query": query,
            "context_notes": context_notes,
            "related_followups": matching_followups,
            "graph_context": graph_context,
        }, indent=2)

    elif name == "get_note_summary":
        note = graph.get_note(arguments["identifier"])
        if note is None:
            return json.dumps({"error": f"Note not found: {arguments['identifier']}"})
        max_chars = arguments.get("max_chars", 500)
        body = note.body or ""
        truncated = len(body) > max_chars
        result = format_note_brief(note)
        result["body_preview"] = body[:max_chars] + ("..." if truncated else "")
        result["truncated"] = truncated
        result["total_chars"] = len(body)
        return json.dumps(result, indent=2)

    elif name == "list_stale_notes":
        notes = graph.list_stale_notes()
        results = []
        for note in notes:
            brief = format_note_brief(note)
            brief["expires"] = str(note.frontmatter.get("expires", ""))
            results.append(brief)
        return json.dumps(results, indent=2)

    elif name == "add_followup":
        followups = _load_followups()
        entry = {
            "id": str(uuid.uuid4()),
            "topic": arguments["topic"],
            "reminder": arguments["reminder"],
            "created": datetime.now().isoformat()
        }
        followups.append(entry)
        _save_followups(followups)
        return json.dumps({"status": "success", "followup": entry}, indent=2)

    elif name == "list_followups":
        followups = _load_followups()
        return json.dumps({"count": len(followups), "followups": followups}, indent=2)

    elif name == "dismiss_followup":
        followup_id = arguments["id"]
        followups = _load_followups()
        updated = [f for f in followups if f.get("id") != followup_id]
        if len(updated) == len(followups):
            return json.dumps({"error": f"Followup not found: {followup_id}"})
        _save_followups(updated)
        return json.dumps({"status": "success", "dismissed_id": followup_id})

    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


def create_server(vault_path: Path) -> Server:
    """Create and configure the MCP server."""
    server = Server("linked-notes-mcp")
    
    # Initialize the graph
    init_graph(vault_path)
    
    @server.list_tools()
    async def list_tools():
        return TOOLS
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]):
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=result)]
    
    return server


async def run_server(vault_path: Path):
    """Run the MCP server."""
    server = create_server(vault_path)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MCP server for markdown knowledge graphs"
    )
    parser.add_argument(
        "vault_path",
        type=Path,
        help="Path to the markdown vault/folder"
    )
    args = parser.parse_args()
    
    if not args.vault_path.exists():
        print(f"Error: Vault path does not exist: {args.vault_path}", file=sys.stderr)
        sys.exit(1)
    
    asyncio.run(run_server(args.vault_path))


if __name__ == "__main__":
    main()
