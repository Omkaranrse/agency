# ADR 0007: FastAPI REST API, Constant-Time Auth, and Server-Sent Events

## Status
Accepted

## Context
The operator dashboard and external automated systems require a secure, performant interface to submit runs, inspect state, download artifacts, and receive real-time streaming updates without WebSocket complexity.

## Decision
We implemented a FastAPI interface featuring:
1. **Constant-Time Authentication**: Uses `hmac.compare_digest` to prevent timing attacks. Enforces fail-closed configuration in production.
2. **Server-Sent Events (SSE)**: Streams durable domain events (`EventFeedPort`) over HTTP with `Last-Event-ID` reconnection support.
3. **Defense-in-Depth Middleware**: `RequestIDMiddleware` (correlation ID) and `RequestSizeLimitMiddleware` (1MB limit).
4. **Sliding-Window Rate Limiting**: In-memory rate limiting across creation, write, and read endpoints.
5. **Contract Enforcement**: Generates OpenAPI specs (`docs/openapi.json`) and verifies TypeScript client alignment with zero-drift CI tests.

## Consequences
- Fast, unidirectional real-time event streaming across browser firewalls.
- Strong API security and strict payload bounds.
- Full TypeScript client type safety.
