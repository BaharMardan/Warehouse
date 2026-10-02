"""Uninvoiced cargo aging, with per-user acknowledgement of displayed entries."""
from datetime import date, datetime
from hashlib import sha256
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.auth.deps import require_permission
from app.core.db import get_connection
from app.services import receipt_db as db

router = APIRouter(prefix="/abandoned", tags=["abandoned"])
AGING_SQL = """
SELECT h."ID_TALI" AS id, h."TALI_NUMBER" AS tally_number,
       h."DATE_UNLOADING" AS unloaded_at,
       TRUNC(CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Tehran' AS DATE)) - TRUNC(h."DATE_UNLOADING") AS age_days,
       COALESCE(o."COMPANY_NAME", TRIM(o."NAME" || ' ' || o."FAMILY")) AS owner_name
FROM "FA_TALI_HEADER" h
LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = h."ID_PRODUCT_OWNEAR"
WHERE h."IS_DELETED" = 'no'
  AND h."DATE_UNLOADING" IS NOT NULL
  AND TRUNC(h."DATE_UNLOADING") <= TRUNC(CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Tehran' AS DATE)) - 80
  AND (h."DATE_CARGO_EXIT" IS NULL OR TRUNC(h."DATE_CARGO_EXIT") >
       TRUNC(CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Tehran' AS DATE)))
  AND NOT EXISTS (
      SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
      WHERE i."TALI_ID_HEADER" = h."ID_TALI" AND NVL(i."SORAT_IS_DELETED", 'no') = 'no')
ORDER BY h."DATE_UNLOADING", h."ID_TALI"
"""


def classify(rows, seen):
    result = []
    for row in rows:
        days = int(row["age_days"])
        if days < 80:
            continue
        stage = "abandoned" if days >= 90 else "warning"
        unloaded = row["unloaded_at"]
        if isinstance(unloaded, datetime):
            unloaded = unloaded.date()
        unloaded = unloaded.isoformat() if isinstance(unloaded, date) else str(unloaded)[:10]
        token = sha256(f'{row["id"]}:{stage}:{unloaded}'.encode()).hexdigest()
        result.append({**row, "unloaded_at": unloaded, "age_days": days,
                       "stage": stage, "days_remaining": max(0, 90 - days),
                       "token": token, "unseen": token not in seen})
    return result


@router.get("")
def list_abandoned(user: dict = Depends(require_permission("abandoned.view"))):
    with get_connection() as conn:
        with conn.cursor() as cur:
            rows = db.rows(cur, AGING_SQL)
            seen = {r["event_token"] for r in db.rows(cur,
                "SELECT EVENT_TOKEN FROM FA_ABANDONED_SEEN WHERE USER_ID = :id", {"id": user["id"]})}
    items = classify(rows, seen)
    return {"items": items, "total": len(items),
            "abandoned_count": sum(r["stage"] == "abandoned" for r in items),
            "warning_count": sum(r["stage"] == "warning" for r in items),
            "has_unseen": any(r["unseen"] for r in items)}


class SeenInput(BaseModel):
    tokens: list[str] = Field(max_length=10000)


@router.post("/seen", status_code=204)
def mark_seen(payload: SeenInput, user: dict = Depends(require_permission("abandoned.view"))):
    # Only acknowledge rows actually rendered by this client, never newer arrivals.
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                # Serialize simultaneous acknowledgements from this user's tabs.
                cur.execute("SELECT ID FROM FA_USERS WHERE ID = :id FOR UPDATE", {"id": user["id"]})
                valid = {r["token"] for r in classify(db.rows(cur, AGING_SQL), set())}
                tokens = valid.intersection(payload.tokens)
                for token in tokens:
                    cur.execute("""MERGE INTO FA_ABANDONED_SEEN dest
                        USING (SELECT :viewer_id AS USER_ID, :token AS EVENT_TOKEN FROM DUAL) src
                        ON (dest.USER_ID = src.USER_ID AND dest.EVENT_TOKEN = src.EVENT_TOKEN)
                        WHEN NOT MATCHED THEN INSERT (USER_ID, EVENT_TOKEN, SEEN_AT)
                        VALUES (:viewer_id, :token, SYSDATE)""", {"viewer_id": user["id"], "token": token})
            conn.commit()
        except Exception:
            conn.rollback()
            raise
