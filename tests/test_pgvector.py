"""Run against an isolated test database with TEST_DATABASE_URL."""

import os
from pathlib import Path
from uuid import uuid4
import psycopg
import pytest
from app.config import Settings
from app.services.rag import RAG


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Postgres integration database not configured"
)
async def test_pgvector_roundtrip():
    url = os.environ["TEST_DATABASE_URL"]

    class Embeddings:
        async def embed(self, texts):
            return [[1.0] + [0.0] * 1535 for _ in texts]

    async with await psycopg.AsyncConnection.connect(url) as conn:
        await conn.execute(Path("sql/001_init.sql").read_text())
    settings = Settings(
        _env_file=None,
        llm_provider="openai",
        openai_api_key="test",
        vector_store="pgvector",
        database_url=url,
    )
    rag = RAG(settings, Embeddings())
    tenant = str(uuid4())
    await rag.open()
    try:
        await rag.ingest(tenant, "test.txt", "old evidence")
        await rag.ingest(tenant, "test.txt", "new evidence")
        rows = await rag.retrieve(tenant, "evidence")
        assert len(rows) == 1 and rows[0]["text"] == "new evidence"
        assert not await rag.retrieve(str(uuid4()), "evidence")
    finally:
        async with rag.pool.connection() as conn:
            await conn.execute("DELETE FROM chunks WHERE tenant=%s", (tenant,))
        await rag.close()
