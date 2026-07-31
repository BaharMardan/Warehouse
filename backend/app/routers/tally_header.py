# """Dedicated CRUD endpoints for the tally header.

# Creation is intentionally not handled by the generic CRUD factory: ID_TALI
# comes from an Oracle sequence and TALI_NUMBER is allocated atomically per
# Jalali year inside the same transaction as the insert.
# """

# from datetime import datetime

# import oracledb
# from fastapi import APIRouter, Depends, HTTPException

# from app.auth.deps import get_current_user
# from app.core.db import get_connection
# from app.crud.registry import TaliHeaderInput
# from app.crud.sql import Audit, plan
# from app.services.base import execute, fetch_all, fetch_one
# from app.services.tally_numbering import (
#     allocate_next_tally_number,
#     jalali_year_for,
# )


# router = APIRouter(prefix="/tally-header", tags=["tally_header"])

# _FIELDS = list(TaliHeaderInput.model_fields.keys())
# _WRITABLE_FIELDS = [field for field in _FIELDS if field != "tali_number"]
# _PLAN = plan(
#     table="FA_TALI_HEADER",
#     pk="ID_TALI",
#     fields=_FIELDS,
#     audit=Audit(),
# )

# _INSERT_COLUMNS = ", ".join(f'"{field.upper()}"' for field in _WRITABLE_FIELDS)
# _INSERT_VALUES = ", ".join(f":{field}" for field in _WRITABLE_FIELDS)
# INSERT_TALLY_SQL = f"""
# INSERT INTO "FA_TALI_HEADER" (
#     "ID_TALI", {_INSERT_COLUMNS}, "TALI_NUMBER",
#     "IS_DELETED", "CREATE_AT", "CREATE_BY"
# ) VALUES (
#     "SEQ_FA_TALI_HEADER".NEXTVAL, {_INSERT_VALUES}, :tali_number,
#     'no', :create_at, :actor_id
# )
# RETURNING "ID_TALI" INTO :new_id
# """


# def _coerce_dates(params: dict) -> dict:
#     converted = dict(params)
#     for key, value in converted.items():
#         if (
#             isinstance(value, str)
#             and value
#             and ("date" in key.lower() or key.lower().endswith("_at"))
#         ):
#             converted[key] = datetime.fromisoformat(value).date()
#     return converted


# def _fetch_one_with_cursor(cursor, sql: str, params: dict) -> dict | None:
#     cursor.execute(sql, params)
#     row = cursor.fetchone()
#     if row is None:
#         return None
#     columns = [column[0].lower() for column in cursor.description]
#     return dict(zip(columns, row))


# def _returned_int(value) -> int:
#     result = value.getvalue()
#     if isinstance(result, (list, tuple)):
#         result = result[0]
#     return int(result)


# @router.get("", dependencies=[Depends(get_current_user)])
# def list_tally_headers():
#     return fetch_all(_PLAN["list"])


# @router.get("/{row_id}", dependencies=[Depends(get_current_user)])
# def get_tally_header(row_id: int):
#     row = fetch_one(_PLAN["one"], {"id": row_id})
#     if row is None:
#         raise HTTPException(status_code=404, detail="تالی یافت نشد")
#     return row


# @router.post("", status_code=201)
# def create_tally_header(
#     item: TaliHeaderInput,
#     current_user: dict = Depends(get_current_user),
# ):
#     # Always discard a client value. TALI_NUMBER is a server-owned identifier.
#     payload = item.model_dump()
#     payload.pop("tali_number", None)
#     params = _coerce_dates(payload)
#     params["actor_id"] = current_user["id"]

#     with get_connection() as conn:
#         try:
#             with conn.cursor() as cursor:
#                 cursor.execute("SELECT SYSDATE FROM DUAL")
#                 database_now = cursor.fetchone()[0]
#                 params["create_at"] = database_now
#                 params["tali_number"] = allocate_next_tally_number(
#                     cursor,
#                     jalali_year_for(database_now.date()),
#                 )

#                 new_id_var = cursor.var(int)
#                 cursor.execute(
#                     INSERT_TALLY_SQL,
#                     {**params, "new_id": new_id_var},
#                 )
#                 new_id = _returned_int(new_id_var)
#                 created = _fetch_one_with_cursor(
#                     cursor,
#                     _PLAN["one"],
#                     {"id": new_id},
#                 )
#             conn.commit()
#             return created
#         except HTTPException:
#             conn.rollback()
#             raise
#         except (oracledb.DatabaseError, ValueError, RuntimeError) as exc:
#             conn.rollback()
#             raise HTTPException(
#                 status_code=500,
#                 detail="تخصیص شماره و ایجاد تالی ناموفق بود.",
#             ) from exc


# @router.put("/{row_id}")
# def update_tally_header(
#     row_id: int,
#     item: TaliHeaderInput,
#     current_user: dict = Depends(get_current_user),
# ):
#     provided = item.model_dump(exclude_unset=True)
#     provided.pop("tali_number", None)  # immutable even if a caller sends it manually
#     params = {**_coerce_dates(provided), "id": row_id, "actor_id": current_user["id"]}

#     if execute(_PLAN["build_update"](provided.keys()), params) == 0:
#         raise HTTPException(status_code=404, detail="تالی یافت نشد")
#     return fetch_one(_PLAN["one"], {"id": row_id})


