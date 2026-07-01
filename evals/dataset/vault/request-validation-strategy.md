---
title: Request Validation Strategy
entity_type: decision
summary: Use JSON Schema for all API request validation
depends_on:
- api-gateway
blocks: []
part_of:
- api-management
---

# Request Validation Strategy

## Approach
- JSON Schema for all request bodies
- Automatic validation at API Gateway
- Return 400 Bad Request on validation failure
- Centralized schema repository

## Tools
- Ajv for JSON Schema validation
- Schema versioning support
