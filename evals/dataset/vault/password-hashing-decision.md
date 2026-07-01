---
title: Password Hashing Decision
entity_type: decision
summary: Selection of bcrypt for password hashing with configurable work factor
depends_on:
- security-best-practices
blocks: []
part_of:
- authentication-architecture
---

# Password Hashing Decision

## Choice: bcrypt
- Work factor: 12
- Automatic salt generation
- GPU-resistant algorithm

## Rationale
Superior to PBKDF2 for modern attack scenarios and simpler implementation than Argon2.
