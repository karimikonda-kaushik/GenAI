import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import CORS_ORIGINS, GOOGLE_API_KEY, REQUIRE_AUTH
from database import check_db_connection
from rate_limit import limiter
from routers import chat, sessions, upload

app = FastAPI(
    title="RAG Application API",
    description="Document & image Q&A with PostgreSQL vector store",
    version="0.2.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(upload.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok and GOOGLE_API_KEY else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "llm_configured": bool(GOOGLE_API_KEY),
        "auth_required": REQUIRE_AUTH,
    }
