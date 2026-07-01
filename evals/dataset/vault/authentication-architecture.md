---
title: Authentication Architecture
entity_type: concept
summary: Overall authentication strategy and component interactions
depends_on:
- jwt-token-strategy
- oauth2-integration
blocks: []
part_of:
- identity-platform
---

# Authentication Architecture

Multi-layered authentication system.

## Flows
1. Traditional login with JWT
2. OAuth2 via Google/GitHub
3. Token refresh
4. Logout

## Security
- HTTPS required
- Secure cookies
- CSRF protection
- Rate limiting on login
