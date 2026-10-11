"""
Core RAG logic for the RAG application.

Used by:
  - CLI:  python app_rag.py
  - API:  backend imports this module (FastAPI → React frontend)

Pipeline:
  Upload → chunk (RecursiveCharacterTextSplitter) → embed + FTS index → hybrid retrieve → LLM
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFDirectoryLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_community.retrievers import BM25Retriever
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from prompts import (
    IMAGE_CAPTION_SYSTEM_PROMPT,
    IMAGE_CAPTION_USER_PROMPT,
    build_rag_answer_prompt,
)

BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "My Documents"

load_dotenv(BASE_DIR / ".env")

LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Retrieval
TOP_K = 4
RETRIEVAL_CANDIDATES = 8
RRF_K = 60
HYBRID_VECTOR_WEIGHT = 0.5
HYBRID_KEYWORD_WEIGHT = 0.5


@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=LLM_MODEL)


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_documents(langchain_docs: list) -> list:
    """Step 2 of indexing: split loaded docs into overlapping chunks."""
    if not langchain_docs:
        return []
    return get_text_splitter().split_documents(langchain_docs)


def load_documents_from_directory(documents_dir: str | Path = DOCUMENTS_DIR) -> list:
    documents_dir = Path(documents_dir)
    documents_dir.mkdir(parents=True, exist_ok=True)

    pdf_loader = PyPDFDirectoryLoader(str(documents_dir))
    pdf_docs = pdf_loader.load()

    text_loader = DirectoryLoader(
        str(documents_dir),
        glob="**/*.txt",
        loader_cls=TextLoader,
    )
    text_docs = text_loader.load()

    return pdf_docs + text_docs


def load_document_from_bytes(data: bytes, filename: str, mime_type: str) -> list:
    suffix = Path(filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        if mime_type == "application/pdf" or suffix.lower() == ".pdf":
            return PyPDFLoader(tmp_path).load()
        if mime_type in ("text/plain", "text/markdown") or suffix.lower() in (".txt", ".md"):
            return TextLoader(tmp_path).load()
        raise ValueError(f"Unsupported document type: {mime_type}")
    finally:
        os.unlink(tmp_path)


@dataclass
class RetrievedChunk:
    chunk_id: str
    page_content: str
    filename: str
    source_type: str = "document"
    source_id: str = ""
    score: float = 0.0
    match_types: list[str] = field(default_factory=list)
    citation_label: str = ""
    chunk_index: int | None = None


def _assign_citation_labels(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    for i, chunk in enumerate(chunks, start=1):
        chunk.citation_label = str(i)
    return chunks


def _langchain_docs_to_chunks(docs: list) -> list[RetrievedChunk]:
    """Convert in-memory LangChain docs to RetrievedChunk for cited context."""
    chunks: list[RetrievedChunk] = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "document")
        filename = Path(str(source)).name if source else "document"
        page = doc.metadata.get("page")
        chunks.append(
            RetrievedChunk(
                chunk_id=str(i),
                page_content=doc.page_content,
                filename=filename,
                source_type="document",
                chunk_index=int(page) + 1 if page is not None else None,
            )
        )
    return chunks


def build_context(retrieved_docs: list) -> str:
    """Build labeled context blocks so the LLM can cite [1], [2], etc."""
    if not retrieved_docs:
        return ""

    blocks: list[str] = []
    for i, doc in enumerate(retrieved_docs, start=1):
        if isinstance(doc, RetrievedChunk):
            cite = doc.citation_label or str(i)
            filename = doc.filename
            source_type = doc.source_type
            content = doc.page_content
            chunk_ref = f", chunk {doc.chunk_index + 1}" if doc.chunk_index is not None else ""
        else:
            cite = str(i)
            source = getattr(doc, "metadata", {}).get("source", "document")
            filename = Path(str(source)).name
            source_type = "document"
            content = doc.page_content
            page = getattr(doc, "metadata", {}).get("page")
            chunk_ref = f", page {int(page) + 1}" if page is not None else ""

        blocks.append(
            f"[{cite}] Source: {filename} ({source_type}{chunk_ref})\n{content}"
        )

    return "\n\n---\n\n".join(blocks)


def _has_meaningful_context(context: str) -> bool:
    empty_markers = {
        "",
        "No documents found.",
        "No documents or images uploaded yet.",
    }
    return context.strip() not in empty_markers


def build_system_prompt(context: str) -> str:
    """Guardrailed system prompt for RAG answer generation."""
    return build_rag_answer_prompt(context, has_context=_has_meaningful_context(context))


def invoke_rag(user_query: str, context: str) -> str:
    """
    Generate an answer with guardrails:
    - Grounded in retrieved context only
    - Refuses off-topic and injection attempts
    - Handles empty context via RAG_NO_CONTEXT_PROMPT
    """
    if not user_query or not user_query.strip():
        return "Please enter a question about your uploaded documents or images."

    messages = [
        SystemMessage(content=build_system_prompt(context)),
        HumanMessage(content=user_query.strip()),
    ]
    response = get_llm().invoke(messages)
    return response.content

# Hybrid retrieval helpers
def _reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]],
    k: int = TOP_K,
) -> list[RetrievedChunk]:
    """
    Merge multiple ranked result lists using Reciprocal Rank Fusion (RRF).
    Chunks appearing in both vector AND keyword lists get boosted.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, RetrievedChunk] = {}

    for results in ranked_lists:
        for rank, chunk in enumerate(results):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (rank + 1 + RRF_K)
            if chunk.chunk_id in chunk_map:
                existing = chunk_map[chunk.chunk_id]
                existing.match_types = list(set(existing.match_types + chunk.match_types))
            else:
                chunk_map[chunk.chunk_id] = RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    page_content=chunk.page_content,
                    filename=chunk.filename,
                    source_type=chunk.source_type,
                    source_id=chunk.source_id,
                    match_types=list(chunk.match_types),
                    chunk_index=chunk.chunk_index,
                )

    fused_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)[:k]
    fused = []
    for cid in fused_ids:
        chunk = chunk_map[cid]
        chunk.score = round(scores[cid], 4)
        if len(chunk.match_types) > 1:
            chunk.match_types = ["hybrid"]
        fused.append(chunk)
    return fused


