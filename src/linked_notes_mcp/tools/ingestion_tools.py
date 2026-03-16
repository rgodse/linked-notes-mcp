"""Ingestion pipeline tools (8 tools)."""

import json
from pathlib import Path
from typing import Callable

from mcp.types import Tool

from ..graph import KnowledgeGraph
from ..ingestion import (
    accept_all_candidates,
    accept_extracted_node,
    ingest_sources,
    list_ingestion_runs,
    merge_extracted_node,
    reject_all_candidates,
    reject_extracted_node,
    review_extracted_nodes,
)
from .helpers import (
    _format_review_candidate,
    _load_reviews,
    _recommended_actions,
    _review_confidence,
    _suggestion_key,
    format_note_full,
)


def _handle_ingest_sources(args: dict, graph: KnowledgeGraph) -> str:
    result = ingest_sources(
        graph=graph,
        sources=args["sources"],
        project=args.get("project"),
        mode=args.get("mode", "stage"),
        use_llm=args.get("use_llm", True),
    )
    return json.dumps(result, indent=2)


def _handle_list_ingestion_runs(args: dict, graph: KnowledgeGraph) -> str:
    runs = list_ingestion_runs(Path(graph.vault_path), args.get("limit", 20))
    return json.dumps(runs, indent=2)


def _handle_review_extracted_nodes(args: dict, graph: KnowledgeGraph) -> str:
    candidates = review_extracted_nodes(
        Path(graph.vault_path),
        run_id=args.get("run_id"),
        state=args.get("state", "pending"),
        recommendation=args.get("recommendation"),
        limit=args.get("limit", 20),
    )
    return json.dumps(
        [_format_review_candidate(candidate) for candidate in candidates],
        indent=2,
    )


