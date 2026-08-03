# """
# Tally-specific endpoints that go beyond the generic CRUD factory.

# Two hand-written reads live here (the factory only does single-table SELECT *):
#   GET /tally/list           - all active tallies, with FK names resolved (border,
#                               country, company, owner) for the list screen.
#   GET /tally/{id}/details   - one tally's goods lines, with anbar/tagh names, for
#                               the master-detail view.

# Writes for both the header and the detail lines still go through the factory
# routers (/tally-header and /tally-details). This router is read-only enrichment.
# """
# from fastapi import APIRouter, Depends
# from app.auth.deps import get_current_user
# from app.services.base import fetch_all

# router = APIRouter(prefix="/tally", tags=["tally"])

# # Every identifier quoted with its EXACT stored case (same rule as the factory),
# # and soft-delete filtered the app's way: IS_DELETED = 'no' means active.

# # --- the tally list, FK ids resolved to names ---
# # Border and country both live in FA_SYS_TERMS, so it's joined twice.
# LIST_SQL = """
# SELECT
#     h."ID_TALI"                         AS id_tali,
#     h."TALI_NUMBER"                     AS tali_number,
#     h."RADEF_MARZE"                     AS radef_marze,
#     h."DATE_ENTER_MARZE"                AS date_enter_marze,
#     h."DATE_UNLOADING"                  AS date_unloading,
#     h."IS_BIMEH"                        AS is_bimeh,
#     h."ID_MARZE"                        AS id_marze,
#     t_marze."SYS_TERM_VALUE"            AS marze_name,
#     h."ID_COUNTRY"                      AS id_country,
#     t_country."SYS_TERM_VALUE"          AS country_name,
#     h."ID_COMPANY"                      AS id_company,
#     (c_comp."NAME" || ' ' || c_comp."FAMILY")   AS company_name,
#     h."ID_PRODUCT_OWNEAR"               AS id_product_ownear,
#     (o."NAME" || ' ' || o."FAMILY")     AS owner_name
# FROM "FA_TALI_HEADER" h
# LEFT JOIN "FA_SYS_TERMS"              t_marze   ON t_marze."SYS_TERM_ID"   = h."ID_MARZE"
# LEFT JOIN "FA_SYS_TERMS"              t_country ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
# LEFT JOIN "FA_REPRESENTATIVE_COMPANY" c_comp    ON c_comp."ID_REPRE_COMPANY" = h."ID_COMPANY"
# LEFT JOIN "FA_PRODUCT_OWNER"          o         ON o."ID_OWNER"           = h."ID_PRODUCT_OWNEAR"
# WHERE h."IS_DELETED" = 'no'
# ORDER BY h."ID_TALI" DESC
# """

# # --- one header's goods lines, anbar/tagh names resolved ---
# DETAILS_SQL = """
# SELECT
#     d."ID_TALI_DETAILS"                 AS id_tali_details,
#     d."ID_HEADERS_TALI"                 AS id_headers_tali,
#     d."ID_ANBAR"                        AS id_anbar,
#     a."NAME_ANBAR"                            AS anbar_name,
#     d."ID_TAGH_ANBAR"                   AS id_tagh_anbar,
#     tg."NAME_TAGH"                      AS tagh_name,
#     d."NUMBER_GHABZE_ANBAR"             AS number_ghabze_anbar,
#     d."CODE_GROUPE_KALA"                AS code_groupe_kala,
#     d."DESCRIPTION_KALA"                AS description_kala,
#     d."HSCODE"                          AS hscode,
#     d."TYPE_BASTEM"                     AS type_bastem,
#     d."NUMBER_KALA"                     AS number_kala,
#     d."WEIGHTE"                         AS weighte,
#     d."TYPE_NUMBER_KANTINER"            AS type_number_kantiner,
#     d."NUMBER_GHABZE_BSKOL"             AS number_ghabze_bskol,
#     d."WEIGHTE_BASKOL"                  AS weighte_baskol,
#     d."NUMBER_HAMEL"                    AS number_hamel,
#     d."ZARIB_MAHAL"                     AS zarib_mahal,
#     d."CONTAINER_TYPE"                  AS container_type,
#     d."CONTAINER_NUMBER"                AS container_number
# FROM "FA_TALI_DETAILES" d
# LEFT JOIN "FA_ANBAR"      a  ON a."ID_ANBAR"  = d."ID_ANBAR"
# LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = d."ID_TAGH_ANBAR"
# WHERE d."ID_HEADERS_TALI" = :hid
#   AND d."IS_DELETED" = 'no'
# ORDER BY d."ID_TALI_DETAILS"
# """


