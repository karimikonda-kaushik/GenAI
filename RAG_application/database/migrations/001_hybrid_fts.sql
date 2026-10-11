-- Hybrid search: add full-text search (keyword/BM25-style) columns
-- Safe to run on existing Supabase databases

DO $$ BEGIN
    ALTER TABLE document_chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE image_chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_document_chunks_fts
    ON document_chunks USING GIN (content_tsv);

CREATE INDEX IF NOT EXISTS idx_image_chunks_fts
    ON image_chunks USING GIN (content_tsv);
