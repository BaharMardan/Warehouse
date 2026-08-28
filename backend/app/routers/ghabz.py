# """قبض انبار (warehouse receipt) reads and the create-from-tally flow.

#   GET  /ghabz/list                            - all receipts, FK names resolved
#   GET  /ghabz/{id}/details                    - one receipt's line items
#   GET  /ghabz/from-tally/{tali_id}/allotments - per goods-code allotment, issued
#                                                 and remaining quantities
#   POST /ghabz/from-tally/{tali_id}            - issue a receipt drawing quantities

# Plain field edits still go through the factory routers (/ghabz-header,
# /ghabz-details). Creation does not, because the receipt number has to be
# allocated in the same transaction as the insert -- see services/ghabz_numbering.

# The receipt-line model is dictated by two objects the legacy schema already
# enforces on FA_ghabz_anbar_DETAILES:

# * FA_CON_تکرار_کدکلا -- UNIQUE (ID_GHABZ_ANBAR_HEADAR, code_kala), so a receipt
#   holds at most one line per goods code.
# * TRG_CHK_GHABZ_TALI_LIMIT -- sums NUMBER_KALA / WEIGHTE_asnad / WEIGHTE_BASKOL
#   over every receipt of the parent tally for a code, and rejects the insert when
#   that total exceeds the tally's own totals for the same CODE_GROUPE_KALA, or
#   when the tally has no such code at all.

# So a receipt line is not a copy of a tally row. One tally row per receipt line
# would collide on the constraint whenever two rows share a code. A line is a
# *draw against a per-code allotment*: the tally says how much of code 110 exists,
# each receipt takes some of it, and the receipts may never sum past the tally.
# That is what makes several receipts per tally meaningful.

# The trigger's two sum queries do not filter IS_DELETED, so a soft-deleted
# receipt still consumes its share. ALLOTMENTS_SQL reproduces that exactly --
# deliberately, because a "remaining" figure the trigger disagrees with would
# offer the operator quantities the database then refuses.
# """
# from datetime import datetime

# import oracledb
# from fastapi import APIRouter, Depends, HTTPException
# from pydantic import BaseModel

# from app.auth.deps import get_current_user
# from app.core.db import get_connection
# from app.services.base import fetch_all
# from app.services.ghabz_allotment import (
#     GhabzFromTallyInput,
#     annotate,
#     plan_lines,
#     shared_anbar,
# )
# from app.services.ghabz_numbering import (
#     TallyNotFound,
#     TallyNotNumbered,
#     allocate_ghabz_number,
# )

# router = APIRouter(prefix="/ghabz", tags=["ghabz"])

# # Legal owners in the imported data keep their name in NAME rather than
# # COMPANY_NAME, so a bare CASE on TYPE returns blank for them. COALESCE reads
# # whichever column is actually populated.
# OWNER_NAME_SQL = """
#     COALESCE(
#         NULLIF(TRIM(o."COMPANY_NAME"), ''),
#         NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')
#     )
# """

# LIST_SQL = f"""
# SELECT
#     h."ID_ghabz"            AS id_ghabz,
#     h."GHABZ_NUMBER"        AS ghabz_number,
#     h."GHABZ_SEQ"           AS ghabz_seq,
#     h."number_ghabz"        AS number_ghabz,
#     h."NUMBER_tali"         AS number_tali,
#     h."TALI_ID"             AS tali_id,
#     h."DATE_UNLOADING"      AS date_unloading,
#     h."ID_MARZE"            AS id_marze,
#     t_marze."SYS_TERM_VALUE" AS marze_name,
#     h."ID_COUNTRY"          AS id_country,
#     t_country."SYS_TERM_VALUE" AS country_name,
#     h."ID_COMPANY"          AS id_company,
#     TRIM(c."COMPANY_NAME") AS company_name,
#     h."ID_PRODUCT_OWNEAR"   AS id_product_ownear,
#     {OWNER_NAME_SQL}        AS owner_name,
#     h."ID_anbar"            AS id_anbar,
#     a."NAME_ANBAR"          AS anbar_name,
#     u."USERNAME"            AS created_by_username,
#     u."FULL_NAME"           AS created_by_full_name
# FROM "fa_ghabz_anbar_header" h
# LEFT JOIN "FA_SYS_TERMS"              t_marze   ON t_marze."SYS_TERM_ID"   = h."ID_MARZE"
# LEFT JOIN "FA_SYS_TERMS"              t_country ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
# LEFT JOIN "FA_TRANSPORT_COMPANY"      c         ON c."ID_COMPANY"          = h."ID_COMPANY"
# LEFT JOIN "FA_PRODUCT_OWNER"          o         ON o."ID_OWNER"            = h."ID_PRODUCT_OWNEAR"
# LEFT JOIN "FA_ANBAR"                  a         ON a."ID_ANBAR"            = h."ID_anbar"
# LEFT JOIN "FA_USERS"                  u         ON u."ID"                  = h."CREATE_BY"
# WHERE h."IS_DELETED" = 'no'
# ORDER BY h."ID_ghabz" DESC
# """