# @router.get("/list", dependencies=[Depends(get_current_user)])
# def list_tallies():
#     return fetch_all(LIST_SQL)


# @router.get("/{header_id}/details", dependencies=[Depends(get_current_user)])
# def list_tally_details(header_id: int):
#     return fetch_all(DETAILS_SQL, {"hid": header_id})

# # --- one tally's diamound-rate entries, catalog title/code resolved ---
# DIAMOUND_SQL = """
# SELECT
#     j."id_tali_kala_diamound"           AS id_tali_kala_diamound,
#     j."tali_id"                         AS tali_id,
#     j."kala_diamound_id"                AS kala_diamound_id,
#     j."code"                            AS code,
#     j."DESCRIPTION"                     AS description,
#     k."title"                           AS rate_title,
#     k."code"                            AS rate_code
# FROM "fa_tali_kala_diamound" j
# LEFT JOIN "fa_kala_diamound" k ON k."id_kala_diamound" = j."kala_diamound_id"
# WHERE j."tali_id" = :hid
#   AND j."IS_DELETED" = 'no'
# ORDER BY j."id_tali_kala_diamound"
# """


# @router.get("/{header_id}/diamound", dependencies=[Depends(get_current_user)])
# def list_tally_diamound(header_id: int):
#     return fetch_all(DIAMOUND_SQL, {"hid": header_id})

# PRICE_SQL = """
# SELECT j."id_tali_kala_price" AS id, j."tali_id" AS tali_id,
#        j."kala_price_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
#        k."CODE" AS rate_code, k."DESCRIPTION" AS rate_title
# FROM "fa_tali_kala_price" j
# LEFT JOIN "fa_kala_price" k ON k."id_kala_price" = j."kala_price_id"
# WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
# ORDER BY j."id_tali_kala_price"
# """

# DANGEROUS_SQL = """
# SELECT j."id_tali_kala_dangerous" AS id, j."tali_id" AS tali_id,
#        j."kala_dangerous_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
#        k."code" AS rate_code, k."TITLE" AS rate_title
# FROM "fa_tali_kala_dangerous" j
# LEFT JOIN "fa_kala_dangerous" k ON k."id_kala_dangerous" = j."kala_dangerous_id"
# WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
# ORDER BY j."id_tali_kala_dangerous"
# """

# OTHER_SERVICE_SQL = """
# SELECT j."id_tali_kala_other_service" AS id, j."tali_id" AS tali_id,
#        j."kala_other_service_id" AS rate_id, j."code" AS code,
#        j."NUMBER_SERVICE" AS number_service, j."DESCRIPTION" AS description,
#        k."code" AS rate_code, k."title" AS rate_title
# FROM "fa_tali_kala_other_service" j
# LEFT JOIN "fa_kala_other_service" k ON k."id_kala_other_service" = j."kala_other_service_id"
# WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
# ORDER BY j."id_tali_kala_other_service"
# """

# STRIP_SQL = """
# SELECT j."id_tali_kala_strip" AS id, j."tali_id" AS tali_id,
#        j."kala_strip_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
#        k."code" AS rate_code, k."title" AS rate_title
# FROM "fa_tali_kala_strip" j
# LEFT JOIN "fa_kala_strip" k ON k."id_kala_strip" = j."kala_strip_id"
# WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
# ORDER BY j."id_tali_kala_strip"
# """

