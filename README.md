# linked-notes-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Graph-first local memory layer for AI agents built on MCP. Notes live on disk as markdown. Links and frontmatter become graph edges. Retrieval uses both text and graph structure. Humans can inspect and edit everything.

Built for agent-authored memory: notes are optimized for retrieval, review, and long-term maintenance using structured frontmatter (`entity_type`, `summary`, `status`, `importance`, `confidence`, `last_reviewed`). Works for technical and non-technical work alike.

## Who This Is For

- teams using Codex, Claude, or other MCP clients repeatedly on the same projects
- people who want durable project context outside chat history
- workflows where humans may want to inspect or edit the memory directly in markdown
- work that depends on relationships such as dependencies, blockers, decisions, owners, and followups

## Who This Is Not For

- passive memory of every conversation
- a hosted wiki, ticket system, or general database
- full conversational recall without curation
- teams that do not want to maintain structured notes at all

## Why graph memory

Plain search tells you which notes mention a word. Graph retrieval answers questions like:

- what is blocking this work
- what depends on this service
- which decision affects this project
- what context should I read next

That matters because most real project questions are about relationships, not documents in isolation. Notes are nodes, wikilinks are edges, and frontmatter fields like `depends_on`, `blocks`, and `related_to` create typed edges you can traverse and filter.

## Why This Over Plain Notes or Chat History

- chat history is fragile and session-bound
- plain markdown is readable but weak at dependencies, blockers, and decision tracing
- vector-only memory is hard to inspect and hard to fix when it drifts
- graph-shaped markdown keeps the source of truth local while making relationships explicit

## Five-Minute Workflow

1. Point `linked-notes-mcp` at a markdown folder.
2. Connect to it from Codex or Claude.
3. Create one project or repo note with `create_from_template(...)`.
4. Add one service, issue, or decision note linked to that project.
5. In the next session, use `start_session(...)` or `get_context(...)` to recover context instead of re-explaining it.

## Quick Start

### Run the MCP server

```bash
uvx --from git+https://github.com/rgodse/linked-notes-mcp linked-notes-mcp /path/to/your/notes
```

## Agent-First Note Shape

Prefer notes with machine-friendly frontmatter:

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
- `entity_type` lets agents separate projects, services, decisions, and sessions
- `project` groups notes by workstream
- `status` distinguishes active vs stale memory
- `summary` gives a short retrieval target better than scraping prose
- `importance`, `confidence`, `last_reviewed` drive health scoring and maintenance

The body still matters, but treat it as supporting detail. Frontmatter carries the retrieval-critical facts.

## Recommended Usage with Codex and Claude

The main path is interactive note creation and maintenance during normal work.

- use `create_from_template(...)` for new notes
- use `upsert_memory_node(...)` and `update_relationships(...)` as the work evolves
- use `save_decision(...)` and `end_session(...)` to preserve reasoning between sessions

This is the intended workflow: the model writes and maintains structured notes while you work, and future sessions recover context from the graph.

## Concrete Example

One realistic loop:

1. Create a repo note for `linked-notes-mcp`.
2. Create a `service` note for the MCP server and mark it `part_of` the repo project.
3. Create an `issue` note for a broken graph edge case and mark it `blocked_by` another service or dependency.
4. Save a `decision` note explaining a key architectural choice.
5. Start the next session with `start_session(topic="linked-notes-mcp", project="linked-notes-mcp")`.

At that point the agent can recover the active project, nearby services, recent decisions, stale notes, and open followups from local markdown instead of from memory or chat history.

## Features

- zero config markdown vaults — point at any folder of `.md` files
- wikilink support: `[[Target]]` and `[[Target|Label]]`
- standard markdown links
- typed graph relationships from frontmatter
- graph traversal and path finding
- graph-first context retrieval
- write tools for persistent agent memory
- Obsidian-compatible

## Tools

### Graph Tools

