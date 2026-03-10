# Quick Start: Claude's Persistent Brain

Get Claude remembering things across sessions in 5 minutes.

## 1. Install

```bash
pip install linked-notes-mcp
```

## 2. Create a Brain Folder

```bash
mkdir ~/claude-brain
```

This is where Claude will read and write notes.

## 3. Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brain": {
      "command": "linked-notes-mcp",
      "args": ["/Users/YOUR_USERNAME/claude-brain"]
    }
  }
}
```

Restart Claude Desktop.

## 4. Test It

Open Claude and say:

> "Create a note called 'First Note' with content 'Hello from my brain!' and tag it with 'test'"

Then:

> "Search your notes for 'hello'"

Claude should find the note it just created.

## 5. Set Up Auto-Memory (Optional)

Add to your `CLAUDE.md` or tell Claude directly:

```
## Memory Instructions

You have access to a notes vault via the "brain" MCP. Use it to:

1. **Start of session**: Search for relevant context before diving in
2. **During work**: Reference past decisions and progress
3. **End of session**: Use `save_session_summary` to capture progress

### Key Tools
- `save_session_summary` - USE THIS at end of significant sessions
- `save_decision` - When important decisions are made
- `search` - Find relevant past notes
- `list_templates` - See all available note templates

### Note Conventions
- Tag decisions with: #decision
- Tag todos with: #todo
- Tag session summaries with: #session
- Tag project context with: #project-[name]
- Always link to related notes using [[Note Name]]
```

## Usage Patterns

### "End of session" (Most Important!)
> "Save a session summary - we discussed X, accomplished Y, decided Z, still need to do W"

Claude uses the `save_session_summary` tool to create a structured note automatically.

### "Record a decision"
> "Save a decision: we chose PostgreSQL over MongoDB because of better JSON support and team familiarity"

Claude uses the `save_decision` tool with full context and reasoning.

### "What did we decide?"
> "Check your notes for any decisions about the database"

### "Context recovery"
> "Search your notes for anything related to the authentication system"

### "Build connections"
> "Create a note about the new API endpoint and link it to [[API Design]] and [[Authentication]]"

### "Use a specific template"
> "Create a meeting note for today's planning session"

Claude uses the `meeting` template with attendees, agenda, decisions, action items.

## How It Saves You Time

| Without Brain | With Brain |
|---------------|------------|
| Re-explain project context every session | Claude reads its notes in 2 seconds |
| Forget why decisions were made | Decision log with reasoning preserved |
| Lose track of what's done vs pending | Progress tracked in linked notes |
| Context window filled with repeated info | Context window free for actual work |

## Suggested Tags

| Tag | Use For |
|-----|---------|
| `#decision` | Architectural/design decisions with reasoning |
| `#todo` | Open tasks and next steps |
| `#session` | Session summaries |
| `#context` | Background info Claude needs to remember |
| `#project-x` | Project-specific notes |
| `#blocked` | Things waiting on external input |
| `#idea` | Ideas to explore later |

## Tips

1. **Be specific with titles** - "Auth Decision: JWT vs Sessions" > "Auth Notes"
2. **Include the "why"** - Future Claude needs reasoning, not just conclusions
3. **Link liberally** - `[[Project X]]` connections make retrieval smarter
4. **Periodic cleanup** - Ask Claude to review and consolidate old notes
5. **Trust the search** - Claude can find notes by content, not just title

## Troubleshooting

**Claude doesn't see the MCP:**
- Restart Claude Desktop after config changes
- Check the path in config matches your actual folder

**Notes not persisting:**
- Verify the folder exists and is writable
- Check Claude Desktop logs for errors

**Can't find notes that exist:**
- Ask Claude to run `rebuild()` to refresh the index
- Check if the note has the expected tags/content