# TIME_STOP_SQL = """
# SELECT j."id_tali_kala_time_stop_vehicle" AS id, j."tali_id" AS tali_id,
#        j."kala_time_stop_vehicle_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
#        k."code" AS rate_code, k."title" AS rate_title
# FROM "fa_tali_kala_time_stop_vehicle" j
# LEFT JOIN "fa_kala_time_stop_vehicle" k ON k."id_kala_time_stop_vehicle" = j."kala_time_stop_vehicle_id"
# WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
# ORDER BY j."id_tali_kala_time_stop_vehicle"
# """

# VEHICLE_ENTER_SQL = """
# SELECT j."id_tali_kala_vehicle_enter_price" AS id, j."tali_id" AS tali_id,
#        j."kala_vehicle_enter_price_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
#        k."code" AS rate_code, k."title" AS rate_title
# FROM "fa_tali_kala_vehicle_enter_price" j
# LEFT JOIN "fa_kala_vehicle_enter_price" k ON k."id_kala_vehicle_enter_price" = j."kala_vehicle_enter_price_id"
# WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
# ORDER BY j."id_tali_kala_vehicle_enter_price"
# """


# @router.get("/{header_id}/price", dependencies=[Depends(get_current_user)])
# def list_tally_price(header_id: int):
#     return fetch_all(PRICE_SQL, {"hid": header_id})

# @router.get("/{header_id}/dangerous", dependencies=[Depends(get_current_user)])
# def list_tally_dangerous(header_id: int):
#     return fetch_all(DANGEROUS_SQL, {"hid": header_id})

# @router.get("/{header_id}/other-service", dependencies=[Depends(get_current_user)])
# def list_tally_other_service(header_id: int):
#     return fetch_all(OTHER_SERVICE_SQL, {"hid": header_id})

# @router.get("/{header_id}/strip", dependencies=[Depends(get_current_user)])
# def list_tally_strip(header_id: int):
#     return fetch_all(STRIP_SQL, {"hid": header_id})

# @router.get("/{header_id}/time-stop", dependencies=[Depends(get_current_user)])
# def list_tally_time_stop(header_id: int):
#     return fetch_all(TIME_STOP_SQL, {"hid": header_id})

# @router.get("/{header_id}/vehicle-enter", dependencies=[Depends(get_current_user)])
# def list_tally_vehicle_enter(header_id: int):
#     return fetch_all(VEHICLE_ENTER_SQL, {"hid": header_id})

"""
Tally-specific endpoints that go beyond the generic CRUD factory.

Two hand-written reads live here (the factory only does single-table SELECT *):
  GET /tally/list           - all active tallies, with FK names resolved (border,
                              country, company, owner) for the list screen.
  GET /tally/{id}/details   - one tally's goods lines, with anbar/tagh names, for
                              the master-detail view.

Header writes go through the dedicated /tally-header router so its business
number can be allocated atomically. Detail-line writes still use the generic
/tally-details router. This router contains read-only enrichment.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import get_current_user
from app.services.base import fetch_all, fetch_one

router = APIRouter(prefix="/tally", tags=["tally"])

# Every identifier quoted with its EXACT stored case (same rule as the factory),
# and soft-delete filtered the app's way: IS_DELETED = 'no' means active.

# --- the tally list, FK ids resolved to names ---
# Border and country both live in FA_SYS_TERMS, so it's joined twice.
LIST_SQL = """
SELECT
    h."ID_TALI"                         AS id_tali,
    h."TALI_NUMBER"                     AS tali_number,
    h."RADEF_MARZE"                     AS radef_marze,
    h."DATE_ENTER_MARZE"                AS date_enter_marze,
    h."DATE_UNLOADING"                  AS date_unloading,
    h."IS_BIMEH"                        AS is_bimeh,
    h."ID_MARZE"                        AS id_marze,
    t_marze."SYS_TERM_VALUE"            AS marze_name,
    h."ID_COUNTRY"                      AS id_country,
    t_country."SYS_TERM_VALUE"          AS country_name,
    h."ID_COMPANY"                      AS id_company,
    TRIM(c_comp."COMPANY_NAME")         AS company_name,
    h."ID_PRODUCT_OWNEAR"               AS id_product_ownear,
    CASE
        WHEN o."TYPE" = 'حقوقی' THEN TRIM(o."COMPANY_NAME")
        ELSE TRIM(o."NAME" || ' ' || o."FAMILY")
    END                                  AS owner_name,
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
    END                                  AS workflow_status
