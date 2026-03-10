---
title: Authentication Service
tags:
  - security
  - service
---

# Authentication Service

Handles all authentication and authorization.

## Features

- User login/logout
- [[JWT Tokens]] generation and validation
- OAuth2 support
- Session management

## Endpoints

- POST /auth/login
- POST /auth/logout
- POST /auth/refresh
- GET /auth/validate

Integrates with [[User Service]] for user data.
