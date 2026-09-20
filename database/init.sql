-- ══════════════════════════════════════════════════════════════════════════════
-- Agentic AI E-Discovery — Database Initialization
-- Runs automatically when the PostgreSQL Docker container starts for the first
-- time (mounted to /docker-entrypoint-initdb.d/).
-- ══════════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";          -- pgvector for embeddings

-- ── Cases ────────────────────────────────────────────────────────────────────

CREATE TYPE case_status AS ENUM (
    'created', 'in_progress', 'under_review', 'completed', 'archived'
);

CREATE TABLE IF NOT EXISTS cases (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(500)   NOT NULL,
    description TEXT,
    status      case_status    NOT NULL DEFAULT 'created',
    created_by  VARCHAR(255),
    metadata    TEXT,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cases_status     ON cases (status);
CREATE INDEX idx_cases_name       ON cases (name);
CREATE INDEX idx_cases_created_at ON cases (created_at DESC);

-- ── Documents ────────────────────────────────────────────────────────────────

CREATE TYPE document_status AS ENUM (
    'uploaded', 'validating', 'ocr_processing', 'chunking',
    'embedding', 'analyzing', 'reviewed', 'flagged', 'error'
);

CREATE TABLE IF NOT EXISTS documents (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id           UUID REFERENCES cases(id) ON DELETE SET NULL,
    filename          VARCHAR(1000)  NOT NULL,
    original_filename VARCHAR(1000)  NOT NULL,
    content_type      VARCHAR(255)   NOT NULL,
    file_size         BIGINT         NOT NULL,
    storage_path      VARCHAR(2000)  NOT NULL,
    checksum_sha256   VARCHAR(64),
    status            document_status NOT NULL DEFAULT 'uploaded',
    page_count        INTEGER,
    extracted_text    TEXT,
    doc_metadata      JSONB,
    created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_case_id    ON documents (case_id);
CREATE INDEX idx_documents_status     ON documents (status);
CREATE INDEX idx_documents_created_at ON documents (created_at DESC);
CREATE INDEX idx_documents_checksum   ON documents (checksum_sha256);

-- ── Document Chunks (for RAG / vector search) ───────────────────────────────

CREATE TABLE IF NOT EXISTS document_chunks (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INTEGER NOT NULL,
    content       TEXT NOT NULL,
    token_count   INTEGER,
    page_number   INTEGER,
    embedding     vector(1024),  -- BGE-M3 default; can be altered for other models
    chunk_metadata JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chunks_document_id ON document_chunks (document_id);
CREATE INDEX idx_chunks_embedding   ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ── Audit Log ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     VARCHAR(255),
    action      VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100),
    entity_id   UUID,
    details     JSONB,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user_id    ON audit_log (user_id);
CREATE INDEX idx_audit_action     ON audit_log (action);
CREATE INDEX idx_audit_created_at ON audit_log (created_at DESC);

-- ── Evaluation Metrics ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS evaluation_metrics (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id                  UUID REFERENCES cases(id) ON DELETE SET NULL,
    document_id              UUID REFERENCES documents(id) ON DELETE SET NULL,
    metric_type              VARCHAR(100) NOT NULL,
    ocr_accuracy             DOUBLE PRECISION,
    retrieval_precision      DOUBLE PRECISION,
    retrieval_recall         DOUBLE PRECISION,
    semantic_similarity      DOUBLE PRECISION,
    rouge_scores             JSONB,
    hallucination_rate       DOUBLE PRECISION,
    latency_ms               DOUBLE PRECISION,
    graph_generation_time_ms DOUBLE PRECISION,
    token_usage              JSONB,
    privilege_accuracy       DOUBLE PRECISION,
    user_feedback            JSONB,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evaluation_case_id    ON evaluation_metrics (case_id);
CREATE INDEX idx_evaluation_document_id ON evaluation_metrics (document_id);
CREATE INDEX idx_evaluation_metric_type ON evaluation_metrics (metric_type);
CREATE INDEX idx_evaluation_created_at  ON evaluation_metrics (created_at DESC);

-- ── Updated-at trigger ──────────────────────────────────────────────────────
-- Automatically updates `updated_at` on any row modification.

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cases_updated_at
    BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_evaluation_updated_at
    BEFORE UPDATE ON evaluation_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
