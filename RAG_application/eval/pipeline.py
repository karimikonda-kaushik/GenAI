"""
Run the production RAG path once per question and collect RAGAS fields.

Uses:
  hybrid_retrieve_from_postgres → contexts
  invoke_rag(build_context(...)) → answer

Avoids double retrieval (answer_query_postgres would retrieve again).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_rag import (  # noqa: E402
    TOP_K,
    _assign_citation_labels,
    build_context,
    hybrid_retrieve_from_postgres,
    invoke_rag,
)


def run_rag_sample(question: str, user_id: str, k: int = TOP_K) -> dict[str, Any]:
    """Return one RAGAS-ready sample for a question."""
    q = (question or "").strip()
    if not q:
        raise ValueError("question is empty")

    retrieved = hybrid_retrieve_from_postgres(q, user_id=user_id, k=k)
    if retrieved:
        retrieved = _assign_citation_labels(retrieved)

    contexts = [c.page_content for c in retrieved]
    context_str = build_context(retrieved) if retrieved else "No documents or images uploaded yet."
    answer = invoke_rag(q, context_str)

    return {
        "user_input": q,
        "retrieved_contexts": contexts,
        "response": answer,
        "sources": [
            {
                "citation": c.citation_label,
                "filename": c.filename,
                "type": c.source_type,
                "score": c.score,
                "match": c.match_types,
            }
            for c in retrieved
        ],
    }
