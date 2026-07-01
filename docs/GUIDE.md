# Claude's Brain: A Guide to Persistent AI Memory

## The Problem

Every time you start a conversation with Claude, it starts fresh. No memory of yesterday's conversation. No recollection of the decision you made last week. No context about your project.

This means you spend time at the start of every session re-explaining:
- What you're working on
- What's already been done
- What decisions were made and why
- What's still left to do

It's like working with a brilliant colleague who has amnesia. Incredibly capable, but you have to re-introduce yourself every morning.

## The Solution

**Give Claude a brain it can write to and read from.**

This tool creates a folder of notes that Claude can:
- **Read** to recover context from past sessions
- **Write** to save important information for later
- **Search** to find relevant past decisions
- **Connect** to build a web of linked knowledge

Think of it as Claude's notebook. After each conversation, Claude jots down what matters. Before the next conversation, Claude reviews its notes.

## How It Works (Non-Technical Version)

Imagine a shared notebook between you and Claude:

1. **You work together** on a project, making decisions, solving problems
2. **Before you leave**, Claude writes down key points in the notebook
3. **Next time you meet**, Claude reads its notes and picks up where you left off

The notes are just text files on your computer. You can read them too. They're organized with:
- **Titles** - What the note is about
- **Tags** - Categories like #decision, #todo, #project-name
- **Links** - Connections to related notes, like "see also [[API Design]]"

## Why This Matters

### 1. You Stop Repeating Yourself

Without memory:
> "Remember, we're building an app for tracking inventory. Last time we decided to use PostgreSQL because... and we finished the login system but still need to..."

With memory:
> "Let's continue where we left off."
>
> Claude checks its notes and responds: "Right, we were working on the inventory app. I see we finished the login system and decided on PostgreSQL for the database. The open items are the product catalog and reporting dashboard. Where would you like to start?"

### 2. Decisions Don't Get Lost

A month ago, you decided to use approach A instead of approach B. Why? Without notes, that reasoning is gone. With notes, Claude wrote:

> **Title:** Decision: REST vs GraphQL
> **Tags:** #decision #api
> **Content:** Chose REST because the team is more familiar with it, the API is simple CRUD operations, and we don't need the flexibility of GraphQL. Revisit if we add mobile clients.

Now when someone asks "why REST?", Claude (or you) can pull up the reasoning instantly.

### 3. Context Doesn't Eat Your Conversation

Claude has a limited "working memory" (called a context window). Every word of background explanation takes up space that could be used for actual work.

When context lives in notes:
- Claude pulls only what's relevant
- Your conversation focuses on new work
- Complex projects become manageable across many sessions

### 4. You Build Institutional Knowledge

Over time, Claude's notes become a knowledge base:
- How your systems work
- Why decisions were made
- What's been tried before
- Patterns and preferences

This is valuable whether you're an individual or a team.

## Real Examples

### Example 1: Project Continuity

**Session 1:**
> You: "We're starting a new project to automate our invoicing."
>
> Claude: Works with you for an hour, designs the system
>
> You: "Save what we've figured out before we wrap up."
>
> Claude: Creates notes for "Invoice Automation - Overview", "Invoice System - Technical Design", tags them #project-invoicing

**Session 2 (three days later):**
> You: "Let's continue on the invoicing project."
>
> Claude: Searches notes, finds the project context
>
> Claude: "I see we designed a system with three components: PDF parser, approval workflow, and accounting integration. We decided to start with the PDF parser. Would you like to begin implementation?"

No re-explanation needed.

### Example 2: Decision Archaeology

**Months ago:** You decided to use Vendor A instead of Vendor B.

**Today:**
> You: "Why are we using Vendor A again?"
>
> Claude: Searches notes for "vendor" decisions
>
> Claude: "According to my notes from March, we evaluated both vendors. Vendor A was chosen because they offered better API documentation, local support, and the pricing was 30% lower for our volume. The note mentions that Vendor B had better features but the integration complexity wasn't worth it for our timeline."

### Example 3: Personal Preferences

**Over time, Claude learns:**
- You prefer concise responses
- Your code style uses tabs, not spaces
- You like decisions presented as options with tradeoffs
- You're more productive in the morning

Claude notes these observations. Future sessions start pre-calibrated to how you work.

