---
title: JWT Tokens
tags:
  - security
  - authentication
---

# JWT Tokens

JSON Web Tokens for stateless authentication.

## Structure

- Header: algorithm and token type
- Payload: claims (user ID, roles, expiry)
- Signature: verification

## Configuration

- Access token: 15 min expiry
- Refresh token: 7 day expiry
- Algorithm: RS256

Used by [[Authentication Service]] and validated at [[API Gateway]].
