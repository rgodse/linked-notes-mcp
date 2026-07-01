---
title: OAuth2 Integration
entity_type: service
summary: External OAuth2 provider integration supporting Google and GitHub authentication
depends_on:
- auth-service
- user-profile-service
blocks:
- oauth-provider-adapter
part_of:
- identity-platform
---

# OAuth2 Integration

Enables authentication via third-party identity providers.

## Supported Providers
- Google OAuth2
- GitHub OAuth2

## Flow
1. Redirect to provider
2. User grants permission
3. Receive authorization code
4. Exchange for access token
5. Fetch user profile
6. Create/link local user
7. Issue JWT token
