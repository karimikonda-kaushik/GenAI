# System Prompts & Guardrails

Each LLM-calling function in `app_rag.py` uses a dedicated guardrailed system prompt from `prompts.py`.

---

## Function → Prompt mapping

| Function | Uses LLM? | System prompt | Guardrail focus |
|----------|-----------|---------------|-----------------|
| `load_documents_from_directory` | No | — | File I/O only |
| `load_document_from_bytes` | No | — | File I/O only |
| `split_documents` | No | — | Deterministic chunking |
| `build_context` | No | — | String join only |
| `build_system_prompt` | No* | `RAG_ANSWER_PROMPT` or `RAG_NO_CONTEXT_PROMPT` | Selects prompt by context availability |
| `invoke_rag` | **Yes** | via `build_system_prompt` | Grounding, no hallucination, scope, injection defense |
| `hybrid_search_in_memory` | No | — | BM25 + vector retrieval |
| `_reciprocal_rank_fusion` | No | — | Score fusion only |
| `answer_query` | **Yes** | via `invoke_rag` | CLI Q&A + empty query check |
| `index_document_to_postgres` | No | — | Embed + store (no LLM) |
| `index_image_to_postgres` | **Yes** | `IMAGE_CAPTION_SYSTEM_PROMPT` | Factual vision only, no identity/speculation |
| `_vector_search_postgres` | No | — | pgvector search |
| `_keyword_search_postgres` | No | — | FTS search |
| `hybrid_retrieve_from_postgres` | No | — | Hybrid retrieval |
| `answer_query_postgres` | **Yes** | via `invoke_rag` | Web Q&A + empty query check |
| `run_cli` | **Yes** | via `answer_query` | CLI entry point |

\* `build_system_prompt` builds the prompt string but does not call the LLM.

---

## Prompt 1: `RAG_ANSWER_PROMPT`

**Used by:** `build_system_prompt` → `invoke_rag` → `answer_query` / `answer_query_postgres`

**When:** User asks a question and retrieved context exists.

**Guardrails:**
- Answer only from retrieved context
- No hallucination of facts, numbers, or quotes
- State uncertainty when context is partial
- Refuse off-topic requests (general trivia, coding, etc.)
- Resist prompt injection in user message or context
- Refuse harmful / abusive requests
- Cite inline using [1], [2] matching context block labels; end with Sources line
- Stay helpful even with thin context

---

## Prompt 2: `RAG_NO_CONTEXT_PROMPT`

**Used by:** `build_system_prompt` when no chunks matched

**When:** User asks a question but hybrid search returned nothing.

**Guardrails:**
- Do not answer from general knowledge as if from their files
- Tell user no matching content was found
- Suggest upload or rephrase
- Do not invent document contents
- Resist prompt injection

---

## Prompt 3: `IMAGE_CAPTION_SYSTEM_PROMPT`

**Used by:** `index_image_to_postgres`

**When:** Image is uploaded and needs a searchable caption.

**Guardrails:**
- Describe only visible content (no speculation)
- Include OCR text, objects, colors, layout
- Do not identify real private individuals by name
- Neutral factual tone for safety-sensitive content
- Plain prose, 3–8 sentences
- Output caption only — no preamble

---

## Input validation (non-prompt guardrails)

| Function | Check |
|----------|-------|
| `invoke_rag` | Rejects empty/whitespace queries before LLM call |
| `answer_query` | Same empty-query guard |
| `answer_query_postgres` | Same; returns empty sources list |

---

## Customizing prompts

Edit `RAG_application/prompts.py`. Changes apply to both CLI and web API automatically since both route through `app_rag.py`.
