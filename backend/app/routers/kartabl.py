"""کارتابل (worklist) read endpoint.

One row per active tally, joined across the three modules so the worklist can
jump straight to that tally's own تالی / قبض انبار / صورتحساب:

  GET /kartabl/list

Each row carries what the table shows (tally number, aggregated goods
description, owner, transport company, its representative, unloading date)
plus navigation payload: the workflow status (the exact CASE /tally/list uses,
so both screens always agree on a tally's colour), the tally's visible
receipts, and the active invoice id when one exists.
"""
from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.services.base import fetch_all

router = APIRouter(prefix="/kartabl", tags=["kartabl"])

# Same owner-name rule as the ghabz router: legal owners in the imported data
# keep their name in NAME rather than COMPANY_NAME, so a bare CASE on TYPE
# returns blank for them. COALESCE reads whichever column is populated.
OWNER_NAME_SQL = """
    COALESCE(
        NULLIF(TRIM(o."COMPANY_NAME"), ''),
        NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')
    )
"""

# Receipts are aggregated into "id|number" pairs joined by "," so the عملیات
# menu can offer one entry per receipt without a second round-trip. Both parts
# are digits/underscores only (GHABZ_NUMBER is <year>_<tally>_<seq>), so the
# separators are unambiguous. Visibility mirrors /ghabz/list: APEX-era receipts
# (no GHABZ_NUMBER) always count, system-issued ones only while they still have
# active lines — the menu must never point at a receipt the list screen hides.
#
# workflow_status deliberately keeps the plainer EXISTS of /tally/list (any
# active receipt header) rather than the visibility rule above, so the row
# colour here always matches the badge on the tally list.
LIST_SQL = f"""
SELECT
    h."ID_TALI"                         AS id_tali,
    h."TALI_NUMBER"                     AS tali_number,
    (
        SELECT LISTAGG(DISTINCT TRIM(d."DESCRIPTION_KALA"), '، ' ON OVERFLOW TRUNCATE)
                   WITHIN GROUP (ORDER BY TRIM(d."DESCRIPTION_KALA"))
        FROM "FA_TALI_DETAILES" d
        WHERE d."ID_HEADERS_TALI" = h."ID_TALI"
          AND d."IS_DELETED" = 'no'
          AND TRIM(d."DESCRIPTION_KALA") IS NOT NULL
    )                                   AS kala_description,
    {OWNER_NAME_SQL}                    AS owner_name,
    TRIM(c_comp."COMPANY_NAME")         AS company_name,
    TRIM(c_resp."NAME" || ' ' || c_resp."FAMILY") AS representative_name,
    h."DATE_UNLOADING"                  AS date_unloading,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM "FA_SORAT_HESAB_HEADER" invoice_header
            WHERE invoice_header."TALI_ID_HEADER" = h."ID_TALI"
              AND invoice_header."SORAT_IS_DELETED" = 'no'
        ) THEN 'closed'
        WHEN EXISTS (
            SELECT 1
            FROM "fa_ghabz_anbar_header" receipt_header
            WHERE receipt_header."TALI_ID" = h."ID_TALI"
              AND receipt_header."IS_DELETED" = 'no'
        ) THEN 'pending'
        ELSE 'open'
    END                                 AS workflow_status,
    (
        SELECT LISTAGG(
                   g."ID_ghabz" || '|' ||
                   NVL(g."GHABZ_NUMBER", TO_CHAR(g."number_ghabz")),
                   ','
               ) WITHIN GROUP (ORDER BY g."ID_ghabz")
        FROM "fa_ghabz_anbar_header" g
        WHERE g."TALI_ID" = h."ID_TALI"
          AND g."IS_DELETED" = 'no'
          AND (
                g."GHABZ_NUMBER" IS NULL
             OR EXISTS (
                    SELECT 1
                    FROM "FA_ghabz_anbar_DETAILES" gd
                    WHERE gd."ID_GHABZ_ANBAR_HEADAR" = g."ID_ghabz"
                      AND gd."IS_DELETED" = 'no'
                )
              )
    )                                   AS receipts,
    (
        SELECT MAX(s."ID_SORAT")
        FROM "FA_SORAT_HESAB_HEADER" s
        WHERE s."TALI_ID_HEADER" = h."ID_TALI"
          AND s."SORAT_IS_DELETED" = 'no'
    )                                   AS invoice_id
FROM "FA_TALI_HEADER" h
LEFT JOIN "FA_TRANSPORT_COMPANY"      c_comp ON c_comp."ID_COMPANY"       = h."ID_COMPANY"
LEFT JOIN "FA_REPRESENTATIVE_COMPANY" c_resp ON c_resp."ID_REPRE_COMPANY" = h."ID_RESPONS_COMPANY"
LEFT JOIN "FA_PRODUCT_OWNER"          o      ON o."ID_OWNER"              = h."ID_PRODUCT_OWNEAR"
WHERE h."IS_DELETED" = 'no'
ORDER BY h."ID_TALI" DESC
"""


@router.get("/list", dependencies=[Depends(get_current_user)])
def list_kartabl():
    return fetch_all(LIST_SQL)
