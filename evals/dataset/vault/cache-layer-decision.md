---
title: Cache Layer Decision
entity_type: decision
summary: Implement multi-level caching with Redis and application-level caching
depends_on:
- redis-infrastructure
blocks: []
part_of:
- performance-optimization
---

# Cache Layer Decision

## Strategy: Multi-Level Caching
1. Application-level (in-process)
2. Distributed (Redis)
3. CDN edge (for static content)

## Cache Invalidation
- TTL-based expiration
- Event-based invalidation
- Cache stampede prevention via locks

## Hot Spots
- Product catalog (1 hour TTL)
- User preferences (30 minutes TTL)
- Category hierarchy (24 hours TTL)
