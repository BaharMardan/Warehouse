"""Nightly backup: retention, archive integrity and row export, without Oracle."""
import datetime as dt
from decimal import Decimal
import json
import sys
import tarfile
import types

import pytest

# extract_schema imports app.core.db, which needs the app .env; tests use a stand-in.
if "app.core.db" not in sys.modules:
    _shim = types.ModuleType("app.core.db")
    _shim.get_connection = lambda: None
    sys.modules["app.core.db"] = _shim

import backup_warehouse as bw  # noqa: E402
import extract_schema  # noqa: E402
from export_live_migration import decode  # noqa: E402


def names(dates):
    return [f"warehouse_{d}_2100.tar.gz" for d in dates]


# --------------------------------------------------------------------------- retention

def test_keeps_newest_daily_and_first_of_each_month():
    days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(120)]  # Jan..Apr
    all_names = names(days)
    doomed = set(bw.archives_to_delete(all_names, keep_daily=7, keep_monthly=12))
    kept = set(all_names) - doomed
    assert set(names(days[-7:])) <= kept
    for month_first in ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"]:
        assert f"warehouse_{month_first}_2100.tar.gz" in kept
    assert len(kept) == 7 + 4


def test_monthly_limit_drops_oldest_months():
    days = [dt.date(2025, m, 1) for m in range(1, 13)] + [dt.date(2026, 1, 1)]
    doomed = bw.archives_to_delete(names(days), keep_daily=1, keep_monthly=3)
    assert names([dt.date(2025, 11, 1), dt.date(2025, 12, 1), dt.date(2026, 1, 1)])[0] not in doomed
    assert "warehouse_2025-01-01_2100.tar.gz" in doomed
    assert len(doomed) == 13 - 3


def test_never_deletes_newest_and_ignores_foreign_files():
    files = names(["2026-10-13", "2026-10-14"]) + ["notes.txt", "last_success.json",
                                                    "warehouse_2026-10-14_2100.tar.gz.sha256"]
    assert bw.archives_to_delete(files, keep_daily=0, keep_monthly=0) == [
        "warehouse_2026-10-13_2100.tar.gz"]


def test_prune_removes_checksum_files_too(tmp_path):
    for n in names(["2026-10-01", "2026-10-02", "2026-10-03"]):
        (tmp_path / n).write_text("x")
        (tmp_path / f"{n}.sha256").write_text("x")
    (tmp_path / "keep.me").write_text("x")
    bw.prune(tmp_path, keep_daily=1, keep_monthly=0)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "keep.me", "warehouse_2026-10-03_2100.tar.gz", "warehouse_2026-10-03_2100.tar.gz.sha256"]


# --------------------------------------------------------------------------- export + archive

class FakeCursor:
    """Answers exactly the dictionary queries export_rows makes."""
    def __init__(self, tables):
        self.tables, self.result = tables, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if sql.startswith("SET TRANSACTION"):
            self.result = []
        elif "FROM dual" in sql:
            self.result = [("WAREHOUSE_LIVE",)]
        elif "user_sequences" in sql:
            self.result = []
        elif "user_tab_cols" in sql:
            self.result = [(c, t, "NO", "YES" if c == "ID" else "NO")
                           for c, t in self.tables[params["t"]]["cols"]]
        elif "user_cons_columns" in sql:
            self.result = [("ID",)]
        else:
            table = sql.split(" FROM ")[1].split(" ORDER BY ")[0].strip('"')
            self.result = list(self.tables[table]["rows"])

    def fetchone(self):
        return self.result[0]

    def fetchall(self):
        return list(self.result)

    def __iter__(self):
        return iter(self.result)


class FakeConn:
    def __init__(self, tables):
        self.tables, self.rolled_back = tables, False

    def cursor(self):
        return FakeCursor(self.tables)

    def rollback(self):
        self.rolled_back = True


TABLES = {
    "FA_TALI_HEADER": {"cols": [("ID", "NUMBER"), ("DESCR", "VARCHAR2"), ("CREATED", "DATE")],
                       "rows": [(Decimal(1), "تالی ۱", dt.datetime(2026, 10, 14, 9, 30)),
                                (Decimal(2), None, None)]},
    "FA_USERS": {"cols": [("ID", "NUMBER"), ("AVATAR", "BLOB")],
                 "rows": [(Decimal(7), b"\x00\xffpng")]},
}


def build_bundle(tmp_path, monkeypatch, tables=TABLES):
    monkeypatch.setattr(extract_schema, "_tables", lambda cur: list(tables))
    bundle = tmp_path / "work" / "warehouse_2026-10-14_2100"
    (bundle / "schema").mkdir(parents=True)
    for n in ["01_sequences", "02_tables", "03_constraints", "04_foreign_keys",
              "05_indexes", "06_triggers", "07_comments"]:
        (bundle / "schema" / f"{n}.sql").write_text(f"-- {n}\n")
    conn = FakeConn(tables)
    manifest = bw.export_rows(conn, bundle)
    assert conn.rolled_back
    return bundle, manifest


def test_export_writes_restorable_rows(tmp_path, monkeypatch):
    bundle, manifest = build_bundle(tmp_path, monkeypatch)
    assert manifest["format"] == 1 and manifest["source_schema"] == "WAREHOUSE_LIVE"
    by_name = {t["name"]: t for t in manifest["tables"]}
    assert by_name["FA_TALI_HEADER"]["rows"] == 2 and by_name["FA_USERS"]["rows"] == 1
    lines = (bundle / by_name["FA_TALI_HEADER"]["file"]).read_text(encoding="utf-8").splitlines()
    first = [decode(v) for v in json.loads(lines[0])]
    assert first == [Decimal(1), "تالی ۱", dt.datetime(2026, 10, 14, 9, 30)]
    blob = [decode(v) for v in json.loads((bundle / by_name["FA_USERS"]["file"]).read_text())]
    assert blob == [Decimal(7), b"\x00\xffpng"]


