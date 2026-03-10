---
title: Deployment Strategy
tags:
  - devops
  - infrastructure
---

# Deployment Strategy

Kubernetes-based deployment.

## Components

- [[API Gateway]] - 3 replicas
- [[Microservices]] - auto-scaled
- [[Database Design|Database]] - managed RDS

## CI/CD

GitHub Actions pipeline:
1. Build and test
2. Build Docker images
3. Deploy to staging
4. Deploy to production

## Monitoring

Prometheus + Grafana for metrics.
