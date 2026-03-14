# Usage Rules

Use the repo as graph memory, not just a pile of notes.

## Core Habits

### 1. Start from an anchor

Use:

- `get_context("topic")`
- `get_graph_context("Anchor Note")`

Do not start by loading random notes unless you already know the exact note you want.

### 2. Prefer explicit relationships

Important project notes should use frontmatter relationships such as:

- `depends_on`
- `blocks`
- `related_to`
- `decision_for`
- `part_of`

This is what makes graph retrieval stronger than plain text retrieval.

Also keep these frontmatter fields current:

- `aliases`
- `entity_type`
- `project`
- `status`
- `summary`
- `importance`
- `confidence`
- `last_reviewed`

### 3. Save decisions as graph objects

Important choices should become notes with links and relationship fields, not only paragraphs buried in a session log.

### 4. End with a summary and followups

Before stopping:

- save a session summary
- dismiss completed followups
- add new followups for unresolved work

## Practical Prompt Patterns

| Situation | Prompt |
|-----------|--------|
| Start work | "Get context on project-x" |
| Inspect structure | "List relationships for API Gateway" |
| Expand nearby context | "Show graph context around API Gateway" |
| Understand a dependency chain | "Find the path between API Gateway and Deployment Strategy" |
| Record a major choice | "Save this as a decision for project-x" |
| Pause work | "Save a session summary and add followups" |

## What Makes the Graph Better

The graph becomes useful when:

- titles are consistent
- notes link to each other
- frontmatter relationships are maintained
- decision and project notes stay current

If you skip those habits, the system falls back to plain note search.

## Maintenance Habits

Run maintenance regularly:

- lint the graph
- score memory health
- accept or reject suggested relationships
- merge duplicate nodes
- review stale but important notes

Treat suggestions as reviewable memory candidates, not automatic truth. Over time the review history becomes a lightweight confidence signal.
