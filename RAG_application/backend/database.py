import os
import sys
from contextlib import contextmanager
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in .env")
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    register_vector(conn)
    return conn


@contextmanager
def db_cursor():
    with get_connection() as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()


def check_db_connection() -> bool:
    try:
        with db_cursor() as cur:
            cur.execute("SELECT 1")
            return True
    except Exception:
        return False
