---
title: Project Architecture
tags:
  - architecture
  - planning
---

# Project Architecture

This document outlines our system architecture decisions.

## Key Components

We use a [[Microservices]] approach with the following services:

- [[API Gateway]] - Handles all incoming requests
- [[Authentication Service]] - Manages user auth via [[JWT Tokens]]
- [[User Service]] - CRUD operations for users

## Data Layer

All services connect to our [[Database Design]] which uses PostgreSQL.

See also: [[Deployment Strategy]]
