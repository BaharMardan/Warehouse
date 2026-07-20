# from typing import Type

# from fastapi import APIRouter, Depends, HTTPException
# from pydantic import BaseModel

# from app.auth.deps import get_current_user
# from app.services.base import fetch_all, fetch_one, execute, insert_returning_id
# from app.crud.sql import Audit, plan
# from datetime import date, datetime

# # Re-export so callers can `from app.crud.factory import make_crud_router, Audit`
# __all__ = ["make_crud_router", "Audit"]


# def make_crud_router(
#     *,
#     prefix: str,
#     table: str,
#     pk: str,
#     model: Type[BaseModel],
#     tag: str,
#     not_found: str = "رکورد یافت نشد",
#     column_overrides: dict[str, str] | None = None,
#     audit: Audit | None = Audit(),
# ) -> APIRouter:
#     """A full soft-delete CRUD router for one table, generated from a Pydantic model.

#     Writable columns come from the model's field names (single source of truth).
#     Every identifier is quoted with its EXACT stored case, so this works whether
#     Oracle folded the name to UPPERCASE or the table was created with quoted
#     lowercase/mixed-case names.

#     For each field the DB column defaults to FIELD.upper(). When the real column name
#     differs - a rename, OR a column the original devs stored lowercase/mixed-case -
#     give it in column_overrides as {api_field: "EXACT_DB_COLUMN"}. Rule of thumb:
#     copy the column name EXACTLY as it appears in your DESC / column dump. UPPERCASE
#     columns can be omitted (the default uppercases for you); anything else must be listed.

#     audit: pass Audit(...) with the exact (UPPERCASE) audit/soft-delete column names.
#     Defaults cover the standard CREATE_AT/CREATE_BY/MODIFY_AT/MODIFY_BY/IS_DELETED set.
#     Set a single field to None to drop that piece; pass audit=None for a table that has
#     no audit columns at all (no soft-delete filter, no stamping, hard DELETE).
#     """
#     p = plan(
#         table=table,
#         pk=pk,
#         fields=list(model.model_fields.keys()),
#         overrides=column_overrides,
#         audit=audit,
#     )
#     router = APIRouter(prefix=prefix, tags=[tag])

#     @router.get("", dependencies=[Depends(get_current_user)])
#     def list_rows():
#         return fetch_all(p["list"])
    
#     @router.get("/{row_id}", dependencies=[Depends(get_current_user)])
#     def get_row(row_id: int):
#         row = fetch_one(p["one"], {"id": row_id})
#         if row is None:
#             raise HTTPException(status_code=404, detail=not_found)
#         return row

#     @router.post("", status_code=201)
#     def create_row(item: model, current_user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
#         params = {**item.model_dump()}
#         for key, value in params.items():
#             if (
#                 isinstance(value, str)
#                 and value
#                 and ("date" in key.lower() or key.lower().endswith("_at"))
#             ):
#                 params[key] = datetime.fromisoformat(value).date()
#         if p["stamps_create_by"]:
#             params["actor_id"] = current_user["id"]
#         new_id = insert_returning_id(p["insert"], params)
#         return fetch_one(p["one"], {"id": new_id})

#     # @router.put("/{row_id}")
#     # def update_row(row_id: int, item: model, current_user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
#     #     params = {**item.model_dump(), "id": row_id}
#     #     if p["stamps_modify_by"]:
#     #         params["actor_id"] = current_user["id"]
#     #     if execute(p["update"], params) == 0:
#     #         raise HTTPException(status_code=404, detail=not_found)
#     #     return fetch_one(p["one"], {"id": row_id})
#     @router.put("/{row_id}")
#     def update_row(row_id: int, item: model, current_user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
#         # Only update columns the client actually sent. Fields omitted from the request
#         # keep their stored value, so a partial form never nulls a NOT NULL column it
#         # doesn't manage (e.g. TALI_ID -> ORA-01407).
#         provided = item.model_dump(exclude_unset=True)
#         if not provided and not (p["stamps_modify_at"] or p["stamps_modify_by"]):
#             # nothing to change and no modify-stamp columns -> empty SET would be invalid SQL
#             return fetch_one(p["one"], {"id": row_id})
#         params = {**provided, "id": row_id}
#         # same ISO-string -> date coercion as create_row, so edits to date columns bind correctly
#         for key, value in params.items():
#             if (
#                 isinstance(value, str)
#                 and value
#                 and ("date" in key.lower() or key.lower().endswith("_at"))
#             ):
#                 params[key] = datetime.fromisoformat(value).date()
#         if p["stamps_modify_by"]:
#             params["actor_id"] = current_user["id"]
#         if execute(p["build_update"](provided.keys()), params) == 0:
#             raise HTTPException(status_code=404, detail=not_found)
#         return fetch_one(p["one"], {"id": row_id})

#     @router.delete("/{row_id}", status_code=204)
#     def delete_row(row_id: int, current_user: dict = Depends(get_current_user)):
#         params = {"id": row_id}
#         if p["stamps_modify_by"] and p["soft_delete"]:
#             params["actor_id"] = current_user["id"]
#         if execute(p["delete"], params) == 0:
#             raise HTTPException(status_code=404, detail=not_found)

