---
title: API Gateway
tags:
  - infrastructure
  - security
---

# API Gateway

The API Gateway is the single entry point for all client requests.

## Responsibilities

- Request routing to [[Microservices]]
- Authentication via [[JWT Tokens]]
- Rate limiting
- Request/response transformation

## Implementation

We use Kong as our gateway, configured in [[Deployment Strategy]].
