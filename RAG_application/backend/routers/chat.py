import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import CurrentUser, assert_session_owner, get_current_user
from config import RATE_LIMIT_CHAT
from database import db_cursor
from rate_limit import limiter
from security import safe_error_message
from services.rag_service import answer_query_postgres

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    message_id: str
    content: str
    sources: list[dict] = []


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT_CHAT)
def chat(
    request: Request,
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    assert_session_owner(body.session_id, user.user_id)

    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'user', %s) RETURNING id",
            (body.session_id, body.message),
        )

    try:
        answer, sources = answer_query_postgres(body.message, user_id=user.user_id)
    except Exception:
        logger.exception("Chat generation failed for user %s", user.user_id)
        raise HTTPException(status_code=500, detail=safe_error_message("Answer generation")) from None

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages (session_id, role, content, metadata)
            VALUES (%s, 'assistant', %s, %s::jsonb)
            RETURNING id
            """,
            (body.session_id, answer, json.dumps({"sources": sources})),
        )
        msg_row = cur.fetchone()

    return ChatResponse(
        message_id=str(msg_row["id"]),
        content=answer,
        sources=sources,
    )
