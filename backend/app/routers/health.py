from fastapi import APIRouter

from app.services.base import fetch_one

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/db")
def health_db():
    # "dual" is Oracle's built-in dummy table, ideal for a connection check.
    row = fetch_one("SELECT 1 AS ok FROM dual")
    return {"db": "ok", "result": row}
