---
title: User Service
tags:
  - service
  - crud
---

# User Service

Manages user data and profiles.

## Endpoints

- GET /users/:id
- POST /users
- PUT /users/:id
- DELETE /users/:id

## Data Model

Stored in [[Database Design]] with:
- id, email, password_hash
- profile fields
- created_at, updated_at

Works with [[Authentication Service]] for credential verification.