# DETAILS_SQL = """
# SELECT
#     d."ID_ghabz_anbar_DETAILS" AS id_ghabz_anbar_details,
#     d."ID_GHABZ_ANBAR_HEADAR"  AS id_ghabz_anbar_headar,
#     d."code_kala"              AS code_kala,
#     d."code_kala_kantiner"     AS code_kala_kantiner,
#     d."DESCRIPTION_KALA"       AS description_kala,
#     d."HSCODE"                 AS hscode,
#     d."TYPE_BASTEh"            AS type_basteh,
#     d."NUMBER_KALA"            AS number_kala,
#     d."NUMBER_KAntiner"        AS number_kantiner,
#     d."WEIGHTE_asnad"          AS weighte_asnad,
#     d."WEIGHTE_BASKOL"         AS weighte_baskol,
#     d."NUMBER_HAMEL"           AS number_hamel,
#     d."ID_TAGH_ANBAR"          AS id_tagh_anbar,
#     tg."NAME_TAGH"             AS tagh_name
# FROM "FA_ghabz_anbar_DETAILES" d
# LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = d."ID_TAGH_ANBAR"
# WHERE d."ID_GHABZ_ANBAR_HEADAR" = :hid AND d."IS_DELETED" = 'no'
# ORDER BY d."ID_ghabz_anbar_DETAILS"
# """

# # One row per goods code on the tally: what the tally allots, what the existing
# # receipts already took, and therefore what is still drawable. The descriptive
# # columns are a representative value (MIN) because several tally rows can share
# # a code while differing in طاق or حامل; the operator can edit the line after.
# #
# # The issued-sum subqueries mirror TRG_CHK_GHABZ_TALI_LIMIT exactly, including
# # its lack of an IS_DELETED filter.
# ALLOTMENTS_SQL = """
# SELECT
#     g.code_kala             AS code_kala,
#     g.description_kala      AS description_kala,
#     g.hscode                AS hscode,
#     g.type_bastem           AS type_bastem,
#     g.id_anbar              AS id_anbar,
#     a."NAME_ANBAR"          AS anbar_name,
#     g.id_tagh_anbar         AS id_tagh_anbar,
#     tg."NAME_TAGH"          AS tagh_name,
#     g.number_hamel          AS number_hamel,
#     g.tally_line_count      AS tally_line_count,
#     g.tally_number_kala     AS tally_number_kala,
#     g.tally_weighte         AS tally_weighte,
#     g.tally_weighte_baskol  AS tally_weighte_baskol,
#     NVL((
#         SELECT SUM(d."NUMBER_KALA")
#         FROM "FA_ghabz_anbar_DETAILES" d
#         JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = d."ID_GHABZ_ANBAR_HEADAR"
#         WHERE h."TALI_ID" = :tid AND d."code_kala" = g.code_kala
#     ), 0) AS issued_number_kala,
#     NVL((
#         SELECT SUM(d."WEIGHTE_asnad")
#         FROM "FA_ghabz_anbar_DETAILES" d
#         JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = d."ID_GHABZ_ANBAR_HEADAR"
#         WHERE h."TALI_ID" = :tid AND d."code_kala" = g.code_kala
#     ), 0) AS issued_weighte_asnad,
#     NVL((
#         SELECT SUM(d."WEIGHTE_BASKOL")
#         FROM "FA_ghabz_anbar_DETAILES" d
#         JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = d."ID_GHABZ_ANBAR_HEADAR"
#         WHERE h."TALI_ID" = :tid AND d."code_kala" = g.code_kala
#     ), 0) AS issued_weighte_baskol
# FROM (
#     SELECT
#         t."CODE_GROUPE_KALA"            AS code_kala,
#         MIN(t."DESCRIPTION_KALA")       AS description_kala,
#         MIN(t."HSCODE")                 AS hscode,
#         MIN(t."TYPE_BASTEM")            AS type_bastem,
#         MIN(t."ID_ANBAR")               AS id_anbar,
#         MIN(t."ID_TAGH_ANBAR")          AS id_tagh_anbar,
#         MIN(t."NUMBER_HAMEL")           AS number_hamel,
#         COUNT(*)                        AS tally_line_count,
#         NVL(SUM(t."NUMBER_KALA"), 0)    AS tally_number_kala,
#         NVL(SUM(t."WEIGHTE"), 0)        AS tally_weighte,
#         NVL(SUM(t."WEIGHTE_BASKOL"), 0) AS tally_weighte_baskol
#     FROM "FA_TALI_DETAILES" t
#     WHERE t."ID_HEADERS_TALI" = :tid
#     GROUP BY t."CODE_GROUPE_KALA"
# ) g
# LEFT JOIN "FA_ANBAR"      a  ON a."ID_ANBAR" = g.id_anbar
# LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = g.id_tagh_anbar
# ORDER BY g.code_kala
# """

