# """FA_COMMODITY_CATALOG endpoints — the new master commodity catalog.

# Deliberately NOT built on the generic CRUD factory, because the catalog needs two
# things the factory doesn't give:
#   * server-side search + pagination (the factory's list returns every row — fatal for
#     ~9k commodities), and
#   * a bulk Excel upsert that preserves the admin-set STORAGE_GROUP_ID.

# Nothing here touches FA_KALA_PRICE, CODE_GROUPE_KALA or the invoice calculation. The
# only bridge to the storage-group world is the nullable STORAGE_GROUP_ID FK, surfaced so
# the tally screen can pre-fill CODE_GROUPE_KALA when it's set.
# """
# from io import BytesIO

# from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

# from app.auth.deps import get_current_user, require_admin
# from app.core.db import get_connection
# from app.services.base import fetch_all, fetch_one, execute, insert_returning_id
# from app.services.xlsx_catalog import parse_catalog, normalize
# from pydantic import BaseModel, Field

# router = APIRouter(prefix="/commodity", tags=["commodity"])

# # columns returned to the client; LEFT JOIN pulls the storage group's CODE for display
# _SELECT = """
#     SELECT c.ID              AS id,
#            c.HS_CODE         AS hs_code,
#            c.DESCRIPTION_FA  AS description_fa,
#            c.UNIT            AS unit,
#            c.CUSTOMS_DUTY    AS customs_duty,
#            c.COMMERCIAL_PROFIT AS commercial_profit,
#            c.STORAGE_GROUP_ID  AS storage_group_id,
#            g.CODE            AS storage_group_code
#     FROM FA_COMMODITY_CATALOG c
#     LEFT JOIN "fa_kala_price" g ON g."id_kala_price" = c.STORAGE_GROUP_ID
# """


# class CommodityUpdate(BaseModel):
#     # admin edits; every field optional so a partial PUT (e.g. only storage_group_id)
#     # never nulls the others
#     hs_code: str | None = Field(default=None, min_length=1)
#     description_fa: str | None = None
#     unit: str | None = None
#     customs_duty: float | None = None
#     commercial_profit: float | None = None
#     storage_group_id: int | None = None


# @router.get("", dependencies=[Depends(get_current_user)])
# def search_commodities(
#     q: str | None = Query(default=None),
#     limit: int = Query(default=20, ge=1, le=100),
#     offset: int = Query(default=0, ge=0),
# ):
#     """Paginated search used by BOTH the catalog page and the tally picker.
#     Matches HS-code prefix OR normalized-description substring. Empty q -> plain page."""
#     where = ["c.IS_DELETED = 'no'"]
#     params: dict = {}
#     if q and q.strip():
#         raw = q.strip()
#         params["hs"] = raw + "%"                 # HS: prefix match on the raw digits
#         # bind name must NOT be :desc -- DESC is an Oracle reserved word -> ORA-01745
#         params["qdesc"] = "%" + normalize(raw) + "%"   # description: folded substring
#         where.append("(c.HS_CODE LIKE :hs OR c.DESCRIPTION_NORM LIKE :qdesc)")
#     where_sql = " WHERE " + " AND ".join(where)

#     total = fetch_one(
#         f"SELECT COUNT(*) AS n FROM FA_COMMODITY_CATALOG c{where_sql}", params
#     )["n"]
#     params["off"] = offset
#     params["lim"] = limit
#     items = fetch_all(
#         f"{_SELECT}{where_sql} ORDER BY c.HS_CODE "
#         f"OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY",
#         params,
#     )
#     return {"items": items, "total": total, "limit": limit, "offset": offset}


# @router.get("/storage-groups", dependencies=[Depends(get_current_user)])
# def storage_groups():
#     """The 33 warehouse storage-price groups, with a HUMAN name for each.

