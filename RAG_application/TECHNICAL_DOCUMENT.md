# RAG Application — Technical Design Document

## 1. Overview

A full-stack Retrieval-Augmented Generation (RAG) application that lets users upload documents and images, then chat with an AI assistant that answers questions grounded in those uploads.

| Layer | Technology |
|-------|------------|
| Frontend | React (Vite) — modern chat UI |
| Backend | FastAPI (Python) |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (384-dim) |
| Database | PostgreSQL + **pgvector** (Supabase-compatible) |
| RAG framework | LangChain |

---

## 2. Goals

1. **Chat interface** — polished, conversational UI between user and AI.
2. **Document Q&A** — upload PDF, TXT, MD, DOCX; ask questions; get answers from retrieved context.
3. **Image Q&A** — upload images; ask questions; AI uses vision + any indexed metadata/embeddings.
4. **PostgreSQL as single store** — file metadata, binary content, text chunks, vector embeddings, and chat history all live in Postgres.
5. **Optimistic answers** — AI responds helpfully from available context; clearly states limits when context is insufficient.

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Chat Panel   │  │ File Upload  │  │ Conversation History  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘  │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │ REST / SSE      │ multipart            │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌────────────┐  ┌─────────────┐  ┌──────────┐  ┌────────────┐  │
│  │ /chat      │  │ /upload/doc │  │ /upload/ │  │ /sessions  │  │
│  │            │  │             │  │ image    │  │            │  │
│  └─────┬──────┘  └──────┬──────┘  └────┬─────┘  └─────┬──────┘  │
│        │                │              │              │         │
│        ▼                ▼              ▼              ▼         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              RAG Pipeline (LangChain)                    │   │
│  │  Ingest → Chunk → Embed → Store → Retrieve → Generate    │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              PostgreSQL (+ pgvector extension)                  │
│  documents │ images │ document_chunks │ image_chunks │ messages │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    Google Gemini 2.5 Flash (LLM + Vision)
```

---

## 4. Data Flow

### 4.1 Document Upload & Indexing

```
User selects file(s)
    → POST /api/upload/document (multipart)
    → Backend validates type & size
    → Store raw bytes + metadata in `documents` table
    → Extract text (PyPDF, TextLoader, etc.)
    → Split into chunks (~500 tokens, overlap 50)
    → Embed each chunk (MiniLM-L6-v2)
    → Insert into `document_chunks` with vector(384)
    → Return document ID + chunk count to frontend
```

### 4.2 Image Upload & Indexing

```
User selects image(s)
    → POST /api/upload/image (multipart)
    → Store raw bytes + metadata in `images` table
    → (Phase 1) Store description/caption via Gemini vision for text retrieval
    → Embed caption text → `image_chunks` with vector(384)
    → (Phase 2) Optional CLIP / multimodal embeddings for direct image similarity
```

### 4.3 Chat / Question Answering

```
User sends message in chat
    → POST /api/chat { session_id, message }
    → Embed user query
    → similarity_search on document_chunks + image_chunks (top-k=4)
    → Build system prompt with retrieved context + source citations
    → If query references images: attach relevant image bytes to Gemini multimodal request
    → Stream or return Gemini response
    → Persist user + assistant messages in `messages` table
    → Frontend renders response in chat thread
