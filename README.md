# linked-notes-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

`linked-notes-mcp` is a graph-first local memory system for AI agents built on MCP. It stores memory as structured markdown nodes plus typed relationships, so agents can retrieve, update, review, and maintain knowledge as an explicit graph instead of relying only on opaque vector memory.

It is designed for agent-authored memory first: notes are optimized for retrieval, review, and long-term maintenance using frontmatter fields like `entity_type`, `summary`, `status`, `importance`, `confidence`, and `last_reviewed`.

The model is domain-agnostic and works for technical and non-technical work alike: projects, services, issues, stakeholders, meetings, research, initiatives, and workstreams.

## Why Graph Memory

This repo is optimized for explicit memory:

- notes are nodes
- wikilinks and markdown links are edges
- frontmatter relationships create typed edges like `depends_on`, `blocks`, and `related_to`
- retrieval can expand from a note through the graph instead of only doing text search

That makes memory:

- inspectable
- deterministic
- easy to edit by hand
- better suited to project context, dependencies, decisions, and followups

## Agent-First Note Shape

Prefer notes with machine-friendly frontmatter like this:

```yaml
---
title: API Gateway
aliases:
  - Gateway
entity_type: service
project: graph-memory
status: active
summary: Entry point for requests and coordinator for auth and downstream services.
depends_on:
  - Auth Service
related_to:
  - User Service
---
```

Why these fields matter:

- `aliases` makes lookup more forgiving
- `entity_type` helps agents separate projects, services, decisions, and sessions
- `project` lets retrieval group notes by workstream
- `status` helps distinguish active vs stale memory
- `summary` gives a short retrieval target that is better than scraping prose from the body
- `importance`, `confidence`, and `last_reviewed` help ranking and memory quality checks

## Features

- zero config markdown vaults
- wikilink support: `[[Target]]` and `[[Target|Label]]`
- standard markdown links
- typed graph relationships from frontmatter
- graph traversal and path finding
- graph-first context retrieval
- write tools for persistent agent memory
- Obsidian-compatible markdown folders

## Installation

The package is not published to PyPI yet. Use one of these install paths instead.

### One-off with `uvx`

```bash
uvx --from git+https://github.com/rgodse/linked-notes-mcp linked-notes-mcp /path/to/your/notes
```

### Local clone

```bash
git clone https://github.com/rgodse/linked-notes-mcp
cd linked-notes-mcp
uv sync
uv run linked-notes-mcp /path/to/your/notes
```

## Codex Configuration

Add this to `~/.codex/config.toml`:

```toml
[features]
rmcp_client = true

[mcp_servers.linked_notes]
command = "uvx"
args = ["--from", "git+https://github.com/rgodse/linked-notes-mcp", "linked-notes-mcp", "/path/to/your/notes"]
```

Or, if you cloned the repo locally:

```toml
[features]
rmcp_client = true

[mcp_servers.linked_notes]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/linked-notes-mcp", "linked-notes-mcp", "/path/to/your/notes"]
```

Restart Codex after updating the config.

## Claude Desktop Configuration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "notes": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/rgodse/linked-notes-mcp",
        "linked-notes-mcp",
        "/path/to/your/notes"
      ]
    }
  }
}
```

## Graph Model

### Inline links

Markdown content creates regular graph edges:

```md
[[Auth Service]]
[Database Design](database-design.md)
```

### Typed relationships

Frontmatter creates explicit semantic edges:

```yaml
---
title: API Gateway
tags: [architecture, backend]
depends_on:
  - Auth Service
  - Database Design
blocks:
  - Deployment Strategy
related_to:
  - User Service
