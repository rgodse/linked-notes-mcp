---
title: Logging Infrastructure
entity_type: service
summary: Centralized logging system for all services with structured logging and log
  aggregation
depends_on:
- structured-logging-concept
- log-aggregation-decision
blocks:
- log-collector
- log-storage
part_of:
- observability-platform
---

# Logging Infrastructure

Centralized logging across all services.

## Components
- Fluent Bit agents per service
- Elasticsearch for storage
- Kibana for visualization
- 30-day retention policy

## Log Format
Structured JSON with standard fields: timestamp, service, level, traceId, userId
