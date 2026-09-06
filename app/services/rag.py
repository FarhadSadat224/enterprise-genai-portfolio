import hashlib
import re
from pathlib import Path
from psycopg_pool import AsyncConnectionPool


def chunks(text, size=1200, overlap=150):
    return [
        text[i : i + size]
        for i in range(0, len(text), size - overlap)
        if text[i : i + size].strip()
    ]


class RAG:
    def __init__(self, settings, provider):
        self.settings, self.provider = settings, provider
        self.docs = {}
        self.pool = None

    async def open(self):
        if self.settings.vector_store == "pgvector":
            self.pool = AsyncConnectionPool(
                self.settings.database_url.get_secret_value(),
                open=False,
                min_size=1,
                max_size=5,
                timeout=10,
            )
            await self.pool.open()
            await self.pool.wait()
        else:
            path = Path(__file__).resolve().parents[2] / "data/company_policy.txt"
            await self.ingest("demo", path.name, path.read_text())

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def ready(self):
        if self.pool:
            async with self.pool.connection() as conn:
                await conn.execute("SELECT 1 FROM chunks LIMIT 1")
        return True

    async def ingest(self, tenant, source, text):
        parts = chunks(text)
        if not parts:
            raise ValueError("Document is empty")
        rows = [
            {
                "chunk_id": hashlib.sha256(f"{tenant}:{source}:{i}:{t}".encode()).hexdigest(),
                "source": source,
                "text": t,
            }
            for i, t in enumerate(parts)
        ]
        if self.pool:
            vectors = await self.provider.embed(parts)
            async with self.pool.connection() as conn:
                # Serialize replacements of the same document, including first writes.
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (tenant + ":" + source,),
                )
                await conn.execute(
                    "DELETE FROM chunks WHERE tenant=%s AND source=%s", (tenant, source)
                )
                for row, vector in zip(rows, vectors, strict=True):
                    await conn.execute(
                        "INSERT INTO chunks (id, tenant, source, content, embedding, model) VALUES (%s,%s,%s,%s,%s::vector,%s)",
                        (
                            row["chunk_id"],
                            tenant,
                            source,
                            row["text"],
                            str(vector),
                            self.settings.embedding_model,
                        ),
                    )
        else:
            self.docs[(tenant, source)] = rows
        return len(rows)

    async def retrieve(self, tenant, query, k=4):
        if self.pool:
            vector = (await self.provider.embed([query]))[0]
            async with self.pool.connection() as conn:
                cursor = await conn.execute(
                    "SELECT id,source,content,1-(embedding <=> %s::vector) AS score FROM chunks WHERE tenant=%s AND model=%s ORDER BY embedding <=> %s::vector LIMIT %s",
                    (str(vector), tenant, self.settings.embedding_model, str(vector), k),
                )
                return [
                    {"chunk_id": r[0], "source": r[1], "text": r[2]}
                    for r in await cursor.fetchall()
                    if r[3] >= self.settings.retrieval_threshold
                ]
        stop = {"what", "is", "the", "a", "our", "of", "me", "tell", "does"}
        tokens = set(re.findall(r"\w+", query.lower())) - stop
        rows = [r for (t, _), docs in self.docs.items() if t == tenant for r in docs]

        def score(r):
            return len(tokens & set(re.findall(r"\w+", r["text"].lower())))

        return sorted([r for r in rows if score(r)], key=score, reverse=True)[:k]
