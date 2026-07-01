---
title: Search Indexing Decision
entity_type: decision
summary: Event-driven indexing with dual-write pattern for search consistency
depends_on:
- event-driven-architecture
blocks: []
part_of:
- search-infrastructure
---

# Search Indexing Decision

## Approach: Event-Driven + Dual-Write
1. Write to database
2. Publish ProductUpdated event
3. Search service listens and indexes
4. Fallback dual-write for resilience

## Consistency Model
- Eventual consistency acceptable
- Index latency: <5 seconds
- Batch reindexing nightly
