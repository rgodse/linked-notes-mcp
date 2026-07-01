---
title: Data Validation
entity_type: concept
summary: Consistent approach to input validation across services
depends_on: []
blocks: []
part_of:
- architecture-patterns
---

# Data Validation Concept

Ensuring data quality and security.

## Layers
1. Client-side validation (UX)
2. API Gateway validation (security)
3. Service-level validation (consistency)
4. Database constraints (integrity)

## Approach
- JSON Schema for API requests
- ORM validators for data models
- Business rule validation in services
