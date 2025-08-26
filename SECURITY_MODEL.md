# Security Model (Initial Draft)

Current (Phase 1):
- JWT secret sourced via env (fallback dev default) – must be overridden.
- Basic rate limiting (in-memory, per-IP) – not distributed.
- No full RBAC yet; placeholder plugin enable/disable only.

Planned:
- Phase 2: Auth middleware integration across endpoints, role claims in JWT, input validation expansion.
- Phase 3: Secrets manager integration, audit logging, anomaly detection, dependency scanning automation.
- Phase 4: Data encryption at rest for sensitive memory segments, fine-grained permission model, key rotation automation.
