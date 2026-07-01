---
title: Search Service
entity_type: service
summary: Full-text search and faceted search implementation for product discovery
depends_on:
- elasticsearch-infrastructure
- search-indexing-decision
blocks:
- search-api
- facet-engine
part_of:
- discovery-platform
---

# Search Service

Enables rich product search experience.

## Features
- Full-text search
- Faceted search (filters)
- Autocomplete suggestions
- Typo tolerance
- Ranked results

## Integration
- Indexes from Product Service
- Near real-time updates via events
- 100ms search latency target