def hybrid_search_in_memory(user_query: str, docs: list, k: int = TOP_K) -> list:
    """CLI hybrid: BM25 (keyword) + dense vectors, merged with weighted ensemble."""
    from langchain.retrievers import EnsembleRetriever

    chunks = split_documents(docs)
    if not chunks:
        return []

    bm25 = BM25Retriever.from_documents(chunks)
    bm25.k = RETRIEVAL_CANDIDATES

    vector_store = InMemoryVectorStore(get_embeddings())
    vector_store.add_documents(chunks)
    vector_retriever = vector_store.as_retriever(search_kwargs={"k": RETRIEVAL_CANDIDATES})

    ensemble = EnsembleRetriever(
        retrievers=[bm25, vector_retriever],
        weights=[HYBRID_KEYWORD_WEIGHT, HYBRID_VECTOR_WEIGHT],
    )
    return ensemble.invoke(user_query)[:k]


def answer_query(user_query: str, docs: list | None = None, k: int = TOP_K) -> str:
    """CLI: load → chunk → hybrid retrieve → guardrailed generate."""
    if not user_query or not user_query.strip():
        return "Please enter a question about your uploaded documents or images."

    if docs is None:
        docs = load_documents_from_directory()
    retrieved_docs = hybrid_search_in_memory(user_query.strip(), docs, k=k)
    if not retrieved_docs:
        context = "No documents found."
    else:
        chunks = _assign_citation_labels(_langchain_docs_to_chunks(retrieved_docs))
        context = build_context(chunks)
    return invoke_rag(user_query.strip(), context)


# PostgreSQL integration
def _db_cursor():
    import sys

    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from backend.database import db_cursor

    return db_cursor