#     code_groupe_kala is an internal id; users must never read raw numbers. The readable
#     name lives in the old FA_KALA master (fa_kala_price.id_kala -> FA_KALA.name_kala), so
#     we join it here. Falls back to the CODE when a group has no linked name. Only ~33 rows,
#     so the client may load them all (unlike the ~9k commodity catalog).
#     """
#     return fetch_all(
#         """
#         SELECT p."id_kala_price"  AS id,
#                p.CODE             AS code,
#                k.name_kala        AS name,
#                p."price_30_day"   AS price_30_day,
#                p."price_60_day"   AS price_60_day,
#                p."price_90_day"   AS price_90_day
#         FROM "fa_kala_price" p
#         LEFT JOIN FA_KALA k ON k.ID_KALA = p."id_kala"
#         WHERE p.IS_DELETED = 'no'
#         ORDER BY p.CODE
#         """
#     )


# @router.get("/{row_id}", dependencies=[Depends(get_current_user)])
# def get_commodity(row_id: int):
#     row = fetch_one(f"{_SELECT} WHERE c.ID = :id", {"id": row_id})
#     if row is None:
#         raise HTTPException(status_code=404, detail="کالا یافت نشد")
#     return row


# @router.post("", status_code=201)
# def create_commodity(item: CommodityUpdate, admin: dict = Depends(require_admin)):
#     if not item.hs_code:
#         raise HTTPException(status_code=422, detail="HS Code لازم است")
#     new_id = insert_returning_id(
#         """
#         INSERT INTO FA_COMMODITY_CATALOG
#             (HS_CODE, DESCRIPTION_FA, DESCRIPTION_NORM, UNIT, CUSTOMS_DUTY,
#              COMMERCIAL_PROFIT, STORAGE_GROUP_ID, IS_DELETED, CREATE_AT, CREATE_BY)
#         VALUES
#             (:hs_code, :description_fa, :description_norm, :unit, :customs_duty,
#              :commercial_profit, :storage_group_id, 'no', SYSDATE, :create_by)
#         RETURNING ID INTO :new_id
#         """,
#         {
#             "hs_code": item.hs_code,
#             "description_fa": item.description_fa,
#             "description_norm": normalize(item.description_fa),
#             "unit": item.unit,
#             "customs_duty": item.customs_duty,
#             "commercial_profit": item.commercial_profit,
#             "storage_group_id": item.storage_group_id,
#             "create_by": admin["id"],
#         },
#     )
#     return fetch_one(f"{_SELECT} WHERE c.ID = :id", {"id": new_id})


# @router.put("/{row_id}")
# def update_commodity(row_id: int, item: CommodityUpdate, admin: dict = Depends(require_admin)):
#     provided = item.model_dump(exclude_unset=True)
#     sets, params = [], {"id": row_id, "actor": admin["id"]}
#     for field in ("hs_code", "description_fa", "unit", "customs_duty",
#                   "commercial_profit", "storage_group_id"):
#         if field in provided:
#             sets.append(f"{field.upper()} = :{field}")
#             params[field] = provided[field]
#     if "description_fa" in provided:                 # keep the search copy in sync
#         sets.append("DESCRIPTION_NORM = :description_norm")
#         params["description_norm"] = normalize(provided["description_fa"])
#     sets.append("MODIFY_AT = SYSDATE")
#     sets.append("MODIFY_BY = :actor")
#     affected = execute(
#         f"UPDATE FA_COMMODITY_CATALOG SET {', '.join(sets)} "
#         f"WHERE ID = :id AND IS_DELETED = 'no'",
#         params,
#     )
#     if affected == 0:
#         raise HTTPException(status_code=404, detail="کالا یافت نشد")
#     return fetch_one(f"{_SELECT} WHERE c.ID = :id", {"id": row_id})


# @router.delete("/{row_id}", status_code=204)
# def delete_commodity(row_id: int, admin: dict = Depends(require_admin)):
#     affected = execute(
#         "UPDATE FA_COMMODITY_CATALOG SET IS_DELETED='yes', MODIFY_AT=SYSDATE, "
#         "MODIFY_BY=:actor WHERE ID=:id AND IS_DELETED='no'",
#         {"id": row_id, "actor": admin["id"]},
#     )
#     if affected == 0:
#         raise HTTPException(status_code=404, detail="کالا یافت نشد")


