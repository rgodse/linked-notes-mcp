"""Session lifecycle, context, and template tools (14 tools)."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml
from mcp.types import Tool

from ..graph import KnowledgeGraph
from ..ingestion import review_extracted_nodes
from ..templates import (
    build_template_frontmatter,
    create_decision_log,
    create_session_summary,
    render_template,
)
from ..templates import list_templates as get_templates
from .helpers import (
    _extract_excerpt,
    _format_review_candidate,
    _load_followups,
    _load_reviews,
    _recommended_actions,
    _recent_session_notes,
    _review_confidence,
    _save_followups,
    _session_next_steps,
    _suggestion_key,
    _touched_note_summaries,
    format_note_brief,
)


def _handle_start_session(args: dict, graph: KnowledgeGraph) -> str:
    topic = args["topic"]
    project = args.get("project")
    limit = args.get("limit", 5)
    graph_depth = min(args.get("graph_depth", 2), 5)
    graph_limit = args.get("graph_limit", 8)
    recent_session_limit = args.get("recent_session_limit", 3)

    query = project or topic
    notes = graph.search(query, limit)
    if not notes and project and project.lower() not in topic.lower():
        notes = graph.search(topic, limit)

    context_notes = []
    for note in notes:
        brief = format_note_brief(note)
        brief["excerpt"] = _extract_excerpt(note, topic)
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

    followups = _load_followups(graph)
    topic_lower = topic.lower()
    project_lower = project.lower() if project else None
    relevant_followups = [
        followup
        for followup in followups
        if topic_lower in followup.get("topic", "").lower()
        or topic_lower in followup.get("reminder", "").lower()
        or (
            project_lower
            and (
                project_lower in followup.get("topic", "").lower()
                or project_lower in followup.get("reminder", "").lower()
            )
        )
    ]

    stale_notes = []
    for note in graph.list_stale_notes():
        if project and note.frontmatter.get("project") != project:
            continue
        brief = format_note_brief(note)
        brief["expires"] = str(note.frontmatter.get("expires", ""))
        stale_notes.append(brief)

    recent_sessions = _recent_session_notes(graph, project, recent_session_limit)

    return json.dumps(
        {
            "topic": topic,
            "project": project,
            "working_brief": {
                "anchor": context_notes[0] if context_notes else None,
                "context_notes": context_notes,
                "graph_context": graph_context,
                "related_followups": relevant_followups,
                "stale_notes": stale_notes[:5],
                "recent_sessions": recent_sessions,
                "suggested_next_steps": _session_next_steps(
                    context_notes=context_notes,
                    followups=relevant_followups,
                    stale_notes=stale_notes[:5],
                    recent_sessions=recent_sessions,
                ),
            },
        },
        indent=2,
    )


def _handle_review_memory(args: dict, graph: KnowledgeGraph) -> str:
    health_limit = args.get("health_limit", 10)
    suggestion_limit = args.get("suggestion_limit", 10)
    stale_limit = args.get("stale_limit", 10)
    candidate_limit = args.get("candidate_limit", 10)
    run_id = args.get("run_id")

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

    pending_candidates = review_extracted_nodes(
        Path(graph.vault_path),
        run_id=run_id,
        state="pending",
        recommendation=args.get("recommendation"),
        limit=candidate_limit,
    )
    formatted_candidates = [
        _format_review_candidate(candidate) for candidate in pending_candidates
    ]
    stale_payload = [
        {
            "id": note.id,
            "title": note.title,
            "expires": str(note.frontmatter.get("expires", "")),
        }
        for note in stale_notes
    ]
    weak_payload = [
        {
            "note_id": item.note_id,
            "score": item.score,
            "max_score": item.max_score,
            "issues": item.issues,
        }
        for item in health_items
    ]

    return json.dumps(
        {
            "summary": {
                "total_notes": stats.total_notes,
                "total_links": stats.total_links,
                "total_relationships": stats.total_relationships,
                "orphan_notes": stats.orphan_notes,
                "pending_relationship_suggestions": len(pending_suggestions),
                "pending_ingestion_candidates": len(formatted_candidates),
                "stale_notes": len(graph.list_stale_notes()),
            },
            "recommended_actions": _recommended_actions(
                weak_notes=weak_payload,
                pending_suggestions=pending_suggestions,
                pending_candidates=formatted_candidates,
                stale_notes=stale_payload,
                limit=max(health_limit, suggestion_limit, stale_limit, candidate_limit),
            ),
            "weak_notes": weak_payload,
            "pending_relationship_suggestions": pending_suggestions,
            "pending_ingestion_candidates": formatted_candidates,
            "stale_notes": stale_payload,
        },
        indent=2,
    )


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


def _handle_end_session(args: dict, graph: KnowledgeGraph) -> str:
    try:
        title, content, tags = create_session_summary(
            summary=args["summary"],
            accomplished=args["accomplished"],
            decisions=args.get("decisions"),
            open_items=args.get("open_items"),
            next_session=args.get("next_session"),
            project_tag=args.get("project"),
            topic=args.get("topic"),
        )
        note = graph.create_note(title=title, content=content, tags=tags)

        touched_notes = args.get("touched_notes", [])
        for identifier in touched_notes:
            touched = graph.get_note(identifier)
            if touched is None:
                continue
            frontmatter = touched.frontmatter.copy()
            frontmatter["last_reviewed"] = datetime.now().isoformat()
            frontmatter["modified"] = datetime.now().isoformat()
            touched.path.write_text(
                f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{touched.body}",
                encoding="utf-8",
            )
            graph._reload_note_from_disk(touched)

        generated_followups = []
        followup_topic = args.get("followup_topic") or args.get("project") or title
        for item in args.get("open_items", []) or []:
            followups = _load_followups(graph)
            entry = {
                "id": str(uuid.uuid4()),
                "topic": followup_topic,
                "reminder": item,
                "created": datetime.now().isoformat(),
            }
            followups.append(entry)
            _save_followups(graph, followups)
            generated_followups.append(entry)

        return json.dumps(
            {
                "status": "success",
                "message": f"Ended session: {note.title}",
                "session_note": format_note_brief(note),
                "touched_notes": _touched_note_summaries(graph, touched_notes),
                "generated_followups": generated_followups,
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_list_templates(args: dict, graph: KnowledgeGraph) -> str:
    templates = get_templates()
    return json.dumps(templates, indent=2)


def _handle_create_from_template(args: dict, graph: KnowledgeGraph) -> str:
    try:
        title, content, tags = render_template(
            template_name=args["template"],
            fields=args.get("fields", {}),
            title=args.get("title"),
            extra_tags=args.get("extra_tags"),
        )
        extra_frontmatter, _ = build_template_frontmatter(
            template_name=args["template"],
            title=title,
            fields=args.get("fields", {}),
            extra_tags=args.get("extra_tags"),
        )
        note = graph.create_note(
            title=title,
            content=content,
            tags=tags,
            extra_frontmatter=extra_frontmatter,
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Created note from template: {note.title}",
                "note": format_note_brief(note),
                "guidance": (
                    "Template-based note created. Prefer this flow for new notes "
                    "so memory stays consistent and graph-friendly."
                ),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_save_session_summary(args: dict, graph: KnowledgeGraph) -> str:
    try:
        title, content, tags = create_session_summary(
            summary=args["summary"],
            accomplished=args["accomplished"],
            decisions=args.get("decisions"),
            open_items=args.get("open_items"),
            next_session=args.get("next_session"),
            project_tag=args.get("project"),
            topic=args.get("topic"),
        )
        note = graph.create_note(title=title, content=content, tags=tags)
        return json.dumps(
            {
                "status": "success",
                "message": f"Saved session summary: {note.title}",
                "note": format_note_brief(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_save_decision(args: dict, graph: KnowledgeGraph) -> str:
    try:
        title, content, tags = create_decision_log(
            decision_title=args["title"],
            context=args["context"],
            options=args["options"],
            decision=args["decision"],
            reasoning=args["reasoning"],
            implications=args.get("implications"),
            project_tag=args.get("project"),
        )
        note = graph.create_note(title=title, content=content, tags=tags)
        return json.dumps(
            {
                "status": "success",
                "message": f"Saved decision: {note.title}",
                "note": format_note_brief(note),
            },
            indent=2,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _handle_get_context(args: dict, graph: KnowledgeGraph) -> str:
    query = args["query"]
    limit = args.get("limit", 10)
    graph_depth = min(args.get("graph_depth", 2), 5)
    graph_limit = args.get("graph_limit", 8)
    notes = graph.search(query, limit)
    followups = _load_followups(graph)
    query_lower = query.lower()
    matching_followups = [
        f
        for f in followups
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
    return json.dumps(
        {
            "query": query,
            "context_notes": context_notes,
            "related_followups": matching_followups,
            "graph_context": graph_context,
        },
        indent=2,
    )


def _handle_get_note_summary(args: dict, graph: KnowledgeGraph) -> str:
    note = graph.get_note(args["identifier"])
    if note is None:
        return json.dumps({"error": f"Note not found: {args['identifier']}"})
    max_chars = args.get("max_chars", 500)
    body = note.body or ""
    truncated = len(body) > max_chars
    result = format_note_brief(note)
    result["body_preview"] = body[:max_chars] + ("..." if truncated else "")
    result["truncated"] = truncated
    result["total_chars"] = len(body)
    return json.dumps(result, indent=2)


def _handle_list_stale_notes(args: dict, graph: KnowledgeGraph) -> str:
    notes = graph.list_stale_notes()
    results = []
    for note in notes:
        brief = format_note_brief(note)
        brief["expires"] = str(note.frontmatter.get("expires", ""))
        results.append(brief)
    return json.dumps(results, indent=2)


def _handle_add_followup(args: dict, graph: KnowledgeGraph) -> str:
    followups = _load_followups(graph)
    entry = {
        "id": str(uuid.uuid4()),
        "topic": args["topic"],
        "reminder": args["reminder"],
        "created": datetime.now().isoformat(),
    }
    followups.append(entry)
    _save_followups(graph, followups)
    return json.dumps({"status": "success", "followup": entry}, indent=2)


def _handle_list_followups(args: dict, graph: KnowledgeGraph) -> str:
    followups = _load_followups(graph)
    return json.dumps({"count": len(followups), "followups": followups}, indent=2)


def _handle_dismiss_followup(args: dict, graph: KnowledgeGraph) -> str:
    followup_id = args["id"]
    followups = _load_followups(graph)
    updated = [f for f in followups if f.get("id") != followup_id]
    if len(updated) == len(followups):
        return json.dumps({"error": f"Followup not found: {followup_id}"})
    _save_followups(graph, updated)
    return json.dumps({"status": "success", "dismissed_id": followup_id})


HANDLERS: dict[str, Callable[[dict, KnowledgeGraph], str]] = {
    "start_session": _handle_start_session,
    "review_memory": _handle_review_memory,
    "review_queue": _handle_review_queue,
    "end_session": _handle_end_session,
    "list_templates": _handle_list_templates,
    "create_from_template": _handle_create_from_template,
    "save_session_summary": _handle_save_session_summary,
    "save_decision": _handle_save_decision,
    "get_context": _handle_get_context,
    "get_note_summary": _handle_get_note_summary,
    "list_stale_notes": _handle_list_stale_notes,
    "add_followup": _handle_add_followup,
    "list_followups": _handle_list_followups,
    "dismiss_followup": _handle_dismiss_followup,
}

TOOL_DEFS: list[Tool] = [
    Tool(
        name="start_session",
        description="Build a compact working brief for a topic or project by combining text search, graph context, followups, stale notes, and recent sessions.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic or project to start working on"},
                "project": {"type": "string", "description": "Optional project grouping"},
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum matching context notes",
                },
                "graph_depth": {"type": "integer", "default": 2, "minimum": 1, "maximum": 5},
                "graph_limit": {
                    "type": "integer",
                    "default": 8,
                    "description": "Maximum related graph nodes",
                },
                "recent_session_limit": {
                    "type": "integer",
                    "default": 3,
                    "description": "Maximum recent sessions",
                },
            },
            "required": ["topic"],
        },
    ),
    Tool(
        name="review_memory",
        description="Return one compact maintenance queue covering weak notes, stale notes, relationship suggestions, and pending ingestion candidates.",
        inputSchema={
            "type": "object",
            "properties": {
                "health_limit": {"type": "integer", "default": 10},
                "suggestion_limit": {"type": "integer", "default": 10},
                "stale_limit": {"type": "integer", "default": 10},
                "candidate_limit": {"type": "integer", "default": 10},
                "run_id": {"type": "string", "description": "Optional ingestion run filter"},
            },
        },
    ),
    Tool(
        name="review_queue",
        description="Return a compact prioritized triage queue across weak notes, stale notes, relationship suggestions, and pending ingestion candidates.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 8,
                    "description": "Maximum actions to return",
                },
                "run_id": {"type": "string", "description": "Optional ingestion run filter"},
                "recommendation": {
                    "type": "string",
                    "enum": ["create_new", "ambiguous", "merge_likely"],
                    "description": "Optional candidate recommendation filter",
                },
            },
        },
    ),
    Tool(
        name="end_session",
        description="Wrap up a work session by saving a session summary, optionally updating touched notes, and creating followups for open items.",
        inputSchema={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Brief 1-2 sentence session summary"},
                "accomplished": {"type": "array", "items": {"type": "string"}},
                "decisions": {"type": "array", "items": {"type": "string"}},
                "open_items": {"type": "array", "items": {"type": "string"}},
                "next_session": {"type": "string"},
                "project": {"type": "string"},
                "topic": {"type": "string"},
                "touched_notes": {"type": "array", "items": {"type": "string"}},
                "followup_topic": {
                    "type": "string",
                    "description": "Optional topic label for generated followups",
                },
            },
            "required": ["summary", "accomplished"],
        },
    ),
    Tool(
        name="list_templates",
        description="List all available note templates. Call this first when creating a new note. Templates are the preferred starting point because they provide consistent structure for repo projects, services, issues, decisions, meetings, sessions, and other graph-friendly memory types.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="create_from_template",
        description="Create a note using a predefined template. This is the preferred way to start a new note because templates provide a consistent shape for graph-friendly memory and improve downstream retrieval, review, and maintenance.",
        inputSchema={
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "enum": [
                        "repo_project",
                        "service",
                        "issue",
                        "initiative",
                        "workstream",
                        "stakeholder",
                        "research",
                        "session",
                        "decision",
                        "project",
                        "meeting",
                        "idea",
                        "bug",
                        "learning",
                    ],
                    "description": "Template to use",
                },
                "title": {
                    "type": "string",
                    "description": "Note title (optional - will auto-generate if not provided)",
                },
                "fields": {
                    "type": "object",
                    "description": "Template fields to fill in (varies by template)",
                },
                "extra_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional tags beyond template defaults",
                },
            },
            "required": ["template", "fields"],
        },
    ),
    Tool(
        name="save_session_summary",
        description="Save a summary at the end of a work session. Captures what was accomplished, decisions made, and what's next. USE THIS before ending significant conversations.",
        inputSchema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief 1-2 sentence summary of the session",
                },
                "accomplished": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of things accomplished this session",
                },
                "decisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key decisions made (optional)",
                },
                "open_items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Items still pending or blocked (optional)",
                },
                "next_session": {
                    "type": "string",
                    "description": "What to pick up next time (optional)",
                },
                "project": {"type": "string", "description": "Project name for tagging (optional)"},
                "topic": {
                    "type": "string",
                    "description": "Topic/focus of this session for the title (optional)",
                },
            },
            "required": ["summary", "accomplished"],
        },
    ),
    Tool(
        name="save_decision",
        description="Record an important decision with full context and reasoning. Use this when a significant choice is made so it can be referenced later.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the decision (e.g., 'JWT vs Sessions')",
                },
                "context": {
                    "type": "string",
                    "description": "Background - why was this decision needed?",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Options that were considered",
                },
                "decision": {"type": "string", "description": "What was decided"},
                "reasoning": {"type": "string", "description": "Why this option was chosen"},
                "implications": {
                    "type": "string",
                    "description": "What this means going forward (optional)",
                },
                "project": {"type": "string", "description": "Project name for tagging (optional)"},
            },
            "required": ["title", "context", "options", "decision", "reasoning"],
        },
    ),
    Tool(
        name="get_context",
        description="Search notes and return excerpts with relevance info, plus any matching followup reminders and graph-local context. Use this at session start to bootstrap context on a topic.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic or keywords to build context around",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of notes to return",
                },
                "graph_depth": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "How far to expand from the best matching note in the graph",
                },
                "graph_limit": {
                    "type": "integer",
                    "default": 8,
                    "description": "Maximum number of graph-neighbor notes to include",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_note_summary",
        description="Get a note's metadata and a truncated body preview without loading the full content. Useful for deciding whether to load a note in full.",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Note ID or title"},
                "max_chars": {
                    "type": "integer",
                    "default": 500,
                    "description": "Maximum characters to return from the body",
                },
            },
            "required": ["identifier"],
        },
    ),
    Tool(
        name="list_stale_notes",
        description="List notes whose 'expires' frontmatter date is in the past. Useful for identifying outdated information.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="add_followup",
        description="Add a persistent followup reminder to the vault. Reminders survive across sessions and can be retrieved with list_followups.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Short topic label for the reminder"},
                "reminder": {"type": "string", "description": "The reminder text"},
            },
            "required": ["topic", "reminder"],
        },
    ),
    Tool(
        name="list_followups",
        description="List all persistent followup reminders stored in the vault.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="dismiss_followup",
        description="Dismiss (delete) a followup reminder by its ID.",
        inputSchema={
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Followup ID to dismiss"}},
            "required": ["id"],
        },
    ),
]
