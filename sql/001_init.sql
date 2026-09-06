CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS chunks (
 id text PRIMARY KEY,
 tenant text NOT NULL,
 source text NOT NULL,
 content text NOT NULL,
 embedding vector(1536) NOT NULL,
 model text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chunks_tenant_model ON chunks(tenant, model);
-- Exact cosine search preserves tenant-filtered recall for this portfolio scale.
-- Benchmark before adding HNSW and tune iterative scans for filtered retrieval.
