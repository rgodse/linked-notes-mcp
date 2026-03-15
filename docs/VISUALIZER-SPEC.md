# Visualizer Spec

## Purpose

This spec proposes a local interactive graph visualizer for `linked-notes-mcp`.

The goal is not to replace markdown or the MCP tools. The goal is to make the existing memory graph visible, explorable, and legible enough that users can:

- see project context at a glance
- inspect relationships visually instead of reconstructing them from text
- review weak or stale areas of the graph faster
- get some "wow factor" without changing the core thesis of the project

The visualizer should treat the existing vault as the source of truth.

## Thesis

`linked-notes-mcp` already has a strong graph model. What it lacks is a native visual surface for that graph.

A graph UI is valuable here because the system is explicitly built around:

- notes as nodes
- wikilinks and markdown links as edges
- typed frontmatter relationships as semantic edges
- graph-local retrieval and traversal

The UI should make those existing primitives visible rather than inventing a second system.

## Product Position

This is not a generic "mind map" app.

It is a local graph workbench for agent memory with three jobs:

1. orient the user around projects, decisions, services, issues, and sessions
2. expose structure and gaps in the memory graph
3. provide a thin operational surface over the existing MCP workflows

The right comparison is not Obsidian canvas.

The closer comparison is: a graph-native local control panel for a markdown memory system, with optional repo-aware enrichment.

## Design Rules

- markdown vault remains the canonical store
- UI must be read-first and graph-first
- low-confidence enrichments must stay staged until accepted
- the visual layer must not silently mutate notes
- typed relationships must stay visible and inspectable
- the first version should privilege clarity over visual density
- repo-derived context is optional enrichment, not the default data model

## User Value

### Why this is worth building

Today the system is useful but mostly text-first. A visual layer would improve:

- orientation in unfamiliar vaults
- project handoffs
- decision archaeology
- dependency tracing
- maintenance passes
- confidence in the graph as a real asset instead of an abstract backend

It also gives the product a stronger demo story:

- open a project
- see the graph
- click into dependencies and decisions
- trace paths visually
- spot stale or weak memory immediately

That is a meaningful usability improvement, not just a cosmetic add-on.

## Core Objects

The visualizer should use the `linked-notes` model directly.

### Canonical nodes

- notes
- followups
- staged ingestion candidates
- relationship suggestions

### Canonical node metadata

- title
- aliases
- entity_type
- project
- status
- tags
- summary
- importance
- confidence
- last_reviewed

### Canonical edges

- wikilinks
- markdown links
- typed frontmatter relationships such as `depends_on`, `blocks`, `related_to`, `part_of`, `contains`, `decision_for`

### Derived visual attributes

- node size from importance, connectivity, or recency
- node color from `entity_type` or status
- edge style from relation type and confidence
- badges for stale, weak, orphaned, or pending-review state

## v1 Scope

The first version should be intentionally small and opinionated.

### Primary views

#### 1. Graph

An interactive graph canvas for the vault or selected project.

Core capabilities:

- pan and zoom
- click node to inspect details
- filter by entity type, project, tag, status, relation type
- highlight incoming and outgoing neighbors
- expand neighborhood depth from a selected anchor
- hide weak relation types or low-signal nodes

#### 2. Detail Panel

A right-side panel for the selected node.

Contents:

- summary
- note preview
- frontmatter metadata
- typed relationships
- linked notes
- followups touching the note
- maintenance flags
- actions that map to existing MCP tools

#### 3. Project Focus View

A focused neighborhood around one project or anchor note.

Use cases:

- "show me this project and everything nearby"
- "what is blocking this initiative"
- "which decisions affect this service"

This should be the default entry for non-trivial vaults.

#### 4. Review Overlay

An operational layer over the graph that highlights:

- weak notes
- stale notes
- orphan notes
- pending relationship suggestions
- pending ingestion candidates

This lets the graph double as a maintenance surface.

### v1 interactions

- search and jump to node
- fit graph to selected neighborhood
- show path between two notes
- highlight dependency chains
- toggle graph layers on and off
- open full note content
- open file in editor if local path is known

## Recommended Information Architecture

The local UI can stay thin if it is organized around a few clear modes:

- `Today`: recent sessions, followups, active projects
- `Graph`: full graph and project-focused exploration
- `Context`: selected note plus local neighborhood
- `Review`: maintenance queue projected onto the graph
- `Ingest`: staged candidate review and promotion

The `Graph` and `Context` views are the highest leverage for v1.

## Repo-Aware Enrichment

This is where the GitNexus-style inspiration is useful.

The visualizer can optionally enrich the graph for notes representing repositories or technical projects.

### Principle

Repo context should be additive and clearly marked as derived.

It should not overwrite or dilute the human-edited markdown graph.

### Example enriched node types

- repository
- module
- service
- package
- key file
- execution flow
- external dependency

### Example enriched edges

- `contains`
- `depends_on`
- `implements`
- `calls`
- `owned_by`
- `entry_point_for`

### Acceptance rule

Repo-derived nodes and edges should begin life as one of:

- ephemeral visual overlay only
- staged candidates for promotion into markdown notes

Only accepted items should become durable notes in the vault.

This keeps the repo enrichment aligned with the broader `linked-notes` design rule:

- extract durable high-value context
- review before promoting low-confidence structure
- keep the markdown graph authoritative

## Enforced Repo Graph Schema

If the visualizer is expected to feel dense and genuinely explorable, repo ingestion cannot stay loose.

The system should enforce a minimum repo graph shape so every repo demo produces:

