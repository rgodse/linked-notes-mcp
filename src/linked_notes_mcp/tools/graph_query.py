"""Read-only graph query tools (12 tools)."""

import json
from typing import Callable

from mcp.types import Tool

from ..graph import KnowledgeGraph
from .helpers import format_note_brief, format_note_full, _extract_excerpt


def _handle_get_note(args: dict, graph: KnowledgeGraph) -> str:
    note = graph.get_note(args["identifier"])
    if note is None:
        return json.dumps({"error": f"Note not found: {args['identifier']}"})
    return json.dumps(format_note_full(note), indent=2)


def _handle_list_links(args: dict, graph: KnowledgeGraph) -> str:
    direction = args.get("direction", "both")
    links = graph.get_links(args["note_id"], direction)
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


def _handle_search(args: dict, graph: KnowledgeGraph) -> str:
    query = args["query"]
    limit = args.get("limit", 20)
    notes = graph.search(query, limit)
    results = []
    for note in notes:
        brief = format_note_brief(note)
        brief["excerpt"] = _extract_excerpt(note, query)
        results.append(brief)
    return json.dumps(results, indent=2)


def _handle_traverse(args: dict, graph: KnowledgeGraph) -> str:
    depth = min(args.get("depth", 2), 5)
    direction = args.get("direction", "both")
    relation_types = args.get("relation_types")
    result = graph.traverse(args["start_id"], depth, direction, relation_types)
    nodes_with_titles = []
    for nid in result.nodes:
        note = graph.get_note(nid)
        if note:
            nodes_with_titles.append({"id": nid, "title": note.title})
        else:
            nodes_with_titles.append({"id": nid, "title": nid})
    return json.dumps(
        {
            "start": result.start_id,
            "depth": result.depth,
            "nodes": nodes_with_titles,
            "edges": [{"from": e[0], "to": e[1]} for e in result.edges],
            "total_nodes": len(result.nodes),
        },
        indent=2,
    )


def _handle_find_path(args: dict, graph: KnowledgeGraph) -> str:
    path = graph.find_path(args["start_id"], args["end_id"])
    if path is None:
        return json.dumps({"error": "No path found between the notes"})
    detailed_path = graph.get_path_details(args["start_id"], args["end_id"]) or []
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


def _handle_list_relationships(args: dict, graph: KnowledgeGraph) -> str:
    direction = args.get("direction", "both")
    relation_type = args.get("relation_type")
    relationships = graph.get_relationships(args["identifier"], direction, relation_type)
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


def _handle_get_graph_context(args: dict, graph: KnowledgeGraph) -> str:
    depth = min(args.get("depth", 2), 5)
    limit = args.get("limit", 12)
    relation_types = args.get("relation_types")
    context = graph.graph_context(
        args["identifier"],
        depth=depth,
        relation_types=relation_types,
        limit=limit,
    )
    if "error" in context:
        return json.dumps(context)
    anchor_note = graph.get_note(context["anchor"])
    context["anchor_title"] = anchor_note.title if anchor_note else context["anchor"]
    return json.dumps(context, indent=2)


def _handle_list_tags(args: dict, graph: KnowledgeGraph) -> str:
    tags = graph.list_tags()
    return json.dumps([{"tag": t, "count": c} for t, c in tags], indent=2)


def _handle_notes_by_tag(args: dict, graph: KnowledgeGraph) -> str:
    notes = graph.notes_by_tag(args["tag"])
    return json.dumps([format_note_brief(n) for n in notes], indent=2)


def _handle_graph_summary(args: dict, graph: KnowledgeGraph) -> str:
    stats = graph.get_stats()
    most_connected = []
    for nid, count in stats.most_connected:
        note = graph.get_note(nid)
        title = note.title if note else nid
        most_connected.append({"id": nid, "title": title, "connections": count})
    return json.dumps(
        {
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
        },
        indent=2,
    )


def _handle_list_notes(args: dict, graph: KnowledgeGraph) -> str:
    limit = args.get("limit", 100)
    notes = graph.list_all_notes()[:limit]
    return json.dumps([format_note_brief(n) for n in notes], indent=2)


def _handle_rebuild(args: dict, graph: KnowledgeGraph) -> str:
    count = graph.rebuild()
    return json.dumps({"status": "success", "notes_indexed": count})


