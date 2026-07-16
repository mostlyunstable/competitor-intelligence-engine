# Utservio Intelligence Platform — Documentation Index

Welcome to the complete documentation for the Utservio Intelligence Platform. This index helps you find the right document based on your role and needs.

## Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](../README.md) | Project overview, quick start, features | Everyone |
| [docs/README.md](#) | This index — documentation navigation | Everyone |

---

## Architecture & Design

| Document | Purpose | Audience |
|----------|---------|----------|
| [architecture.md](architecture.md) | System architecture, components, lifecycles | Engineers, Architects |
| [data-flow.md](data-flow.md) | End-to-end data movement diagrams | Engineers, QA |
| [module-integration.md](module-integration.md) | How all modules connect | Engineers |
| [end-to-end-flow.md](end-to-end-flow.md) | 10 complete sequence diagrams | Engineers, QA |
| [project-structure.md](project-structure.md) | Repository organization with responsibilities | Engineers, New Hires |

## Technology & Stack

| Document | Purpose | Audience |
|----------|---------|----------|
| [technology-stack.md](technology-stack.md) | All technologies, versions, decisions | Engineers, Tech Leads |
| [database.md](database.md) | ER diagram, 13 tables, relationships | Backend Engineers |

## API & Frontend

| Document | Purpose | Audience |
|----------|---------|----------|
| [api.md](api.md) | Complete API endpoint reference | Frontend Engineers, QA |
| [api-frontend-mapping.md](api-frontend-mapping.md) | UI ↔ API endpoint mapping | Full-Stack Engineers |
| [ui-guide.md](ui-guide.md) | React frontend architecture, components, routing | Frontend Engineers |

## Operations & Deployment

| Document | Purpose | Audience |
|----------|---------|----------|
| [deployment-architecture.md](deployment-architecture.md) | Docker, scaling, networking diagrams | DevOps, SRE |
| [installation-guide.md](installation-guide.md) | Complete setup from fresh clone | Engineers, QA |
| [security.md](security.md) | Authentication, authorization, hardening | Security, Engineers |
| [scalability-performance.md](scalability-performance.md) | Scaling architecture, optimizations | Architects, SRE |

## Quality & Verification

| Document | Purpose | Audience |
|----------|---------|----------|
| [verification-checklist.md](verification-checklist.md) | 18-component verification matrix | QA, Engineers |
| [acceptance-criteria.md](acceptance-criteria.md) | 84 acceptance criteria with status | Product, QA, Engineering |
| [feature-traceability.md](feature-traceability.md) | 53 features traced from requirements | Product, QA |

## Planning & Roadmap

| Document | Purpose | Audience |
|----------|---------|----------|
| [production-features.md](production-features.md) | Implemented production feature matrix | Product, Engineers |
| [known-limitations.md](known-limitations.md) | Current constraints and workarounds | Engineers, Product |
| [future-scope.md](future-scope.md) | Planned enhancements and extension points | Product, Engineers |
| [version-information.md](version-information.md) | Release history, component versions, roadmap | Everyone |

---

## Suggested Reading Order

### For New Engineers (Day 1)

1. [README.md](../README.md) — Project overview
2. [docs/README.md](#) — This index
3. [architecture.md](architecture.md) — System architecture
4. [project-structure.md](project-structure.md) — Repository layout
5. [technology-stack.md](technology-stack.md) — Tech decisions
6. [installation-guide.md](installation-guide.md) — Set up locally

### For Backend Engineers

1. [architecture.md](architecture.md) — System overview
2. [database.md](database.md) — Schema design
3. [api.md](api.md) — API reference
4. [module-integration.md](module-integration.md) — Module connections
5. [end-to-end-flow.md](end-to-end-flow.md) — Sequence diagrams

### For Frontend Engineers

1. [ui-guide.md](ui-guide.md) — Frontend architecture
2. [api-frontend-mapping.md](api-frontend-mapping.md) — Endpoint mapping
3. [api.md](api.md) — API reference
4. [project-structure.md](project-structure.md) — File organization

### For QA Engineers

1. [acceptance-criteria.md](acceptance-criteria.md) — All criteria
2. [verification-checklist.md](verification-checklist.md) — Verification matrix
3. [feature-traceability.md](feature-traceability.md) — Feature coverage
4. [end-to-end-flow.md](end-to-end-flow.md) — Expected flows

### For DevOps / SRE

1. [deployment-architecture.md](deployment-architecture.md) — Deployment modes
2. [installation-guide.md](installation-guide.md) — Setup procedures
3. [security.md](security.md) — Security hardening
4. [scalability-performance.md](scalability-performance.md) — Scaling strategy

### For Product / Management

1. [README.md](../README.md) — Project overview
2. [production-features.md](production-features.md) — What's built
3. [future-scope.md](future-scope.md) — What's planned
4. [version-information.md](version-information.md) — Release history
5. [known-limitations.md](known-limitations.md) — Current constraints

---

## Screenshots

> **Note:** Screenshots require the application to be running in a browser. Capture these after deployment.

```
docs/
└── screenshots/
    ├── login.png
    ├── dashboard.png
    ├── competitors.png
    ├── competitor-profile.png
    ├── collections.png
    ├── logs.png
    ├── reports.png
    ├── admin.png
    └── mobile-dashboard.png
```

Referenced from: [ui-guide.md](ui-guide.md)

---

## Documentation Statistics

| Category | Count | Total Pages (est.) |
|----------|-------|-------------------|
| Architecture & Design | 5 | ~50 |
| Technology & Stack | 2 | ~20 |
| API & Frontend | 3 | ~30 |
| Operations & Deployment | 4 | ~40 |
| Quality & Verification | 3 | ~30 |
| Planning & Roadmap | 4 | ~30 |
| **Total** | **21** | **~200** |

---

## Contributing to Documentation

When updating documentation:

1. Keep the table above in sync
2. Update the version history in [version-information.md](version-information.md)
3. Maintain consistent formatting across all files
4. Use Mermaid diagrams for visual documentation
5. Include file path references (`file.py:line_number`) for code references

---

*Last updated: 2025-07-16*
