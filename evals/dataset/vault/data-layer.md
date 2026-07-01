---
title: Data Layer
entity_type: project
summary: Data persistence and retrieval infrastructure
depends_on:
- database-schema-decision
- redis-infrastructure
blocks:
- databases
- caches
part_of:
- platform
---

# Data Layer Project

Data persistence infrastructure.

## Components
- PostgreSQL primary DB
- Redis cache layer
- Elasticsearch for search
- BigQuery for analytics

## Strategy
- Primary data in PostgreSQL
- Hot data in Redis
- Search in Elasticsearch
- Historical in BigQuery