def _handle_accept_extracted_node(args: dict, graph: KnowledgeGraph) -> str:
    try:
        result = accept_extracted_node(graph, args["candidate_id"])
        note = result["note"]
        payload = {
            "status": "success",
            "action": result["action"],
            "candidate_id": result["candidate_id"],
            "note": format_note_full(note),
        }
        if "merge_suggestion" in result:
            payload["merge_suggestion"] = result["merge_suggestion"]
        return json.dumps(payload, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_reject_extracted_node(args: dict, graph: KnowledgeGraph) -> str:
    try:
        result = reject_extracted_node(
            graph,
            args["candidate_id"],
            args.get("reason"),
        )
        return json.dumps(
            {
                "status": "success",
                "candidate_id": result["candidate_id"],
                "review_state": result["status"],
                "reason": result.get("reason"),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_merge_extracted_node(args: dict, graph: KnowledgeGraph) -> str:
    try:
        result = merge_extracted_node(
            graph,
            args["candidate_id"],
            args["target_identifier"],
        )
        return json.dumps(
            {
                "status": "success",
                "action": result["action"],
                "candidate_id": result["candidate_id"],
                "note": format_note_full(result["note"]),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_accept_all_candidates(args: dict, graph: KnowledgeGraph) -> str:
    try:
        result = accept_all_candidates(
            graph,
            args["run_id"],
            recommendation=args.get("recommendation"),
            limit=args.get("limit"),
        )
        return json.dumps({"status": "success", **result}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_reject_all_candidates(args: dict, graph: KnowledgeGraph) -> str:
    try:
        result = reject_all_candidates(
            graph,
            args["run_id"],
            recommendation=args.get("recommendation"),
            reason=args.get("reason"),
            limit=args.get("limit"),
        )
        return json.dumps({"status": "success", **result}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_review_queue(args: dict, graph: KnowledgeGraph) -> str:
    limit = args.get("limit", 8)
    run_id = args.get("run_id")
    recommendation = args.get("recommendation")
    health_items = graph.get_graph_health(limit)
    stale_notes = graph.list_stale_notes()[:limit]
    reviews = _load_reviews(graph)
    suggestions = graph.suggest_relationships(limit)
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
    pending_candidates = [
        _format_review_candidate(candidate)
        for candidate in review_extracted_nodes(
            Path(graph.vault_path),
            run_id=run_id,
            state="pending",
            recommendation=recommendation,
            limit=limit,
        )
    ]
    weak_notes = [
        {
            "note_id": item.note_id,
            "score": item.score,
            "max_score": item.max_score,
            "issues": item.issues,
        }
        for item in health_items
    ]
    stale_payload = [
        {
            "id": note.id,
            "title": note.title,
            "expires": str(note.frontmatter.get("expires", "")),
        }
        for note in stale_notes
    ]
    return json.dumps(
        {
            "recommended_actions": _recommended_actions(
                weak_notes=weak_notes,
                pending_suggestions=pending_suggestions,
                pending_candidates=pending_candidates,
                stale_notes=stale_payload,
                limit=limit,
            ),
            "counts": {
                "weak_notes": len(weak_notes),
                "pending_relationship_suggestions": len(pending_suggestions),
                "pending_ingestion_candidates": len(pending_candidates),
                "stale_notes": len(stale_payload),
            },
        },
        indent=2,
    )


HANDLERS: dict[str, Callable[[dict, KnowledgeGraph], str]] = {
    "ingest_sources": _handle_ingest_sources,
    "list_ingestion_runs": _handle_list_ingestion_runs,
    "review_extracted_nodes": _handle_review_extracted_nodes,
    "accept_extracted_node": _handle_accept_extracted_node,
    "reject_extracted_node": _handle_reject_extracted_node,
    "merge_extracted_node": _handle_merge_extracted_node,
    "accept_all_candidates": _handle_accept_all_candidates,
    "reject_all_candidates": _handle_reject_all_candidates,
}

TOOL_DEFS: list[Tool] = [
    Tool(
        name="ingest_sources",
        description="Create a staged ingestion run from local files or inline text and extract candidate memory nodes for review.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Optional project grouping for extracted candidates",
                },
                "mode": {
                    "type": "string",
                    "enum": ["stage"],
                    "default": "stage",
                    "description": "Ingestion mode. v1 supports staged review only.",
                },
                "use_llm": {
                    "type": "boolean",
                    "default": True,
                    "description": "Use LLM extraction when ANTHROPIC_API_KEY is set. Falls back to heuristic chunking.",
                },
                "sources": {
                    "type": "array",
                    "description": "List of source descriptors to ingest",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["file", "text", "directory", "glob"],
                                "description": "Source kind",
                            },
                            "path": {
                                "type": "string",
                                "description": "Absolute file path for file sources",
                            },
                            "name": {
                                "type": "string",
                                "description": "Display name for inline text",
                            },
                            "content": {"type": "string", "description": "Inline text content"},
                            "recursive": {
                                "type": "boolean",
                                "description": "Whether to scan subdirectories for directory sources",
                            },
                            "extensions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Allowed file extensions for directory sources",
                            },
                            "include": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional include glob patterns for directory sources",
                            },
                            "exclude": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional exclude glob patterns for directory sources",
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern for glob sources",
                            },
                        },
                        "required": ["type"],
                    },
                },
            },
            "required": ["sources"],
        },
    ),
    Tool(
        name="list_ingestion_runs",
        description="List recent staged ingestion runs and their pending review counts.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20, "description": "Maximum runs to return"}
            },
        },
    ),
    Tool(
        name="review_extracted_nodes",
        description="Review staged ingestion candidates before they are promoted into the main memory graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Optional ingestion run filter"},
                "state": {
                    "type": "string",
                    "enum": ["pending", "accepted", "rejected", "merged", "all"],
                    "default": "pending",
                    "description": "Candidate review state filter",
                },
                "recommendation": {
                    "type": "string",
                    "enum": ["create_new", "ambiguous", "merge_likely"],
                    "description": "Optional recommendation filter",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum candidates to return",
                },
            },
        },
    ),
    Tool(
        name="accept_extracted_node",
        description="Accept a staged ingestion candidate and promote it into the memory graph. Clear matches may merge into an existing note.",
        inputSchema={
            "type": "object",
            "properties": {
                "candidate_id": {
                    "type": "string",
                    "description": "Candidate ID from review_extracted_nodes",
                }
            },
            "required": ["candidate_id"],
        },
    ),
    Tool(
        name="reject_extracted_node",
        description="Reject a staged ingestion candidate and record the reason.",
        inputSchema={
            "type": "object",
            "properties": {
                "candidate_id": {
                    "type": "string",
                    "description": "Candidate ID from review_extracted_nodes",
                },
                "reason": {"type": "string", "description": "Optional rejection reason"},
            },
            "required": ["candidate_id"],
        },
    ),
    Tool(
        name="merge_extracted_node",
        description="Merge a staged ingestion candidate into an existing note instead of creating a new one.",
        inputSchema={
            "type": "object",
            "properties": {
                "candidate_id": {
                    "type": "string",
                    "description": "Candidate ID from review_extracted_nodes",
                },
                "target_identifier": {"type": "string", "description": "Existing note ID or title"},
            },
            "required": ["candidate_id", "target_identifier"],
        },
    ),
    Tool(
        name="accept_all_candidates",
        description="Bulk-accept pending ingestion candidates for a run, optionally filtered by recommendation.",
        inputSchema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Ingestion run ID"},
                "recommendation": {
                    "type": "string",
                    "enum": ["create_new", "ambiguous", "merge_likely"],
                    "description": "Optional recommendation filter",
                },
                "limit": {"type": "integer", "description": "Optional bulk limit"},
            },
            "required": ["run_id"],
        },
    ),
    Tool(
        name="reject_all_candidates",
        description="Bulk-reject pending ingestion candidates for a run, optionally filtered by recommendation.",
        inputSchema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Ingestion run ID"},
                "recommendation": {
                    "type": "string",
                    "enum": ["create_new", "ambiguous", "merge_likely"],
                    "description": "Optional recommendation filter",
                },
                "reason": {"type": "string", "description": "Optional rejection reason"},
                "limit": {"type": "integer", "description": "Optional bulk limit"},
            },
            "required": ["run_id"],
        },
    ),
]
