# Hybrid RAG — How It Works

This document explains each step of the improved RAG pipeline: **chunking**, **hybrid retrieval**, and **answer generation**.

---

## Overview

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Upload    │ →  │   Chunking   │ →  │  Dual indexing  │ →  │   Postgres   │
│  doc/image  │    │ 1000/200 ovlp│    │ vector + FTS    │    │   Supabase   │
└─────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘

┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│ User query  │ →  │ Hybrid search│ →  │  RRF fusion     │ →  │ Gemini answer│
│  in chat    │    │ vector+keyword│   │  top-k chunks   │    │  with context│
└─────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
```

---

## Phase 1 — Upload & Indexing

### Step 1: File upload (React → API)

- User drops a file in the sidebar (`FileUploadZone.jsx`)
- Sent as `multipart/form-data` to `/api/upload/document` or `/api/upload/image`
- Raw bytes stored in `documents.file_data` or `images.file_data`

### Step 2: Text extraction (LangChain loaders)

| File type | Loader | Output |
|-----------|--------|--------|
| PDF | `PyPDFLoader` | One LangChain Document per page |
| TXT / MD | `TextLoader` | One Document for the file |
| Image | Gemini 2.5 Flash vision | One text caption |

**Code:** `load_document_from_bytes()` in `app_rag.py`

### Step 3: Chunking (RecursiveCharacterTextSplitter)

**Strategy:** Fixed-size overlapping chunks (not whole-page or whole-file anymore).

| Setting | Value | Why |
|---------|-------|-----|
| `CHUNK_SIZE` | 1000 characters | Fits embedding model context |
| `CHUNK_OVERLAP` | 200 characters | Preserves context across chunk boundaries |
| Separators | `\n\n`, `\n`, `. `, ` ` | Splits on paragraphs → sentences → words |

**Example:**

```
Long 5000-char document
  → [chunk 0: chars 0–1000]
  → [chunk 1: chars 800–1800]   ← 200-char overlap with chunk 0
  → [chunk 2: chars 1600–2600]
  → ...
```

**Code:** `split_documents()` → `get_text_splitter()` in `app_rag.py`

### Step 4: Dual indexing (two search indexes per chunk)

Each chunk gets **two** indexes stored in PostgreSQL:

| Index type | Technology | Good for |
|------------|------------|----------|
| **Dense (vector)** | `embedding vector(384)` via MiniLM-L6-v2 | Meaning, paraphrases, concepts |
| **Sparse (keyword)** | `content_tsv` via PostgreSQL FTS | Exact terms, IDs, names, codes |

```sql
-- Auto-generated on insert:
content_tsv = to_tsvector('english', content)
```

**Code:** `index_document_to_postgres()` embeds chunks; FTS column is automatic.

---

## Phase 2 — Hybrid Retrieval (at query time)

When the user asks a question in chat, **two searches run in parallel**:

### Step 5a: Vector search (semantic)

1. Embed the user query with `all-MiniLM-L6-v2`
2. Cosine similarity against all chunk embeddings
3. Return top 8 candidates (`RETRIEVAL_CANDIDATES`)

```sql
ORDER BY embedding <=> query_vector
LIMIT 8
```

**Finds:** "What is the revenue?" matches "total income was $45,000"

### Step 5b: Keyword search (BM25-style)

1. Convert query to `plainto_tsquery('english', query)`
2. Match against `content_tsv` (inverted index)
3. Rank with `ts_rank_cd` (BM25-like scoring)
4. Return top 8 candidates

```sql
WHERE content_tsv @@ plainto_tsquery('english', query)
ORDER BY ts_rank_cd(...) DESC
```

**Finds:** "SKU-12345" or exact product codes that vector search might miss

### Step 6: RRF fusion (Reciprocal Rank Fusion)

Merge both ranked lists. Chunks that appear in **both** lists get a higher combined score.

```
RRF score = Σ  1 / (rank + 60)
            for each list the chunk appears in
```

| Chunk | Vector rank | Keyword rank | RRF score | Selected? |
|-------|-------------|--------------|-----------|-----------|
| A | 1 | 2 | 1/61 + 1/63 = 0.032 | Yes (hybrid) |
| B | 3 | — | 1/64 = 0.016 | Maybe |
| C | — | 1 | 1/61 = 0.016 | Maybe |

Top `TOP_K = 4` chunks after fusion are sent to the LLM.

**Code:** `hybrid_retrieve_from_postgres()` → `_reciprocal_rank_fusion()`

---

## Phase 3 — Answer Generation

### Step 7: Context injection

Retrieved chunks are joined into one context string:

```python
context = "\n\n".join(chunk.page_content for chunk in retrieved)
```

### Step 8: LLM call (Gemini 2.5 Flash)

```python
SystemMessage: "you are a helpful assistant... {context}"
HumanMessage:   user question
→ Gemini generates answer grounded in retrieved chunks
```

**Code:** `invoke_rag()` in `app_rag.py`

### Step 9: Response to frontend

API returns answer + sources with match type:

```json
{
  "content": "The revenue in 2025 was...",
  "sources": [
    { "filename": "report.pdf", "score": 0.032, "match": "hybrid" }
  ]
}
```

---

## Models used

| Role | Model | Type |
|------|-------|------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Dense vectors (384-dim) |
| Keyword search | PostgreSQL FTS (`ts_rank_cd`) | Sparse / BM25-style |
| Answer generation | `gemini-2.5-flash` | LLM |
| Image captioning | `gemini-2.5-flash` (vision) | Multimodal LLM |

---

## CLI vs Web app

| | CLI (`python app_rag.py`) | Web app (React + API) |
|--|---------------------------|------------------------|
| Storage | In-memory | PostgreSQL (Supabase) |
| Keyword search | `BM25Retriever` (rank-bm25) | PostgreSQL FTS |
| Vector search | `InMemoryVectorStore` | pgvector |
| Fusion | `EnsembleRetriever` (weighted) | RRF (Reciprocal Rank Fusion) |
| Chunking | Same splitter | Same splitter |

---

## Configuration (`backend/config.py`)

```python
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4                  # chunks sent to LLM
RETRIEVAL_CANDIDATES = 8   # candidates per search leg before fusion
RRF_K = 60                 # RRF constant (standard default)
HYBRID_VECTOR_WEIGHT = 0.5 # CLI ensemble only
HYBRID_KEYWORD_WEIGHT = 0.5
```

---

## Database migration

If your Supabase DB was created before hybrid search, run:

```bash
psql $DATABASE_URL -f database/migrations/001_hybrid_fts.sql
```

This adds `content_tsv` generated columns and GIN indexes for keyword search.

---

## Why hybrid is better

| Query type | Vector only | Keyword only | Hybrid |
|------------|-------------|--------------|--------|
| "What did the company earn?" | Good | Weak | Good |
| "Find invoice INV-2024-001" | Weak | Good | Good |
| "Explain the refund policy" | Good | OK | Good |
| "SKU-99887 specifications" | Weak | Good | Good |

Hybrid gives you the best of both: **semantic understanding** + **exact keyword matching**.
