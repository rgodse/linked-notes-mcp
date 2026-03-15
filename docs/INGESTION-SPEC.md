# Seed Context Ingestion Spec

## Goal

Add an ingestion-first workflow to `linked-notes-mcp` so agents can start with base memory from source material instead of relying only on prior chats to accumulate notes over time.

The core behavior should be:

1. ingest source material
2. extract candidate memory nodes and relationships
3. stage candidates for review
4. promote accepted candidates into the normal markdown graph
5. let regular session workflows keep enriching the graph afterward

This is intended as an add-on to the existing graph memory model, not a replacement for it.

## Why This Matters

The current system assumes memory mostly appears through conversation and later note creation. That works, but it is slow to bootstrap and weak for:

- new projects with existing docs
- existing repos with no prior chat history
- imported meeting notes, tickets, transcripts, or design docs
- handoffs where the relevant context already exists outside the vault

Seed ingestion makes the graph useful on day one. Conversation then becomes a delta layer on top of explicit starting context.

## Product Principles

- markdown notes remain the source of truth
- ingestion creates staged candidates before modifying the main graph
- provenance must be preserved for every extracted fact
- low-confidence extraction should be reviewable, not silently committed
- accepted memory nodes should look like normal linked-notes nodes
- the workflow should work without hosted infrastructure

## Non-Goals

The first implementation should not try to solve all ingestion use cases.

Out of scope for v1:

- OCR-heavy PDF workflows
- browser scraping
- remote connector auth flows
- autonomous ingestion from arbitrary URLs
- perfect entity resolution across noisy corpora
- replacing `create_note`, `upsert_memory_node`, or existing session tools

## Primary User Stories

### Repo bootstrap

The user points the system at a repository README, architecture docs, and issue notes. The system proposes project, service, issue, and decision nodes that can be accepted into the graph.

### Meeting import

The user ingests a transcript or raw meeting notes. The system extracts decisions, followups, stakeholders, and workstreams.

### Research import

The user ingests research notes or design docs. The system extracts findings, risks, open questions, and related entities.

### Work handoff

The user imports a folder of docs before beginning work with an agent. The agent starts with explicit context instead of asking basic setup questions.

## End-to-End Flow

### 1. Source registration

Accepted inputs for v1:

- local markdown files
- local plain text files
- inline text blobs passed directly to the tool

Each source becomes an ingestion artifact with:

- `artifact_id`
- `run_id`
- `source_type`
- `source_ref`
- `checksum`
- `project`
- `created_at`

### 2. Chunking and classification

Sources are chunked into manageable blocks. Chunks are classified with coarse labels such as:

- project context
- service/system description
- issue/blocker
- decision/rationale
- meeting content
- research/findings

### 3. Candidate extraction

The system extracts:

- candidate nodes
- candidate aliases
- candidate summaries
- candidate tags
- candidate relationships
- supporting evidence snippets

Candidates should target existing linked-notes shapes when possible:

- `project`
- `repo_project`
- `service`
- `issue`
- `decision`
- `workstream`
- `stakeholder`
- `research`

### 4. Deduplication and merge proposal

Before writing to the main graph, candidates are compared against existing notes using:

- normalized title match
- alias match
- project match
- summary/title overlap
- explicit relationship references

Each candidate should end in one of these states:

- `new`
- `merge_into_existing`
- `duplicate`
- `rejected`

### 5. Review

The user or agent inspects staged candidates and can:

- accept as a new memory node
- merge into an existing memory node
- reject with a reason
- defer for later review

### 6. Promotion

Accepted candidates become normal linked-notes nodes through existing write paths where possible:

- `create_from_template(...)`
- `upsert_memory_node(...)`
- `update_relationships(...)`

### 7. Enrichment by normal work

After promotion, existing workflows continue:

- `get_context(...)`
- `save_decision(...)`
- `save_session_summary(...)`
- `add_followup(...)`
- `promote_to_memory_node(...)`

## Storage Model

The main vault should continue to hold canonical memory notes.

Staged ingestion metadata should live beside the vault in hidden files so it is local and inspectable without polluting the graph:

- `.linked_notes_ingestion_runs.json`
- `.linked_notes_ingestion_candidates.json`
- `.linked_notes_ingestion_reviews.json`

If candidate bodies or large evidence need separate storage, use:

- `.linked_notes_ingestion/`

Suggested structure:

```text
vault/
  project-a.md
  service-b.md
  .linked_notes_followups.json
  .linked_notes_reviews.json
  .linked_notes_ingestion_runs.json
  .linked_notes_ingestion_candidates.json
  .linked_notes_ingestion_reviews.json
  .linked_notes_ingestion/
    run-20260315-abc123/
      artifact-index.json
      extracted-candidates.json
```

## Candidate Schema

Each candidate should be JSON-serializable and include:

```json
{
  "id": "candidate-123",
  "run_id": "run-20260315-abc123",
  "review_state": "pending",
  "candidate_type": "node",
  "entity_type": "service",
  "title": "API Gateway",
  "aliases": ["Gateway"],
  "summary": "Entry point for requests and auth coordination.",
  "project": "graph-memory",
  "status": "active",
  "tags": ["service", "backend"],
  "relationships": [
    { "type": "depends_on", "target": "Auth Service" }
  ],
  "body": "Optional supporting markdown body",
  "evidence": [
    {
      "artifact_id": "artifact-1",
      "snippet": "The gateway handles auth and forwards traffic...",
      "loc": "README.md:42"
    }
  ],
  "confidence": 0.81,
  "dedupe": {
    "strategy": "merge_into_existing",
    "matched_note_id": "api-gateway",
    "reasons": ["title match", "same project"]
  },
  "created_at": "2026-03-15T13:00:00Z"
}
```

