# linked-notes-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Graph-first local memory layer for AI agents built on MCP. Notes live on disk as markdown. Links and frontmatter become graph edges. Retrieval uses both text and graph structure. Humans can inspect and edit everything.

Built for agent-authored memory: notes are optimized for retrieval, review, and long-term maintenance using structured frontmatter (`entity_type`, `summary`, `status`, `importance`, `confidence`, `last_reviewed`). Works for technical and non-technical work alike.

## Why graph memory

Plain search tells you which notes mention a word. Graph retrieval answers questions like:

- what is blocking this work
- what depends on this service
- which decision affects this project
- what context should I read next

That matters because most real project questions are about relationships, not documents in isolation. Notes are nodes, wikilinks are edges, and frontmatter fields like `depends_on`, `blocks`, and `related_to` create typed edges you can traverse and filter.

## Quick Start

### Run the MCP server

```bash
uvx --from git+https://github.com/rgodse/linked-notes-mcp linked-notes-mcp /path/to/your/notes
```

### Run the local visualizer

```bash
git clone https://github.com/rgodse/linked-notes-mcp
cd linked-notes-mcp
uv sync
uv run python scripts/run_linked_notes_ui.py /path/to/your/notes
```

Then open `http://127.0.0.1:8765` in your browser.

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

## Features

- zero config markdown vaults — point at any folder of `.md` files
- wikilink support: `[[Target]]` and `[[Target|Label]]`
- standard markdown links
- typed graph relationships from frontmatter
- graph traversal and path finding
- graph-first context retrieval
- staged seed ingestion for local files and inline text
- write tools for persistent agent memory
- local browser visualizer
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
| `save_session_summary(...)` | Structured session memory |
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
| `get_memory_health(identifier?)` | Score nodes by retrieval-readiness |
| `review_relationship_suggestions(...)` | See pending/accepted/rejected suggestions |
| `accept_relationship_suggestion(...)` | Apply a reviewed relationship suggestion |
| `reject_relationship_suggestion(...)` | Record a rejected suggestion so it stops resurfacing |
| `memory_dashboard(...)` | Compact view of weak notes, stale notes, and pending suggestions |
| `promote_to_memory_node(...)` | Convert raw work output into a structured memory node |

### Ingestion Tools

| Tool | What it is good for |
|------|----------------------|
| `ingest_sources(...)` | Stage candidate memory nodes from local files, directories, glob patterns, or inline text |
| `list_ingestion_runs(...)` | Review recent staged ingestion runs |
| `review_extracted_nodes(...)` | Inspect candidates before promotion |
| `accept_extracted_node(...)` | Promote a candidate into the graph (exact duplicates auto-merge; ambiguous matches surface a `merge_suggestion`) |
| `reject_extracted_node(...)` | Reject a low-value candidate |
| `merge_extracted_node(...)` | Merge a candidate into a specific existing note |
| `accept_all_candidates(...)` | Bulk-accept pending candidates for a run |
| `reject_all_candidates(...)` | Bulk-reject pending candidates for a run |

## LLM-Assisted Ingestion

`ingest_sources` can optionally call an LLM to extract multiple structured memory node candidates from each document — including entities that a simple heuristic would miss. By default, ingestion stays heuristic-first even if LLM credentials are configured. This keeps the normal Codex/Claude note workflow simple and deterministic.

Pass `use_llm=true` only when you want a richer batch import or seed extraction pass.

### Configuration

Create `<vault>/.linked-notes-config.json` (add to `.gitignore`):

```json
{
  "llm": {
    "model":    "gpt-4o-mini",
    "api_key":  "YOUR_KEY_HERE",
    "base_url": null
  }
}
```

