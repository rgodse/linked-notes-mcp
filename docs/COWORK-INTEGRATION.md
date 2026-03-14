# Claude Cowork + Persistent Memory

## The Problem with Autonomous AI Agents

When Claude Cowork runs autonomously on long tasks, you lose visibility:
- What decisions did it make while working?
- Why did it choose approach A over B?
- What's the current state if it gets interrupted?
- How do you hand off context to the next session?

## The Solution

Give Claude a persistent "brain" - a folder of markdown notes it can read and write. During autonomous work, Claude:
1. **Reads** past context and decisions before starting
2. **Writes** progress notes and decision logs as it works
3. **Summarizes** at completion for easy handoff

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Cowork                           │
│                                                             │
│  1. Task starts                                             │
│     └─> Reads brain for relevant context                    │
│                                                             │
│  2. Working autonomously                                    │
│     └─> Writes progress notes at milestones                 │
│     └─> Logs decisions with reasoning                       │
│                                                             │
│  3. Task completes (or pauses)                              │
│     └─> Writes summary: done, pending, blockers             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   ~/claude-brain/                           │
│                                                             │
│  project-auth-refactor.md                                   │
│  decision-jwt-vs-sessions.md                                │
│  session-2024-01-15-auth-work.md                            │
│  progress-api-migration.md                                  │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Next Session                             │
│                                                             │
│  You: "Continue the auth refactor"                          │
│  Claude: *reads notes* "I see I completed X and Y,          │
│          decided on JWT for reasons Z, and the open         │
│          items are A and B. Want me to continue with A?"    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Concrete Example

**Task:** "Refactor the authentication system to use JWT"

**Without Brain:**
- Cowork runs for 2 hours
- You come back to changed code
- No idea why certain choices were made
- If something breaks, archaeology required

**With Brain:**

Cowork uses built-in templates to create structured notes as it works:

**Session summary (via `save_session_summary`):**
```markdown
---
title: Session - 2024-01-15 - Auth Refactor
tags:
  - session
  - project-auth
created: 2024-01-15T16:00:00
---

## Summary
Major progress on JWT authentication migration.

## Accomplished
- Replaced session middleware with JWT validation
- Updated User model with refresh token field
- Migrated 12 API endpoints

## Decisions Made
- Token expiry: 1 hour access, 7 day refresh (see [[Decision: JWT Config]])
- Storage: HttpOnly cookies (not localStorage) for security
- Added migration endpoint for backwards compatibility

## Open Items
- [ ] Update API documentation
- [ ] Add token rotation on refresh
- [ ] Load testing with new auth flow

## Next Session
Continue with API documentation and token rotation
```

**Decision log (via `save_decision`):**
```markdown
---
title: Decision: JWT Config
tags:
  - decision
  - project-auth
created: 2024-01-15T14:30:00
---

## Context
Need to configure JWT token expiry for the new auth system.

## Options Considered
- **Short-lived only (15 min)**
- **Long-lived only (7 days)**
- **Short access + long refresh**

## Decision
1 hour access tokens, 7 day refresh tokens.

## Reasoning
Balances security (short access) with UX (don't re-login constantly).
Refresh tokens allow revocation without invalidating all sessions.

## Implications
Need to implement token refresh endpoint and rotation logic.
```

You return, ask "what's the status?", and Claude has full context instantly.

## Business Value

| Metric | Impact |
|--------|--------|
| Context recovery time | Minutes → Seconds |
| Decision traceability | "Why did we...?" always answered |
| Handoff friction | Seamless between sessions/people |
| Autonomous work visibility | Full audit trail |
| Knowledge retention | Survives employee turnover |

## Technical Details

- **What it is:** MCP (Model Context Protocol) server that exposes read/write tools for a markdown folder
- **Storage:** Local filesystem (your machine), not cloud
- **Format:** Standard markdown with YAML frontmatter - compatible with Obsidian, any text editor
- **Dependencies:** Python, ~4 small packages
- **Security:** Notes stay on your machine, nothing sent externally beyond normal MCP client conversation

## Setup

5 minutes:
1. `git clone https://github.com/rgodse/linked-notes-mcp && cd linked-notes-mcp && uv sync`
2. Create folder: `mkdir ~/agent-brain`
3. Add to Codex or Claude Desktop config
4. Restart Claude Desktop

Full instructions in QUICKSTART.md.

## Recommended Cowork Instructions

Add to your client instructions:

```
When working autonomously via Cowork:
1. Check your brain for relevant context before starting
2. Use `save_decision` when making significant choices
3. Use `save_session_summary` at completion or when pausing
4. Tag notes with relevant project tags
5. Link to related notes using [[Note Name]]
```

## FAQ

**Does this slow down Cowork?**
No. Reading/writing notes takes milliseconds. The context benefit far outweighs the cost.

**Can I read Claude's notes?**
Yes. They're just markdown files. Browse them, edit them, open in Obsidian.

**What if Claude writes something wrong?**
Edit or delete the file directly, or ask Claude to correct it.

**Does this work with regular chat too?**
Yes. Same brain works across chat and Cowork - context persists everywhere.

**Is this like memory features in ChatGPT?**
Similar goal, different approach. This is local, transparent, editable, and you control what's saved. It's not a black box.
