---
title: Database Design
tags:
  - database
  - infrastructure
---

# Database Design

PostgreSQL database architecture.

## Schema

Each [[Microservices|microservice]] has its own schema:
- `auth.*` - [[Authentication Service]] tables
- `users.*` - [[User Service]] tables

## Migrations

Using Flyway for version control.

## Backups

Daily automated backups, see [[Deployment Strategy]].
