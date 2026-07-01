---
title: Data Warehouse Decision
entity_type: decision
summary: Use BigQuery as cloud data warehouse for analytics and ML
depends_on:
- analytics-platform
blocks: []
part_of:
- analytics-platform
---

# Data Warehouse Decision

## Choice: Google BigQuery
- Serverless architecture
- Managed infrastructure
- ML integration (BigQuery ML)
- Cost-effective for analytics

## Alternative Considered
- Snowflake: Higher cost
- Redshift: More operational overhead

## Data Pipeline
- Streaming via Dataflow
- Batch via Cloud Functions
- 24-hour latency acceptable
