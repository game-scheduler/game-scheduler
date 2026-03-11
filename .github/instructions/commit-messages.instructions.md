---
description: 'Write clear, detailed git commit messages with summaries and rationale'
applyTo: '**'
---

# Commit Message Guidelines

When creating git commits, use a multi-line message format:

- **Subject line**: short, imperative summary (no trailing period)
- **Body**: bullet list of notable changes
- **Rationale**: include a brief reason when the change is non-obvious

## Example

```
feat: add scheduler health endpoint

- add /healthz route with database connectivity check
- include timeout and retry configuration
- update service documentation

Rationale: required for load balancer health checks in staging
```
