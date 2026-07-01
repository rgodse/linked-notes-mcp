---
title: User Profile Service
entity_type: service
summary: Manages user profile data, preferences, and account settings
depends_on:
- auth-service
- data-validation-concept
blocks:
- profile-api
- preference-store
part_of:
- identity-platform
---

# User Profile Service

Handles all user profile and account-related operations.

## Capabilities
- Profile CRUD operations
- Preference management
- Account settings
- Profile picture upload
- Email verification

## Storage
PostgreSQL with Redis caching for frequent access
