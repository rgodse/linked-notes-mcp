# linked-notes-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

MCP server for navigating markdown knowledge graphs via wikilinks. Point it at any folder of markdown files and an MCP client like Codex or Claude can traverse, search, and update your notes.

## Features

- Zero config
- Wikilink support: `[[Target]]` and `[[Target|Display Text]]`
- Standard markdown links
- YAML frontmatter extraction
- Graph traversal and path finding
- Full-text search
- Obsidian-compatible markdown folders
- Read and write tools for persistent agent memory

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

If you cloned the repo locally instead:

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

Or, if installed from a local clone:

```json
{
  "mcpServers": {
    "notes": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/linked-notes-mcp",
        "linked-notes-mcp",
        "/path/to/your/notes"
      ]
    }
  }
}
```

Restart Claude Desktop after updating the config.

## Common Workflows

Examples:

- "Find all notes related to project architecture"
- "Show me everything connected to [[API Design]] within 2 hops"
- "Find the path between [[Authentication]] and [[User Management]]"
- "Create a note summarizing what we just discussed"
- "Save this decision and the reasoning behind it"
- "Remember this for next time"

## Tools

### Navigation Tools

| Tool | Description |
|------|-------------|
| `overview()` | High-level summary of the vault |
| `search(query, limit)` | Search titles, content, and tags |
| `get_note(identifier)` | Read a note by id, title, or path |
| `list_neighbors(identifier)` | List directly linked notes |
| `find_path(start, end)` | Find a path between two notes |
| `expand_context(identifier, hops)` | Explore connected notes within N hops |
| `list_by_tag(tag)` | List notes matching a tag |
| `list_notes(limit)` | List notes in the vault |
| `rebuild()` | Rebuild the graph index |

### Write Tools

| Tool | Description |
|------|-------------|
| `create_note(title, content, tags)` | Create a new note |
| `update_note(identifier, content, title, tags)` | Update an existing note |
| `append_to_note(identifier, content)` | Append to an existing note |
| `delete_note(identifier)` | Delete a note |

### Template Tools

| Tool | Description |
|------|-------------|
| `list_templates()` | List available note templates |
| `create_from_template(template, fields)` | Create a note from a template |
| `save_session_summary(...)` | Save structured session notes |
| `save_decision(...)` | Save a decision with rationale |

### Agent Memory Tools

| Tool | Description |
|------|-------------|
| `get_context(query, limit)` | Search notes and matching followups for a topic |
| `get_note_summary(identifier, max_chars)` | Cheap peek before loading a full note |
| `list_stale_notes()` | Surface expired notes |
| `add_followup(topic, reminder)` | Persist a reminder across sessions |
| `list_followups()` | List pending reminders |
| `dismiss_followup(id)` | Remove a reminder |

Followups are stored in `.linked_notes_followups.json` in the vault root. Add that file to `.gitignore` if you do not want reminders committed.

## Note Format

The server works with standard markdown files and supports:

- YAML frontmatter like `title`, `tags`, and custom fields
- `expires` for time-limited notes
- Wikilinks and standard markdown links

If no title exists in frontmatter, the server falls back to the first heading or the filename.

## Development

```bash
git clone https://github.com/rgodse/linked-notes-mcp
cd linked-notes-mcp
uv sync --dev
uv run pytest
uv run linked-notes-mcp /path/to/test/vault
```

## Comparison with Alternatives

| Feature | linked-notes-mcp | basic-memory | library-mcp |
|---------|------------------|--------------|-------------|
| Zero config | ✅ | ❌ | ✅ |
| Graph traversal | ✅ | ✅ | ❌ |
| Write capability | ✅ | ✅ | ❌ |
| Wikilinks | ✅ | ✅ | ❌ |
| License | MIT | AGPL | - |
| Dependencies | Minimal | Heavy | Minimal |

linked-notes-mcp is minimal and designed to work with any existing markdown folder. Use it as persistent cross-session memory for Codex, Claude, or another MCP client.

## License

MIT License. See [LICENSE](LICENSE).
