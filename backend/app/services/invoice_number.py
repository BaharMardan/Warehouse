"""Temporary manual numbering using the existing BY DEFAULT identity column.

Before restoring generated numbers, resync the identity using START WITH LIMIT VALUE.
"""
import re
import oracledb
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator


class ManualInvoiceNumber(BaseModel):
    invoice_number: int | None = Field(default=None, gt=0, le=999999999999999, strict=True)

    @field_validator("invoice_number", mode="before")
    @classmethod
    def normalize_number(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not re.fullmatch(r"[0-9۰-۹٠-٩]{1,15}", value):
                raise ValueError("شماره صورتحساب باید عدد صحیح مثبت و حداکثر ۱۵ رقمی باشد")
            return int(value)
        return value


def require_number(value):
    if value is None:
        raise HTTPException(422, "شماره صورتحساب را وارد کنید")
    return value


def ensure_available(cur, value):
    from app.services import receipt_db as db
    if db.one(cur, 'SELECT "ID_SORAT" AS id FROM "FA_SORAT_HESAB_HEADER" WHERE "ID_SORAT" = :invoice_number',
              {"invoice_number": value}):
        raise HTTPException(409, "این شماره صورتحساب قبلاً استفاده شده است؛ شماره دیگری وارد کنید")


def insert_numbered_header(cur, sql, params):
    try:
        cur.execute(sql, params)
    except oracledb.IntegrityError as exc:
        if exc.args and getattr(exc.args[0], "code", None) == 1:
            raise HTTPException(409, "این شماره صورتحساب قبلاً استفاده شده است؛ شماره دیگری وارد کنید") from exc
        raise
