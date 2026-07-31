"""
قبض انبار (warehouse receipt) reads that go beyond the generic factory:
  GET /ghabz/list          - all receipts, FK names resolved (border/country/company/owner/anbar)
  GET /ghabz/{id}/details  - one receipt's line items

Plus the create-from-tally convenience:
  POST /ghabz/from-tally/{tali_id} - a new receipt pre-filled from a tally's header

Writes go through the factory routers (/ghabz-header, /ghabz-details).
"""
from fastapi import APIRouter, Depends
from app.auth.deps import get_current_user
from app.services.base import fetch_all, fetch_one, insert_returning_id

router = APIRouter(prefix="/ghabz", tags=["ghabz"])

# soft-delete filtered the app's way; exact-case identifiers throughout.
LIST_SQL = """
SELECT
    h."ID_ghabz"            AS id_ghabz,
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
    CASE
        WHEN o."TYPE" = 'حقوقی' THEN TRIM(o."COMPANY_NAME")
        ELSE TRIM(o."NAME" || ' ' || o."FAMILY")
    END AS owner_name,
    h."ID_anbar"            AS id_anbar,
    a."NAME_ANBAR"          AS anbar_name
FROM "fa_ghabz_anbar_header" h
LEFT JOIN "FA_SYS_TERMS"              t_marze   ON t_marze."SYS_TERM_ID"   = h."ID_MARZE"
LEFT JOIN "FA_SYS_TERMS"              t_country ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
LEFT JOIN "FA_TRANSPORT_COMPANY"      c         ON c."ID_COMPANY"          = h."ID_COMPANY"
LEFT JOIN "FA_PRODUCT_OWNER"          o         ON o."ID_OWNER"            = h."ID_PRODUCT_OWNEAR"
LEFT JOIN "FA_ANBAR"                  a         ON a."ID_ANBAR"            = h."ID_anbar"
WHERE h."IS_DELETED" = 'no'
ORDER BY h."ID_ghabz" DESC
"""

DETAILS_SQL = """
SELECT
    d."ID_ghabz_anbar_DETAILS" AS id_ghabz_anbar_details,
    d."ID_GHABZ_ANBAR_HEADAR"  AS id_ghabz_anbar_headar,
    d."code_kala"              AS code_kala,
    d."code_kala_kantiner"     AS code_kala_kantiner,
    d."DESCRIPTION_KALA"       AS description_kala,
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

# --- create a receipt pre-filled from a tally's header ---
# There's no copy-process in the original, so this fills the fields that overlap
# between FA_TALI_HEADER and fa_ghabz_anbar_header. The user then completes/edits.
FROM_TALLY_READ = """
SELECT "ID_TALI", "NUMBER_KARANEH", "TALI_NUMBER", "DATE_UNLOADING",
       "DATE_ENTER_MARZE", "ID_MARZE", "ID_COUNTRY", "ID_COMPANY",
       "ID_PRODUCT_OWNEAR", "NAME_ARZYAB", "NAME_ANBARDAR", "IS_BIMEH", "NUMBER_BIMEH"
FROM "FA_TALI_HEADER" WHERE "ID_TALI" = :tid AND "IS_DELETED" = 'no'
"""

INSERT_GHABZ = """
INSERT INTO "fa_ghabz_anbar_header" (
    "ID_ghabz", "TALI_ID", "NUMBER_tali", "NUMBER_KARANEH", "DATE_UNLOADING",
    "DATE_ENTER_MARZE", "ID_MARZE", "ID_COUNTRY", "ID_COMPANY", "ID_PRODUCT_OWNEAR",
    "NAME_ANBARDAR", "status_BIMEH", "NUMBER_BIMEH", "IS_DELETED", "CREATE_AT", "CREATE_BY"
) VALUES (
    (SELECT NVL(MAX("ID_ghabz"), 0) + 1 FROM "fa_ghabz_anbar_header"),
    :tali_id, :number_tali, :number_karaneh, :date_unloading,
    :date_enter_marze, :id_marze, :id_country, :id_company, :id_product_ownear,
    :name_anbardar, :status_bimeh, :number_bimeh, 'no', SYSDATE, :actor_id
) RETURNING "ID_ghabz" INTO :new_id
"""



@router.get("/list", dependencies=[Depends(get_current_user)])
def list_ghabz():
    return fetch_all(LIST_SQL)


@router.get("/{header_id}/details", dependencies=[Depends(get_current_user)])
def list_ghabz_details(header_id: int):
    return fetch_all(DETAILS_SQL, {"hid": header_id})

@router.post("/from-tally/{tali_id}", status_code=201, dependencies=[Depends(get_current_user)])
def create_ghabz_from_tally(tali_id: int, current_user: dict = Depends(get_current_user)):
    tally = fetch_one(FROM_TALLY_READ, {"tid": tali_id})
    if tally is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    params = {
        "tali_id": tali_id,
        "number_tali": tally.get("tali_number"),
        "number_karaneh": tally.get("number_karaneh"),
        "date_unloading": tally.get("date_unloading"),
        "date_enter_marze": tally.get("date_enter_marze"),
        "id_marze": tally.get("id_marze"),
        "id_country": tally.get("id_country"),
        "id_company": tally.get("id_company"),
        "id_product_ownear": tally.get("id_product_ownear"),
        "name_anbardar": tally.get("name_anbardar"),
        "status_bimeh": tally.get("is_bimeh"),
        "number_bimeh": tally.get("number_bimeh"),
        "actor_id": current_user["id"],
    }
    new_id = insert_returning_id(INSERT_GHABZ, params)
    return {"id_ghabz": new_id}
