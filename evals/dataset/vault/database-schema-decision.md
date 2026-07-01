---
title: Database Schema Decision
entity_type: decision
summary: Use normalized PostgreSQL schema with careful denormalization for performance
depends_on:
- product-service
blocks: []
part_of:
- data-layer
---

# Database Schema Decision

## Approach: Normalized + Strategic Denormalization
- Third normal form as baseline
- Denormalize product counts/totals
- Materialized views for complex queries

## Rationale
Balance between data integrity and query performance