## Provenance Fields For Promoted Notes

When a candidate is promoted into the main graph, the final note should preserve at least some provenance:

- `derived_from`
- `source_refs`
- `confidence`
- `last_reviewed`

Where full provenance is too verbose for frontmatter, keep detailed evidence in the body or in ingestion metadata and add a compact reference in frontmatter.

## Proposed MCP Tools

### `ingest_sources`

Purpose:
Create an ingestion run from local files or inline text, extract staged candidates, and return a summary.

Input:

```json
{
  "project": "linked-notes-mcp",
  "sources": [
    { "type": "file", "path": "/abs/path/README.md" },
    { "type": "text", "name": "handoff", "content": "raw handoff notes..." }
  ],
  "mode": "stage"
}
```

Output:

```json
{
  "run_id": "run-20260315-abc123",
  "artifacts": 2,
  "candidates_created": 9,
  "pending_review": 9
}
```

### `list_ingestion_runs`

Purpose:
Show recent ingestion runs and their status.

Input:

```json
{
  "limit": 20
}
```

### `review_extracted_nodes`

Purpose:
List staged candidates, optionally filtered by run, review state, entity type, or dedupe strategy.

Input:

```json
{
  "run_id": "run-20260315-abc123",
  "state": "pending",
  "limit": 20
}
```

### `accept_extracted_node`

Purpose:
Promote a staged candidate into the main graph as a real memory node.

Input:

```json
{
  "candidate_id": "candidate-123"
}
```

Behavior:

- create a new note when dedupe strategy is `new`
- use `upsert_memory_node(...)` when appropriate
- attach relationships after promotion
- mark candidate state as `accepted`

### `merge_extracted_node`

Purpose:
Merge a staged candidate into an existing note instead of creating a new one.

Input:

```json
{
  "candidate_id": "candidate-123",
  "target_identifier": "API Gateway"
}
```

Behavior:

- preserve the candidate evidence in the target note or ingestion metadata
- append or reconcile aliases, summary, and body content
- mark candidate state as `merged`

### `reject_extracted_node`

Purpose:
Reject a staged candidate and record why.

Input:

```json
{
  "candidate_id": "candidate-123",
  "reason": "Too vague to be durable memory"
}
```

### `generate_briefing`

Purpose:
Generate a durable report or briefing from notes that were seeded and enriched.

Input:

```json
{
  "identifier": "linked-notes-mcp",
  "format": "status_brief"
}
```

Output:

- generated markdown artifact
- linked note or staged report candidate

## Suggested Internal Modules

These modules fit the current project layout:

```text
src/linked_notes_mcp/
  ingestion.py
  ingestion_models.py
  ingestion_store.py
  ingestion_extract.py
  briefing.py
```

Responsibilities:

- `ingestion.py`: orchestration entry points
- `ingestion_models.py`: run, artifact, candidate, review dataclasses
- `ingestion_store.py`: local persistence for ingestion metadata
- `ingestion_extract.py`: chunking, extraction, and dedupe helpers
- `briefing.py`: graph-to-report synthesis

## Server Integration

Add new tools to `server.py` in phases.

Phase 1 should expose:

- `ingest_sources`
- `list_ingestion_runs`
- `review_extracted_nodes`
- `accept_extracted_node`
- `reject_extracted_node`

Phase 2 should add:

- `merge_extracted_node`
- `generate_briefing`

These tools should reuse existing graph write paths instead of inventing a second note creation mechanism.

## Ranking and Dedup Heuristics

Initial heuristics should stay simple and deterministic.

Candidate merge scoring can use:

- exact normalized title match: `+8`
- alias match: `+7`
- same project: `+3`
- title mentioned in summary/body: `+2`
- shared tags: `+1` each

Suggested thresholds:

- `>= 8`: likely merge candidate
- `4-7`: ambiguous, require review
- `< 4`: treat as new candidate

## Review UX Expectations

The review path should be compact and explainable.

For each candidate, surface:

- title
- entity type
- summary
- dedupe strategy
- confidence
- evidence snippets
- proposed relationships
- matched existing note, if any

The goal is not perfect automation. The goal is fast review with enough evidence to trust the result.

## Reporting and Briefing

Briefing generation should come after ingestion because it depends on graph coverage.

Useful briefing types:

- project status brief
- dependency/risk brief
- decision history brief
- stakeholder context brief
- handoff brief

Each generated artifact should either:

- become a normal note in the graph, or
- remain a staged artifact that can be promoted later

## Incremental Delivery Plan

### Milestone 1: staged ingestion foundation

- define ingestion dataclasses and hidden-file storage
- support file and text ingestion
- create staged node candidates
- expose run listing and candidate review

### Milestone 2: promotion and merge

- accept candidates into the graph
- merge candidates into existing notes
- preserve provenance and evidence
- add tests for dedupe and review state transitions

### Milestone 3: briefing generation

- generate markdown briefings from graph context
- link generated artifacts back to project nodes
- support follow-on review and promotion flows

## Testing Requirements

Add tests for:

- ingestion run creation
- candidate extraction from markdown and text
- dedupe matching against existing notes
- review state transitions
- candidate promotion into notes
- merge behavior preserving evidence
- briefing generation from a seeded graph

## Open Questions

- should promoted notes keep full provenance in frontmatter or only a compact summary
- how much extraction should be heuristic-only versus model-assisted
- should ingestion candidates be visible as graph nodes before acceptance
- should reports be first-class notes or separate generated artifacts
- when connectors are added later, should they live in this repo or companion repos

## Recommendation

Build this inside `linked-notes-mcp` first, behind a small set of tools and hidden-file metadata. If it proves valuable, connector-specific ingestion can later move to companion repos while still targeting the same staged-candidate format.
