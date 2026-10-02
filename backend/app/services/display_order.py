"""Shared lookup ordering, separate from business fields and primary keys."""
import json
from fastapi import HTTPException
from pydantic import BaseModel, Field, StrictInt
from app.core.db import get_connection


class DisplayOrderInput(BaseModel):
    ids: list[StrictInt] = Field(min_length=1, max_length=10000)


def merge_order(current: list[int], requested: list[int]) -> list[int]:
    if len(set(requested)) != len(requested) or not set(requested).issubset(current):
        raise HTTPException(422, "ردیف‌های چینش تکراری یا نامعتبر هستند؛ صفحه را به‌روزرسانی کنید")
    # Only replace slots in the requested category; other categories keep position.
    selected = set(requested)
    replacements = iter(requested)
    return [next(replacements) if item in selected else item for item in current]


def apply_order(rows: list[dict], pk: str, ids: list[int]) -> list[dict]:
    ranks = {value: index for index, value in enumerate(ids)}
    return sorted(rows, key=lambda row: ranks.get(int(row[pk.lower()]), len(ranks)))


def read_order(prefix: str) -> list[int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT "ORDER_JSON" FROM "FA_DISPLAY_ORDER" WHERE "RESOURCE" = :scope_key',
                        {"scope_key": prefix})
            row = cur.fetchone()
            return json.loads(row[0]) if row else []


def save_order(prefix: str, list_sql: str, pk: str, requested: list[int], actor: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT "ORDER_JSON" FROM "FA_DISPLAY_ORDER" WHERE "RESOURCE" = :scope_key FOR UPDATE',
                        {"scope_key": prefix})
            stored = cur.fetchone()
            if stored is None:
                raise HTTPException(503, "جدول چینش آماده نیست؛ مهاجرت add_display_order.py را اجرا کنید")
            cur.execute(list_sql)
            names = [column[0].lower() for column in cur.description]
            rows = [dict(zip(names, row)) for row in cur.fetchall()]
            current = [int(row[pk.lower()]) for row in apply_order(rows, pk, json.loads(stored[0]))]
            merged = merge_order(current, requested)
            cur.execute('UPDATE "FA_DISPLAY_ORDER" SET "ORDER_JSON" = :ordering, '
                        '"UPDATED_BY" = :actor, "UPDATED_AT" = SYSTIMESTAMP WHERE "RESOURCE" = :scope_key',
                        {"ordering": json.dumps(merged), "actor": actor, "scope_key": prefix})
        conn.commit()
    return {"ids": merged}
