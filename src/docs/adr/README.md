# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the MCP Server with OAuth 2.1 and OBO Flow project.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences. ADRs help teams understand why certain decisions were made and provide a historical record for future reference.

## ADR Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-001](ADR-001-mcp-server-hosting-architecture.md) | MCP Server Hosting Architecture for OAuth 2.1 + OBO Flow | Accepted | 2026-01-20 |

## ADR Lifecycle

- **Proposed** - Under discussion, open for feedback
- **Accepted** - Decision has been made and implemented
- **Deprecated** - No longer applies but kept for historical context
- **Superseded** - Replaced by a newer ADR (link to replacement)

## Creating a New ADR

1. Copy the template below
2. Name the file `ADR-NNN-short-title.md` (NNN = next number)
3. Fill in the sections
4. Submit a PR for review

## ADR Template

```markdown
# ADR-NNN: Title

## Status

Proposed | Accepted | Deprecated | Superseded by [ADR-XXX](link)

## Date

YYYY-MM-DD

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision Drivers

- Driver 1
- Driver 2
- ...

## Considered Options

### Option A: Name

Description and characteristics.

### Option B: Name

Description and characteristics.

## Decision

What is the change that we're proposing and/or doing?

## Rationale

Why is this decision being made?

## Consequences

### Positive

- Benefit 1
- Benefit 2

### Negative

- Drawback 1
- Drawback 2

## References

- [Link 1](url)
- [Link 2](url)
```

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Documenting Architecture Decisions - Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