def index_document_to_postgres(
    doc_id: str, data: bytes, mime_type: str, filename: str, user_id: str
) -> int:
    """
    Index pipeline:
      1. Load file (PyPDFLoader / TextLoader)
      2. Split into 1000-char chunks with 200-char overlap
      3. Embed each chunk (MiniLM-L6-v2)
      4. Store in Postgres (FTS column auto-generated for keyword search)
    """
    db_cursor = _db_cursor()

    raw_docs = load_document_from_bytes(data, filename, mime_type)
    chunks = split_documents(raw_docs)
    if not chunks:
        raise ValueError("No content could be loaded from document")

    texts = [c.page_content for c in chunks]
    full_text = "\n".join(texts)
    embeddings = get_embeddings().embed_documents(texts)

    with db_cursor() as cur:
        cur.execute(
            "SELECT id FROM documents WHERE id = %s AND user_id = %s",
            (doc_id, user_id),
        )
        if not cur.fetchone():
            raise ValueError("Document not found for this user")

        cur.execute(
            "UPDATE documents SET extracted_text = %s, status = 'indexed' WHERE id = %s AND user_id = %s",
            (full_text, doc_id, user_id),
        )
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            cur.execute(
                """
                INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (doc_id, i, text, embedding),
            )

    return len(chunks)


def index_image_to_postgres(
    image_id: str, data: bytes, mime_type: str, filename: str, user_id: str
) -> str:
    """
    Index image with guardrailed vision captioning:
    - Factual, search-oriented description only
    - No identity claims or speculation
    """
    import base64

    db_cursor = _db_cursor()

    b64 = base64.b64encode(data).decode("utf-8")
    messages = [
        SystemMessage(content=IMAGE_CAPTION_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {"type": "text", "text": IMAGE_CAPTION_USER_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ]
        ),
    ]
    caption = get_llm().invoke(messages).content
    embedding = get_embeddings().embed_query(caption)

    with db_cursor() as cur:
        cur.execute(
            "SELECT id FROM images WHERE id = %s AND user_id = %s",
            (image_id, user_id),
        )
        if not cur.fetchone():
            raise ValueError("Image not found for this user")

        cur.execute(
            "UPDATE images SET caption = %s, status = 'indexed' WHERE id = %s AND user_id = %s",
            (caption, image_id, user_id),
        )
        cur.execute(
            "INSERT INTO image_chunks (image_id, content, embedding) VALUES (%s, %s, %s)",
            (image_id, caption, embedding),
        )

    return caption


def _vector_search_postgres(
    cur, query_embedding: list[float], limit: int, user_id: str
) -> list[RetrievedChunk]:
    results: list[RetrievedChunk] = []

    cur.execute(
        """
        SELECT dc.id, dc.content, d.filename, dc.document_id, dc.chunk_index,
               1 - (dc.embedding <=> %s::vector) AS score
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.embedding IS NOT NULL AND d.user_id = %s
        ORDER BY dc.embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, user_id, query_embedding, limit),
    )
    for row in cur.fetchall():
        results.append(
            RetrievedChunk(
                chunk_id=str(row["id"]),
                page_content=row["content"],
                filename=row["filename"],
                source_type="document",
                source_id=str(row["document_id"]),
                score=float(row["score"]),
                match_types=["vector"],
                chunk_index=row.get("chunk_index"),
            )
        )

    cur.execute(
        """
        SELECT ic.id, ic.content, i.filename, i.id AS image_id,
               1 - (ic.embedding <=> %s::vector) AS score
        FROM image_chunks ic
        JOIN images i ON i.id = ic.image_id
        WHERE ic.embedding IS NOT NULL AND i.user_id = %s
        ORDER BY ic.embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, user_id, query_embedding, limit),
    )
    for row in cur.fetchall():
        results.append(
            RetrievedChunk(
                chunk_id=str(row["id"]),
                page_content=row["content"],
                filename=row["filename"],
                source_type="image",
                source_id=str(row["image_id"]),
                score=float(row["score"]),
                match_types=["vector"],
            )
        )

    results.sort(key=lambda c: c.score, reverse=True)
    return results[:limit]


def _keyword_search_postgres(cur, user_query: str, limit: int, user_id: str) -> list[RetrievedChunk]:
    """BM25-style keyword search via PostgreSQL full-text search (ts_rank_cd)."""
    results: list[RetrievedChunk] = []

    cur.execute(
        """
        SELECT dc.id, dc.content, d.filename, dc.document_id, dc.chunk_index,
               ts_rank_cd(dc.content_tsv, plainto_tsquery('english', %s)) AS score
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.content_tsv @@ plainto_tsquery('english', %s) AND d.user_id = %s
        ORDER BY score DESC
        LIMIT %s
        """,
        (user_query, user_query, user_id, limit),
    )
    for row in cur.fetchall():
        results.append(
            RetrievedChunk(
                chunk_id=str(row["id"]),
                page_content=row["content"],
                filename=row["filename"],
                source_type="document",
                source_id=str(row["document_id"]),
                score=float(row["score"]),
                match_types=["keyword"],
                chunk_index=row.get("chunk_index"),
            )
        )

    cur.execute(
        """
        SELECT ic.id, ic.content, i.filename, i.id AS image_id,
               ts_rank_cd(ic.content_tsv, plainto_tsquery('english', %s)) AS score
        FROM image_chunks ic
        JOIN images i ON i.id = ic.image_id
        WHERE ic.content_tsv @@ plainto_tsquery('english', %s) AND i.user_id = %s
        ORDER BY score DESC
        LIMIT %s
        """,
        (user_query, user_query, user_id, limit),
    )
    for row in cur.fetchall():
        results.append(
            RetrievedChunk(
                chunk_id=str(row["id"]),
                page_content=row["content"],
                filename=row["filename"],
                source_type="image",
                source_id=str(row["image_id"]),
                score=float(row["score"]),
                match_types=["keyword"],
            )
        )

    results.sort(key=lambda c: c.score, reverse=True)
    return results[:limit]


def hybrid_retrieve_from_postgres(user_query: str, user_id: str, k: int = TOP_K) -> list[RetrievedChunk]:
    """
    Hybrid retrieval (web app):
      1. Vector search  — semantic similarity (embeddings)
      2. Keyword search — exact term matching (PostgreSQL FTS / BM25-style)
      3. RRF fusion     — merge both ranked lists, boost chunks in both
    """
    db_cursor = _db_cursor()
    query_embedding = get_embeddings().embed_query(user_query)

    with db_cursor() as cur:
        vector_results = _vector_search_postgres(cur, query_embedding, RETRIEVAL_CANDIDATES, user_id)
        keyword_results = _keyword_search_postgres(cur, user_query, RETRIEVAL_CANDIDATES, user_id)

    if not vector_results and not keyword_results:
        return []

    if not keyword_results:
        return vector_results[:k]

    if not vector_results:
        return keyword_results[:k]

    return _reciprocal_rank_fusion([vector_results, keyword_results], k=k)


def answer_query_postgres(user_query: str, user_id: str, k: int = TOP_K) -> tuple[str, list[dict]]:
    """Web app Q&A: hybrid retrieve (scoped to user) → guardrailed invoke_rag."""
    if not user_query or not user_query.strip():
        return "Please enter a question about your uploaded documents or images.", []

    retrieved = hybrid_retrieve_from_postgres(user_query.strip(), user_id=user_id, k=k)
    if retrieved:
        retrieved = _assign_citation_labels(retrieved)
    context = build_context(retrieved) if retrieved else "No documents or images uploaded yet."
    answer = invoke_rag(user_query.strip(), context)

    sources = [
        {
            "citation": chunk.citation_label,
            "type": chunk.source_type,
            "filename": chunk.filename,
            f"{chunk.source_type}_id": chunk.source_id,
            "chunk_index": chunk.chunk_index,
            "score": chunk.score,
            "match": chunk.match_types[0] if chunk.match_types else "hybrid",
        }
        for chunk in retrieved
    ]
    return answer, sources


def run_cli():
    user_query = input("Enter your query: ")
    print(answer_query(user_query))


if __name__ == "__main__":
    run_cli()