# FROM_TALLY_READ = """
# SELECT "ID_TALI", "NUMBER_KARANEH", "TALI_NUMBER", "DATE_UNLOADING",
#        "DATE_ENTER_MARZE", "ID_MARZE", "ID_COUNTRY", "ID_COMPANY",
#        "ID_PRODUCT_OWNEAR", "NAME_ARZYAB", "NAME_ANBARDAR", "IS_BIMEH",
#        "NUMBER_BIMEH", "COMPANY_BIMEH", "RADEF_MARZE", "TRACKING_NUMBER",
#        "CUSTOMS_PROCEDURE"
# FROM "FA_TALI_HEADER" WHERE "ID_TALI" = :tid AND "IS_DELETED" = 'no'
# """

# INSERT_GHABZ = """
# INSERT INTO "fa_ghabz_anbar_header" (
#     "TALI_ID", "NUMBER_tali", "GHABZ_NUMBER", "GHABZ_SEQ",
#     "NUMBER_KARANEH", "number_royea", "number_MARZE", "TRACKING_NUMBER",
#     "DATE_UNLOADING", "DATE_ENTER_MARZE",
#     "ID_MARZE", "ID_COUNTRY", "ID_COMPANY", "ID_PRODUCT_OWNEAR", "ID_anbar",
#     "NAME_ANBARDAR", "status_BIMEH", "NUMBER_BIMEH", "COMPANY_BIMEH",
#     "IS_DELETED", "CREATE_AT", "CREATE_BY"
# ) VALUES (
#     :tali_id, :number_tali, :ghabz_number, :ghabz_seq,
#     :number_karaneh, :number_royea, :number_marze, :tracking_number,
#     :date_unloading, :date_enter_marze,
#     :id_marze, :id_country, :id_company, :id_product_ownear, :id_anbar,
#     :name_anbardar, :status_bimeh, :number_bimeh, :company_bimeh,
#     'no', :created_at, :actor_id
# ) RETURNING "ID_ghabz" INTO :new_id
# """

# INSERT_LINE = """
# INSERT INTO "FA_ghabz_anbar_DETAILES" (
#     "ID_GHABZ_ANBAR_HEADAR", "code_kala", "DESCRIPTION_KALA", "HSCODE",
#     "TYPE_BASTEh", "NUMBER_KALA", "WEIGHTE_asnad", "WEIGHTE_BASKOL",
#     "NUMBER_HAMEL", "ID_TAGH_ANBAR", "IS_DELETED", "CREATE_AT", "CREATE_BY"
# ) VALUES (
#     :header_id, :code_kala, :description_kala, :hscode,
#     :type_basteh, :number_kala, :weighte_asnad, :weighte_baskol,
#     :number_hamel, :id_tagh_anbar, 'no', :created_at, :actor_id
# )
# """


# def _rows_with_columns(cursor) -> list[dict]:
#     columns = [column[0].lower() for column in cursor.description]
#     return [dict(zip(columns, row)) for row in cursor.fetchall()]







# def _returned_int(value) -> int:
#     result = value.getvalue()
#     if isinstance(result, (list, tuple)):
#         result = result[0]
#     return int(result)


# def _as_date(value):
#     if isinstance(value, str) and value:
#         return datetime.fromisoformat(value).date()
#     return value


# def _trigger_message(exc: oracledb.DatabaseError) -> str | None:
#     """Surface the trigger's own Persian text instead of a raw ORA- dump."""
#     text = str(exc)
#     for code in ("ORA-20001", "ORA-20002", "ORA-20003", "ORA-20010", "ORA-20011"):
#         if code in text:
#             fragment = text.split(code + ":", 1)[1]
#             return fragment.split("ORA-")[0].strip()
#     if "FA_CON_" in text and "ORA-00001" in text:
#         return "برای هر کد کالا فقط یک ردیف در هر قبض انبار مجاز است."
#     return None


# @router.get("/list", dependencies=[Depends(get_current_user)])
# def list_ghabz():
#     return fetch_all(LIST_SQL)


# @router.get("/from-tally/{tali_id}/allotments", dependencies=[Depends(get_current_user)])
# def list_ghabz_allotments(tali_id: int):
#     """Per goods code: tally allotment, already issued, and what remains."""
#     return annotate(fetch_all(ALLOTMENTS_SQL, {"tid": tali_id}))


# @router.get("/{header_id}/details", dependencies=[Depends(get_current_user)])
# def list_ghabz_details(header_id: int):
#     return fetch_all(DETAILS_SQL, {"hid": header_id})


# @router.post("/from-tally/{tali_id}", status_code=201)
# def create_ghabz_from_tally(
#     tali_id: int,
#     selection: GhabzFromTallyInput | None = None,
#     current_user: dict = Depends(get_current_user),
# ):
#     """Issue one receipt, drawing quantities per goods code against the tally."""
#     requested = selection.lines if selection is not None else None

