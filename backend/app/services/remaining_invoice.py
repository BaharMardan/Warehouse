"""Pure remaining-cargo billing using the current storage rates and user-entered days."""
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.services import storage_calc as sc, receipt_invoice as ri


class OtherServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_id: int = Field(gt=0, strict=True)
    quantity: Decimal = Field(gt=0, allow_inf_nan=False, max_digits=18, decimal_places=4)


class RemainingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    other_services: list[OtherServiceInput] = Field(default_factory=list, max_length=100)
    days: int = Field(gt=0, strict=True)
    source_id: int = Field(gt=0)
    hscode: str = Field(min_length=1, max_length=100)
    kala_code: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(gt=0, allow_inf_nan=False, max_digits=18, decimal_places=4)
    insurance_percent: Decimal = Field(ge=0, le=100, allow_inf_nan=False, max_digits=7, decimal_places=4)


class RemainingIssue(RemainingInput):
    preview_hash: str = Field(min_length=64, max_length=64)
    request_id: UUID


def serializable(value):
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def calculate(*, payload: RemainingInput, source: dict, tariff: dict, cargo: str,
              settings: dict, original_id: int, original_insurance,
              receipt_id: int, tally_id: int, service_catalog=None):
    if payload.source_id != int(source["id"]):
        raise ValueError("کالای انتخاب‌شده متعلق به این تالی نیست")
    if not payload.hscode.strip() or not payload.kala_code.strip():
        raise ValueError("HS Code و کد گروه کالا الزامی هستند")
    cargo = ri.cargo_type(cargo)
    days = payload.days
    loc = sc.location(source.get("zarib_mahal"))
    capacity = {"118": 10, "120": 15}.get(str(tariff["kala_code"]))
    if cargo == "container" and capacity is not None:
        charge = sc.container_storage_charge(rate=tariff["storage_price"],
            excess_rate=tariff.get("excess_storage_price"), capacity_tons=capacity,
            weight_kg=payload.amount, share=Decimal(1), loc=loc, days=days)
    else:
        charge = sc.storage_charge(cargo, rate=tariff["storage_price"], loc=loc, days=days,
            weight_kg=payload.amount if cargo != "volumetric" else None,
            pallets=payload.amount if cargo == "volumetric" else None)
    storage = ri.InvoiceRow("storage", f"انبارداری باقی‌مانده — {source.get('description') or payload.hscode} (کد {payload.kala_code})",
        charge.amount, charge.note, quantity=payload.amount if cargo == "volumetric" else None,
        weight=payload.amount if cargo != "volumetric" else None)
    insurance_base = Decimal(str(original_insurance or 0))
    insurance_amount = sc.round_rial(insurance_base * payload.insurance_percent / 100)
    insurance = ri.InvoiceRow("insurance", "بیمه باقی‌مانده", insurance_amount,
        f"بیمه صورتحساب اصلی {original_id}: {sc.fmt(insurance_base)} × {sc.fmt(payload.insurance_percent)}٪ = {sc.fmt(insurance_amount)}")
    for name in ("system_service_rate", "tax_rate"):
        number = Decimal(str(settings.get(name)))
        if not number.is_finite() or number < 0:
            raise ValueError("تنظیمات خدمات سیستمی یا مالیات نامعتبر است")
    services, service_snapshot = [], []
    catalog = {int(item["id"]): item for item in (service_catalog or [])}
    for selected in payload.other_services:
        item = catalog.get(selected.service_id)
        if item is None:
            raise ValueError("خدمت انتخاب‌شده فعال نیست یا یافت نشد")
        rate = ri.to_decimal(item.get("price"))
        if rate is None or not rate.is_finite() or rate < 0:
            raise ValueError("تعرفهٔ سایر خدمات نامعتبر است")
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError("نام خدمت ثبت نشده است")
        amount = sc.round_rial(rate * selected.quantity)
        services.append(ri.InvoiceRow("service", f"سایر خدمات — {title}", amount,
            f"{sc.fmt(rate)} × {sc.fmt(selected.quantity)} = {sc.fmt(amount)}",
            quantity=selected.quantity))
        service_snapshot.append({"service_id": selected.service_id, "title": title,
            "unit_price": rate, "quantity": selected.quantity, "amount": amount})
    rows, totals = ri.build_invoice(system_rate=settings["system_service_rate"], storage=[storage],
        services=services, tax_rate=settings["tax_rate"], insurance=insurance)
    snapshot = serializable({"inputs": payload.model_dump(include=set(RemainingInput.model_fields)),
        "other_services": service_snapshot, "source": source, "tariff": tariff, "cargo": cargo,
        "billed_days": days, "day_basis": "manual",
        "settings": settings, "original_invoice_id": original_id, "original_insurance": insurance_base,
        "receipt_id": receipt_id, "tally_id": tally_id})
    result = {"rows": serializable([asdict(row) for row in rows]), "total": str(totals.payable),
              "subtotal": str(totals.subtotal), "tax": str(totals.tax), "snapshot": snapshot,
              "calc_note": f"صورتحساب باقی‌مانده؛ اصلی {original_id}؛ نوع بار: {ri.CARGO_LABELS[cargo]}؛ تعداد روز واردشده: {days} روز"}
    result["preview_hash"] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result
