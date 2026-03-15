# linked-notes-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

`linked-notes-mcp` is a graph-first local memory layer for AI agents built on MCP. It keeps markdown notes structured, retrievable, and maintainable so local agent memory does not collapse into an unstructured pile of `.md` files.

The core idea is simple: agent memory should be local, editable, and structurally explicit. Notes live on disk as markdown. Links and frontmatter become graph edges. Retrieval can use both text and graph structure. Humans can inspect the result at any time.

It is designed for agent-authored memory first: notes are optimized for retrieval, review, and long-term maintenance using frontmatter fields like `entity_type`, `summary`, `status`, `importance`, `confidence`, and `last_reviewed`.

The model is domain-agnostic and works for technical and non-technical work alike: projects, repositories, services, issues, stakeholders, meetings, research, initiatives, and workstreams.

## Thesis

Most local note-based memory fails for agents for the same reason it fails for humans at scale: the notes exist, but the structure does not.

`linked-notes-mcp` is built around a narrower claim:

- keep the source of truth local
- keep the memory human-readable
- keep the structure explicit enough for agents to retrieve and maintain it

This is not a cognition stack. It is the durable memory layer underneath one.

## Who This Is For

This project is a good fit if you want:

- local-first agent memory
- durable project and decision context across sessions
- a shared memory format that humans can inspect and edit
- structured notes instead of free-form markdown sprawl
- compatibility across MCP clients and agents

It is a poor fit if you want:

- a hosted memory product
- passive memory of every conversation without curation
- a replacement for short-term working context
- a generic database for arbitrary high-volume event logging

## Why This Exists

Most AI memory ends up in one of three forms:

- chat transcripts that are hard to reuse
- vector memory that is hard to inspect
- plain notes with weak structural context

`linked-notes-mcp` is for the case where you want memory to be:

- local and portable
- readable and editable without proprietary tooling
- graph-shaped instead of flat
- durable across sessions and across different MCP clients
- maintainable by both humans and agents

This makes it a good fit for open source use. The value is not monetization or hosted infrastructure. The value is having a shared memory graph that stays under your control.

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
- staged seed ingestion for local files and inline text
- write tools for persistent agent memory
- Obsidian-compatible markdown folders

## Selling Point

The selling point is not "an MCP for notes."

The selling point is: `linked-notes-mcp` gives agents a shared markdown memory graph that humans can inspect, edit, and improve over time.

That matters because it means:

- project context survives beyond one chat
- decisions and dependencies become explicit instead of implied
- memory can be reviewed and cleaned up with dashboard and lint tools
- the same vault can be used across Claude, Codex, and other MCP clients

## Practical Use Cases

### Project continuity

Start a new session by asking for context on a project. Instead of re-explaining the entire background, the agent can pull the project note, nearby services, recent decisions, and open followups from the graph.

### Decision archaeology

When someone asks "why did we choose this?", the graph can connect a project or service node to the decision note that justified it, and then to supporting research or meetings.

### Blocker tracing

When work is stuck, graph retrieval can follow `blocked_by`, `blocks`, and `depends_on` relationships instead of relying on raw keyword matches.

### Handoffs and onboarding

A new agent or teammate can start from a project node and expand outward through services, issues, decisions, and stakeholders instead of reading a flat directory of notes.

### Seeded memory plus ongoing enrichment

The long-term direction is to ingest source material up front, stage structured memory candidates, and then let normal conversation flows keep enriching the accepted graph over time.

## Why Graph Retrieval Helps

Plain search tells you which notes mention a word.

Graph retrieval helps answer questions like:

- what is blocking this work
- what depends on this service
- which decision affects this project
- what context should I read next

