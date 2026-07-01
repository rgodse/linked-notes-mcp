---
title: Elasticsearch Infrastructure
entity_type: service
summary: Distributed search and analytics engine for product search and logging
depends_on:
- search-service
- logging-infrastructure
blocks:
- search-cluster
- analytics-cluster
part_of:
- infrastructure-layer
---

# Elasticsearch Infrastructure

Searching and analytics backbone.

## Clusters
- Search cluster: 5 nodes, 3 replicas
- Logging cluster: 3 nodes, 2 replicas

## Configuration
- ILM for log retention
- Custom analyzers for product search
- Shard allocation awareness
