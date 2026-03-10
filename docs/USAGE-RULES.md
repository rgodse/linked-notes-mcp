# Claude Brain - Usage Rules

Simple rules for getting the most out of Claude's persistent memory.

---

## The Two Essential Habits

### 1. Start sessions with context
```
"I'm working on [project-name] today, check your notes"
```
or
```
"What do you know about [topic]?"
```

### 2. End sessions with a summary
```
"Save a session summary for [project-name]"
```

That's it. Everything else builds on these two habits.

---

## Quick Reference

| Situation | What to Say |
|-----------|-------------|
| Starting work on a project | "Check your notes for project-x" |
| Made an important decision | "Save this as a decision: [what and why]" |
| Ending a work session | "Save a session summary" |
| Can't remember something | "Search your notes for [topic]" |
| Want to see everything | "List your notes" or "Show me notes tagged #project-x" |

---

## Project Workflow

### First session on a new project
```
You: "Starting a new project called customer-portal. It's a React app for
      enterprise customers to manage their accounts. Save this as project context."

Claude: [Creates project context note tagged #project-customer-portal]
```

### Subsequent sessions
```
You: "Working on customer-portal today, check your notes"

Claude: [Reads project context and recent session summaries]
        "I see customer-portal is a React app for enterprise account management.
         Last session you completed the login flow and decided to use Auth0.
         Open items are the dashboard layout and API integration. Where would
         you like to start?"
```

### Ending any session
```
You: "Save a session summary"

Claude: "What did we accomplish, and what's still open?"

You: "We finished the dashboard wireframes, decided to use Recharts for
      graphs, still need to finalize the color scheme"

Claude: [Saves structured session summary with all details]
```

---

## Tagging Convention

Use consistent project tags so notes are easy to find:

- `#project-customer-portal`
- `#project-api-redesign`
- `#project-mobile-app`

Other useful tags (auto-applied by templates):
- `#session` - Session summaries
- `#decision` - Decision logs
- `#meeting` - Meeting notes
- `#idea` - Ideas and brainstorms

---

## Cowork / Autonomous Mode

When Claude works autonomously, add this instruction:

```
When working autonomously:
1. Check your notes for project context before starting
2. Save decisions as you make them using save_decision
3. Save a session summary when done or pausing
```

This ensures you have visibility into what Cowork did and why.

---

## Tips

**Be specific about projects**
- Good: "Save this for project-customer-portal"
- Bad: "Remember this"

**Ask Claude to link notes**
- "Link this to the API decisions note"
- Builds a connected knowledge graph over time

**Review occasionally**
- Notes are just markdown files in `~/claude-brain/`
- Open in any text editor or Obsidian
- Delete outdated notes, edit mistakes

**Don't over-organize**
- Let notes accumulate naturally
- Search is fast - you don't need perfect folder structure
- Tags and links matter more than hierarchy

---

## Example Session Flow

```
┌─────────────────────────────────────────────────────┐
│ SESSION START                                        │
│                                                      │
│ You: "Working on customer-portal, check your notes"  │
│                                                      │
│ Claude: [Searches, reads relevant notes]             │
│         "Here's what I know about customer-portal.." │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ DURING SESSION                                       │
│                                                      │
│ [Normal work conversation]                           │
│                                                      │
│ You: "Let's use Tailwind instead of styled-         │
│       components - save that decision"               │
│                                                      │
│ Claude: [Saves decision with reasoning]              │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ SESSION END                                          │
│                                                      │
│ You: "Save a session summary before we wrap up"      │
│                                                      │
│ Claude: [Creates summary: accomplished, decisions,   │
│          open items, next session]                   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ NEXT SESSION                                         │
│                                                      │
│ You: "Continue on customer-portal"                   │
│                                                      │
│ Claude: [Reads last summary, has full context]       │
│         "Last time we decided on Tailwind and        │
│          finished X. Open items are Y and Z."        │
└─────────────────────────────────────────────────────┘
```

---

## That's It

Two habits, consistent tagging, done. The brain handles the rest.