#     with get_connection() as conn:
#         try:
#             with conn.cursor() as cursor:
#                 cursor.execute(FROM_TALLY_READ, {"tid": tali_id})
#                 tally_rows = _rows_with_columns(cursor)
#                 if not tally_rows:
#                     raise HTTPException(status_code=404, detail="تالی یافت نشد")
#                 tally = tally_rows[0]

#                 cursor.execute(ALLOTMENTS_SQL, {"tid": tali_id})
#                 allotments = _rows_with_columns(cursor)
#                 by_code = {
#                     row["code_kala"]: row
#                     for row in allotments
#                     if row["code_kala"] is not None
#                 }

#                 lines = plan_lines(requested, allotments, by_code)

#                 ghabz_number, sequence, tali_number = allocate_ghabz_number(
#                     cursor, tali_id
#                 )

#                 cursor.execute("SELECT SYSDATE FROM DUAL")
#                 created_at = cursor.fetchone()[0]

#                 new_id_var = cursor.var(int)
#                 cursor.execute(
#                     INSERT_GHABZ,
#                     {
#                         "tali_id": tali_id,
#                         "number_tali": tali_number,
#                         "ghabz_number": ghabz_number,
#                         "ghabz_seq": sequence,
#                         "number_karaneh": tally.get("number_karaneh"),
#                         "number_royea": tally.get("customs_procedure"),
#                         "number_marze": tally.get("radef_marze"),
#                         "tracking_number": tally.get("tracking_number"),
#                         "date_unloading": _as_date(tally.get("date_unloading")),
#                         "date_enter_marze": _as_date(tally.get("date_enter_marze")),
#                         "id_marze": tally.get("id_marze"),
#                         "id_country": tally.get("id_country"),
#                         "id_company": tally.get("id_company"),
#                         "id_product_ownear": tally.get("id_product_ownear"),
#                         "id_anbar": shared_anbar(
#                             [by_code[line["code_kala"]] for line in lines]
#                         ),
#                         "name_anbardar": tally.get("name_anbardar"),
#                         "status_bimeh": tally.get("is_bimeh"),
#                         "number_bimeh": tally.get("number_bimeh"),
#                         "company_bimeh": tally.get("company_bimeh"),
#                         "created_at": created_at,
#                         "actor_id": current_user["id"],
#                         "new_id": new_id_var,
#                     },
#                 )
#                 new_id = _returned_int(new_id_var)

#                 cursor.executemany(
#                     INSERT_LINE,
#                     [
#                         {
#                             "header_id": new_id,
#                             "created_at": created_at,
#                             "actor_id": current_user["id"],
#                             **line,
#                         }
#                         for line in lines
#                     ],
#                 )

#             conn.commit()
#             return {
#                 "id_ghabz": new_id,
#                 "ghabz_number": ghabz_number,
#                 "ghabz_seq": sequence,
#                 "line_count": len(lines),
#             }
#         except HTTPException:
#             conn.rollback()
#             raise
#         except TallyNotFound as exc:
#             conn.rollback()
#             raise HTTPException(status_code=404, detail="تالی یافت نشد") from exc
#         except TallyNotNumbered as exc:
#             conn.rollback()
#             raise HTTPException(
#                 status_code=400,
#                 detail="این تالی شماره ندارد و نمی‌توان برای آن قبض انبار صادر کرد.",
#             ) from exc
#         except oracledb.DatabaseError as exc:
#             conn.rollback()
#             message = _trigger_message(exc)
#             if message:
#                 raise HTTPException(status_code=400, detail=message) from exc
#             raise HTTPException(
#                 status_code=500,
#                 detail="تخصیص شماره و صدور قبض انبار ناموفق بود.",
#             ) from exc
#         except ValueError as exc:
#             conn.rollback()
#             raise HTTPException(
#                 status_code=500,
#                 detail="تخصیص شماره و صدور قبض انبار ناموفق بود.",
#             ) from exc

