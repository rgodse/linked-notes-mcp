---
title: Inventory Sync Decision
entity_type: decision
summary: Event-driven inventory synchronization between Order and Product services
depends_on:
- order-service
- product-service
blocks: []
part_of:
- ecommerce-platform
---

# Inventory Sync Decision

## Approach: Event-Driven
1. Order created -> InventoryReserved event
2. Product service listens and updates counts
3. Order shipped -> InventoryAllocated event
4. Order cancelled -> InventoryReleased event

## Consistency
- Eventual consistency acceptable
- Overselling prevention via distributed locks
- Reconciliation job nightly
