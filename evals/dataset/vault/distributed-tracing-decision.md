---
title: Distributed Tracing Decision
entity_type: decision
summary: Implement distributed tracing with Jaeger for request flow analysis
depends_on:
- observability-platform
blocks: []
part_of:
- observability-platform
---

# Distributed Tracing Decision

## Choice: Jaeger
- OpenTelemetry compatible
- Multi-language support
- Sampled tracing (1% of requests)
- Latency analysis

## Benefits
- Understand request flows
- Identify bottlenecks
- Performance debugging