"""قبض انبار (warehouse receipt) reads and the create-from-tally flow.

  GET  /ghabz/list                            - all receipts, FK names resolved
  GET  /ghabz/{id}/details                    - one receipt's line items
  GET  /ghabz/from-tally/{tali_id}/allotments - per goods-code allotment, issued
                                                and remaining quantities
  POST /ghabz/from-tally/{tali_id}            - issue a receipt drawing quantities

Plain field edits still go through the factory routers (/ghabz-header,
/ghabz-details). Creation does not, because the receipt number has to be
allocated in the same transaction as the insert -- see services/ghabz_numbering.

The receipt-line model is dictated by two objects the legacy schema already
enforces on FA_ghabz_anbar_DETAILES:

* FA_CON_تکرار_کدکلا -- UNIQUE (ID_GHABZ_ANBAR_HEADAR, code_kala), so a receipt
  holds at most one line per goods code.
* TRG_CHK_GHABZ_TALI_LIMIT -- sums NUMBER_KALA / WEIGHTE_asnad / WEIGHTE_BASKOL
  over every receipt of the parent tally for a code, and rejects the insert when
  that total exceeds the tally's own totals for the same CODE_GROUPE_KALA, or
  when the tally has no such code at all.

So a receipt line is not a copy of a tally row. One tally row per receipt line
would collide on the constraint whenever two rows share a code. A line is a
*draw against a per-code allotment*: the tally says how much of code 110 exists,
each receipt takes some of it, and the receipts may never sum past the tally.
That is what makes several receipts per tally meaningful.

The trigger's two sum queries do not filter IS_DELETED, so a soft-deleted
receipt still consumes its share. ALLOTMENTS_SQL reproduces that exactly --
deliberately, because a "remaining" figure the trigger disagrees with would
offer the operator quantities the database then refuses.
"""
from datetime import datetime

import oracledb
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.core.db import get_connection
from app.services.base import fetch_all
from app.services.ghabz_allotment import (
    GhabzFromTallyInput,
    annotate,
    plan_lines,
    shared_anbar,
)
from app.services.ghabz_numbering import (
    TallyNotFound,
    TallyNotNumbered,
    allocate_ghabz_number,
)

router = APIRouter(prefix="/ghabz", tags=["ghabz"])

# Legal owners in the imported data keep their name in NAME rather than
# COMPANY_NAME, so a bare CASE on TYPE returns blank for them. COALESCE reads
# whichever column is actually populated.
OWNER_NAME_SQL = """
    COALESCE(
        NULLIF(TRIM(o."COMPANY_NAME"), ''),
        NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')
    )
"""

LIST_SQL = f"""
SELECT
    h."ID_ghabz"            AS id_ghabz,
    h."GHABZ_NUMBER"        AS ghabz_number,
    h."GHABZ_SEQ"           AS ghabz_seq,
    h."number_ghabz"        AS number_ghabz,
    h."NUMBER_tali"         AS number_tali,
    h."TALI_ID"             AS tali_id,
    h."DATE_UNLOADING"      AS date_unloading,
    h."ID_MARZE"            AS id_marze,
    t_marze."SYS_TERM_VALUE" AS marze_name,
    h."ID_COUNTRY"          AS id_country,
    t_country."SYS_TERM_VALUE" AS country_name,
    h."ID_COMPANY"          AS id_company,
    TRIM(c."COMPANY_NAME") AS company_name,
    h."ID_PRODUCT_OWNEAR"   AS id_product_ownear,
    {OWNER_NAME_SQL}        AS owner_name,
    h."ID_anbar"            AS id_anbar,
    a."NAME_ANBAR"          AS anbar_name,
    u."USERNAME"            AS created_by_username,
    u."FULL_NAME"           AS created_by_full_name
FROM "fa_ghabz_anbar_header" h
LEFT JOIN "FA_SYS_TERMS"              t_marze   ON t_marze."SYS_TERM_ID"   = h."ID_MARZE"
LEFT JOIN "FA_SYS_TERMS"              t_country ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
LEFT JOIN "FA_TRANSPORT_COMPANY"      c         ON c."ID_COMPANY"          = h."ID_COMPANY"
LEFT JOIN "FA_PRODUCT_OWNER"          o         ON o."ID_OWNER"            = h."ID_PRODUCT_OWNEAR"
LEFT JOIN "FA_ANBAR"                  a         ON a."ID_ANBAR"            = h."ID_anbar"
LEFT JOIN "FA_USERS"                  u         ON u."ID"                  = h."CREATE_BY"
WHERE h."IS_DELETED" = 'no'
ORDER BY h."ID_ghabz" DESC
"""