HANDLERS: dict[str, Callable[[dict, KnowledgeGraph], str]] = {
    "get_note": _handle_get_note,
    "list_links": _handle_list_links,
    "search": _handle_search,
    "traverse": _handle_traverse,
    "find_path": _handle_find_path,
    "list_relationships": _handle_list_relationships,
    "get_graph_context": _handle_get_graph_context,
    "list_tags": _handle_list_tags,
    "notes_by_tag": _handle_notes_by_tag,
    "graph_summary": _handle_graph_summary,
    "list_notes": _handle_list_notes,
    "rebuild": _handle_rebuild,
}

TOOL_DEFS: list[Tool] = [
    Tool(
        name="get_note",
        description="Get the full content of a note by its ID or title. Returns the complete markdown content, frontmatter, tags, and outgoing links.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Note ID (filename without .md) or title",
                }
            },
            "required": ["identifier"],
        },
    ),
    Tool(
        name="list_links",
        description="Get the outgoing and/or incoming links for a note. Useful for understanding how a note connects to others in the knowledge graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "Note ID or title"},
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both",
                    "description": "Which links to return: outgoing (this note links to), incoming (link to this note), or both",
                },
            },
            "required": ["note_id"],
        },
    ),
    Tool(
        name="search",
        description="Full-text search across all notes. Searches titles, content, and tags. Returns matching notes sorted by relevance.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum number of results to return",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="traverse",
        description="Traverse the knowledge graph starting from a note, finding all connected notes within N hops. Useful for exploring related concepts and building context.",
        inputSchema={
            "type": "object",
            "properties": {
                "start_id": {"type": "string", "description": "Starting note ID or title"},
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Maximum number of hops from the starting note",
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both",
                    "description": "Direction to traverse",
                },
                "relation_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional relationship types to keep during traversal, for example depends_on, blocks, or related_to",
                },
            },
            "required": ["start_id"],
        },
    ),
    Tool(
        name="find_path",
        description="Find the shortest path between two notes in the knowledge graph. Useful for understanding how concepts connect.",
        inputSchema={
            "type": "object",
            "properties": {
                "start_id": {"type": "string", "description": "Starting note ID or title"},
                "end_id": {"type": "string", "description": "Ending note ID or title"},
            },
            "required": ["start_id", "end_id"],
        },
    ),
    Tool(
        name="list_relationships",
        description="List typed graph relationships for a note, including frontmatter relationships and inline link edges. Use this when you want explicit memory edges instead of raw note search.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Note ID or title"},
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both",
                    "description": "Which direction of relationships to inspect",
                },
                "relation_type": {
                    "type": "string",
                    "description": "Optional relationship type filter",
                },
            },
            "required": ["identifier"],
        },
    ),
    Tool(
        name="get_graph_context",
        description="Get graph-first context around a note. This expands nearby nodes and edges, scores them by distance and relationship density, and is more useful than raw note search when your memory is structured as a graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Anchor note ID or title"},
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Maximum graph distance from the anchor note",
                },
                "limit": {
                    "type": "integer",
                    "default": 12,
                    "description": "Maximum number of related nodes to return",
                },
                "relation_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional relationship types to prioritize or restrict",
                },
            },
            "required": ["identifier"],
        },
    ),
    Tool(
        name="list_tags",
        description="List all tags used across notes, with counts. Useful for understanding the structure of the knowledge base.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="notes_by_tag",
        description="Get all notes with a specific tag.",
        inputSchema={
            "type": "object",
            "properties": {"tag": {"type": "string", "description": "Tag to filter by"}},
            "required": ["tag"],
        },
    ),
    Tool(
        name="graph_summary",
        description="Get an overview of the knowledge graph: total notes, links, tags, orphan notes, and most connected notes. Useful for orientation.",
        inputSchema={"type": "object", "properties": {}},
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
                    "description": "Maximum number of notes to return",
                }
            },
        },
    ),
    Tool(
        name="rebuild",
        description="Rebuild the knowledge graph index. Use this after adding, editing, or deleting notes to refresh the graph.",
        inputSchema={"type": "object", "properties": {}},
    ),
]
