---
title: Stateless Authentication
entity_type: concept
summary: Authentication approach without server-side session storage using tokens
depends_on:
- jwt-token-strategy
blocks: []
part_of:
- authentication-architecture
---

# Stateless Authentication Concept

Authentication without server-side session storage.

## Benefits
- Horizontal scalability
- No session affinity required
- Easier multi-server deployments
- Better for microservices

## Trade-offs
- Cannot revoke tokens instantly
- Larger request payloads
- Client-side token storage concerns