| Tool | What it is good for |
|------|----------------------|
| `list_relationships(identifier, direction?, relation_type?)` | Inspect explicit memory edges for a note |
| `get_graph_context(identifier, depth?, limit?, relation_types?)` | Expand nearby nodes and edges around an anchor note |
| `traverse(start_id, depth?, direction?, relation_types?)` | Walk the graph outward |
| `find_path(start_id, end_id)` | See how two notes connect |
| `list_tags()` | Tag inventory with usage counts |
| `notes_by_tag(tag)` | All notes with a specific tag |
| `graph_summary()` | Quick structural overview of the vault |
| `list_notes(limit?)` | List all notes (brief info) |
| `rebuild()` | Refresh the index after file changes |

### Retrieval Tools

| Tool | What it is good for |
|------|----------------------|
| `get_context(query, limit?, graph_depth?, graph_limit?)` | Search notes and expand graph context around the best match |
| `search(query, limit?)` | Raw text search |
| `get_note(identifier)` | Full note read |
| `get_note_summary(identifier, max_chars?)` | Cheap preview before loading a full note |
| `list_stale_notes()` | Notes whose `expires` frontmatter date is in the past |

### Write Tools

| Tool | What it is good for |
|------|----------------------|
| `create_from_template(template, fields, ...)` | Start new notes from a consistent shape |
| `upsert_memory_node(...)` | Create or update a structured memory node with agent-friendly frontmatter |
| `update_relationships(identifier, add?, remove?, replace?)` | Edit graph relationships without rewriting note bodies |
| `create_note(title, content, tags?, filename?)` | Create new notes |
| `update_note(identifier, content?, title?, tags?)` | Replace note content or metadata |
| `append_to_note(identifier, content)` | Add updates without replacing the whole note |
| `delete_note(identifier)` | Delete a note from the vault |
| `save_decision(...)` | Decision log with rationale |
| `add_followup(topic, reminder)` | Persistent reminder across sessions |
| `list_followups()` | List all pending followup reminders |
| `dismiss_followup(id)` | Remove a followup reminder by ID |

### Maintenance Tools

| Tool | What it is good for |
|------|----------------------|
| `lint_memory_graph()` | Find weak nodes missing structure or freshness metadata |
| `suggest_relationships(limit?)` | Propose likely graph edges from shared structure |
| `merge_memory_nodes(source, target)` | Merge duplicate or overlapping memory nodes |
| `promote_to_memory_node(...)` | Convert raw work output into a structured memory node |

### Session Tools

| Tool | What it is good for |
|------|----------------------|
| `start_session(...)` | Build a compact working brief from search, graph context, followups, stale notes, and recent sessions |
| `end_session(...)` | Save a session summary, update touched notes, create followups for open items |

## Templates

Use `create_from_template(template, fields)` with any of these:

| Template | Use for | Emits frontmatter defaults |
|----------|---------|---------------------------|
| `repo_project` | Codebases and repositories | `entity_type=project`, `status=active`, `importance=high`, `confidence=0.8` |
| `service` | Systems and components | `entity_type=service`, `status=active`, `importance=high`, `confidence=0.8` |
| `issue` | Bugs and blockers | `entity_type=issue`, `status=open`, `importance=high`, `confidence=0.7` |
| `initiative` | Cross-team programs | `entity_type=project`, `status=active`, `importance=high`, `confidence=0.75` |
| `workstream` | Ongoing processes | `entity_type=workstream`, `status=active`, `importance=high`, `confidence=0.8` |
| `stakeholder` | People and teams | `entity_type=person`, `status=active`, `importance=medium`, `confidence=0.75` |
| `research` | Findings and supporting evidence | `entity_type=concept`, `status=active`, `importance=medium`, `confidence=0.6` |
| `project` | General projects | `entity_type=project`, `status=active`, `importance=high`, `confidence=0.75` |
| `decision` | Architectural and product choices | `entity_type=decision`, `status=decided`, `importance=high`, `confidence=0.9` |
| `meeting` | Meeting notes and outcomes | `entity_type=process`, `status=done`, `importance=medium`, `confidence=0.8` |
| `session` | End-of-session summaries | `entity_type=session`, `status=done`, `importance=medium`, `confidence=0.8` |
| `idea` | Proposals and explorations | `entity_type=concept`, `status=draft`, `importance=low`, `confidence=0.4` |
| `bug` | Bug reports | `entity_type=issue`, `status=open`, `importance=high`, `confidence=0.75` |
| `learning` | Learnings and reference notes | `entity_type=concept`, `status=active`, `importance=low`, `confidence=0.7` |

