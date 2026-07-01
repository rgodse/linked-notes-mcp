# Autonomous Agent Integration

## Why This Works Well for Autonomous Runs

Long-running agent workflows need more than search. They need:

- explicit dependencies
- visible decision history
- recoverable session state
- handoff context that is easy to inspect

This repo gives you that by keeping memory in a local markdown graph.

## Recommended Pattern

Before starting work:

1. call `get_context` for the project/topic
2. call `get_graph_context` on the anchor note
3. inspect `list_relationships` for dependency edges

During work:

1. update notes when the graph changes
2. write decisions with `save_decision`
3. add followups for unresolved work

At pause or completion:

1. write `end_session`
2. link the summary note to the project or decision notes it affected

## Good Note Shapes

### Project note

Use:

- `part_of`
- `contains`
- `related_to`

### Dependency note

Use:

- `depends_on`
- `blocks`
- `blocked_by`

### Decision note

Use:

- `decision_for`
- `supersedes`
- `related_to`

## Client Instructions

Add something like this to your client instructions:

```text
When working autonomously:
1. Prefer graph tools over raw search when a note already exists.
2. Maintain explicit frontmatter relationships for important dependencies and decisions.
3. Use save_decision for meaningful choices.
4. Use end_session before stopping.
5. Use add_followup for anything the next session should remember to check.
```
