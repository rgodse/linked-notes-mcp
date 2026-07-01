---
title: Message Broker Decision
entity_type: decision
summary: Use RabbitMQ as primary message broker for event distribution
depends_on:
- event-driven-architecture
blocks: []
part_of:
- messaging-infrastructure
---

# Message Broker Decision

## Choice: RabbitMQ
- Reliable message delivery
- Exchange and binding model
- Dead letter queues
- Persistent storage

## Alternatives Considered
- Kafka: Overkill for current scale
- Redis: Less reliable persistence
- AWS SQS: Vendor lock-in

## Configuration
- Durable queues
- Message TTL: 24 hours
- 3-node cluster for HA
