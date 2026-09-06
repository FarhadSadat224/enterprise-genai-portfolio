# Architecture

React → Nginx (body/rate limits) → FastAPI (JWT, validation, deadline) → LangGraph → input gate → tenant-filtered retrieval → OpenAI + allowlisted health tool → output gate → answer and retrieved evidence.

- `app/main.py`: dependency lifespan, HTTP routes, health/readiness, request metadata logs and sanitized failures.
- `app/auth.py`: RS256 verification with fixed algorithm, issuer, audience and required expiry. Admin ingestion; tenant comes from signed claims.
- `app/services/orchestrator.py`: compiled state graph. No persistent checkpoints or cross-user conversation state.
- `app/services/llm.py`: asynchronous Responses API, `store=False`, finite retries, output and tool budgets. Health tool is read-only and accepts no arguments.
- `app/services/rag.py`: overlapping character chunks, batched OpenAI embeddings, atomic source replacement and cosine search constrained by tenant and embedding model. Exact search favors correctness at portfolio scale; benchmark indexing before scaling.
- `sql/001_init.sql`: initial schema, run separately from API startup. Later migrations must be additive and reviewed; Compose initialization only runs on a fresh volume.

## Security and operational limits

Pattern-based guardrails are defense in depth, not a complete prompt-injection or PII detector. Documents remain untrusted. Retrieved citations identify evidence supplied to the model, not proof that every generated claim is grounded. No arbitrary outbound tool URLs or write tools exist.

Tenant filters are enforced in application SQL; add RLS or database-per-tenant isolation for higher assurance. Production requires edge TLS and rate limiting; do not expose the API directly. Nginx limits are per IP and instance, not distributed per-user quotas. Ingestion is synchronous, bounded at 100,000 characters; large files require an authenticated queue/worker design. Runtime logs omit content and credentials; configure centralized retention and alerts in your cloud.

No streaming, PDF parsing, reranking, persistent chat, login UI, managed key rotation, infrastructure-as-code or automatic cloud deployment is claimed. These are deliberate future extensions.

## References

- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [pgvector](https://github.com/pgvector/pgvector)
