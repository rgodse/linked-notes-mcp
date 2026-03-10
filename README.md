# linked-notes-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

MCP server for navigating markdown knowledge graphs via wikilinks. Point it at any folder of markdown files and Claude can traverse your knowledge graph.

## Features

- **Zero config** — Point at any folder of markdown files, it just works
- **Wikilink support** — Parses `[[Target]]` and `[[Target|Display Text]]` links
- **Standard markdown links** — Also parses `[text](path.md)` style links
- **YAML frontmatter** — Extracts title, tags, and custom metadata
- **Graph traversal** — Find connections within N hops of any note
- **Full-text search** — Search across titles, content, and tags
- **Path finding** — Discover how concepts connect
- **Obsidian compatible** — Works with existing Obsidian vaults
- **Read & Write** — Claude can create, update, and append to notes (persistent memory)

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv tool install linked-notes-mcp

# Or with pip
pip install linked-notes-mcp
```

### Claude Desktop Configuration

Edit your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "notes": {
      "command": "uvx",
      "args": [
        "linked-notes-mcp",
        "/path/to/your/notes"
      ]
    }
  }
}
```

Or if installed with pip:

```json
{
  "mcpServers": {
    "notes": {
      "command": "linked-notes-mcp",
      "args": ["/path/to/your/notes"]
    }
  }
}
```

### Usage with Claude

Once configured, you can ask Claude things like:

**Reading & Exploring:**
- "What notes do I have about project architecture?"
- "Show me everything connected to [[API Design]] within 2 hops"
- "Find the path between [[Authentication]] and [[User Management]]"
- "List all notes tagged with #planning"
- "Give me an overview of my knowledge base"

**Writing & Remembering:**
- "Create a note summarizing what we just discussed"
- "Save this decision and the reasoning behind it"
- "Add a follow-up section to the project-status note"
- "Remember this for next time" (Claude creates a note it can find later)

## Tools

### Read Tools

| Tool | Description |
|------|-------------|
| `get_note(identifier)` | Get full content of a note by ID or title |
| `get_note_summary(identifier, max_chars)` | Get metadata + truncated body preview without loading full content |
| `list_links(note_id, direction)` | Get outgoing/incoming/both links for a note |
| `search(query, limit)` | Full-text search — returns matching notes with inline excerpts |
| `traverse(start_id, depth, direction)` | Get all connected notes within N hops |
| `find_path(start_id, end_id)` | Find shortest path between two notes |
| `list_tags()` | List all tags with counts |
| `notes_by_tag(tag)` | Get all notes with a specific tag |
| `graph_summary()` | Overview stats: total notes, links, orphans, most connected |
| `list_notes(limit)` | List all notes (brief info) |
| `list_stale_notes()` | List notes whose `expires` frontmatter date is in the past |
| `rebuild()` | Refresh the index after file changes |

### Write Tools

| Tool | Description |
|------|-------------|
| `create_note(title, content, tags)` | Create a new note with optional tags |
| `update_note(identifier, content, title, tags)` | Update an existing note's content, title, or tags |
| `append_to_note(identifier, content)` | Append content to an existing note |
| `delete_note(identifier)` | Delete a note from the vault |

### Template Tools

| Tool | Description |
|------|-------------|
| `list_templates()` | List all available note templates |
| `create_from_template(template, fields)` | Create a note using a template (session, decision, project, meeting, idea, bug, learning) |
| `save_session_summary(...)` | Quick session summary with accomplishments, decisions, open items |
| `save_decision(...)` | Record a decision with context, options, reasoning |

### Claude-Perspective Tools

These tools reduce friction when Claude is navigating the vault across sessions.

| Tool | Description |
|------|-------------|
| `get_context(query, limit)` | Search notes + return excerpts with relevance info + matching followup reminders. Use at session start. |
| `get_note_summary(identifier, max_chars)` | Cheap peek at a note before deciding whether to load it fully |
| `list_stale_notes()` | Surface expired notes that may contain outdated information |
| `add_followup(topic, reminder)` | Persist a reminder across sessions (stored in `.claude_followups.json`) |
| `list_followups()` | List all pending followup reminders |
| `dismiss_followup(id)` | Remove a followup reminder by its ID |

## Note Format

linked-notes-mcp works with standard markdown files. It extracts:

### Frontmatter (optional)

```yaml
---
title: My Note Title
tags:
  - project
  - planning
custom_field: any value
expires: 2025-12-31   # optional — mark note as expiring on this date
---
```

If no title is in frontmatter, it uses the first `# Heading` or the filename.

The `expires` field marks a note as time-limited. `list_stale_notes` returns all notes whose expiry date is in the past so you can review or archive them.

### Links

Both wikilink and standard markdown link formats are supported:

```markdown
This links to [[Another Note]] in your vault.

You can also use [[Another Note|display text]] for custom text.

Standard [markdown links](another-note.md) work too.
```

### Tags

Tags are extracted from YAML frontmatter:

```yaml
tags:
  - tag1
  - tag2
# or
tags: tag1, tag2, tag3
```

## How It Works

1. On startup, scans your vault directory recursively for `.md` files
2. Parses each file to extract frontmatter, links, and content
3. Builds an in-memory directed graph using NetworkX
4. Exposes MCP tools for Claude to query and traverse the graph

The graph is stored in memory and rebuilt on startup. Use the `rebuild` tool to refresh after making changes to your notes.

## Use Case: Claude's Persistent Brain

The write tools turn this MCP into Claude's memory between sessions:

```
You: "Summarize what we decided about the auth system and save it"

Claude: [creates note with title "Auth System Decisions", tags ["architecture", "auth"],
         links to [[API Gateway]] and [[User Service]]]

--- next session ---

You: "What did we decide about auth?"

Claude: [calls get_context("auth"), gets excerpts + any followup reminders]
        "Based on my notes, you decided to use JWT tokens with..."
```

Claude automatically adds `created` and `modified` timestamps, and can link new notes to existing ones using `[[wikilinks]]`.

### Followup Reminders

Claude can leave itself notes between sessions using the followup tools:

```
Claude: [end of session] add_followup(topic="auth", reminder="Check if refresh token rotation was implemented")

--- next session ---

Claude: [start of session] get_context("auth")
        → returns matching notes AND the pending followup reminder
```

Reminders are stored in `.claude_followups.json` in the vault root (add this to `.gitignore` if desired).

## Development

```bash
# Clone the repo
git clone https://github.com/yourusername/linked-notes-mcp
cd linked-notes-mcp

# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run the server locally
uv run linked-notes-mcp /path/to/test/vault
```

## Comparison with Alternatives

| Feature | linked-notes-mcp | basic-memory | library-mcp |
|---------|-----------------|--------------|-------------|
| Zero config | ✅ | ❌ (requires specific format) | ✅ |
| Graph traversal | ✅ | ✅ | ❌ |
| Write capability | ✅ | ✅ | ❌ |
| Wikilinks | ✅ | ✅ | ❌ |
| License | MIT | AGPL | - |
| Dependencies | Minimal | Heavy | Minimal |

linked-notes-mcp is **minimal** and designed to work with any existing markdown folder. Use it as Claude's persistent brain across sessions.

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

Contributions welcome! Please open an issue or PR.

## Roadmap

- [ ] Semantic search with embeddings (optional)
- [ ] Export graph to various formats
- [x] Note creation/editing tools
- [x] Claude-perspective tools (get_context, followups, stale notes, note summaries)
