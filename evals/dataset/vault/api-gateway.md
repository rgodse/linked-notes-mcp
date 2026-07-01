---
title: API Gateway
entity_type: service
summary: Central entry point for all API requests with routing, rate limiting, and
  request transformation
depends_on:
- request-validation-strategy
- rate-limiting-decision
- logging-infrastructure
blocks:
- request-router
- middleware-pipeline
part_of:
- backend-infrastructure
---

# API Gateway

Manages all incoming API requests with intelligent routing and cross-cutting concerns.

## Features
- Request routing to microservices
- Rate limiting per client
- Request/response transformation
- Centralized logging
- Authentication enforcement
