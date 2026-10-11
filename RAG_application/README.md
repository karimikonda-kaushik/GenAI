# RAG Application

Full-stack document & image Q&A with a React chat UI, FastAPI backend, and PostgreSQL + pgvector.

See [TECHNICAL_DOCUMENT.md](./TECHNICAL_DOCUMENT.md) for architecture and phased plan.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with [pgvector](https://github.com/pgvector/pgvector) extension

## Quick Start

### 1. Database

```bash
# Create database and enable pgvector
createdb rag_app
psql rag_app -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql rag_app -f database/schema.sql
```

For Supabase, enable the **vector** extension in the SQL editor, then run `database/schema.sql`.

### 2. Environment

```bash
cp .env.example .env
# Edit .env with GOOGLE_API_KEY and DATABASE_URL
```

### 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Project Structure

```
RAG_application/
├── app_rag.py                # Core RAG logic (CLI + imported by backend)
├── TECHNICAL_DOCUMENT.md     # Architecture & phases
├── database/schema.sql       # Postgres + pgvector DDL
├── backend/                  # FastAPI API (thin layer over app_rag.py)
├── frontend/                 # React chat UI
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/sessions` | Create chat session |
| GET | `/api/sessions/{id}/messages` | Get history |
| POST | `/api/upload/document` | Upload & index document |
| POST | `/api/upload/image` | Upload & index image |
| POST | `/api/chat` | Ask a question |
| GET | `/api/documents` | List documents |
| GET | `/api/images` | List images |
