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

Status:
Implemented in the MCP layer with:

- `review_memory(...)` returning prioritized `recommended_actions`
- `review_queue(...)` for compact triage
- formatted ingestion candidate recommendations and explanations
- tighter `start_session(...)` next-step suggestions

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

Status:
Partially implemented in the MCP layer with:

- directory and glob ingestion
- extension/include/exclude filtering
- recommendation-filtered review
- bulk accept/reject actions by run

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

Status:
Planned. The next meaningful UX jump is a graph-native local interface rather than a generic dashboard.

Goal:
Add a thin local interface on top of the MCP backend.

Candidate views:

- `Today`: current projects, recent sessions, followups
- `Context`: graph-local project brief
- `Review`: weak notes, suggestions, ingestion review
- `Ingest`: source registration and candidate promotion
- `Graph`: interactive graph exploration of notes and relationships

Success condition:
The system is usable daily without relying only on direct MCP tool calls.

See [Visualizer Spec](VISUALIZER-SPEC.md) for the proposed shape of the graph UI and optional repo-aware enrichment.

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
5. graph-native local UI