# Header read for the detail screen and, later, the printed sheet. Separate from
# the factory route because GHABZ_NUMBER must never be writable: it is allocated
# server-side, and a model field would expose it to the header form's PUT.
SUMMARY_SQL = f"""
SELECT
    h."ID_ghabz"             AS id_ghabz,
    h."GHABZ_NUMBER"         AS ghabz_number,
    h."GHABZ_SEQ"            AS ghabz_seq,
    h."number_ghabz"         AS number_ghabz,
    h."TALI_ID"              AS tali_id,
    h."NUMBER_tali"          AS number_tali,
    h."NUMBER_KARANEH"       AS number_karaneh,
    h."number_ghabz_uniqe"   AS number_ghabz_uniqe,
    h."number_royea"         AS number_royea,
    h."number_MARZE"         AS number_marze,
    h."TRACKING_NUMBER"      AS tracking_number,
    h."DATE_UNLOADING"       AS date_unloading,
    h."DATE_ENTER_MARZE"     AS date_enter_marze,
    h."ID_MARZE"             AS id_marze,
    t_marze."SYS_TERM_VALUE" AS marze_name,
    h."ID_COUNTRY"           AS id_country,
    t_country."SYS_TERM_VALUE" AS country_name,
    h."ID_COMPANY"           AS id_company,
    TRIM(c."COMPANY_NAME")   AS company_name,
    h."ID_PRODUCT_OWNEAR"    AS id_product_ownear,
    {OWNER_NAME_SQL}         AS owner_name,
    h."ID_anbar"             AS id_anbar,
    a."NAME_ANBAR"           AS anbar_name,
    a."NAME_MASOL"           AS anbar_masol,
    h."NAME_ANBARDAR"        AS name_anbardar,
    h."status_BIMEH"         AS status_bimeh,
    h."NUMBER_BIMEH"         AS number_bimeh,
    h."COMPANY_BIMEH"        AS company_bimeh,
    h."DESCRIPTION"          AS description,
    h."CREATE_AT"            AS create_at,
    u."USERNAME"             AS created_by_username,
    u."FULL_NAME"            AS created_by_full_name
FROM "fa_ghabz_anbar_header" h
LEFT JOIN "FA_SYS_TERMS"         t_marze   ON t_marze."SYS_TERM_ID"   = h."ID_MARZE"
LEFT JOIN "FA_SYS_TERMS"         t_country ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
LEFT JOIN "FA_TRANSPORT_COMPANY" c         ON c."ID_COMPANY"          = h."ID_COMPANY"
LEFT JOIN "FA_PRODUCT_OWNER"     o         ON o."ID_OWNER"            = h."ID_PRODUCT_OWNEAR"
LEFT JOIN "FA_ANBAR"             a         ON a."ID_ANBAR"            = h."ID_anbar"
LEFT JOIN "FA_USERS"             u         ON u."ID"                  = h."CREATE_BY"
WHERE h."ID_ghabz" = :hid AND h."IS_DELETED" = 'no'
"""

DETAILS_SQL = """
SELECT
    d."ID_ghabz_anbar_DETAILS" AS id_ghabz_anbar_details,
    d."ID_GHABZ_ANBAR_HEADAR"  AS id_ghabz_anbar_headar,
    d."code_kala"              AS code_kala,
    d."code_kala_kantiner"     AS code_kala_kantiner,
    d."DESCRIPTION_KALA"       AS description_kala,
    d."HSCODE"                 AS hscode,
    d."TYPE_BASTEh"            AS type_basteh,
    d."NUMBER_KALA"            AS number_kala,
    d."NUMBER_KAntiner"        AS number_kantiner,
    d."WEIGHTE_asnad"          AS weighte_asnad,
    d."WEIGHTE_BASKOL"         AS weighte_baskol,
    d."NUMBER_HAMEL"           AS number_hamel,
    d."ID_TAGH_ANBAR"          AS id_tagh_anbar,
    tg."NAME_TAGH"             AS tagh_name
FROM "FA_ghabz_anbar_DETAILES" d
LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = d."ID_TAGH_ANBAR"
WHERE d."ID_GHABZ_ANBAR_HEADAR" = :hid AND d."IS_DELETED" = 'no'
ORDER BY d."ID_ghabz_anbar_DETAILS"
"""

# One row per goods code on the tally: what the tally allots, what the existing
# receipts already took, and therefore what is still drawable. The descriptive
# columns are a representative value (MIN) because several tally rows can share
# a code while differing in طاق or حامل; the operator can edit the line after.
#
# The issued-sum subqueries mirror TRG_CHK_GHABZ_TALI_LIMIT exactly, including
# its lack of an IS_DELETED filter.
ALLOTMENTS_SQL = """
SELECT
    g.code_kala             AS code_kala,
    g.description_kala      AS description_kala,
    g.hscode                AS hscode,
    g.type_bastem           AS type_bastem,
    g.id_anbar              AS id_anbar,
    a."NAME_ANBAR"          AS anbar_name,
    g.id_tagh_anbar         AS id_tagh_anbar,
    tg."NAME_TAGH"          AS tagh_name,
    g.number_hamel          AS number_hamel,
    g.tally_line_count      AS tally_line_count,
    g.tally_number_kala     AS tally_number_kala,
    g.tally_weighte         AS tally_weighte,
    g.tally_weighte_baskol  AS tally_weighte_baskol,
    NVL((
        SELECT SUM(d."NUMBER_KALA")
        FROM "FA_ghabz_anbar_DETAILES" d
        JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = d."ID_GHABZ_ANBAR_HEADAR"
        WHERE h."TALI_ID" = :tid AND d."code_kala" = g.code_kala
    ), 0) AS issued_number_kala,
    NVL((
        SELECT SUM(d."WEIGHTE_asnad")
        FROM "FA_ghabz_anbar_DETAILES" d
        JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = d."ID_GHABZ_ANBAR_HEADAR"
        WHERE h."TALI_ID" = :tid AND d."code_kala" = g.code_kala
    ), 0) AS issued_weighte_asnad,
    NVL((
        SELECT SUM(d."WEIGHTE_BASKOL")
        FROM "FA_ghabz_anbar_DETAILES" d
        JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = d."ID_GHABZ_ANBAR_HEADAR"
        WHERE h."TALI_ID" = :tid AND d."code_kala" = g.code_kala
    ), 0) AS issued_weighte_baskol
FROM (
    SELECT
        t."CODE_GROUPE_KALA"            AS code_kala,
        MIN(t."DESCRIPTION_KALA")       AS description_kala,
        MIN(t."HSCODE")                 AS hscode,
        MIN(t."TYPE_BASTEM")            AS type_bastem,
        MIN(t."ID_ANBAR")               AS id_anbar,
        MIN(t."ID_TAGH_ANBAR")          AS id_tagh_anbar,
        MIN(t."NUMBER_HAMEL")           AS number_hamel,
        COUNT(*)                        AS tally_line_count,
        NVL(SUM(t."NUMBER_KALA"), 0)    AS tally_number_kala,
        NVL(SUM(t."WEIGHTE"), 0)        AS tally_weighte,
        NVL(SUM(t."WEIGHTE_BASKOL"), 0) AS tally_weighte_baskol
    FROM "FA_TALI_DETAILES" t
    WHERE t."ID_HEADERS_TALI" = :tid
        AND t."IS_DELETED" = 'no'
    GROUP BY t."CODE_GROUPE_KALA"
) g
LEFT JOIN "FA_ANBAR"      a  ON a."ID_ANBAR" = g.id_anbar
LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = g.id_tagh_anbar
ORDER BY g.code_kala
"""

