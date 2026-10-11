import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import CurrentUser, assert_session_owner, get_current_user
from config import RATE_LIMIT_DEFAULT
from database import db_cursor
from rate_limit import limiter

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    metadata: dict = {}


@router.post("", response_model=SessionResponse)
@limiter.limit(RATE_LIMIT_DEFAULT)
def create_session(
    request: Request,
    body: SessionCreate,
    user: CurrentUser = Depends(get_current_user),
):
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO sessions (user_id, title) VALUES (%s, %s)
            RETURNING id, title, created_at, updated_at
            """,
            (user.user_id, body.title),
        )
        row = cur.fetchone()
    return SessionResponse(
        id=str(row["id"]),
        title=row["title"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
@limiter.limit(RATE_LIMIT_DEFAULT)
def get_messages(
    request: Request,
    session_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
):
    assert_session_owner(str(session_id), user.user_id)

    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, role, content, created_at, metadata
            FROM messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (str(session_id),),
        )
        rows = cur.fetchall()

    return [
        MessageResponse(
            id=str(r["id"]),
            role=r["role"],
            content=r["content"],
            created_at=r["created_at"].isoformat(),
            metadata=r["metadata"] or {},
        )
        for r in rows
    ]
