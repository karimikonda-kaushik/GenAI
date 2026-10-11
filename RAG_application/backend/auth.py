from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from config import API_KEY, DEV_USER_ID, REQUIRE_AUTH, SUPABASE_JWT_SECRET

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass
class CurrentUser:
    user_id: str
    auth_method: str


def _verify_jwt(token: str) -> CurrentUser:
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT auth is not configured on the server")
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return CurrentUser(user_id=str(user_id), auth_method="jwt")


def _verify_api_key(provided_key: str) -> CurrentUser:
    if not API_KEY or not secrets.compare_digest(provided_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return CurrentUser(user_id="api-key-user", auth_method="api_key")


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> CurrentUser:
    if not REQUIRE_AUTH:
        return CurrentUser(user_id=DEV_USER_ID, auth_method="dev")

    if credentials and credentials.credentials:
        return _verify_jwt(credentials.credentials)

    if api_key:
        return _verify_api_key(api_key)

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Bearer JWT or X-API-Key header.",
    )


def assert_session_owner(session_id: str, user_id: str) -> None:
    from database import db_cursor

    with db_cursor() as cur:
        cur.execute(
            "SELECT id FROM sessions WHERE id = %s AND user_id = %s",
            (session_id, user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")
