# Enterprise GenAI Workspace

FastAPI + React portfolio with OpenAI Responses API, LangGraph orchestration, PostgreSQL/pgvector RAG, text ingestion, bounded tool calling, JWT authentication, safety checks and container delivery.

## Run locally (no credentials or database)
Requires Python 3.12 and Node 22 with pnpm 11.19.0.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:
```sh
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```
Open http://127.0.0.1:5173 and API docs at http://127.0.0.1:8000/docs. Demo mode uses in-memory keyword retrieval and deterministic responses; it never silently substitutes for OpenAI. Demo documents reset on restart. Chat requests are independent; no conversation history is retained.

## Real OpenAI + pgvector
Copy `.env.example` to `.env`, set `OPENAI_API_KEY`, and add `POSTGRES_PASSWORD` (use a long alphanumeric value for the Compose connection URL). Run:
```sh
docker compose up --build
```
Open http://localhost:8080. Compose forces OpenAI and pgvector and initializes SQL on the first database volume creation. Upload `data/company_policy.txt` through the interface before asking policy questions. Only UTF-8 TXT/Markdown text is supported. A same-tenant, same-source upload atomically replaces that document. Embeddings use 1536 dimensions and the configured model; reingest all documents when changing models. No sample documents are automatically loaded into production tenants.

For OpenAI without Docker, set `LLM_PROVIDER=openai`; memory retrieval remains a demo facility. For an external database also set `VECTOR_STORE=pgvector` and `DATABASE_URL`, and apply `sql/001_init.sql` with a migration administrator first. Do not use the Compose database owner as the production runtime role.

## Authentication
Local `AUTH_MODE=none` grants a demo admin identity. Production requires `APP_ENV=production`, `AUTH_MODE=jwt`, OpenAI and pgvector. Supply an RS256 public PEM key, issuer and audience. JWTs require `sub`, `tenant`, `iat`, and `exp`; `role=admin` may ingest, while the default reader may chat. The server derives the tenant from the signed token. The frontend keeps pasted tokens only in memory. Integrate your identity provider's login and key rotation before public deployment; this is an authentication-ready structure, not a complete SSO UI.

## Verification
```sh
ruff check app tests evals
ruff format --check app tests evals
python -m pytest -q
python -m evals.run_evals
pnpm --dir frontend build
```
`TEST_DATABASE_URL` enables real pgvector integration tests against a disposable database. CI runs these with a pgvector service. Offline evaluations enforce routes, expected facts, citation source presence, abstention and safety. They do not measure live model groundedness; use a representative labeled dataset and a live staging run before release.

See [architecture](ARCHITECTURE.md), [review and verification](REVIEW.md), and [AWS deployment](docs/DEPLOYMENT.md). Dependencies are fully pinned in `requirements.lock` and `frontend/pnpm-lock.yaml`; update intentionally and rerun checks.