def test_seal_archive_and_verify_roundtrip(tmp_path, monkeypatch):
    bundle, manifest = build_bundle(tmp_path, monkeypatch)
    bw.seal_bundle(bundle, manifest, "warehouse_live")
    out = tmp_path / "backups"
    out.mkdir()
    archive = bw.make_archive(bundle, out)
    assert archive.name == "warehouse_2026-10-14_2100.tar.gz"
    assert not list(out.glob(".*partial"))
    checked = bw.verify_archive(archive, bundle.name)
    assert "rows/000.jsonl" in checked["files"] and "schema/06_triggers.sql" in checked["files"]
    digest, name = (out / f"{archive.name}.sha256").read_text().split()
    assert name == archive.name and digest == bw.sha256(archive)


def test_verify_detects_corruption(tmp_path, monkeypatch):
    bundle, manifest = build_bundle(tmp_path, monkeypatch)
    bw.seal_bundle(bundle, manifest, "WAREHOUSE_LIVE")
    (bundle / "rows" / "000.jsonl").write_text("tampered\n")
    bad = tmp_path / "bad.tar.gz"
    with tarfile.open(bad, "w:gz") as tar:
        tar.add(bundle, arcname=bundle.name)
    with pytest.raises(RuntimeError, match="verification failed"):
        bw.verify_archive(bad, bundle.name)


def test_refuses_wrong_schema(tmp_path, monkeypatch):
    bundle, manifest = build_bundle(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="expected HR"):
        bw.seal_bundle(bundle, manifest, "HR")
    bundle2, manifest2 = build_bundle(tmp_path / "b", monkeypatch,
                                      {"FA_KALA": {"cols": [("ID", "NUMBER")], "rows": []}})
    with pytest.raises(RuntimeError, match="Required tables missing"):
        bw.seal_bundle(bundle2, manifest2, "WAREHOUSE_LIVE")


def test_config_requires_credentials():
    with pytest.raises(SystemExit):
        bw.load_config({"ORACLE_USER": "WAREHOUSE_LIVE"})
    cfg = bw.load_config({"ORACLE_USER": "u", "ORACLE_PASSWORD": "p", "ORACLE_DSN": "d"})
    assert cfg["keep_daily"] == 30 and cfg["keep_monthly"] == 12

def test_timestamp_with_seconds_and_invalid_date():
    assert bw.archive_date("warehouse_2026-10-14_210059.tar.gz") == dt.datetime(2026, 10, 14, 21, 0, 59)
    assert bw.archive_date("warehouse_2026-99-14_2100.tar.gz") is None


def test_config_rejects_negative_retention():
    env = {"ORACLE_USER": "u", "ORACLE_PASSWORD": "p", "ORACLE_DSN": "d", "KEEP_MONTHLY": "-1"}
    with pytest.raises(ValueError):
        bw.load_config(env)


def test_archive_cannot_overwrite_existing_backup(tmp_path, monkeypatch):
    bundle, manifest = build_bundle(tmp_path, monkeypatch)
    bw.seal_bundle(bundle, manifest, "WAREHOUSE_LIVE")
    out = tmp_path / "backups"
    out.mkdir()
    archive = bw.make_archive(bundle, out)
    before = archive.read_bytes()
    with pytest.raises(FileExistsError):
        bw.make_archive(bundle, out)
    assert archive.read_bytes() == before
    assert bw.verify_archive(archive, bundle.name)["source_schema"] == "WAREHOUSE_LIVE"


def test_full_run_publishes_verified_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(extract_schema, "_tables", lambda cur: list(TABLES))

    class Conn(FakeConn):
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return False

    def schema(cfg, target):
        target.mkdir()
        for name in ["01_sequences", "02_tables", "03_constraints", "04_foreign_keys",
                     "05_indexes", "06_triggers", "07_comments"]:
            (target / f"{name}.sql").write_text("-- test schema\n")

    monkeypatch.setattr(bw, "capture_schema", schema)
    monkeypatch.setattr(bw, "connect", lambda cfg: Conn(TABLES))
    cfg = {"backup_dir": tmp_path, "user": "WAREHOUSE_LIVE", "dsn": "test",
           "keep_daily": 30, "keep_monthly": 12}
    archive = bw.run(cfg)
    status = json.loads((tmp_path / "last_success.json").read_text())
    assert status["tables"] == 2 and status["rows"] == 3
    assert bw.verify_archive(archive, archive.name[:-7])["source_schema"] == "WAREHOUSE_LIVE"


def test_failed_export_keeps_published_archives(tmp_path, monkeypatch):
    previous = tmp_path / "warehouse_2026-01-01_2100.tar.gz"
    previous.write_bytes(b"previous backup")

    def fail(cfg, target):
        raise RuntimeError("export failed")

    monkeypatch.setattr(bw, "capture_schema", fail)
    cfg = {"backup_dir": tmp_path, "user": "WAREHOUSE_LIVE", "dsn": "test",
           "keep_daily": 1, "keep_monthly": 0}
    with pytest.raises(RuntimeError, match="export failed"):
        bw.run(cfg)
    assert previous.read_bytes() == b"previous backup"
    assert not (tmp_path / "last_success.json").exists()
