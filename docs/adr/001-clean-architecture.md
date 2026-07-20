# ADR-001: Clean Architecture with Domain-Driven Design

## Status
Accepted

## Context
The project needs to be maintainable, testable, and adaptable to changing business requirements. Direct coupling to frameworks and infrastructure leads to brittle code.

## Decision
We adopt Clean Architecture (Robert C. Martin) with elements of Domain-Driven Design:

- **Domain layer** — pure Python business logic, zero framework imports
- **Application/Service layer** — orchestration and use cases
- **Infrastructure layer** — external APIs, databases, caches
- **API/Presentation layer** — FastAPI endpoints, Pydantic schemas

## Consequences
- Framework replacements (e.g., FastAPI → another web framework) only affect the API layer
- Domain logic is fully unit-testable without dependencies
- Higher initial setup cost but significantly lower maintenance cost

## Compliance
All new modules must follow the dependency rule: dependencies point inward, never outward.