**Template-first workflow:**
1. Call `list_templates()` to see available shapes
2. Use `create_from_template(...)` for new notes whenever possible
3. Pass relationship fields like `depends_on`, `blocked_by`, `part_of`, `decision_for`, or `related_to` at creation time when you know them
4. Refine with `upsert_memory_node(...)` when summary, status, or project metadata changes materially
5. Use `update_relationships(...)` when graph edges change after the note exists
6. Use `promote_to_memory_node(...)` for messy raw output after the fact

### Template Workflow Example

For a new service note:

```json
{
  "template": "service",
  "title": "Payments Service",
  "fields": {
    "summary": "Handles billing and subscription lifecycle events.",
    "project": "core-platform",
    "responsibilities": ["Charge cards", "Sync invoices"],
    "owners": ["Platform Team"],
    "depends_on": ["Auth Service", "Ledger Service"],
    "related_to": ["Billing Dashboard"],
    "runbook": "Pager rotation lives in Ops handbook."
  }
}
```

This now creates a note with machine-friendly frontmatter such as:

```yaml
---
entity_type: service
summary: Handles billing and subscription lifecycle events.
project: core-platform
status: active
importance: high
confidence: 0.8
depends_on:
  - Auth Service
  - Ledger Service
related_to:
  - Billing Dashboard
---
```

### Good Template Inputs

Prefer these fields when they apply:
- `summary`: one or two sentences, retrieval-friendly, not prose sprawl
- `project`: stable project or workstream grouping
- relationship fields: actual note titles, not IDs or vague phrases
- `owners`, `next_actions`, `risks`, `concerns`: bullet-list-friendly facts
- `importance` and `confidence`: override defaults only when you have a reason

## Suggested Workflow

### Session start

1. `get_context("project or topic")` to bootstrap context
2. If one note is clearly central, call `get_graph_context` on it
3. Check `list_relationships` before making changes

### During work

1. Update notes with new links and frontmatter relationships
2. Prefer `create_from_template` for new notes, refine with `upsert_memory_node` and `update_relationships`
3. Save decisions explicitly with `save_decision`
4. `add_followup` for anything that should survive the session

### Session end

1. `end_session(...)` — saves summary, links touched notes, handles followups

### Maintenance pass

1. `lint_memory_graph()`
2. `suggest_relationships()` — review proposed edges
3. `merge_memory_nodes(...)` for duplicates
4. Refresh `last_reviewed`, `importance`, `confidence` on key notes

## Graph Model

### Inline links

```md
[[Auth Service]]
[Database Design](database-design.md)
```

### Typed relationships (frontmatter)

```yaml
---
title: API Gateway
depends_on:
  - Auth Service
  - Database Design
blocks:
  - Deployment Strategy
related_to:
  - User Service
---
```

Supported relationship fields: `depends_on`, `blocks`, `blocked_by`, `related_to`, `part_of`, `contains`, `decision_for`, `decided_by`, `supersedes`, `superseded_by`

## Installation

Not yet published to PyPI. Use one of these:

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

## Codex Configuration

Add to `~/.codex/config.toml`:

```toml
[features]
rmcp_client = true

[mcp_servers.linked_notes]
command = "uvx"
args = ["--from", "git+https://github.com/rgodse/linked-notes-mcp", "linked-notes-mcp", "/path/to/your/notes"]
```

