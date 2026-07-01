---
title: JWT Token Strategy
entity_type: decision
summary: Decision to use JWT tokens for stateless authentication across services
depends_on:
- stateless-auth-concept
blocks: []
part_of:
- authentication-architecture
---

# JWT Token Strategy Decision

## Rationale
JWT provides stateless authentication suitable for microservices architecture.

## Implementation
- HS256 signing algorithm
- 1 hour access token expiry
- 7 day refresh token expiry
- Payload includes user ID, roles, permissions

## Trade-offs
- Cannot revoke tokens before expiry
- Larger payload per request
- Mitigated by short expiry times