That is useful because many real work questions are about relationships, not documents in isolation.

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
uv run python scripts/run_linked_notes_mcp.py /path/to/your/notes
```

The launcher script imports from `src/` directly, which keeps local-clone MCP setups working even if an environment's editable install support is unreliable.

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
args = ["run", "--directory", "/absolute/path/to/linked-notes-mcp", "python", "scripts/run_linked_notes_mcp.py", "/path/to/your/notes"]
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
| `create_from_template(template, fields, ...)` | Start new notes from a consistent shape instead of inventing structure each time |
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

### Ingestion Tools

| Tool | What it is good for |
|------|----------------------|
| `ingest_sources(...)` | Stage candidate memory nodes from local files or inline text |
| `list_ingestion_runs(...)` | Review recent staged ingestion runs |
| `review_extracted_nodes(...)` | Inspect candidates before promotion |
| `accept_extracted_node(...)` | Promote a candidate into the graph or merge a clear match |
| `reject_extracted_node(...)` | Reject a low-value candidate and keep review history |
| `merge_extracted_node(...)` | Merge a candidate into a specific existing note |

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

## Template-First Workflow

The best experience with this MCP is template-first, not free-form note creation.

Recommended pattern:

1. Start with `list_templates()` when entering a new domain or workflow.
2. Use `create_from_template(...)` for the first version of a note whenever possible.
3. Use `upsert_memory_node(...)` when you need stronger machine-friendly frontmatter or want to refine an existing note.
4. Use `promote_to_memory_node(...)` for messy raw output that should become structured memory after the fact.

In practice:

- use `repo_project` for codebases and repositories
- use `service` for systems and components
- use `issue` for bugs and blockers
- use `decision` for architectural choices
- use `session` for end-of-session summaries
- use `research`, `initiative`, `workstream`, and `stakeholder` for broader operating context

Followups are stored in `.linked_notes_followups.json` in the vault root. Add that file to `.gitignore` if you do not want reminders committed.

## Known Limitations

This project is intentionally opinionated and still early.

Current limits:

- it works best when notes use structured frontmatter consistently
- it is optimized for durable explicit memory, not full conversational recall
- graph quality still depends on review and maintenance over time
- mutation and retrieval behavior are tested, but the project is still evolving quickly
- seed ingestion v1 is implemented, but only for staged local file and inline text flows
- there is not yet a higher-level UX for session-start, session-end, or compact review workflows

Planned next step:

- improve the UX layer on top of the memory graph so common flows feel like workflows instead of raw tool choreography

## Next Steps

The most likely direction from here is not turning `linked-notes-mcp` into a larger all-in-one system. It is keeping this repo as the local memory substrate and validating a small set of companion add-ons that write durable, graph-shaped memory into it.

Examples worth validating before building:

- `repo-context-mcp` for durable repository and codebase memory
- `jira-context-mcp` for durable execution memory around epics, blockers, dependencies, and workstreams
- business-process or operating-context ingestion for recurring workflows, owners, risks, and exceptions

The design rule for these add-ons is simple:

- do not mirror source systems wholesale
- extract only durable, high-value context
- emit structured notes and typed relationships into the same local graph

This is intentionally framed as a validation direction, not a committed build plan. The right next move is to test whether people actually want domain-specific memory producers on top of a shared local memory layer.

## Suggested Workflow

### Session start

1. Ask for `get_context("project or topic")`
2. If one note is clearly central, call `get_graph_context` on it
3. Traverse or inspect `list_relationships` before making changes
4. Use `memory_dashboard()` when you want a compact view of what needs maintenance

### During work

1. Update notes with new links and frontmatter relationships
2. Prefer `create_from_template` for new notes, then refine with `upsert_memory_node` and `update_relationships`
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
uv run python scripts/run_linked_notes_mcp.py /path/to/test/vault
```

## Docs

- [Quickstart](docs/QUICKSTART.md)
- [Guide](docs/GUIDE.md)
- [Usage Rules](docs/USAGE-RULES.md)
- [Autonomous Agent Integration](docs/COWORK-INTEGRATION.md)
- [Seed Context Ingestion Spec](docs/INGESTION-SPEC.md)
- [UX Roadmap](docs/UX-ROADMAP.md)

## Comparison with Memory Styles

| Memory style | Strengths | Weaknesses |
|--------------|-----------|------------|
| Graph-first markdown memory | Transparent, editable, deterministic, good for dependencies/decisions | Requires you to maintain structure |
| Vector memory | Good fuzzy recall | Opaque, harder to audit, weaker explicit structure |
| Plain note search | Simple | Misses structural context |

linked-notes-mcp is for the case where you want agent memory to be a real graph you can inspect and control, not just a retrieval backend.

## License

MIT License. See [LICENSE](LICENSE).