# @router.post("/import")
# async def import_catalog(file: UploadFile = File(...), admin: dict = Depends(require_admin)):
#     """Bulk import / re-import from the yearly HS Excel. Upsert by HS_CODE.
#     On an existing HS code the descriptive fields are refreshed but STORAGE_GROUP_ID is
#     left untouched, so an admin's group assignments survive a re-import."""
#     if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
#         raise HTTPException(status_code=422, detail="فایل باید xlsx باشد")
#     raw = await file.read()
#     try:
#         rows = parse_catalog(BytesIO(raw))
#     except Exception as exc:  # malformed workbook
#         raise HTTPException(status_code=422, detail=f"خطا در خواندن اکسل: {exc}")
#     if not rows:
#         raise HTTPException(status_code=422, detail="هیچ ردیف کالایی یافت نشد")

#     merge = """
#         MERGE INTO FA_COMMODITY_CATALOG t
#         USING (SELECT :hs_code AS HS_CODE FROM dual) s
#         ON (t.HS_CODE = s.HS_CODE)
#         WHEN MATCHED THEN UPDATE SET
#             t.DESCRIPTION_FA = :description_fa,
#             t.DESCRIPTION_NORM = :description_norm,
#             t.UNIT = :unit,
#             t.CUSTOMS_DUTY = :customs_duty,
#             t.COMMERCIAL_PROFIT = :commercial_profit,
#             t.IS_DELETED = 'no',
#             t.MODIFY_AT = SYSDATE,
#             t.MODIFY_BY = :actor
#         WHEN NOT MATCHED THEN INSERT
#             (HS_CODE, DESCRIPTION_FA, DESCRIPTION_NORM, UNIT, CUSTOMS_DUTY,
#              COMMERCIAL_PROFIT, IS_DELETED, CREATE_AT, CREATE_BY)
#             VALUES (:hs_code, :description_fa, :description_norm, :unit, :customs_duty,
#                     :commercial_profit, 'no', SYSDATE, :actor)
#     """
#     binds = [{**r, "actor": admin["id"]} for r in rows]
#     with get_connection() as conn:
#         with conn.cursor() as cur:
#             cur.execute("SELECT COUNT(*) FROM FA_COMMODITY_CATALOG")
#             before = cur.fetchone()[0]
#             cur.executemany(merge, binds)
#             cur.execute("SELECT COUNT(*) FROM FA_COMMODITY_CATALOG")
#             after = cur.fetchone()[0]
#         conn.commit()
#     inserted = after - before
#     return {"processed": len(rows), "inserted": inserted, "updated": len(rows) - inserted}

"""FA_COMMODITY_CATALOG endpoints — the new master commodity catalog.

Deliberately NOT built on the generic CRUD factory, because the catalog needs two
things the factory doesn't give:
  * server-side search + pagination (the factory's list returns every row — fatal for
    ~9k commodities), and
  * a bulk Excel upsert that preserves the admin-set STORAGE_GROUP_ID.

Nothing here touches FA_KALA_PRICE, CODE_GROUPE_KALA or the invoice calculation. The
only bridge to the storage-group world is the nullable STORAGE_GROUP_ID FK, surfaced so
the tally screen can pre-fill CODE_GROUPE_KALA when it's set.
"""
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from app.auth.deps import get_current_user, require_admin
from app.core.db import get_connection
from app.services.base import fetch_all, fetch_one, execute, insert_returning_id
from app.services.xlsx_catalog import parse_catalog, normalize
from pydantic import BaseModel

router = APIRouter(prefix="/commodity", tags=["commodity"])

# columns returned to the client; LEFT JOIN pulls the storage group's CODE for display
_SELECT = """
    SELECT c.ID              AS id,
           c.HS_CODE         AS hs_code,
           c.DESCRIPTION_FA  AS description_fa,
           c.UNIT            AS unit,
           c.CUSTOMS_DUTY    AS customs_duty,
           c.COMMERCIAL_PROFIT AS commercial_profit,
           c.STORAGE_GROUP_ID  AS storage_group_id,
           g.CODE            AS storage_group_code
    FROM FA_COMMODITY_CATALOG c
    LEFT JOIN "fa_kala_price" g ON g."id_kala_price" = c.STORAGE_GROUP_ID
"""