#     return router

from typing import Type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.services.base import fetch_all, fetch_one, execute, insert_returning_id
from app.crud.sql import Audit, plan
from datetime import date, datetime

# Re-export so callers can `from app.crud.factory import make_crud_router, Audit`
__all__ = ["make_crud_router", "Audit"]


def make_crud_router(
    *,
    prefix: str,
    table: str,
    pk: str,
    model: Type[BaseModel],
    tag: str,
    not_found: str = "رکورد یافت نشد",
    column_overrides: dict[str, str] | None = None,
    audit: Audit | None = Audit(),
    order_by: str | list[str] | None = None,
) -> APIRouter:
    """A full soft-delete CRUD router for one table, generated from a Pydantic model.

    Writable columns come from the model's field names (single source of truth).
    Every identifier is quoted with its EXACT stored case, so this works whether
    Oracle folded the name to UPPERCASE or the table was created with quoted
    lowercase/mixed-case names.

    For each field the DB column defaults to FIELD.upper(). When the real column name
    differs - a rename, OR a column the original devs stored lowercase/mixed-case -
    give it in column_overrides as {api_field: "EXACT_DB_COLUMN"}. Rule of thumb:
    copy the column name EXACTLY as it appears in your DESC / column dump. UPPERCASE
    columns can be omitted (the default uppercases for you); anything else must be listed.

    audit: pass Audit(...) with the exact (UPPERCASE) audit/soft-delete column names.
    Defaults cover the standard CREATE_AT/CREATE_BY/MODIFY_AT/MODIFY_BY/IS_DELETED set.
    Set a single field to None to drop that piece; pass audit=None for a table that has
    no audit columns at all (no soft-delete filter, no stamping, hard DELETE).

    order_by: optional display ordering for the list, for any lookup whose order must
    not depend on the pk. Pass a column name, or a list of column names for multi-key
    ordering; each is quoted and the pk is appended as a stable tiebreaker. Defaults to
    None -> ORDER BY pk, so tables that don't pass it are completely unaffected. This is
    generic framework config (like column_overrides/audit) - no per-table logic lives here.
    """
    p = plan(
        table=table,
        pk=pk,
        fields=list(model.model_fields.keys()),
        overrides=column_overrides,
        audit=audit,
        order_by=order_by,
    )
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("", dependencies=[Depends(get_current_user)])
    def list_rows():
        return fetch_all(p["list"])
    
    @router.get("/{row_id}", dependencies=[Depends(get_current_user)])
    def get_row(row_id: int):
        row = fetch_one(p["one"], {"id": row_id})
        if row is None:
            raise HTTPException(status_code=404, detail=not_found)
        return row

    @router.post("", status_code=201)
    def create_row(item: model, current_user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
        params = {**item.model_dump()}
        for key, value in params.items():
            if (
                isinstance(value, str)
                and value
                and ("date" in key.lower() or key.lower().endswith("_at"))
            ):
                params[key] = datetime.fromisoformat(value).date()
        if p["stamps_create_by"]:
            params["actor_id"] = current_user["id"]
        new_id = insert_returning_id(p["insert"], params)
        return fetch_one(p["one"], {"id": new_id})

    # @router.put("/{row_id}")
    # def update_row(row_id: int, item: model, current_user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
    #     params = {**item.model_dump(), "id": row_id}
    #     if p["stamps_modify_by"]:
    #         params["actor_id"] = current_user["id"]
    #     if execute(p["update"], params) == 0:
    #         raise HTTPException(status_code=404, detail=not_found)
    #     return fetch_one(p["one"], {"id": row_id})
    @router.put("/{row_id}")
    def update_row(row_id: int, item: model, current_user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
        # Only update columns the client actually sent. Fields omitted from the request
        # keep their stored value, so a partial form never nulls a NOT NULL column it
        # doesn't manage (e.g. TALI_ID -> ORA-01407).
        provided = item.model_dump(exclude_unset=True)
        if not provided and not (p["stamps_modify_at"] or p["stamps_modify_by"]):
            # nothing to change and no modify-stamp columns -> empty SET would be invalid SQL
            return fetch_one(p["one"], {"id": row_id})
        params = {**provided, "id": row_id}
        # same ISO-string -> date coercion as create_row, so edits to date columns bind correctly
        for key, value in params.items():
            if (
                isinstance(value, str)
                and value
                and ("date" in key.lower() or key.lower().endswith("_at"))
            ):
                params[key] = datetime.fromisoformat(value).date()
        if p["stamps_modify_by"]:
            params["actor_id"] = current_user["id"]
        if execute(p["build_update"](provided.keys()), params) == 0:
            raise HTTPException(status_code=404, detail=not_found)
        return fetch_one(p["one"], {"id": row_id})

    @router.delete("/{row_id}", status_code=204)
    def delete_row(row_id: int, current_user: dict = Depends(get_current_user)):
        params = {"id": row_id}
        if p["stamps_modify_by"] and p["soft_delete"]:
            params["actor_id"] = current_user["id"]
        if execute(p["delete"], params) == 0:
            raise HTTPException(status_code=404, detail=not_found)

    return router