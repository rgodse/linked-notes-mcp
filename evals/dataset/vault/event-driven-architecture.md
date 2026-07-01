---
title: Event-Driven Architecture
entity_type: concept
summary: Asynchronous event-based communication between services using message broker
depends_on:
- message-broker-decision
blocks: []
part_of:
- architecture-patterns
---

# Event-Driven Architecture

Services communicate through events rather than direct calls.

## Benefits
- Loose coupling
- Scalability
- Resilience
- Audit trail

## Event Types
- User events (signup, login)
- Order events (created, paid, shipped)
- Product events (updated, deleted)
- Payment events (succeeded, failed)
