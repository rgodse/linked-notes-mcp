---
title: Metrics Collection Decision
entity_type: decision
summary: Use Prometheus for metrics collection and storage with Grafana dashboards
depends_on:
- observability-platform
blocks: []
part_of:
- observability-platform
---

# Metrics Collection Decision

## Choice: Prometheus
- Pull-based model
- Time-series database
- PromQL query language
- Grafana integration

## Metrics Collected
- Request latency
- Error rates
- Resource utilization
- Business metrics
