"""Uninvoiced cargo aging, with per-user acknowledgement of displayed entries."""
from datetime import date, datetime
from hashlib import sha256
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.auth.deps import require_permission
from app.core.db import get_connection
from app.services import receipt_db as db
from app.services.abandoned_stock import attach_remaining_goods

router = APIRouter(prefix="/abandoned", tags=["abandoned"])
TEHRAN_TODAY = "TRUNC(CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Tehran' AS DATE))"

# A tally whose cargo has not left yet: no exit date, or one that has not arrived,
# and no tally-level invoice releasing everything. The aging report and the
# warehouse stock report (routers/reports.py) share this definition.
STILL_IN_WAREHOUSE_SQL = f"""AND (h."DATE_CARGO_EXIT" IS NULL OR TRUNC(h."DATE_CARGO_EXIT") >
       {TEHRAN_TODAY})
  AND NOT EXISTS (
      SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
      WHERE i."TALI_ID_HEADER" = h."ID_TALI" AND NVL(i."SORAT_IS_DELETED", 'no') = 'no'
        AND i."ID_GHABZ_ANBAR" IS NULL
        AND NOT EXISTS (SELECT 1 FROM "FA_REMAINING_INVOICE" extra WHERE extra."INVOICE_ID" = i."ID_SORAT"))"""

AGING_SQL = f"""
SELECT h."ID_TALI" AS id, h."TALI_NUMBER" AS tally_number,
       h."DATE_UNLOADING" AS unloaded_at,
       h."SABT_SEFARESH_NUMBER" AS order_registration_number,
       {TEHRAN_TODAY} - TRUNC(h."DATE_UNLOADING") AS age_days,
       COALESCE(o."COMPANY_NAME", TRIM(o."NAME" || ' ' || o."FAMILY")) AS owner_name
FROM "FA_TALI_HEADER" h
LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = h."ID_PRODUCT_OWNEAR"
WHERE h."IS_DELETED" = 'no'
  AND h."DATE_UNLOADING" IS NOT NULL
  AND TRUNC(h."DATE_UNLOADING") <= {TEHRAN_TODAY} - 80
  {STILL_IN_WAREHOUSE_SQL}
ORDER BY h."DATE_UNLOADING", h."ID_TALI"
"""


# Keep the tally-level aging counts and event tokens unchanged. Goods are read
# separately, once for the entire report, so multiple receipts cannot multiply
# the tally count or the value/weight of an original goods row.
# `eligible_sql` must return the tallies as id and unloaded_at columns.
def goods_sql(eligible_sql: str) -> str:
    return f"""
WITH eligible AS ({eligible_sql})
SELECT d."ID_HEADERS_TALI" AS tally_id, d."ID_TALI_DETAILS" AS detail_id,
       d."HSCODE" AS hscode, d."DESCRIPTION_KALA" AS description,
       d."CUSTOMS_VALUE" AS customs_value, d."WEIGHTE" AS remaining_weight,
       d."NUMBER_KALA" AS quantity, d."WEIGHTE_BASKOL" AS baskol,
       r."ID_ghabz" AS receipt_id, r."GHABZ_NUMBER" AS receipt_number,
       src."TALLY_DETAIL_ID" AS source_detail_id,
       src."WEIGHT_SHARE" AS weight_share, src."QUANTITY_SHARE" AS quantity_share,
       src."BASKOL_SHARE" AS baskol_share,
       CASE WHEN EXISTS (SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
           WHERE i."ID_GHABZ_ANBAR" = r."ID_ghabz" AND NVL(i."SORAT_IS_DELETED", 'no') = 'no'
             AND NOT EXISTS (SELECT 1 FROM "FA_REMAINING_INVOICE" extra WHERE extra."INVOICE_ID" = i."ID_SORAT"))
         THEN 1 ELSE 0 END AS invoiced,
       (SELECT SUM(NVL(rd."WEIGHTE_asnad", 0)) FROM "FA_ghabz_anbar_DETAILES" rd
        WHERE rd."ID_GHABZ_ANBAR_HEADAR" = r."ID_ghabz" AND rd."IS_DELETED" = 'no'
          AND NVL(UPPER(TRIM(rd."HSCODE")), ' ') = NVL(UPPER(TRIM(d."HSCODE")), ' ')) AS receipt_weight,
       (SELECT SUM(NVL(rd."NUMBER_KALA", 0)) FROM "FA_ghabz_anbar_DETAILES" rd
        WHERE rd."ID_GHABZ_ANBAR_HEADAR" = r."ID_ghabz" AND rd."IS_DELETED" = 'no'
          AND NVL(UPPER(TRIM(rd."HSCODE")), ' ') = NVL(UPPER(TRIM(d."HSCODE")), ' ')) AS receipt_quantity,
       (SELECT SUM(NVL(rd."WEIGHTE_BASKOL", 0)) FROM "FA_ghabz_anbar_DETAILES" rd
        WHERE rd."ID_GHABZ_ANBAR_HEADAR" = r."ID_ghabz" AND rd."IS_DELETED" = 'no'
          AND NVL(UPPER(TRIM(rd."HSCODE")), ' ') = NVL(UPPER(TRIM(d."HSCODE")), ' ')) AS receipt_baskol
FROM "FA_TALI_DETAILES" d
JOIN eligible h ON h.id = d."ID_HEADERS_TALI"
LEFT JOIN "fa_ghabz_anbar_header" r ON r."TALI_ID" = h.id
  AND r."IS_DELETED" = 'no'
  AND (NVL(r."IS_MASTER", 'no') = 'no' OR NOT EXISTS (
      SELECT 1 FROM "fa_ghabz_anbar_header" child
      WHERE child."TALI_ID" = h.id AND child."IS_DELETED" = 'no'
        AND NVL(child."IS_MASTER", 'no') = 'no'
        AND EXISTS (SELECT 1 FROM "FA_ghabz_anbar_DETAILES" cd
          WHERE cd."ID_GHABZ_ANBAR_HEADAR" = child."ID_ghabz" AND cd."IS_DELETED" = 'no')))
  AND (EXISTS (SELECT 1 FROM "FA_GHABZ_TALLY_SOURCE" src
          WHERE src."RECEIPT_ID" = r."ID_ghabz" AND src."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS")
       OR (NOT EXISTS (SELECT 1 FROM "FA_GHABZ_TALLY_SOURCE" src
               WHERE src."RECEIPT_ID" = r."ID_ghabz")
           AND EXISTS (SELECT 1 FROM "FA_ghabz_anbar_DETAILES" rd
               WHERE rd."ID_GHABZ_ANBAR_HEADAR" = r."ID_ghabz" AND rd."IS_DELETED" = 'no'
                 AND NVL(UPPER(TRIM(rd."HSCODE")), ' ') = NVL(UPPER(TRIM(d."HSCODE")), ' '))))
LEFT JOIN "FA_GHABZ_TALLY_SOURCE" src
  ON src."RECEIPT_ID" = r."ID_ghabz" AND src."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS"
WHERE d."IS_DELETED" = 'no'
ORDER BY h.unloaded_at, h.id, d."ID_TALI_DETAILS", r."ID_ghabz"
"""


GOODS_SQL = goods_sql(AGING_SQL)


def attach_goods(items, goods_rows):
    return attach_remaining_goods(items, goods_rows)


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
            goods_rows = db.rows(cur, GOODS_SQL) if rows else []
    items = attach_goods(classify(rows, seen), goods_rows)
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
                headers = db.rows(cur, AGING_SQL)
                current = attach_goods(classify(headers, set()), db.rows(cur, GOODS_SQL) if headers else [])
                valid = {r["token"] for r in current}
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