class CommodityUpdate(BaseModel):
    # admin edits; every field optional so a partial PUT (e.g. only storage_group_id)
    # never nulls the others
    hs_code: str | None = None
    description_fa: str | None = None
    unit: str | None = None
    customs_duty: float | None = None
    commercial_profit: float | None = None
    storage_group_id: int | None = None


@router.get("", dependencies=[Depends(get_current_user)])
def search_commodities(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Paginated search used by BOTH the catalog page and the tally picker.
    Matches HS-code prefix OR normalized-description substring. Empty q -> plain page."""
    where = ["c.IS_DELETED = 'no'"]
    params: dict = {}
    if q and q.strip():
        raw = q.strip()
        params["hs"] = raw + "%"                 # HS: prefix match on the raw digits
        # bind name must NOT be :desc -- DESC is an Oracle reserved word -> ORA-01745
        params["qdesc"] = "%" + normalize(raw) + "%"   # description: folded substring
        where.append("(c.HS_CODE LIKE :hs OR c.DESCRIPTION_NORM LIKE :qdesc)")
    where_sql = " WHERE " + " AND ".join(where)

    total = fetch_one(
        f"SELECT COUNT(*) AS n FROM FA_COMMODITY_CATALOG c{where_sql}", params
    )["n"]
    params["off"] = offset
    params["lim"] = limit
    items = fetch_all(
        f"{_SELECT}{where_sql} ORDER BY c.HS_CODE "
        f"OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY",
        params,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/storage-groups", dependencies=[Depends(get_current_user)])
def storage_groups():
    """The warehouse storage-price groups, with a HUMAN name for each.

    code_groupe_kala is an internal id; users must never read raw numbers. The readable
    name is the Table-1 گروه کالا label (fa_kala_price."goods_group"), falling back to the
    old FA_KALA master name (via id_kala) for any legacy row without one, and to the CODE
    if neither exists. Few rows, so the client may load them all.
    """
    return fetch_all(
        """
        SELECT p."id_kala_price"  AS id,
               p.CODE             AS code,
               COALESCE(p."goods_group", k.name_kala) AS name
        FROM "fa_kala_price" p
        LEFT JOIN FA_KALA k ON k.ID_KALA = p."id_kala"
        WHERE p.IS_DELETED = 'no'
        ORDER BY p.CODE
        """
    )


@router.get("/{row_id}", dependencies=[Depends(get_current_user)])
def get_commodity(row_id: int):
    row = fetch_one(f"{_SELECT} WHERE c.ID = :id", {"id": row_id})
    if row is None:
        raise HTTPException(status_code=404, detail="کالا یافت نشد")
    return row


@router.post("", status_code=201)
def create_commodity(item: CommodityUpdate, admin: dict = Depends(require_admin)):
    new_id = insert_returning_id(
        """
        INSERT INTO FA_COMMODITY_CATALOG
            (HS_CODE, DESCRIPTION_FA, DESCRIPTION_NORM, UNIT, CUSTOMS_DUTY,
             COMMERCIAL_PROFIT, STORAGE_GROUP_ID, IS_DELETED, CREATE_AT, CREATE_BY)
        VALUES
            (:hs_code, :description_fa, :description_norm, :unit, :customs_duty,
             :commercial_profit, :storage_group_id, 'no', SYSDATE, :create_by)
        RETURNING ID INTO :new_id
        """,
        {
            "hs_code": item.hs_code,
            "description_fa": item.description_fa,
            "description_norm": normalize(item.description_fa),
            "unit": item.unit,
            "customs_duty": item.customs_duty,
            "commercial_profit": item.commercial_profit,
            "storage_group_id": item.storage_group_id,
            "create_by": admin["id"],
        },
    )
    return fetch_one(f"{_SELECT} WHERE c.ID = :id", {"id": new_id})


@router.put("/{row_id}")
def update_commodity(row_id: int, item: CommodityUpdate, admin: dict = Depends(require_admin)):
    provided = item.model_dump(exclude_unset=True)
    sets, params = [], {"id": row_id, "actor": admin["id"]}
    for field in ("hs_code", "description_fa", "unit", "customs_duty",
                  "commercial_profit", "storage_group_id"):
        if field in provided:
            sets.append(f"{field.upper()} = :{field}")
            params[field] = provided[field]
    if "description_fa" in provided:                 # keep the search copy in sync
        sets.append("DESCRIPTION_NORM = :description_norm")
        params["description_norm"] = normalize(provided["description_fa"])
    sets.append("MODIFY_AT = SYSDATE")
    sets.append("MODIFY_BY = :actor")
    affected = execute(
        f"UPDATE FA_COMMODITY_CATALOG SET {', '.join(sets)} "
        f"WHERE ID = :id AND IS_DELETED = 'no'",
        params,
    )
    if affected == 0:
        raise HTTPException(status_code=404, detail="کالا یافت نشد")
    return fetch_one(f"{_SELECT} WHERE c.ID = :id", {"id": row_id})


@router.delete("/{row_id}", status_code=204)
def delete_commodity(row_id: int, admin: dict = Depends(require_admin)):
    affected = execute(
        "UPDATE FA_COMMODITY_CATALOG SET IS_DELETED='yes', MODIFY_AT=SYSDATE, "
        "MODIFY_BY=:actor WHERE ID=:id AND IS_DELETED='no'",
        {"id": row_id, "actor": admin["id"]},
    )
    if affected == 0:
        raise HTTPException(status_code=404, detail="کالا یافت نشد")


@router.post("/import")
async def import_catalog(file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    """Bulk import / re-import from the yearly HS Excel. Upsert by HS_CODE.
    On an existing HS code the descriptive fields are refreshed but STORAGE_GROUP_ID is
    left untouched, so an admin's group assignments survive a re-import."""
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="فایل باید xlsx باشد")
    raw = await file.read()
    try:
        rows = parse_catalog(BytesIO(raw))
    except Exception as exc:  # malformed workbook
        raise HTTPException(status_code=422, detail=f"خطا در خواندن اکسل: {exc}")
    if not rows:
        raise HTTPException(status_code=422, detail="هیچ ردیف کالایی یافت نشد")

    merge = """
        MERGE INTO FA_COMMODITY_CATALOG t
        USING (SELECT :hs_code AS HS_CODE FROM dual) s
        ON (t.HS_CODE = s.HS_CODE)
        WHEN MATCHED THEN UPDATE SET
            t.DESCRIPTION_FA = :description_fa,
            t.DESCRIPTION_NORM = :description_norm,
            t.UNIT = :unit,
            t.CUSTOMS_DUTY = :customs_duty,
            t.COMMERCIAL_PROFIT = :commercial_profit,
            t.IS_DELETED = 'no',
            t.MODIFY_AT = SYSDATE,
            t.MODIFY_BY = :actor
        WHEN NOT MATCHED THEN INSERT
            (HS_CODE, DESCRIPTION_FA, DESCRIPTION_NORM, UNIT, CUSTOMS_DUTY,
             COMMERCIAL_PROFIT, IS_DELETED, CREATE_AT, CREATE_BY)
            VALUES (:hs_code, :description_fa, :description_norm, :unit, :customs_duty,
                    :commercial_profit, 'no', SYSDATE, :actor)
    """
    binds = [{**r, "actor": admin["id"]} for r in rows]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM FA_COMMODITY_CATALOG")
            before = cur.fetchone()[0]
            cur.executemany(merge, binds)
            cur.execute("SELECT COUNT(*) FROM FA_COMMODITY_CATALOG")
            after = cur.fetchone()[0]
        conn.commit()
    inserted = after - before
    return {"processed": len(rows), "inserted": inserted, "updated": len(rows) - inserted}