---
```

Supported relationship fields:

- `depends_on`
- `blocks`
- `blocked_by`
- `related_to`
- `part_of`
- `contains`
- `decision_for`
- `decided_by`
- `supersedes`
- `superseded_by`

The body should still exist, but treat it as supporting detail. The frontmatter should carry the retrieval-critical facts.

## High-Value Tools

### Graph Tools

| Tool | What it is good for |
|------|----------------------|
| `list_relationships(identifier, direction?, relation_type?)` | Inspect explicit memory edges for a note |
| `get_graph_context(identifier, depth?, limit?, relation_types?)` | Expand nearby nodes and edges around an anchor note |
| `traverse(start_id, depth?, direction?, relation_types?)` | Walk the graph outward |
| `find_path(start_id, end_id)` | See how two notes connect |
| `graph_summary()` | Quick structural overview of the vault |

### Retrieval Tools

| Tool | What it is good for |
|------|----------------------|
| `get_context(query, limit?, graph_depth?, graph_limit?)` | Search notes and also expand graph context around the best match |
| `search(query, limit?)` | Raw text search |
| `get_note_summary(identifier, max_chars?)` | Cheap preview before loading a full note |
| `get_note(identifier)` | Full note read |

### Write Tools

| Tool | What it is good for |
|------|----------------------|
| `upsert_memory_node(...)` | Create or update a structured memory node with agent-friendly frontmatter |
| `update_relationships(identifier, add?, remove?, replace?)` | Edit graph relationships without rewriting note bodies |
| `create_note(title, content, tags?, filename?)` | Create new notes |
| `update_note(identifier, content?, title?, tags?)` | Replace note content or metadata |
| `append_to_note(identifier, content)` | Add updates without replacing the whole note |
| `save_session_summary(...)` | Structured session memory |
| `save_decision(...)` | Decision log with rationale |
| `add_followup(topic, reminder)` | Persistent reminder across sessions |

### Maintenance Tools

| Tool | What it is good for |
|------|----------------------|
| `lint_memory_graph()` | Find weak nodes missing structure or freshness metadata |
| `suggest_relationships(limit?)` | Propose likely graph edges from shared structure |
| `merge_memory_nodes(source, target)` | Merge duplicate or overlapping memory nodes |
| `get_memory_health(identifier?)` | Score nodes by retrieval-readiness |
| `review_relationship_suggestions(...)` | See pending/accepted/rejected suggestions |
| `accept_relationship_suggestion(...)` | Apply a reviewed relationship suggestion |
| `reject_relationship_suggestion(...)` | Record a rejected suggestion so it stops resurfacing |
| `memory_dashboard(...)` | Compact operational view of weak notes, stale notes, and pending suggestions |
| `promote_to_memory_node(...)` | Convert raw work output into a structured memory node |

### Template Coverage

Templates now cover both technical and non-technical work:

- `repo_project`
- `service`
- `issue`
- `initiative`
- `workstream`
- `stakeholder`
- `research`
- `project`
- `meeting`
- `decision`
- `session`
- `idea`
- `learning`

Followups are stored in `.linked_notes_followups.json` in the vault root. Add that file to `.gitignore` if you do not want reminders committed.

## Suggested Workflow

### Session start

1. Ask for `get_context("project or topic")`
2. If one note is clearly central, call `get_graph_context` on it
3. Traverse or inspect `list_relationships` before making changes
4. Use `memory_dashboard()` when you want a compact view of what needs maintenance

### During work

1. Update notes with new links and frontmatter relationships
2. Prefer `upsert_memory_node` and `update_relationships` for durable graph memory objects
3. Save decisions explicitly
4. Add followups for anything that should survive the session
5. Use `promote_to_memory_node` when you have raw notes or messy outputs that should become structured memory

### Session end

1. Save a structured session summary
2. Link it to the project or decision notes it touched
3. Add or dismiss followups

### Maintenance pass

Run this periodically:

1. `lint_memory_graph()`
2. `get_memory_health()`
3. `review_relationship_suggestions()`
4. accept or reject good suggestions
5. `merge_memory_nodes(...)` for duplicates
6. refresh `last_reviewed`, `importance`, and `confidence`

Accepted and rejected suggestions are tracked over time, and review confidence is surfaced alongside future suggestions.

## Development

```bash
git clone https://github.com/rgodse/linked-notes-mcp
cd linked-notes-mcp
uv sync --dev
uv run pytest
uv run linked-notes-mcp /path/to/test/vault
```

## Comparison with Memory Styles

| Memory style | Strengths | Weaknesses |
|--------------|-----------|------------|
| Graph-first markdown memory | Transparent, editable, deterministic, good for dependencies/decisions | Requires you to maintain structure |
| Vector memory | Good fuzzy recall | Opaque, harder to audit, weaker explicit structure |
| Plain note search | Simple | Misses structural context |

linked-notes-mcp is for the case where you want agent memory to be a real graph you can inspect and control, not just a retrieval backend.

## License

MIT License. See [LICENSE](LICENSE).
