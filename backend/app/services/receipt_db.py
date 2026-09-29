"""Shared transaction and edit guards for receipt workflow and source records."""
from datetime import date, datetime
from fastapi import HTTPException
from app.core.db import get_connection


def rows(cursor, sql, params=None):
    cursor.execute(sql, params or {})
    names = [c[0].lower() for c in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def one(cursor, sql, params=None):
    result = rows(cursor, sql, params)
    return result[0] if result else None


def conflict(message):
    raise HTTPException(status_code=409, detail=message)


def lock_tally(cursor, tally_id):
    tally = one(cursor, '''SELECT * FROM "FA_TALI_HEADER"
        WHERE "ID_TALI" = :id AND "IS_DELETED" = 'no' FOR UPDATE''', {"id": tally_id})
    if not tally:
        raise HTTPException(404, "تالی یافت نشد")
    return tally


def receipts(cursor, tally_id):
    return rows(cursor, '''SELECT h."ID_ghabz" AS id, h."TALI_ID" AS tally_id,
        h."GHABZ_NUMBER" AS number_text, NVL(h."IS_MASTER", 'no') AS is_master,
        h."WORKFLOW_STATUS" AS status, h."REQUIRES_INVOICE" AS requires_invoice,
        h."KEEPER_REQUIRED" AS keeper_required, h."PALLET_QUANTITY" AS pallet_quantity,
        h."ALLOCATION_RATIO" AS allocation_ratio,
        (SELECT COUNT(*) FROM "FA_ghabz_anbar_DETAILES" d
         WHERE d."ID_GHABZ_ANBAR_HEADAR" = h."ID_ghabz" AND d."IS_DELETED" = 'no') AS line_count
        FROM "fa_ghabz_anbar_header" h
        WHERE h."TALI_ID" = :id AND h."IS_DELETED" = 'no'
        ORDER BY h."ID_ghabz"''', {"id": tally_id})


def receipt(cursor, receipt_id, lock=False):
    ref = one(cursor, '''SELECT "TALI_ID" AS tally_id FROM "fa_ghabz_anbar_header"
        WHERE "ID_ghabz" = :id AND "IS_DELETED" = 'no' ''', {"id": receipt_id})
    if not ref or not ref["tally_id"]:
        raise HTTPException(404, "قبض یا تالی مرتبط یافت نشد")
    tally = lock_tally(cursor, ref["tally_id"]) if lock else None
    siblings = receipts(cursor, ref["tally_id"])
    current = next((r for r in siblings if r["id"] == receipt_id), None)
    if not current:
        raise HTTPException(404, "قبض یافت نشد")
    return current, siblings, tally


def summary_only(current, siblings):
    return current["is_master"] == "yes" and any(
        r["is_master"] != "yes" and r.get("line_count", 1) > 0 for r in siblings)


def operational(siblings):
    return [r for r in siblings if not summary_only(r, siblings) and r.get("line_count", 1) > 0]


def workflow(current, siblings):
    summary = summary_only(current, siblings)
    pending = current["status"] in ("created", "sent_to_keeper")
    return {**current, "summary_only": summary,
            "show_checklist": not summary,
            "show_invoice": not summary and current["requires_invoice"] == "yes",
            "can_finalize": not summary and pending,
            "can_invoice": not summary and current["requires_invoice"] == "yes"
                           and current["status"] == "finalized"}


def guard_services(cursor, tally_id):
    tally = lock_tally(cursor, tally_id)
    docs = operational(receipts(cursor, tally_id))
    if any(r["status"] in ("finalized", "invoice_issued") for r in docs):
        conflict("خدمات این تالی پس از ثبت نهایی قبض قفل شده است")
    if docs:
        if not any(r["status"] in ("created", "sent_to_keeper") for r in docs):
            conflict("ابتدا قبض را برای انباردار ارسال کنید")
    elif tally["handoff_step"] != "keeper":
        conflict("تالی در اختیار انباردار نیست")


def validate_header_dates(values):
    def as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(value).date()

    start, end = values.get("date_unloading"), values.get("date_cargo_exit")
    if start and end and as_date(end) < as_date(start):
        raise HTTPException(422, "تاریخ خروج بار نمی‌تواند پیش از تاریخ تخلیه باشد")


def guard_source(cursor, tally_id):
    lock_tally(cursor, tally_id)
    if receipts(cursor, tally_id):
        conflict("تالی دارای قبض قابل حذف نیست و ردیف‌های آن قابل تغییر نیستند")


SERVICE_TABLES = {
    "fa_tali_kala_strip", "fa_tali_kala_diamound", "fa_tali_kala_other_service",
    "fa_tali_kala_time_stop_vehicle", "fa_tali_kala_vehicle_enter_price",
}
SOURCE_TABLES = {"FA_TALI_HEADER", "FA_TALI_DETAILES", "fa_tali_kala_price", "fa_tali_kala_dangerous"}
RECEIPT_TABLES = {"fa_ghabz_anbar_header", "FA_ghabz_anbar_DETAILES"}


def guarded_write(table, pk, action, sql, params, *, row_id=None, values=None):
    """Execute checks and the mutation on the same locked connection."""
    values = values or {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            existing = None
            if row_id is not None:
                existing = one(cur, f'SELECT * FROM "{table}" WHERE "{pk}" = :id', {"id": row_id})
                if existing is None:
                    raise HTTPException(404, "رکورد یافت نشد")
            if table in SERVICE_TABLES | SOURCE_TABLES:
                parent = "id_headers_tali" if table == "FA_TALI_DETAILES" else "tali_id"
                tid = row_id if table == "FA_TALI_HEADER" else (existing or values).get(parent)
                if existing and parent in values and values[parent] != tid:
                    conflict("تغییر تالی مرتبط مجاز نیست")
                if not tid:
                    raise HTTPException(422, "تالی مرتبط الزامی است")
                if table == "FA_TALI_HEADER" and action == "update":
                    locked_header = lock_tally(cur, tid)
                    validate_header_dates({**locked_header, **values})
                else:
                    (guard_services if table in SERVICE_TABLES else guard_source)(cur, tid)
            elif table in RECEIPT_TABLES:
                rid = row_id if table == "fa_ghabz_anbar_header" else (existing or values).get("id_ghabz_anbar_headar")
                current, siblings, _ = receipt(cur, rid, lock=True)
                if current["status"] in ("finalized", "invoice_issued"):
                    conflict("قبض نهایی قابل ویرایش نیست")
                if existing and table == "FA_ghabz_anbar_DETAILES":
                    if "id_ghabz_anbar_headar" in values and values["id_ghabz_anbar_headar"] != rid:
                        conflict("تغییر قبض مرتبط مجاز نیست")
                if table == "fa_ghabz_anbar_header" and action == "update":
                    if "tali_id" in values and values["tali_id"] != current["tally_id"]:
                        conflict("تغییر تالی مرتبط مجاز نیست")
                if action == "delete" and any(r["status"] in ("finalized", "invoice_issued") for r in siblings):
                    conflict("حذف قبض‌های تالی پس از ثبت نهایی مجاز نیست")
                if table == "FA_ghabz_anbar_DETAILES" or action == "delete":
                    cur.execute('DELETE FROM "FA_GHABZ_TALLY_SOURCE" WHERE "RECEIPT_ID" = :id', {"id": rid})
            if action == "create":
                output = cur.var(int)
                cur.execute(sql, {**params, "new_id": output})
                result = output.getvalue()[0]
            else:
                cur.execute(sql, params)
                result = cur.rowcount
        conn.commit()
        return result
