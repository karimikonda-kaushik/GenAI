import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from auth import CurrentUser, get_current_user
from config import ALLOWED_DOCUMENT_TYPES, ALLOWED_IMAGE_TYPES, MAX_UPLOAD_SIZE_MB, RATE_LIMIT_UPLOAD
from database import db_cursor
from rate_limit import limiter
from security import safe_error_message, sanitize_filename
from services.rag_service import index_document_to_postgres, index_image_to_postgres

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])

MAX_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload/document")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type: {file.content_type}",
        )

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_UPLOAD_SIZE_MB}MB limit")

    safe_name = sanitize_filename(file.filename or "document")
    doc_id = uuid.uuid4()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (id, user_id, filename, mime_type, file_size, file_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'processing')
            RETURNING id, filename, mime_type, file_size, created_at
            """,
            (str(doc_id), user.user_id, safe_name, file.content_type, len(data), data),
        )
        row = cur.fetchone()

    try:
        chunk_count = index_document_to_postgres(
            str(doc_id), data, file.content_type, safe_name, user_id=user.user_id
        )
    except Exception:
        logger.exception("Document indexing failed for user %s", user.user_id)
        with db_cursor() as cur:
            cur.execute(
                "UPDATE documents SET status = 'failed', error_message = %s WHERE id = %s AND user_id = %s",
                ("Indexing failed", str(doc_id), user.user_id),
            )
        raise HTTPException(status_code=500, detail=safe_error_message("Document indexing")) from None

    return {
        "id": str(row["id"]),
        "filename": row["filename"],
        "mime_type": row["mime_type"],
        "file_size": row["file_size"],
        "chunk_count": chunk_count,
        "status": "indexed",
        "created_at": row["created_at"].isoformat(),
    }


@router.post("/upload/image")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}",
        )

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_UPLOAD_SIZE_MB}MB limit")

    safe_name = sanitize_filename(file.filename or "image")
    image_id = uuid.uuid4()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO images (id, user_id, filename, mime_type, file_size, file_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'processing')
            RETURNING id, filename, mime_type, file_size, created_at
            """,
            (str(image_id), user.user_id, safe_name, file.content_type, len(data), data),
        )
        row = cur.fetchone()

    try:
        caption = index_image_to_postgres(
            str(image_id), data, file.content_type, safe_name, user_id=user.user_id
        )
    except Exception:
        logger.exception("Image indexing failed for user %s", user.user_id)
        with db_cursor() as cur:
            cur.execute(
                "UPDATE images SET status = 'failed', error_message = %s WHERE id = %s AND user_id = %s",
                ("Indexing failed", str(image_id), user.user_id),
            )
        raise HTTPException(status_code=500, detail=safe_error_message("Image indexing")) from None

    return {
        "id": str(row["id"]),
        "filename": row["filename"],
        "mime_type": row["mime_type"],
        "file_size": row["file_size"],
        "caption": caption,
        "status": "indexed",
        "created_at": row["created_at"].isoformat(),
    }


@router.get("/documents")
@limiter.limit(RATE_LIMIT_UPLOAD)
def list_documents(request: Request, user: CurrentUser = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, filename, mime_type, file_size, status, created_at,
                   (SELECT COUNT(*) FROM document_chunks dc WHERE dc.document_id = d.id) AS chunk_count
            FROM documents d
            WHERE d.user_id = %s
            ORDER BY created_at DESC
            """,
            (user.user_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "id": str(r["id"]),
            "filename": r["filename"],
            "mime_type": r["mime_type"],
            "file_size": r["file_size"],
            "status": r["status"],
            "chunk_count": r["chunk_count"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/images")
@limiter.limit(RATE_LIMIT_UPLOAD)
def list_images(request: Request, user: CurrentUser = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, filename, mime_type, file_size, status, caption, created_at
            FROM images
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user.user_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "id": str(r["id"]),
            "filename": r["filename"],
            "mime_type": r["mime_type"],
            "file_size": r["file_size"],
            "status": r["status"],
            "caption": r["caption"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
