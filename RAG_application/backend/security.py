import re
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Strip path components and dangerous characters from upload filenames."""
    name = Path(filename or "upload").name
    name = re.sub(r"[^\w.\- ]", "_", name)
    return name[:255] or "upload"


def safe_error_message(action: str) -> str:
    """Return a generic client-facing error without leaking internals."""
    return f"{action} failed. Please try again or contact support."
