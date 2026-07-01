---
title: Payment Retry Decision
entity_type: decision
summary: Implement exponential backoff retry strategy for failed payment attempts
depends_on:
- payment-service
- event-driven-architecture
blocks: []
part_of:
- payment-infrastructure
---

# Payment Retry Decision

## Strategy: Exponential Backoff
- 3 retry attempts
- 1 second, 4 seconds, 16 seconds delays
- Jitter to prevent thundering herd
- Max retry window: 1 hour

## Implementation
Async job queue with scheduled retries
