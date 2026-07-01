---
title: ML Infrastructure
entity_type: service
summary: Machine learning platform for model training, testing, and deployment
depends_on:
- data-warehouse-decision
blocks:
- training-pipeline
- model-registry
part_of:
- analytics-platform
---

# ML Infrastructure

Supports ML workflows for recommendations and analytics.

## Components
- Jupyter notebooks for development
- MLflow for experiment tracking
- Docker for reproducibility
- Kubernetes for distributed training
- Model registry for version control

## Frameworks
- Scikit-learn for classical ML
- TensorFlow for deep learning
