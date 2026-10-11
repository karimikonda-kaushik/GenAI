"""Thin wrapper — all RAG logic lives in app_rag.py."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app_rag import answer_query_postgres, index_document_to_postgres, index_image_to_postgres

__all__ = ["answer_query_postgres", "index_document_to_postgres", "index_image_to_postgres"]