- one repo anchor note
- 5 to 10 major subsystem notes
- 2 to 5 second-order detail notes under each major subsystem
- at least one process-flow note
- at least one data-flow note
- typed cross-links between subsystems, flows, and supporting notes

### Required note classes

Each ingested repo should be able to emit some or all of these note classes:

- `project`: repo root
- `service`: major subsystem or module
- `research`: architecture or exploration note
- `decision`: notable architectural or operational choice
- `issue`: risk, hotspot, or operational concern
- `process`: request or execution flow note
- `data-flow`: movement of data across boundaries or stages

### Required relationship patterns

Each repo graph should include enough typed structure to support both overview and drill-down:

- repo `contains` subsystem notes
- subsystem notes `contain` detail notes or detail notes are `part_of` the subsystem
- process and data-flow notes `related_to` or `depends_on` the subsystems they traverse
- decisions and issues connect back to the affected services or flows
- second-order notes should interlink laterally, not only vertically to the repo root

### Required flow notes

The repo schema should intentionally create notes that read like flows, not only components.

Minimum examples:

- one process-flow note such as `Request path`, `Auth lifecycle`, or `Report generation flow`
- one data-flow note such as `Event ingestion`, `Record storage`, or `Metrics aggregation`

Those notes should use wikilinks in the body to narrate the path across the graph so the visualizer has both typed edges and readable context.

### Enforcement strategy

This should be enforced in the repo-context ingestion layer, not left to manual note creation.

Recommended controls:

- a generator that emits a standard repo note set from a public repo
- a linter that checks required note classes and relationship counts
- warnings for shallow repo graphs such as:
  - fewer than 5 subsystem notes
  - no process-flow note
  - no data-flow note
  - too many leaf nodes with no lateral links
- a review queue that asks the user to promote or refine weak repo-derived notes

### Why this matters

Without schema enforcement, the visualizer will oscillate between sparse, attractive toy graphs and noisy, inconsistent real graphs.

With schema enforcement, the graph becomes a dependable exploration surface:

- a user can start at repo level
- branch into subsystems
- trace a process
- inspect a data path
- discover decisions, risks, and ownership context nearby

## Visual Language

The interface should feel intentional and distinctive rather than a generic admin panel.

### Suggested direction

- graph canvas as the primary surface
- bold but restrained color mapping by entity type
- visible edge labeling for typed relationships
- smooth transition between overview and neighborhood focus
- clear visual distinction between canonical and derived graph layers

### Example node treatment

- projects: large anchor nodes
- decisions: high-contrast diamond or badge treatment
- sessions: lighter transient nodes
- stale notes: subdued with warning indicator
- pending suggestions: dashed or ghost styling

The UI should make the graph feel alive without becoming visually noisy.

## Data Access Layer

The visualizer should consume the existing MCP/backend capabilities rather than inventing a second domain model.

### Minimum backend needs

- graph summary
- note summaries
- full note fetch
- relationships
- graph context
- traversal
- path finding
- memory health
- review queues

### Likely addition

A dedicated graph snapshot endpoint or helper would simplify the UI significantly.

For example:

`get_visual_graph(anchor?, depth?, filters?)`

This would return a UI-ready subgraph with:

- nodes
- edges
- display metadata
- health flags
- relationship labels

That would avoid forcing the frontend to synthesize too much from many small tool calls.

## Suggested Backend Shape

The cleanest implementation path is a local companion app that imports the same parsing and graph logic used by the MCP server.

Possible options:

### Option A: Thin local web UI in this repo

- same codebase
- local backend plus browser frontend
- fastest path to integrated UX

### Option B: Separate `linked-notes-ui` companion

- keeps this repo focused
- easier to iterate on frontend independently
- still reads the same vault and backend contracts

For early validation, Option A is probably faster. For long-term separation, Option B is cleaner.

## v1 Non-Goals

- full multi-user collaboration
- hosted or cloud-first sync
- real-time shared editing
- arbitrary graph database import
- replacing the existing MCP write flows
- deep code intelligence as a mandatory dependency
- automatic promotion of repo-derived structure into durable notes

## Success Criteria

The first release succeeds if a user can:

1. open a vault and immediately understand its major projects and clusters
2. select a note and inspect its nearby graph without raw MCP calls
3. visually identify missing structure or stale memory
4. trace a path between two notes that would be tedious to reconstruct from text
5. review optional repo context without losing the markdown-first model

## Implementation Phases

### Phase 1: Graph Read Surface

- project-focused graph view
- detail panel
- search and jump
- graph filters
- path view

### Phase 2: Maintenance Overlay

- weak/stale/orphan highlighting
- review queue integration
- suggestion visibility
- ingestion candidate visibility

### Phase 3: Repo Enrichment

- attach repo/project nodes to derived subgraphs
- show ephemeral repo overlays
- stage selected enrichments for promotion

## Open Questions

- Should the first UI live in this repo or a separate companion repo?
- Should the frontend talk directly to Python helpers or through a local HTTP layer?
- How much graph should load by default for large vaults before switching to project-focused subgraphs?
- Which repo-enrichment source should be first: simple filesystem/project parsing, or a richer external analyzer?
- Should followups appear as first-class nodes or as panel-local operational state in v1?

## Recommendation

Build this.

Not because the project needs a flashy graph for its own sake, but because the underlying data model is already graph-native and the current UX hides that strength behind text-heavy workflows.

The right first step is a local graph visualizer that makes the current `linked-notes-mcp` graph visible and useful, then adds optional repo-aware overlays later.