FROM_TALLY_READ = """
SELECT "ID_TALI", "NUMBER_KARANEH", "TALI_NUMBER", "DATE_UNLOADING",
       "DATE_ENTER_MARZE", "ID_MARZE", "ID_COUNTRY", "ID_COMPANY",
       "ID_PRODUCT_OWNEAR", "NAME_ARZYAB", "NAME_ANBARDAR", "IS_BIMEH",
       "NUMBER_BIMEH", "COMPANY_BIMEH", "RADEF_MARZE", "TRACKING_NUMBER",
       "CUSTOMS_PROCEDURE"
FROM "FA_TALI_HEADER" WHERE "ID_TALI" = :tid AND "IS_DELETED" = 'no'
"""

INSERT_GHABZ = """
INSERT INTO "fa_ghabz_anbar_header" (
    "TALI_ID", "NUMBER_tali", "GHABZ_NUMBER", "GHABZ_SEQ",
    "NUMBER_KARANEH", "number_royea", "number_MARZE", "TRACKING_NUMBER",
    "DATE_UNLOADING", "DATE_ENTER_MARZE",
    "ID_MARZE", "ID_COUNTRY", "ID_COMPANY", "ID_PRODUCT_OWNEAR", "ID_anbar",
    "NAME_ANBARDAR", "status_BIMEH", "NUMBER_BIMEH", "COMPANY_BIMEH",
    "IS_DELETED", "CREATE_AT", "CREATE_BY"
) VALUES (
    :tali_id, :number_tali, :ghabz_number, :ghabz_seq,
    :number_karaneh, :number_royea, :number_marze, :tracking_number,
    :date_unloading, :date_enter_marze,
    :id_marze, :id_country, :id_company, :id_product_ownear, :id_anbar,
    :name_anbardar, :status_bimeh, :number_bimeh, :company_bimeh,
    'no', :created_at, :actor_id
) RETURNING "ID_ghabz" INTO :new_id
"""

INSERT_LINE = """
INSERT INTO "FA_ghabz_anbar_DETAILES" (
    "ID_GHABZ_ANBAR_HEADAR", "code_kala", "DESCRIPTION_KALA", "HSCODE",
    "TYPE_BASTEh", "NUMBER_KALA", "WEIGHTE_asnad", "WEIGHTE_BASKOL",
    "NUMBER_HAMEL", "ID_TAGH_ANBAR", "IS_DELETED", "CREATE_AT", "CREATE_BY"
) VALUES (
    :header_id, :code_kala, :description_kala, :hscode,
    :type_basteh, :number_kala, :weighte_asnad, :weighte_baskol,
    :number_hamel, :id_tagh_anbar, 'no', :created_at, :actor_id
)
"""


def _rows_with_columns(cursor) -> list[dict]:
    columns = [column[0].lower() for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]







def _returned_int(value) -> int:
    result = value.getvalue()
    if isinstance(result, (list, tuple)):
        result = result[0]
    return int(result)


def _as_date(value):
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value).date()
    return value


def _trigger_message(exc: oracledb.DatabaseError) -> str | None:
    """Surface the trigger's own Persian text instead of a raw ORA- dump."""
    text = str(exc)
    for code in ("ORA-20001", "ORA-20002", "ORA-20003", "ORA-20010", "ORA-20011"):
        if code in text:
            fragment = text.split(code + ":", 1)[1]
            return fragment.split("ORA-")[0].strip()
    if "FA_CON_" in text and "ORA-00001" in text:
        return "برای هر کد کالا فقط یک ردیف در هر قبض انبار مجاز است."
    return None


