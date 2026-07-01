---
title: Product Service
entity_type: service
summary: Manages product catalog, inventory, and product information
depends_on:
- database-schema-decision
- cache-layer-decision
blocks:
- product-api
- inventory-manager
part_of:
- ecommerce-platform
---

# Product Service

Core service for product management.

## Responsibilities
- Product catalog management
- Inventory tracking
- Product search and filtering
- SKU management
- Category hierarchy

## Architecture
- PostgreSQL for authoritative data
- Elasticsearch for full-text search
- Redis cache for hot products
