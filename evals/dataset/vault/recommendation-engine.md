---
title: Recommendation Engine
entity_type: service
summary: ML-powered product recommendation system using collaborative filtering
depends_on:
- ml-infrastructure
- user-behavior-tracking
blocks:
- recommendation-api
- model-trainer
part_of:
- discovery-platform
---

# Recommendation Engine

Personalized product recommendations using machine learning.

## Algorithm
- Collaborative filtering
- User-based and item-based approaches
- Hybrid model

## Data
- User browse history
- Purchase history
- Product similarity
- Seasonal trends

## Serving
- Pre-computed recommendations
- 5-minute update frequency
- A/B testing framework