FROM "FA_TALI_HEADER" h
LEFT JOIN "FA_SYS_TERMS"              t_marze   ON t_marze."SYS_TERM_ID"   = h."ID_MARZE"
LEFT JOIN "FA_SYS_TERMS"              t_country ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
LEFT JOIN "FA_TRANSPORT_COMPANY"      c_comp    ON c_comp."ID_COMPANY"       = h."ID_COMPANY"
LEFT JOIN "FA_PRODUCT_OWNER"          o         ON o."ID_OWNER"           = h."ID_PRODUCT_OWNEAR"
WHERE h."IS_DELETED" = 'no'
ORDER BY h."ID_TALI" DESC
"""

# --- one header's goods lines, anbar/tagh names resolved ---
DETAILS_SQL = """
SELECT
    d."ID_TALI_DETAILS"                 AS id_tali_details,
    d."ID_HEADERS_TALI"                 AS id_headers_tali,
    d."ID_ANBAR"                        AS id_anbar,
    a."NAME_ANBAR"                            AS anbar_name,
    d."ID_TAGH_ANBAR"                   AS id_tagh_anbar,
    tg."NAME_TAGH"                      AS tagh_name,
    d."NUMBER_GHABZE_ANBAR"             AS number_ghabze_anbar,
    d."CODE_GROUPE_KALA"                AS code_groupe_kala,
    d."DESCRIPTION_KALA"                AS description_kala,
    d."HSCODE"                          AS hscode,
    d."TYPE_BASTEM"                     AS type_bastem,
    d."NUMBER_KALA"                     AS number_kala,
    d."NUMBER_PALLET"                   AS number_pallet,
    d."VALUE_KALA"                      AS value_kala,
    d."CUSTOMS_VALUE"                   AS customs_value,
    d."INSURED_VALUE"                   AS insured_value,
    d."INSURANCE_EXPIRY_DATE"           AS insurance_expiry_date,
    d."WEIGHTE"                         AS weighte,
    d."TYPE_NUMBER_KANTINER"            AS type_number_kantiner,
    d."NUMBER_GHABZE_BSKOL"             AS number_ghabze_bskol,
    d."WEIGHTE_BASKOL"                  AS weighte_baskol,
    d."NUMBER_HAMEL"                    AS number_hamel,
    d."ZARIB_MAHAL"                     AS zarib_mahal,
    d."CONTAINER_TYPE"                  AS container_type,
    d."CONTAINER_NUMBER"                AS container_number
FROM "FA_TALI_DETAILES" d
LEFT JOIN "FA_ANBAR"      a  ON a."ID_ANBAR"  = d."ID_ANBAR"
LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = d."ID_TAGH_ANBAR"
WHERE d."ID_HEADERS_TALI" = :hid
  AND d."IS_DELETED" = 'no'
ORDER BY d."ID_TALI_DETAILS"
"""

# All display values needed by the landscape A4 tally print form. The normal
# tally-header endpoint intentionally returns raw foreign keys; printing needs
# the resolved border/country/company/owner labels. The owner's national ID is
# an independent, user-entered value stored on the tally header itself.
PRINT_HEADER_SQL = """
SELECT
    h."ID_TALI"                         AS id_tali,
    h."TALI_NUMBER"                     AS tali_number,
    h."NUMBER_KARANEH"                  AS number_karaneh,
    h."RADEF_MARZE"                     AS radef_marze,
    h."DATE_ENTER_MARZE"                AS date_enter_marze,
    h."DATE_UNLOADING"                  AS date_unloading,
    h."NUMBER_BIMEH"                    AS number_bimeh,
    h."NUMBER_BARNAMEH"                 AS number_barnameh,
    h."NAME_ARZYAB"                     AS name_arzyab,
    h."IS_BIMEH"                        AS is_bimeh,
    h."NAME_ANBARDAR"                   AS name_anbardar,
    h."ACCEPTED_GOMROK"                 AS accepted_gomrok,
    h."COMPANY_BIMEH"                   AS company_bimeh,
    h."DESCRIPTION"                     AS description,
    h."OWNER_NATIONAL_CODE"             AS owner_national_code,
    t_marze."SYS_TERM_VALUE"            AS marze_name,
    t_country."SYS_TERM_VALUE"          AS country_name,
    TRIM(c_comp."COMPANY_NAME")         AS company_name,
    TRIM(c_resp."NAME" || ' ' || c_resp."FAMILY") AS representative_name,
    CASE
        WHEN o."TYPE" = 'حقوقی' THEN TRIM(o."COMPANY_NAME")
        ELSE TRIM(o."NAME" || ' ' || o."FAMILY")
    END                                  AS owner_name