# @router.delete("/{row_id}", status_code=204)
# def delete_tally_header(
#     row_id: int,
#     current_user: dict = Depends(get_current_user),
# ):
#     params = {"id": row_id, "actor_id": current_user["id"]}
#     if execute(_PLAN["delete"], params) == 0:
#         raise HTTPException(status_code=404, detail="تالی یافت نشد")


"""Dedicated CRUD endpoints for the tally header.

Creation is intentionally not handled by the generic CRUD factory: ID_TALI
comes from an Oracle sequence and TALI_NUMBER is allocated atomically from one
continuous counter inside the same transaction as the insert.
"""

from datetime import datetime

import oracledb
from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import get_current_user
from app.core.db import get_connection
from app.crud.registry import TaliHeaderInput
from app.crud.sql import Audit, plan
from app.services.base import execute, fetch_all, fetch_one
from app.services.tally_numbering import allocate_next_tally_number


router = APIRouter(prefix="/tally-header", tags=["tally_header"])

_FIELDS = list(TaliHeaderInput.model_fields.keys())
_WRITABLE_FIELDS = [field for field in _FIELDS if field != "tali_number"]
_PLAN = plan(
    table="FA_TALI_HEADER",
    pk="ID_TALI",
    fields=_FIELDS,
    audit=Audit(),
)
GET_BY_NUMBER_SQL = _PLAN["one"].replace(
    'WHERE "ID_TALI" = :id',
    'WHERE "TALI_NUMBER" = :tali_number',
)

_INSERT_COLUMNS = ", ".join(f'"{field.upper()}"' for field in _WRITABLE_FIELDS)
_INSERT_VALUES = ", ".join(f":{field}" for field in _WRITABLE_FIELDS)
INSERT_TALLY_SQL = f"""
INSERT INTO "FA_TALI_HEADER" (
    "ID_TALI", {_INSERT_COLUMNS}, "TALI_NUMBER",
    "IS_DELETED", "CREATE_AT", "CREATE_BY"
) VALUES (
    "SEQ_FA_TALI_HEADER".NEXTVAL, {_INSERT_VALUES}, :tali_number,
    'no', :create_at, :actor_id
)
RETURNING "ID_TALI" INTO :new_id
"""


def _coerce_dates(params: dict) -> dict:
    converted = dict(params)
    for key, value in converted.items():
        if (
            isinstance(value, str)
            and value
            and ("date" in key.lower() or key.lower().endswith("_at"))
        ):
            converted[key] = datetime.fromisoformat(value).date()
    return converted


def _fetch_one_with_cursor(cursor, sql: str, params: dict) -> dict | None:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [column[0].lower() for column in cursor.description]
    return dict(zip(columns, row))


def _returned_int(value) -> int:
    result = value.getvalue()
    if isinstance(result, (list, tuple)):
        result = result[0]
    return int(result)


@router.get("", dependencies=[Depends(get_current_user)])
def list_tally_headers():
    return fetch_all(_PLAN["list"])


@router.get("/by-number/{tali_number}", dependencies=[Depends(get_current_user)])
def get_tally_header_by_number(tali_number: str):
    """Resolve the public tally number to its header and internal relational ID."""
    row = fetch_one(GET_BY_NUMBER_SQL, {"tali_number": tali_number})
    if row is None:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    return row


@router.get("/{row_id}", dependencies=[Depends(get_current_user)])
def get_tally_header(row_id: int):
    row = fetch_one(_PLAN["one"], {"id": row_id})
    if row is None:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    return row


@router.post("", status_code=201)
def create_tally_header(
    item: TaliHeaderInput,
    current_user: dict = Depends(get_current_user),
):
    # Always discard a client value. TALI_NUMBER is a server-owned identifier.
    payload = item.model_dump()
    payload.pop("tali_number", None)
    params = _coerce_dates(payload)
    params["actor_id"] = current_user["id"]

    with get_connection() as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT SYSDATE FROM DUAL")
                database_now = cursor.fetchone()[0]
                params["create_at"] = database_now
                params["tali_number"] = allocate_next_tally_number(cursor)

                new_id_var = cursor.var(int)
                cursor.execute(
                    INSERT_TALLY_SQL,
                    {**params, "new_id": new_id_var},
                )
                new_id = _returned_int(new_id_var)
                created = _fetch_one_with_cursor(
                    cursor,
                    _PLAN["one"],
                    {"id": new_id},
                )
            conn.commit()
            return created
        except HTTPException:
            conn.rollback()
            raise
        except (oracledb.DatabaseError, ValueError, RuntimeError) as exc:
            conn.rollback()
            raise HTTPException(
                status_code=500,
                detail="تخصیص شماره و ایجاد تالی ناموفق بود.",
            ) from exc


@router.put("/{row_id}")
def update_tally_header(
    row_id: int,
    item: TaliHeaderInput,
    current_user: dict = Depends(get_current_user),
):
    provided = item.model_dump(exclude_unset=True)
    provided.pop("tali_number", None)  # immutable even if a caller sends it manually
    existing = fetch_one(_PLAN["one"], {"id": row_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    params = {**_coerce_dates(provided), "id": row_id, "actor_id": current_user["id"]}

    if execute(_PLAN["build_update"](provided.keys()), params) == 0:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    return fetch_one(_PLAN["one"], {"id": row_id})


@router.delete("/{row_id}", status_code=204)
def delete_tally_header(
    row_id: int,
    current_user: dict = Depends(get_current_user),
):
    params = {"id": row_id, "actor_id": current_user["id"]}
    if execute(_PLAN["delete"], params) == 0:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
