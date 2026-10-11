import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Auth — set REQUIRE_AUTH=true in production / Kubernetes
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
API_KEY = os.getenv("API_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
DEV_USER_ID = os.getenv("DEV_USER_ID", "dev-user")

LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4

HYBRID_VECTOR_WEIGHT = 0.5
HYBRID_KEYWORD_WEIGHT = 0.5
RRF_K = 60
RETRIEVAL_CANDIDATES = 8

MAX_UPLOAD_SIZE_MB = 25
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
}
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

# Comma-separated origins, e.g. https://rag.example.com,http://localhost:5173
_cors = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]

# Rate limits (per client IP per minute)
RATE_LIMIT_CHAT = os.getenv("RATE_LIMIT_CHAT", "20/minute")
RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "10/minute")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
