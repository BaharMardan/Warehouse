"""Private payment receipt attachment for a tally's prepayment."""
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from app.auth.deps import require_permission
from app.core.db import get_connection
from app.services import receipt_db as db

router = APIRouter(prefix="/tally-header", tags=["prepayment_receipt"])
MAX_BYTES = 10 * 1024 * 1024


def file_type(data):
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise HTTPException(415, "فقط تصویر JPG، PNG، WEBP یا فایل PDF قابل بارگذاری است")


def active_tally(cur, tally_id):
    if not db.one(cur, """SELECT "ID_TALI" FROM "FA_TALI_HEADER"
        WHERE "ID_TALI" = :id AND "IS_DELETED" = 'no'""", {"id": tally_id}):
        raise HTTPException(404, "تالی یافت نشد")


@router.get("/{tally_id}/prepayment-receipt", dependencies=[Depends(require_permission("tally.view"))])
def receipt_info(tally_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            active_tally(cur, tally_id)
            return db.one(cur, """SELECT FILE_NAME AS name, MIME_TYPE AS mime_type
                FROM FA_TALLY_PAYMENT_RECEIPT WHERE TALLY_ID = :id""", {"id": tally_id})


@router.post("/{tally_id}/prepayment-receipt")
async def upload_receipt(tally_id: int, file: UploadFile = File(...),
                         user: dict = Depends(require_permission("tally.edit"))):
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "حجم فیش نباید بیشتر از ۱۰ مگابایت باشد")
    mime = file_type(data)
    name = (file.filename or "receipt").replace("\\", "/").split("/")[-1]
    name = "".join(c for c in name if ord(c) >= 32)[:240] or "receipt"
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                db.lock_tally(cur, tally_id)
                import oracledb
                cur.setinputsizes(content=oracledb.DB_TYPE_BLOB)
                cur.execute("""MERGE INTO FA_TALLY_PAYMENT_RECEIPT dest
                    USING (SELECT :id AS TALLY_ID FROM DUAL) src ON (dest.TALLY_ID = src.TALLY_ID)
                    WHEN MATCHED THEN UPDATE SET FILE_NAME = :name, MIME_TYPE = :mime,
                        FILE_CONTENT = :content, MODIFIED_AT = SYSDATE, MODIFIED_BY = :actor
                    WHEN NOT MATCHED THEN INSERT
                        (TALLY_ID, FILE_NAME, MIME_TYPE, FILE_CONTENT, MODIFIED_AT, MODIFIED_BY)
                        VALUES (:id, :name, :mime, :content, SYSDATE, :actor)""",
                    {"id": tally_id, "name": name, "mime": mime, "content": data, "actor": user["id"]})
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"name": name, "mime_type": mime}


@router.get("/{tally_id}/prepayment-receipt/file", dependencies=[Depends(require_permission("tally.view"))])
def download_receipt(tally_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            active_tally(cur, tally_id)
            row = db.one(cur, """SELECT FILE_NAME AS name, MIME_TYPE AS mime_type,
                FILE_CONTENT AS content FROM FA_TALLY_PAYMENT_RECEIPT WHERE TALLY_ID = :id""",
                {"id": tally_id})
            if not row:
                raise HTTPException(404, "فیش واریزی ثبت نشده است")
    return Response(content=row["content"], media_type=row["mime_type"], headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(row["name"], safe=""),
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
    })
