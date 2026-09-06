# Project review and verification

## Original findings
The original two tests passed under Python 3.12. The default system Python was 3.9 and unsuitable for the project syntax/dependencies. The README overstated implementation: retrieval was keyword overlap, the provider always returned mock text, LangGraph was absent, and service status was hard-coded. The evaluation script printed results without failing on regressions. Authentication, ingestion and tenant isolation were missing. Resource initialization happened at import time and data loading depended on the current directory.

## Implemented changes
- Created a Python 3.12 virtual environment and installed/pinned dependencies.
- Added real asynchronous OpenAI Responses and embedding integrations, SDK retries, deadlines, bounded tool calls and strict tool allowlisting.
- Added a compiled LangGraph state workflow with input/output gates.
- Added pgvector SQL, tenant/model-filtered retrieval, overlapping chunks and atomic document replacement. Kept an explicitly labeled offline demo.
- Added React chat, evidence disclosure, token input and TXT/Markdown ingestion.
- Added RS256 JWT checks, tenant derivation, admin-only ingestion and fail-closed production settings.
- Added metadata logging, sanitized failures, health/readiness and non-root images, Compose, Nginx edge limits, CI and manual image publishing.
- Added regression evaluations that fail on missed expectations, plus tests for API validation, safety, tool protocol, JWT permissions and isolation.
- Rewrote documentation around actual behavior and provided an AWS deployment runbook.

## Verification on this machine
- Original suite: 2 passed.
- Upgraded suite: 17 passed; 1 PostgreSQL integration test skipped because TEST_DATABASE_URL is absent.
- Offline evaluation: 5/5 passed.
- Ruff lint/format checks and pip dependency consistency checks passed.
- React/Vite production build passed.
- Started FastAPI and React dev servers; HTTP health/chat smoke checks passed.
- Browser end-to-end check returned the 30-day refund answer and evidence disclosure through the React proxy.

## Remaining external verification
No OpenAI credential was supplied, so live generation/embedding requests were not made. API protocol tests use injected clients; these do not establish model/account availability. Docker is not installed here, so images and Compose were not executed locally. CI includes a real pgvector service test and image builds but has not run remotely. No cloud resources were provisioned and nothing was pushed to GitHub.

This is a production-oriented portfolio implementation, not a certified production deployment. Complete live staging evaluation, cloud identity-provider login/key rotation, least-privilege database setup, TLS, monitoring, load tests and restore tests before exposing it publicly. See ARCHITECTURE.md for detailed limits.
