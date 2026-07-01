---
title: Order Service
entity_type: service
summary: Handles order creation, processing, and fulfillment workflows
depends_on:
- product-service
- payment-service
- inventory-sync-decision
- event-driven-architecture
blocks:
- order-api
- fulfillment-engine
part_of:
- ecommerce-platform
---

# Order Service

Manages complete order lifecycle.

## Workflows
- Order creation and validation
- Payment processing coordination
- Inventory reservation
- Fulfillment coordination
- Order tracking

## Integrations
- Payment Service for transactions
- Product Service for inventory
- Notification Service for updates