FROM "FA_TALI_HEADER" h
LEFT JOIN "FA_SYS_TERMS" t_marze
       ON t_marze."SYS_TERM_ID" = h."ID_MARZE"
LEFT JOIN "FA_SYS_TERMS" t_country
       ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
LEFT JOIN "FA_TRANSPORT_COMPANY" c_comp
       ON c_comp."ID_COMPANY" = h."ID_COMPANY"
LEFT JOIN "FA_REPRESENTATIVE_COMPANY" c_resp
       ON c_resp."ID_REPRE_COMPANY" = h."ID_RESPONS_COMPANY"
LEFT JOIN "FA_PRODUCT_OWNER" o
       ON o."ID_OWNER" = h."ID_PRODUCT_OWNEAR"
WHERE h."ID_TALI" = :hid
  AND h."IS_DELETED" = 'no'
"""


@router.get("/list", dependencies=[Depends(get_current_user)])
def list_tallies():
    return fetch_all(LIST_SQL)


@router.get("/{header_id}/details", dependencies=[Depends(get_current_user)])
def list_tally_details(header_id: int):
    return fetch_all(DETAILS_SQL, {"hid": header_id})


@router.get("/{header_id}/print")
def get_tally_print_data(
    header_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Return one print-ready tally with resolved header labels and goods rows."""
    header = fetch_one(PRINT_HEADER_SQL, {"hid": header_id})
    if header is None:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    header["print_user_name"] = (
        current_user.get("full_name") or current_user.get("username") or ""
    )
    header["details"] = fetch_all(DETAILS_SQL, {"hid": header_id})
    return header

# --- one tally's diamound-rate entries, catalog title/code resolved ---
DIAMOUND_SQL = """
SELECT
    j."id_tali_kala_diamound"           AS id,
    j."tali_id"                         AS tali_id,
    j."kala_diamound_id"                AS rate_id,
    j."code"                            AS code,
    j."NUMBER_SERVICE"                  AS number_service,
    j."DESCRIPTION"                     AS description,
    NVL(j."pricing_type", 'off_hours')  AS pricing_type,
    k."title"                           AS rate_title,
    k."code"                            AS rate_code,
    CASE NVL(j."pricing_type", 'off_hours')
        WHEN 'holiday' THEN k."price_holiday"
        ELSE k."price_gher_edari"
    END                                 AS selected_price
FROM "fa_tali_kala_diamound" j
LEFT JOIN "fa_kala_diamound" k ON k."id_kala_diamound" = j."kala_diamound_id"
WHERE j."tali_id" = :hid
  AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_diamound"
"""


@router.get("/{header_id}/diamound", dependencies=[Depends(get_current_user)])
def list_tally_diamound(header_id: int):
    return fetch_all(DIAMOUND_SQL, {"hid": header_id})

PRICE_SQL = """
SELECT j."id_tali_kala_price" AS id, j."tali_id" AS tali_id,
       j."kala_price_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
       k."CODE" AS rate_code, k."DESCRIPTION" AS rate_title
FROM "fa_tali_kala_price" j
LEFT JOIN "fa_kala_price" k ON k."id_kala_price" = j."kala_price_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_price"
"""

