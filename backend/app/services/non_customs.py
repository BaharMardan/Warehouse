"""Validation shared by registration, physical exits and remaining billing."""
from decimal import Decimal
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from uuid import UUID

FIELDS = ("weight", "quantity", "pallets")
class Amounts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weight: Decimal = Field(default=Decimal(0), ge=0, max_digits=22, decimal_places=4, allow_inf_nan=False)
    quantity: Decimal = Field(default=Decimal(0), ge=0, max_digits=22, decimal_places=4, allow_inf_nan=False)
    pallets: Decimal = Field(default=Decimal(0), ge=0, max_digits=22, decimal_places=4, allow_inf_nan=False)
class Registration(Amounts):
    source_id: int = Field(gt=0)
    start_date: date
    settlement_confirmed: bool
class RegistrationRow(Amounts):
    receipt_id: int = Field(gt=0)
    source_id: int = Field(gt=0)
class BatchRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date
    settlement_confirmed: bool
    rows: list[RegistrationRow] = Field(min_length=1, max_length=100)
class Exit(Amounts):
    request_id: UUID

def validate_amounts(payload, available, cargo):
    values = {key: Decimal(str(getattr(payload, key))) for key in FIELDS}
    basis = "pallets" if cargo in ("yes", "volumetric") else "weight"
    if values[basis] <= 0:
        raise HTTPException(422, "وزن یا تعداد پالت متناسب با نوع بار باید مثبت باشد")
    if any(values[key] > Decimal(str(available.get(key) or 0)) for key in FIELDS):
        raise HTTPException(409, "مقدار واردشده بیشتر از موجودی قابل ثبت یا خروج است")
    return values

def validate_bill(payload, goods, cargo):
    amounts = {}
    for row in getattr(payload, "rows", [payload]):
        amounts[row.source_id] = amounts.get(row.source_id, Decimal(0)) + row.amount
    basis = "pallets" if cargo in ("yes", "volumetric") else "weight"
    by_id = {int(row["source_id"]): row for row in goods}
    for sid, amount in amounts.items():
        source = by_id.get(sid)
        if source is None or amount > Decimal(str(source[basis])):
            raise HTTPException(409, "مقدار صورتحساب بیشتر از موجودی انبار غیر گمرکی است")
