---
title: Notification Service
entity_type: service
summary: Unified notification system supporting email, SMS, and push notifications
depends_on:
- event-driven-architecture
- template-engine-decision
blocks:
- email-dispatcher
- sms-dispatcher
- push-dispatcher
part_of:
- customer-engagement
---

# Notification Service

Multi-channel notification delivery system.

## Channels
- Email via SendGrid
- SMS via Twilio
- Push notifications via Firebase

## Features
- Template management
- Delivery tracking
- Retry logic
- Preference management
- Unsubscribe support