DANGEROUS_SQL = """
SELECT j."id_tali_kala_dangerous" AS id, j."tali_id" AS tali_id,
       j."kala_dangerous_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
       k."code" AS rate_code, k."TITLE" AS rate_title
FROM "fa_tali_kala_dangerous" j
LEFT JOIN "fa_kala_dangerous" k ON k."id_kala_dangerous" = j."kala_dangerous_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_dangerous"
"""

OTHER_SERVICE_SQL = """
SELECT j."id_tali_kala_other_service" AS id, j."tali_id" AS tali_id,
       j."kala_other_service_id" AS rate_id, j."code" AS code,
       j."NUMBER_SERVICE" AS number_service, j."DESCRIPTION" AS description,
       k."code" AS rate_code, k."title" AS rate_title
FROM "fa_tali_kala_other_service" j
LEFT JOIN "fa_kala_other_service" k ON k."id_kala_other_service" = j."kala_other_service_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_other_service"
"""

STRIP_SQL = """
SELECT j."id_tali_kala_strip" AS id, j."tali_id" AS tali_id,
       j."kala_strip_id" AS rate_id, j."code" AS code,
       j."NUMBER_SERVICE" AS number_service, j."DESCRIPTION" AS description,
       j."pricing_type" AS pricing_type,
       k."code" AS rate_code, k."title" AS rate_title
FROM "fa_tali_kala_strip" j
LEFT JOIN "fa_kala_strip" k ON k."id_kala_strip" = j."kala_strip_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_strip"
"""

TIME_STOP_SQL = """
SELECT j."id_tali_kala_time_stop_vehicle" AS id, j."tali_id" AS tali_id,
       j."kala_time_stop_vehicle_id" AS rate_id, j."code" AS code,
       j."NUMBER_SERVICE" AS number_service, j."DESCRIPTION" AS description,
       k."code" AS rate_code, k."title" AS rate_title
FROM "fa_tali_kala_time_stop_vehicle" j
LEFT JOIN "fa_kala_time_stop_vehicle" k ON k."id_kala_time_stop_vehicle" = j."kala_time_stop_vehicle_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_time_stop_vehicle"
"""

VEHICLE_ENTER_SQL = """
SELECT j."id_tali_kala_vehicle_enter_price" AS id, j."tali_id" AS tali_id,
       j."kala_vehicle_enter_price_id" AS rate_id, j."code" AS code,
       j."NUMBER_SERVICE" AS number_service, j."DESCRIPTION" AS description,
       k."code" AS rate_code, k."title" AS rate_title
FROM "fa_tali_kala_vehicle_enter_price" j
LEFT JOIN "fa_kala_vehicle_enter_price" k ON k."id_kala_vehicle_enter_price" = j."kala_vehicle_enter_price_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_vehicle_enter_price"
"""


@router.get("/{header_id}/price", dependencies=[Depends(get_current_user)])
def list_tally_price(header_id: int):
    return fetch_all(PRICE_SQL, {"hid": header_id})

@router.get("/{header_id}/dangerous", dependencies=[Depends(get_current_user)])
def list_tally_dangerous(header_id: int):
    return fetch_all(DANGEROUS_SQL, {"hid": header_id})

@router.get("/{header_id}/other-service", dependencies=[Depends(get_current_user)])
def list_tally_other_service(header_id: int):
    return fetch_all(OTHER_SERVICE_SQL, {"hid": header_id})

@router.get("/{header_id}/strip", dependencies=[Depends(get_current_user)])
def list_tally_strip(header_id: int):
    return fetch_all(STRIP_SQL, {"hid": header_id})

@router.get("/{header_id}/time-stop", dependencies=[Depends(get_current_user)])
def list_tally_time_stop(header_id: int):
    return fetch_all(TIME_STOP_SQL, {"hid": header_id})

@router.get("/{header_id}/vehicle-enter", dependencies=[Depends(get_current_user)])
def list_tally_vehicle_enter(header_id: int):
    return fetch_all(VEHICLE_ENTER_SQL, {"hid": header_id})
