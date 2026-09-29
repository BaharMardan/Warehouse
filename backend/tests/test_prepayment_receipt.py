import asyncio
from io import BytesIO
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException, UploadFile
from app.routers import prepayment_receipt as api


@pytest.fixture
def wired(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    lock = MagicMock()
    monkeypatch.setattr(api.db, "lock_tally", lock)
    return conn, cur, lock


def test_upload_stores_exact_bytes_and_actor(wired):
    conn, cur, lock = wired
    data = b"%PDF-1.7\nreceipt data"
    result = asyncio.run(api.upload_receipt(7, UploadFile(filename="../receipt.pdf", file=BytesIO(data)), {"id": 3}))
    assert result == {"name": "receipt.pdf", "mime_type": "application/pdf"}
    assert cur.execute.call_args.args[1]["content"] == data
    assert cur.execute.call_args.args[1]["actor"] == 3
    lock.assert_called_once_with(cur, 7)
    conn.commit.assert_called_once()


@pytest.mark.parametrize("data,status", [(b"", 415), (b"<html>bad</html>", 415),
                                          (b"x" * (api.MAX_BYTES + 1), 413)], ids=["empty", "invalid-type", "oversized"])
def test_invalid_upload_does_not_write(wired, data, status):
    conn, cur, _ = wired
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.upload_receipt(7, UploadFile(filename="fake.pdf", file=BytesIO(data)), {"id": 3}))
    assert exc.value.status_code == status
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_missing_tally_does_not_store(wired):
    conn, cur, lock = wired
    lock.side_effect = HTTPException(404, "missing")
    with pytest.raises(HTTPException):
        asyncio.run(api.upload_receipt(7, UploadFile(filename="file.pdf", file=BytesIO(b"%PDF-1.7")), {"id": 3}))
    cur.execute.assert_not_called()
    conn.rollback.assert_called_once()


def test_download_is_attachment_with_private_cache(wired, monkeypatch):
    monkeypatch.setattr(api.db, "one", MagicMock(side_effect=[
        {"id_tali": 7}, {"name": "فیش.pdf", "mime_type": "application/pdf", "content": b"%PDF-1.7"}]))
    response = api.download_receipt(7)
    assert response.body == b"%PDF-1.7"
    assert response.headers["content-disposition"].startswith("attachment; filename*=UTF-8''")
    assert response.headers["cache-control"] == "private, no-store"


def test_missing_attachment_returns_404(wired, monkeypatch):
    monkeypatch.setattr(api.db, "one", MagicMock(side_effect=[{"id_tali": 7}, None]))
    with pytest.raises(HTTPException) as exc:
        api.download_receipt(7)
    assert exc.value.status_code == 404


def test_storage_failure_rolls_back(wired):
    conn, cur, _ = wired
    cur.execute.side_effect = RuntimeError("failed")
    with pytest.raises(RuntimeError):
        asyncio.run(api.upload_receipt(7, UploadFile(filename="file.pdf", file=BytesIO(b"%PDF-1.7")), {"id": 3}))
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
