# UX Roadmap

This roadmap focuses on making `linked-notes-mcp` usable as a daily local memory layer for heavy agent use in coding and business-process work.

The principle is simple:

- keep the markdown graph as the durable substrate
- reduce tool choreography
- make review and maintenance feel like workflows instead of raw commands

## Current State

Today the project already supports:

- graph-first note retrieval
- structured note creation and updates
- relationship review and memory-health workflows
- staged seed ingestion v1 for local files and inline text

The main UX gap is not capability. It is orchestration.

## v0.2: session workflows

Status:
Implemented in the MCP layer with:

- `start_session(...)`
- `review_memory(...)`
- `end_session(...)`

Goal:
Reduce the number of primitive calls needed to begin and end work.

Target additions:

- `start_session(topic, project?)`
- `end_session(summary, accomplished, decisions?, open_items?, next_session?)`
- compact project brief generation at session start
- automatic surfacing of followups, stale notes, and nearby graph context

Outcome:
The system now has a first-pass workflow layer, but the presentation is still JSON-first and better suited to power users than general daily use.

## v0.3: review workflow

Goal:
Make maintenance feel operational instead of manual.

Target additions:

- `review_memory(limit?)`
- one compact view for:
  - weak notes
  - stale notes
  - relationship suggestions
  - pending ingestion candidates
- better explanation for why a note, edge, or suggestion is shown

Success condition:
Users can do a useful maintenance pass without manually stitching together multiple tools.

## v0.4: seed ingestion UX

Goal:
Turn staged ingestion into an approachable workflow.

Target additions:

- grouped candidate review by run
- easier merge-vs-create decisions
- better evidence display
- more conservative duplicate handling
- first-pass project and repo bootstrapping helpers

Success condition:
A user can ingest a few docs and promote the top candidates without reading raw JSON output.

## v0.5: local UI

Goal:
Add a thin local interface on top of the MCP backend.

Candidate views:

- `Today`: current projects, recent sessions, followups
- `Context`: graph-local project brief
- `Review`: weak notes, suggestions, ingestion review
- `Ingest`: source registration and candidate promotion

Success condition:
The system is usable daily without relying only on direct MCP tool calls.

## Design Rules

- do not replace markdown as the source of truth
- do not hide graph structure behind opaque automation
- prefer staged review over silent writes when confidence is low
- keep the number of default user flows small and obvious

## Immediate Priorities

If only a few things get built next, the priority order should be:

1. `start_session`
2. `review_memory`
3. seed ingestion review improvements
4. `end_session`
5. thin local UI
