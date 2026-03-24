<!--
Sync Impact Report
Version change: 0.0.0 -> 1.0.0
Modified principles:
- Template placeholder -> I. Python + FastAPI First
- Template placeholder -> II. API-Only Backend Boundary
- Template placeholder -> III. Readable Code With Business Comments
- Template placeholder -> IV. Testable Contracts And Quality Gates
- Template placeholder -> V. Dockerized Delivery And Deployment Docs
Added sections:
- Technical Standards
- Delivery Workflow
Removed sections:
- None
Templates requiring updates:
- ✅ updated `.specify/templates/plan-template.md`
- ✅ updated `.specify/templates/spec-template.md`
- ✅ updated `.specify/templates/tasks-template.md`
- ⚠ pending `.specify/templates/commands/*.md` (directory not present in repository)
Follow-up TODOs:
- None
-->
# IGES Parser Constitution

## Core Principles

### I. Python + FastAPI First
All backend functionality MUST be implemented in Python and exposed through
FastAPI. New runtime components, examples, and generated project structures MUST
assume a backend API service, not a mixed-language platform. Introducing another
primary backend framework or language requires an explicit amendment to this
constitution.

Rationale: a single language and framework reduce operational complexity,
onboarding cost, and architectural drift.

### II. API-Only Backend Boundary
This project MUST remain backend-only. The repository MUST NOT introduce a
frontend application, UI bundle, or browser-specific delivery flow unless the
constitution is amended first. Feature specifications MUST describe API
contracts, request/response behavior, validation, and error handling for all
user-visible behavior.

Rationale: the project scope is a service API, and a strict boundary prevents
scope creep and accidental frontend coupling.

### III. Readable Code With Business Comments
Code MUST prefer the simplest readable implementation that satisfies the
requirement. New functions, services, and non-trivial branches MUST include
comments that explain how the logic works and why it exists from a business
perspective. Existing comments MUST be preserved unless they are provably wrong,
and new code MUST avoid unnecessary abstraction.

Rationale: maintainability depends on clarity of intent, not only correctness.
Business-context comments reduce the cost of future changes and reviews.

### IV. Testable Contracts And Quality Gates
Every feature that changes API behavior MUST define verifiable acceptance
scenarios and include automated tests at the appropriate level. API contract and
integration tests are REQUIRED for new endpoints, changed schemas, validation
rules, and error handling. Unit tests SHOULD cover isolated business logic where
they improve feedback speed and safety.

Rationale: backend APIs fail at boundaries first, so contracts and integrations
must be protected before delivery.

### V. Dockerized Delivery And Deployment Docs
Every deployable application MUST be runnable from a Docker container, and the
repository MUST contain deployment instructions describing required environment
variables, startup steps, and verification steps. A feature is not complete if
it cannot be built, started, and checked in a containerized flow.

Rationale: deployment is part of the product. Containerization and explicit
instructions make environments reproducible and reduce release risk.

## Technical Standards

- Default implementation stack MUST target Python and FastAPI.
- Generated plans and tasks MUST assume an API service structure without a
  frontend directory.
- API behavior MUST be documented through contracts, validation rules, and
  measurable acceptance criteria.
- Docker assets such as `Dockerfile`, optional `docker-compose.yml`, and runtime
  configuration documentation MUST be planned whenever the application is
  deployable.
- Logging, configuration, and error responses MUST stay simple, explicit, and
  observable.

## Delivery Workflow

- Each specification MUST capture independently testable user scenarios, edge
  cases, API-facing requirements, and operational constraints.
- Each implementation plan MUST pass a constitution check for stack choice,
  backend-only scope, testing impact, Docker readiness, deployment
  documentation, and code comment expectations.
- Each task list MUST include work for API implementation, required automated
  tests, Docker packaging, deployment documentation, and code comments where new
  business logic is introduced.
- Reviews MUST reject changes that add avoidable complexity, omit required
  comments, skip boundary tests, or leave deployment steps undocumented.

## Governance

This constitution overrides conflicting local practices for this repository. Any
change to stack, architectural scope, delivery rules, or quality gates MUST be
documented in the constitution and reviewed together with the dependent
templates.

Amendments use semantic versioning:
- MAJOR for incompatible governance changes or removed principles.
- MINOR for new principles, new mandatory sections, or materially expanded
  guidance.
- PATCH for clarifications, wording updates, and non-semantic refinements.

Compliance review is mandatory for every plan, spec, and task set generated from
`.specify` templates. Reviewers MUST verify:
- Python + FastAPI alignment
- backend-only scope
- required comments for business logic
- required automated tests for API changes
- Docker packaging and deployment documentation

This document is ratified on first adoption and amended whenever these rules
change.

**Version**: 1.0.0 | **Ratified**: 2026-03-24 | **Last Amended**: 2026-03-24
