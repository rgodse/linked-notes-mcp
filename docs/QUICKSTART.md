# Quick Start: Persistent MCP Notes

Get an MCP client remembering things across sessions in 5 minutes.

## 1. Clone and Install

```bash
git clone https://github.com/rgodse/linked-notes-mcp
cd linked-notes-mcp
uv sync
```

## 2. Create a Brain Folder

```bash
mkdir ~/agent-brain
```

This is where your MCP client will read and write notes.

## 3. Configure Codex or Claude Desktop

### Codex

Edit `~/.codex/config.toml`:

```toml
[features]
rmcp_client = true

[mcp_servers.brain]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/linked-notes-mcp", "linked-notes-mcp", "/Users/YOUR_USERNAME/agent-brain"]
```

Restart Codex.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brain": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/linked-notes-mcp",
        "linked-notes-mcp",
        "/Users/YOUR_USERNAME/agent-brain"
      ]
    }
  }
}
```

Restart Claude Desktop.

## 4. Test It

Open your MCP client and say:

> "Create a note called 'First Note' with content 'Hello from my brain!' and tag it with 'test'"

Then:

> "Search your notes for 'hello'"

The client should find the note it just created.

## 5. Add Memory Instructions

Add to your client instructions:

```text
You have access to a notes vault via the "brain" MCP. Use it to:

1. Start of session: search for relevant context before diving in.
2. During work: reference past decisions and progress.
3. End of session: use save_session_summary to capture progress.

Key tools:
- save_session_summary
- save_decision
- search
- list_templates
```

## Suggested Tags

| Tag | Use For |
|-----|---------|
| `#decision` | Architectural/design decisions with reasoning |
| `#todo` | Open tasks and next steps |
| `#session` | Session summaries |
| `#context` | Background info the agent should remember |
| `#project-x` | Project-specific notes |
| `#blocked` | Things waiting on external input |
| `#idea` | Ideas to explore later |

## Troubleshooting

**Client doesn't see the MCP:**
- Restart the client after config changes
- Check the path in config matches your actual folder

**Notes not persisting:**
- Verify the folder exists and is writable
- Check the client logs for errors

**Can't find notes that exist:**
- Run `rebuild()` to refresh the index
- Check if the note has the expected tags/content