```

---

## 5. Database Schema

### Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Tables

| Table | Purpose |
|-------|---------|
| `sessions` | Chat sessions (id, title, created_at) |
| `messages` | Chat history (session_id, role, content, created_at) |
| `documents` | Uploaded files (filename, mime_type, file_data BYTEA, extracted_text) |
| `images` | Uploaded images (filename, mime_type, file_data BYTEA) |
| `document_chunks` | Text chunks + `embedding vector(384)` + FK to documents |
| `image_chunks` | Caption/description chunks + `embedding vector(384)` + FK to images |

Vector indexes use **HNSW** or **IVFFlat** for fast cosine similarity search.

---

## 6. API Endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check + DB connectivity |
| `POST` | `/api/sessions` | Create new chat session |
| `GET` | `/api/sessions/{id}/messages` | Load conversation history |
| `POST` | `/api/upload/document` | Upload & index document(s) |
| `POST` | `/api/upload/image` | Upload & index image(s) |
| `POST` | `/api/chat` | Send message, run RAG, return AI reply |
| `GET` | `/api/documents` | List uploaded documents |
| `GET` | `/api/images` | List uploaded images |

---

## 7. Frontend Components

| Component | Responsibility |
|-----------|----------------|
| `ChatLayout` | Shell: sidebar + main chat area |
| `MessageList` | Scrollable thread of user/assistant bubbles |
| `ChatInput` | Text input + send button + file attach |
| `FileUploadZone` | Drag-and-drop for docs & images |
| `UploadProgress` | Per-file upload/indexing status |
| `SourceCitations` | Show which docs/chunks grounded the answer |

**UX principles:** dark/light theme, smooth scroll, streaming tokens, optimistic UI for sends, clear upload feedback.

---

## 8. RAG Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| Embedding model | `all-MiniLM-L6-v2` | 384 dimensions, local via HuggingFace |
| Chunk size | 1000 chars | Tunable |
| Chunk overlap | 200 chars | Preserves context across splits |
| Top-k retrieval | 4 | Balance recall vs. prompt size |
| LLM | `gemini-2.5-flash` | Fast, supports multimodal |
| Similarity metric | Cosine | Via pgvector `<=>` operator |

---

## 9. Security & Configuration

Environment variables (`RAG_application/.env`):

```
GOOGLE_API_KEY=...
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

- CORS restricted to frontend origin in development.
- Max upload size enforced (e.g. 25 MB per file).
- Allowed MIME types whitelist for documents and images.
- `.env` gitignored; `.env.example` committed.

---

## 10. Development Phases

### Phase 1 — Foundation (current)
- [x] Technical design document
- [ ] PostgreSQL schema + pgvector setup
- [ ] FastAPI backend skeleton (health, upload, chat stubs)
- [ ] React chat UI scaffold
- [ ] Local dev README

### Phase 2 — Core RAG
- [ ] Document ingestion pipeline (chunk + embed + store)
- [ ] Vector similarity search via pgvector
- [ ] Chat endpoint with context injection
- [ ] End-to-end document Q&A test

### Phase 3 — Images & Polish
- [ ] Image upload + Gemini vision captions
- [ ] Multimodal chat (image + text in same session)
- [ ] Source citations in UI
- [ ] Streaming responses

### Phase 4 — Production Readiness
- [ ] Session management & persistence
- [ ] Error handling, rate limits
- [ ] Docker compose (Postgres + API + frontend)
- [ ] Deployment guide (Supabase + cloud)

---

## 11. Project Structure

```
RAG_application/
├── TECHNICAL_DOCUMENT.md      # This file
├── README.md
├── .env                       # Secrets (gitignored)
├── .env.example
├── app_rag.py                 # Original CLI prototype (reference)
├── database/
│   └── schema.sql             # Postgres + pgvector DDL
├── backend/
│   ├── main.py                # FastAPI entry point
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   │   ├── chat.py
│   │   ├── upload.py
│   │   └── sessions.py
│   └── requirements.txt
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        └── components/
            ├── ChatLayout.jsx
            ├── MessageList.jsx
            ├── ChatInput.jsx
            └── FileUploadZone.jsx
```

---

## 12. Testing Plan

| Test | Type | Validates |
|------|------|-----------|
| Schema apply | Manual / script | pgvector extension, tables created |
| Upload PDF | Integration | File stored, chunks embedded |
| Ask doc question | E2E | Retrieval returns relevant chunk, LLM answers |
| Upload image | Integration | Image stored, caption indexed |
| Ask image question | E2E | Vision + retrieval produces grounded answer |
| Multi-turn chat | E2E | History persisted, context maintained |
| RAGAS eval | Offline (`eval/`) | Faithfulness, answer relevancy, context precision/recall |

See [eval/README.md](./eval/README.md) for the RAGAS runner.
---

*Document version: 1.0 — Phase 1 foundation*