Or with a local clone:

```toml
[features]
rmcp_client = true

[mcp_servers.linked_notes]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/linked-notes-mcp", "python", "scripts/run_linked_notes_mcp.py", "/path/to/your/notes"]
```

## Retrieval: measured, not guessed

Most memory tools claim their retrieval is good; the field's public benchmarks
contradict each other and don't reproduce. This repo ships a **local, reproducible
retrieval benchmark** instead — recall@5 / MRR with bootstrap 95% CIs, over a
committed synthetic vault (60 notes + 40 query→gold pairs). Full write-up:
[`results.md`](results.md); harness in [`evals/`](evals) + [`optimize/`](optimize).

**What it caught.** The first run scored `text: recall@5 = 0.00`. Not a weak
baseline — a *broken* one: `search` matched the whole query as a substring, so
`get_context` returned **nothing** for natural-language questions (single keywords
worked; questions didn't). Tokenizing search fixed it — **recall@5 0.00 → 0.81**.
That bug fix, surfaced by the benchmark, was the biggest retrieval win here, and it
shipped in the server.

| Rung | recall@5 | 95% CI | MRR |
|---|---|---|---|
| text (tokenized) | **0.81** | 0.71–0.90 | 0.82 |
| + salience (importance-weighted) | 0.81 | 0.71–0.90 | 0.82 |
| + hybrid (FastEmbed vectors) | 0.82 | 0.72–0.91 | 0.84 |

**The honest finding.** Salience and hybrid embeddings show **no significant lift**
on this vault — the CIs overlap; well-tokenized lexical search is already enough.
The likely cause is a stated limitation, not a triumph: the queries were written by
the same model as the notes, so they share vocabulary and lexical search saturates,
leaving embeddings nothing to recover. On real vaults with a genuine paraphrase gap,
hybrid should help — but *this* benchmark can't prove it, so it doesn't claim it.
Hybrid ships as an optional `[embeddings]` extra (local FastEmbed, no API); the
server falls back to text-only without it.

Reproduce: `uv sync --extra embeddings && uv run python -m optimize.run`.

## Known Limitations and Roadmap

Current limits:
- works best when notes use structured frontmatter consistently
- optimized for durable explicit memory, not full conversational recall
- graph quality depends on review and maintenance over time

Planned directions:
- `repo-context-mcp` — durable repository and codebase memory as a companion producer
- `jira-context-mcp`, `meeting-context-mcp`, `research-context-mcp` — domain-specific memory producers writing into the same local graph
- graph diff for understanding how memory changes over time
- improved graph readability and richer repo/process-specific note generation

The design rule for companion producers: don't mirror source systems wholesale — extract only durable, high-value context and emit structured notes with typed relationships into the local graph.

## Comparison with Adjacent Tools

| Project | Primary model | How `linked-notes-mcp` differs |
|---------|---------------|--------------------------------|
| [Anthropic Memory MCP](https://modelcontextprotocol.io/examples) | local knowledge graph with entities, relations, observations | markdown-vault-first; optimized for human-editable durable notes rather than a standalone entity store |
| [Vault MCP / Obsidian MCP Plugin](https://github.com/jlevere/obsidian-mcp-plugin) | Obsidian vault access through MCP | more opinionated about graph shape, typed relationships, maintenance, and agent-first workflows |
| [knowledgegraph-mcp](https://github.com/n-r-w/knowledgegraph-mcp) | knowledge graph with SQLite/PostgreSQL backends | keeps markdown as the canonical layer; leans harder on inspectability, staged review, and human-maintained quality |
| [RepoMemory](https://mcpmarket.com/server/repomemory) | repo-aware memory graph backed by SQLite | broader than repo memory; treats repo intelligence as one future producer writing into a general local graph |

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

## License

MIT License. See [LICENSE](LICENSE).