@router.get("/list", dependencies=[Depends(get_current_user)])
def list_ghabz():
    return fetch_all(LIST_SQL)


@router.get("/from-tally/{tali_id}/allotments", dependencies=[Depends(get_current_user)])
def list_ghabz_allotments(tali_id: int):
    """Per goods code: tally allotment, already issued, and what remains."""
    return annotate(fetch_all(ALLOTMENTS_SQL, {"tid": tali_id}))


@router.get("/{header_id}/summary", dependencies=[Depends(get_current_user)])
def get_ghabz_summary(header_id: int):
    """One receipt's header with FK names resolved, for the detail and print screens."""
    rows = fetch_all(SUMMARY_SQL, {"hid": header_id})
    if not rows:
        raise HTTPException(status_code=404, detail="قبض انبار یافت نشد")
    return rows[0]


@router.get("/{header_id}/details", dependencies=[Depends(get_current_user)])
def list_ghabz_details(header_id: int):
    return fetch_all(DETAILS_SQL, {"hid": header_id})


@router.post("/from-tally/{tali_id}", status_code=201)
def create_ghabz_from_tally(
    tali_id: int,
    selection: GhabzFromTallyInput | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Issue one receipt, drawing quantities per goods code against the tally."""
    requested = selection.lines if selection is not None else None

    with get_connection() as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(FROM_TALLY_READ, {"tid": tali_id})
                tally_rows = _rows_with_columns(cursor)
                if not tally_rows:
                    raise HTTPException(status_code=404, detail="تالی یافت نشد")
                tally = tally_rows[0]

                cursor.execute(ALLOTMENTS_SQL, {"tid": tali_id})
                allotments = _rows_with_columns(cursor)
                by_code = {
                    row["code_kala"]: row
                    for row in allotments
                    if row["code_kala"] is not None
                }

                lines = plan_lines(requested, allotments, by_code)

                ghabz_number, sequence, tali_number = allocate_ghabz_number(
                    cursor, tali_id
                )

                cursor.execute("SELECT SYSDATE FROM DUAL")
                created_at = cursor.fetchone()[0]

                new_id_var = cursor.var(int)
                cursor.execute(
                    INSERT_GHABZ,
                    {
                        "tali_id": tali_id,
                        "number_tali": tali_number,
                        "ghabz_number": ghabz_number,
                        "ghabz_seq": sequence,
                        "number_karaneh": tally.get("number_karaneh"),
                        "number_royea": tally.get("customs_procedure"),
                        "number_marze": tally.get("radef_marze"),
                        "tracking_number": tally.get("tracking_number"),
                        "date_unloading": _as_date(tally.get("date_unloading")),
                        "date_enter_marze": _as_date(tally.get("date_enter_marze")),
                        "id_marze": tally.get("id_marze"),
                        "id_country": tally.get("id_country"),
                        "id_company": tally.get("id_company"),
                        "id_product_ownear": tally.get("id_product_ownear"),
                        "id_anbar": shared_anbar(
                            [by_code[line["code_kala"]] for line in lines]
                        ),
                        "name_anbardar": tally.get("name_anbardar"),
                        "status_bimeh": tally.get("is_bimeh"),
                        "number_bimeh": tally.get("number_bimeh"),
                        "company_bimeh": tally.get("company_bimeh"),
                        "created_at": created_at,
                        "actor_id": current_user["id"],
                        "new_id": new_id_var,
                    },
                )
                new_id = _returned_int(new_id_var)

                cursor.executemany(
                    INSERT_LINE,
                    [
                        {
                            "header_id": new_id,
                            "created_at": created_at,
                            "actor_id": current_user["id"],
                            **line,
                        }
                        for line in lines
                    ],
                )

            conn.commit()
            return {
                "id_ghabz": new_id,
                "ghabz_number": ghabz_number,
                "ghabz_seq": sequence,
                "line_count": len(lines),
            }
        except HTTPException:
            conn.rollback()
            raise
        except TallyNotFound as exc:
            conn.rollback()
            raise HTTPException(status_code=404, detail="تالی یافت نشد") from exc
        except TallyNotNumbered as exc:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail="این تالی شماره ندارد و نمی‌توان برای آن قبض انبار صادر کرد.",
            ) from exc
        except oracledb.DatabaseError as exc:
            conn.rollback()
            message = _trigger_message(exc)
            if message:
                raise HTTPException(status_code=400, detail=message) from exc
            raise HTTPException(
                status_code=500,
                detail="تخصیص شماره و صدور قبض انبار ناموفق بود.",
            ) from exc
        except ValueError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=500,
                detail="تخصیص شماره و صدور قبض انبار ناموفق بود.",
            ) from exc