## What Good Notes Look Like

Claude uses **built-in templates** to create consistently structured notes. Here's what they look like:

### Session Summary (created with `end_session`)
```
---
title: Session - 2024-01-15 - API Planning
tags:
  - session
  - project-webapp
created: 2024-01-15T16:30:00
---

## Summary
Planned the API architecture and made key technology decisions.

## Accomplished
- Defined API endpoints for user management
- Chose authentication approach
- Sketched database schema

## Decisions Made
- Use JWT tokens (see [[Decision: JWT vs Sessions]])
- PostgreSQL for the database

## Open Items
- [ ] Finalize rate limiting strategy
- [ ] Get DevOps input on deployment

## Next Session
Start implementing the user registration endpoint
```

### Decision Log (created with `save_decision`)
```
---
title: Decision: JWT vs Sessions
tags:
  - decision
  - project-webapp
created: 2024-01-15T14:00:00
---

## Context
Need to implement authentication for the new API.

## Options Considered
- **JWT tokens**
- **Server-side sessions**
- **OAuth only**

## Decision
JWT tokens with 1-hour expiry and refresh tokens.

## Reasoning
- Stateless (scales better than sessions)
- Works across our web and mobile apps
- Team has JWT experience from previous project

## Implications
Need to implement token refresh logic and decide on storage strategy.
```

### Available Templates
Claude has templates for many situations:
- **session** - End-of-session summaries
- **decision** - Decisions with reasoning
- **project** - Project overview
- **meeting** - Meeting notes
- **idea** - Brainstorming
- **bug** - Bug investigation (technical)
- **learning** - Things learned

You can say "use the meeting template" or just describe what you need and Claude picks the right one.

## Tips for Getting the Most Out of It

### 1. End Sessions Properly

This is the most important habit. At the end of any significant session:
> "Save a session summary"

Claude will ask what you accomplished, what was decided, and what's next. This is how context survives between sessions.

### 2. Record Decisions When They Happen

When you make an important choice:
> "Save this as a decision - we chose X because Y"

Future you (and future Claude) will thank you when someone asks "why did we do it this way?"

### 3. Ask Claude to Check Its Notes

At the start of sessions:
> "Check your notes for anything relevant to [topic]"

When you're not sure:
> "Do you have any notes about when we discussed [thing]?"

### 4. Use the Right Template

For structured discussions, ask for specific templates:
- "Create a meeting note" - for meeting notes
- "Log this as a decision" - for decisions
- "Save this idea" - for brainstorming
- "Create a project context note" - for project overviews

### 5. Let Connections Build

Encourage Claude to link related notes:
> "Link this to any related notes about the API"

Over time, this creates a web of connected knowledge, not just isolated documents.

### 6. Works for Non-Technical Sessions Too

The templates work for strategy, planning, and business discussions - not just coding:
- Session summaries for planning meetings
- Decisions for strategic choices
- Ideas for product brainstorming
- Meeting notes for any meeting

### 7. Review Occasionally

The notes are just files on your computer. You can:
- Browse them in any text editor
- Open them in Obsidian for a visual graph
- Edit them yourself if Claude got something wrong
- Delete outdated information

## Common Questions

**Can I read Claude's notes?**
Yes. They're just text files in a folder you choose. Open them in any text editor or note-taking app.

**Can I edit Claude's notes?**
Yes. They're your files. Claude will see your edits next time it reads them.

**What if Claude writes something wrong?**
Edit or delete the note. Or ask Claude to update it: "Your note about X is outdated. Update it with [new info]."

**Does this cost extra?**
No. It's a free, open-source tool. The notes are stored on your computer, not in any cloud service.

**Is this secure?**
The notes stay on your computer. Nothing is sent anywhere except what you share in your Claude conversations (which you're already doing).

**Can I use this with Obsidian?**
Yes. Point the tool at your Obsidian vault, or point Obsidian at Claude's brain folder. They use the same markdown format.

## The Bottom Line

AI assistants are powerful but forgetful. This tool gives Claude memory.

Instead of every conversation starting from zero, Claude builds up knowledge about your work over time. Past decisions, project context, personal preferences - all preserved and searchable.

The result: less time explaining, more time doing. Claude becomes a true long-term collaborator instead of a capable stranger you meet fresh every day.