Set `model` using [litellm's model naming](https://docs.litellm.ai/docs/providers):

| Provider | `model` value |
|----------|--------------|
| OpenAI | `gpt-4o-mini` |
| Anthropic | `claude-haiku-4-5-20251001` |
| Google Gemini | `gemini/gemini-1.5-flash` |
| Groq | `groq/llama-3.1-8b-instant` |
| Ollama (local) | `openai/llama3` + `"base_url": "http://localhost:11434/v1"` |

Then install litellm:

```bash
uv add "linked-notes-mcp[llm]"
```

### Environment variable fallback

If no config file is present, the server reads env vars:

```bash
# Generic
LLM_API_KEY=...   LLM_MODEL=gpt-4o-mini   LLM_BASE_URL=https://...

# Legacy — still supported
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

### How extraction works

1. If `use_llm=true` and an LLM is configured, a single API call extracts all distinct entities from the document as separate candidates.
2. Otherwise, the document is split on H2/H3 headings (when ≥ 2 headings exist and the document is > 300 chars) — each section becomes one candidate.
3. Re-running `ingest_sources` on the same file or text is safe — already-seen content is detected by checksum and skipped.
4. Accepted notes carry provenance frontmatter (`confidence`, `last_reviewed`, `source_refs`, `derived_from`).

### Workflow Tools

| Tool | What it is good for |
|------|----------------------|
| `start_session(...)` | Build a compact working brief from search, graph context, followups, stale notes, and recent sessions |
| `review_memory(...)` | Combined queue of weak notes, stale notes, relationship suggestions, and pending ingestion candidates |
| `review_queue(...)` | Prioritized triage queue of highest-value memory actions |
| `end_session(...)` | Save a session summary, update touched notes, create followups for open items |

## Templates

Use `create_from_template(template, fields)` with any of these:

| Template | Use for |
|----------|---------|
| `repo_project` | Codebases and repositories |
| `service` | Systems and components |
| `issue` | Bugs and blockers |
| `initiative` | Cross-team programs |
| `workstream` | Ongoing processes |
| `stakeholder` | People and teams |
| `research` | Findings and supporting evidence |
| `project` | General projects |
| `decision` | Architectural and product choices |
| `meeting` | Meeting notes and outcomes |
| `session` | End-of-session summaries |
| `idea` | Proposals and explorations |
| `bug` | Bug reports |
| `learning` | Learnings and reference notes |

**Template-first workflow:**
1. Call `list_templates()` to see available shapes
2. Use `create_from_template(...)` for new notes whenever possible
3. Refine with `upsert_memory_node(...)` for stronger machine-friendly frontmatter
4. Use `promote_to_memory_node(...)` for messy raw output after the fact

## Suggested Workflow

### Session start

1. `get_context("project or topic")` to bootstrap context
2. If one note is clearly central, call `get_graph_context` on it
3. Check `list_relationships` before making changes
4. Use `memory_dashboard()` for a compact view of what needs maintenance

### During work

1. Update notes with new links and frontmatter relationships
2. Prefer `create_from_template` for new notes, refine with `upsert_memory_node` and `update_relationships`
3. Save decisions explicitly with `save_decision`
4. `add_followup` for anything that should survive the session

### Session end

1. `end_session(...)` — saves summary, links touched notes, handles followups

### Maintenance pass

1. `lint_memory_graph()`
2. `review_relationship_suggestions()` — accept or reject
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

## Local Visualizer

React Flow-based graph UI over the same local markdown vault. No hosted backend, no CDN, no cloud dependency.

```bash
uv run python scripts/run_linked_notes_ui.py /path/to/your/notes
```

Then open `http://127.0.0.1:8765`.

Supports:
- `Overview`, `Subsystem`, and `Flow` graph lenses
- focus-area and detail-level controls
- node detail with `Note` and `Source` modes
- local source previews from repo evidence with line-aware file previews
- persistent local UI state

To rebuild the UI after editing:

```bash
npm install
npm run build:ui
```

Built assets are served from `src/linked_notes_mcp/static/`.

## Known Limitations and Roadmap

Current limits:
- works best when notes use structured frontmatter consistently
- optimized for durable explicit memory, not full conversational recall
- graph quality depends on review and maintenance over time
- local UI is functional but still an early workbench

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
- [Seed Context Ingestion Spec](docs/INGESTION-SPEC.md)
- [UX Roadmap](docs/UX-ROADMAP.md)
- [Visualizer Spec](docs/VISUALIZER-SPEC.md)

## License

MIT License. See [LICENSE](LICENSE).
