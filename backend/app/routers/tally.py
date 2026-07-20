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

Writes for both the header and the detail lines still go through the factory
routers (/tally-header and /tally-details). This router is read-only enrichment.
"""
from fastapi import APIRouter, Depends
from app.auth.deps import get_current_user
from app.services.base import fetch_all

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
    (c_comp."NAME" || ' ' || c_comp."FAMILY")   AS company_name,
    h."ID_PRODUCT_OWNEAR"               AS id_product_ownear,
    (o."NAME" || ' ' || o."FAMILY")     AS owner_name
FROM "FA_TALI_HEADER" h
LEFT JOIN "FA_SYS_TERMS"              t_marze   ON t_marze."SYS_TERM_ID"   = h."ID_MARZE"
LEFT JOIN "FA_SYS_TERMS"              t_country ON t_country."SYS_TERM_ID" = h."ID_COUNTRY"
LEFT JOIN "FA_REPRESENTATIVE_COMPANY" c_comp    ON c_comp."ID_REPRE_COMPANY" = h."ID_COMPANY"
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


@router.get("/list", dependencies=[Depends(get_current_user)])
def list_tallies():
    return fetch_all(LIST_SQL)


@router.get("/{header_id}/details", dependencies=[Depends(get_current_user)])
def list_tally_details(header_id: int):
    return fetch_all(DETAILS_SQL, {"hid": header_id})

# --- one tally's diamound-rate entries, catalog title/code resolved ---
DIAMOUND_SQL = """
SELECT
    j."id_tali_kala_diamound"           AS id_tali_kala_diamound,
    j."tali_id"                         AS tali_id,
    j."kala_diamound_id"                AS kala_diamound_id,
    j."code"                            AS code,
    j."DESCRIPTION"                     AS description,
    k."title"                           AS rate_title,
    k."code"                            AS rate_code
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
       j."kala_strip_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
       j."pricing_type" AS pricing_type,
       k."code" AS rate_code, k."title" AS rate_title
FROM "fa_tali_kala_strip" j
LEFT JOIN "fa_kala_strip" k ON k."id_kala_strip" = j."kala_strip_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_strip"
"""

TIME_STOP_SQL = """
SELECT j."id_tali_kala_time_stop_vehicle" AS id, j."tali_id" AS tali_id,
       j."kala_time_stop_vehicle_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
       k."code" AS rate_code, k."title" AS rate_title
FROM "fa_tali_kala_time_stop_vehicle" j
LEFT JOIN "fa_kala_time_stop_vehicle" k ON k."id_kala_time_stop_vehicle" = j."kala_time_stop_vehicle_id"
WHERE j."tali_id" = :hid AND j."IS_DELETED" = 'no'
ORDER BY j."id_tali_kala_time_stop_vehicle"
"""

VEHICLE_ENTER_SQL = """
SELECT j."id_tali_kala_vehicle_enter_price" AS id, j."tali_id" AS tali_id,
       j."kala_vehicle_enter_price_id" AS rate_id, j."code" AS code, j."DESCRIPTION" AS description,
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