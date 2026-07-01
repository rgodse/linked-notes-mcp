---
title: Redis Infrastructure
entity_type: service
summary: Distributed in-memory data store for caching and session management
depends_on:
- cache-layer-decision
blocks:
- cache-cluster
- session-store
part_of:
- infrastructure-layer
---

# Redis Infrastructure

Central in-memory data store.

## Deployment
- Redis Cluster with 6 nodes
- Master-replica replication
- Persistence via RDB + AOF
- Automatic failover

## Usage
- Session store
- Cache layer
- Rate limiting counters
- Real-time leaderboards
