"""Nightly backup of the warehouse Oracle schema.

Runs on the backup VM and pulls over the network with python-oracledb thin mode,
so no Oracle client is needed. The supplied SSH tunnel reaches the DB VM's
localhost-only Oracle port using a restricted key.

Each run writes ONE archive containing a format-1 bundle, the same format that
export_live_migration.py produces and import_live_migration.py restores and
verifies value-by-value:

    warehouse_2026-10-14_2100.tar.gz        (time is Tehran time)
    warehouse_2026-10-14_2100.tar.gz.sha256
        warehouse_2026-10-14_2100/manifest.json   tables, row counts, sha256 of every file
        warehouse_2026-10-14_2100/schema/*.sql    DDL captured by extract_schema.py
        warehouse_2026-10-14_2100/rows/NNN.jsonl  every row of every table

All rows are read inside one READ ONLY transaction, so the data is a consistent
snapshot even while users keep working. Nothing is ever written to the database.

Configuration (environment; on the backup VM: /etc/warehouse-backup/backup.env):

    ORACLE_USER       schema owner, e.g. WAREHOUSE_LIVE  (DDL capture needs the owner)
    ORACLE_PASSWORD
    ORACLE_DSN        e.g. 127.0.0.1:11521/FREEPDB1 (SSH tunnel)
    BACKUP_DIR        default /var/backups/warehouse
    KEEP_DAILY        newest N archives always kept            (default 30)
    KEEP_MONTHLY      first archive of each of the last N months (default 12)

Exit code 0 only when the archive is written AND re-verified. Any failure exits
non-zero, leaves earlier archives untouched and deletes nothing.
"""
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import types
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
ARCHIVE_RE = re.compile(r"^warehouse_(\d{4})-(\d{2})-(\d{2})_(\d{4})(\d{2})?\.tar\.gz$")
# A backup without these is a backup of the wrong schema, not of the warehouse.
REQUIRED_TABLES = {"FA_TALI_HEADER", "FA_USERS"}


# --------------------------------------------------------------------------- config

def load_config(env=os.environ) -> dict:
    missing = [k for k in ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN") if not env.get(k)]
    if missing:
        raise SystemExit(f"Missing configuration: {', '.join(missing)}")
    daily = int(env.get("KEEP_DAILY", "30"))
    monthly = int(env.get("KEEP_MONTHLY", "12"))
    if daily < 1 or monthly < 0:
        raise ValueError("KEEP_DAILY must be >= 1 and KEEP_MONTHLY must be >= 0.")
    return {
        "user": env["ORACLE_USER"],
        "password": env["ORACLE_PASSWORD"],
        "dsn": env["ORACLE_DSN"],
        "backup_dir": Path(env.get("BACKUP_DIR", "/var/backups/warehouse")),
        "keep_daily": daily,
        "keep_monthly": monthly,
    }


def connect(cfg):
    import oracledb
    oracledb.defaults.fetch_lobs = False      # CLOB/BLOB as plain str/bytes
    if hasattr(oracledb.defaults, "fetch_decimals"):
        oracledb.defaults.fetch_decimals = True   # exact NUMBERs, as the exporter does
    return oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=cfg["dsn"])


# --------------------------------------------------------------------------- export

def capture_schema(cfg, out_dir: Path) -> None:
    """Run extract_schema.py in-process against the backup connection.

    extract_schema imports app.core.db, which needs the app's .env (SECRET_KEY etc.).
    The backup VM has no app config, so hand it a stand-in module instead.
    """
    shim = types.ModuleType("app.core.db")
    shim.get_connection = lambda: connect(cfg)
    sys.modules["app.core.db"] = shim
    import extract_schema

    argv = sys.argv
    sys.argv = ["extract_schema.py", "--output", str(out_dir), "--keep-start-with", "--skip-counts"]
    try:
        extract_schema.main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise RuntimeError("Schema capture is not rebuild-safe; see output above.") from exc
    finally:
        sys.argv = argv


def export_rows(conn, out_dir: Path) -> dict:
    """Write every row of every warehouse table; return the manifest (without checksums)."""
    from export_live_migration import encode, quote
    from extract_schema import _tables

    rows_dir = out_dir / "rows"
    rows_dir.mkdir()
    manifest = {
        "format": 1,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "created_tehran": dt.datetime.now(TEHRAN).isoformat(),
        "kind": "nightly-backup",
        "tables": [], "sequences": [], "files": {},
    }
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute("SELECT USER FROM dual")
        manifest["source_schema"] = cur.fetchone()[0]
        tables = _tables(cur)
        cur.execute(
            "SELECT sequence_name, last_number FROM user_sequences "
            "WHERE sequence_name NOT LIKE 'ISEQ$$_%'"
        )
        manifest["sequences"] = [
            {"name": name, "next_value": int(number)} for name, number in cur.fetchall()
        ]
        for index, table in enumerate(tables):
            cur.execute(
                "SELECT column_name, data_type, virtual_column, identity_column "
                "FROM user_tab_cols WHERE table_name=:t AND hidden_column='NO' "
                "ORDER BY column_id", {"t": table},
            )
            columns = [
                {"name": name, "type": dtype, "identity": identity == "YES"}
                for name, dtype, virtual, identity in cur.fetchall()
                if virtual != "YES"
            ]
            if any(c["type"] == "BFILE" for c in columns):
                raise RuntimeError(f"{table}: BFILE columns point outside the database; not backed up.")
            cur.execute(
                "SELECT column_name FROM user_cons_columns "
                "WHERE constraint_name IN (SELECT constraint_name FROM user_constraints "
                "WHERE table_name=:t AND constraint_type='P') ORDER BY position",
                {"t": table},
            )
            pk = [row[0] for row in cur.fetchall()]
            sql = "SELECT " + ", ".join(quote(c["name"]) for c in columns) + " FROM " + quote(table)
            if pk:
                sql += " ORDER BY " + ", ".join(quote(name) for name in pk)
            cur.execute(sql)
            filename = f"rows/{index:03d}.jsonl"
            count = 0
            with (out_dir / filename).open("x", encoding="utf-8", newline="\n") as handle:
                for row in cur:
                    handle.write(json.dumps([encode(v) for v in row],
                                            ensure_ascii=False, allow_nan=False) + "\n")
                    count += 1
            manifest["tables"].append({"name": table, "columns": columns, "pk": pk,
                                       "file": filename, "rows": count})
            print(f"  {table}: {count} rows", flush=True)
    conn.rollback()   # ends the read-only transaction
    return manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seal_bundle(bundle: Path, manifest: dict, expected_user: str) -> None:
    """Sanity-check the export, then record a checksum for every file."""
    if manifest["source_schema"].upper() != expected_user.upper():
        raise RuntimeError(f"Connected as {manifest['source_schema']}, expected {expected_user}.")
    names = {t["name"].upper() for t in manifest["tables"]}
    absent = REQUIRED_TABLES - names
    if absent:
        raise RuntimeError(f"Wrong schema? Required tables missing: {sorted(absent)}")
    for name in ["01_sequences.sql", "02_tables.sql", "03_constraints.sql", "04_foreign_keys.sql",
                 "05_indexes.sql", "06_triggers.sql", "07_comments.sql"]:
        if not (bundle / "schema" / name).is_file():
            raise RuntimeError(f"Schema capture incomplete: {name} missing.")
    for file in sorted(bundle.rglob("*")):
        if file.is_file():
            manifest["files"][file.relative_to(bundle).as_posix()] = sha256(file)
    with (bundle / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


def make_archive(bundle: Path, backup_dir: Path) -> Path:
    """tar.gz the bundle, re-read it to prove it is complete, then publish atomically."""
    final = backup_dir / f"{bundle.name}.tar.gz"
    partial = backup_dir / f".{bundle.name}.tar.gz.partial"
    with tarfile.open(partial, "w:gz", compresslevel=6) as tar:
        tar.add(bundle, arcname=bundle.name)
    verify_archive(partial, bundle.name)
    digest = sha256(partial)
    # Never replace an earlier published archive, even after a clock rollback.
    os.link(partial, final)
    partial.unlink()
    (backup_dir / f"{final.name}.sha256").write_text(f"{digest}  {final.name}\n", encoding="utf-8")
    return final


def verify_archive(archive: Path, top: str) -> dict:
    """Every file listed in the manifest is in the archive with the recorded checksum."""
    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.load(tar.extractfile(f"{top}/manifest.json"))
        for rel, digest in manifest["files"].items():
            member = tar.extractfile(f"{top}/{rel}")
            if member is None:
                raise RuntimeError(f"Archive verification failed: {rel}")
            checked = hashlib.sha256()
            with member:
                for chunk in iter(lambda: member.read(1024 * 1024), b""):
                    checked.update(chunk)
            if checked.hexdigest() != digest:
                raise RuntimeError(f"Archive verification failed: {rel}")
    return manifest


# --------------------------------------------------------------------------- retention

def archive_date(name: str):
    m = ARCHIVE_RE.match(name)
    if not m:
        return None
    y, mo, d, hm, seconds = m.groups()
    try:
        return dt.datetime(int(y), int(mo), int(d), int(hm[:2]), int(hm[2:]), int(seconds or 0))
    except ValueError:
        return None


def archives_to_delete(names: list[str], keep_daily: int, keep_monthly: int) -> list[str]:
    """Keep the newest `keep_daily`, plus the first archive of each of the newest
    `keep_monthly` months. The newest archive is never deleted. Unknown names are ignored."""
    dated = sorted(((archive_date(n), n) for n in names if archive_date(n)), reverse=True)
    keep = {n for _, n in dated[:max(keep_daily, 1)]}
    first_of_month = {}
    for when, name in dated:                       # newest -> oldest, so the last write wins
        first_of_month[(when.year, when.month)] = name
    for month in sorted(first_of_month, reverse=True)[:keep_monthly]:
        keep.add(first_of_month[month])
    return sorted(n for _, n in dated if n not in keep)


def prune(backup_dir: Path, keep_daily: int, keep_monthly: int) -> list[str]:
    names = [p.name for p in backup_dir.iterdir() if p.is_file()]
    doomed = archives_to_delete(names, keep_daily, keep_monthly)
    for name in doomed:
        (backup_dir / name).unlink()
        (backup_dir / f"{name}.sha256").unlink(missing_ok=True)
    return doomed


# --------------------------------------------------------------------------- main

def run(cfg) -> Path:
    backup_dir: Path = cfg["backup_dir"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    lock = open(backup_dir / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("Another backup is already running.")

    # Leftovers of a run that crashed or lost power; never a published archive.
    for stale in backup_dir.glob(".warehouse_*"):
        shutil.rmtree(stale) if stale.is_dir() else stale.unlink()

    stamp = dt.datetime.now(TEHRAN).strftime("warehouse_%Y-%m-%d_%H%M%S")
    work = backup_dir / f".{stamp}.work"
    bundle = work / stamp
    bundle.mkdir(parents=True)
    try:
        print(f"Backup {stamp} (Tehran time) from {cfg['user']}@{cfg['dsn']}", flush=True)
        capture_schema(cfg, bundle / "schema")
        with connect(cfg) as conn:
            manifest = export_rows(conn, bundle)
        seal_bundle(bundle, manifest, cfg["user"])
        archive = make_archive(bundle, backup_dir)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    deleted = prune(backup_dir, cfg["keep_daily"], cfg["keep_monthly"])
    total = sum(t["rows"] for t in manifest["tables"])
    status = {
        "archive": archive.name,
        "finished_tehran": dt.datetime.now(TEHRAN).isoformat(timespec="seconds"),
        "tables": len(manifest["tables"]),
        "rows": total,
        "bytes": archive.stat().st_size,
        "deleted_by_retention": deleted,
    }
    tmp = backup_dir / ".last_success.json.tmp"
    tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, backup_dir / "last_success.json")
    print(f"BACKUP OK: {archive} — {len(manifest['tables'])} tables, {total} rows, "
          f"{status['bytes'] / 1024:.0f} KiB; retention removed {len(deleted)}", flush=True)
    return archive


if __name__ == "__main__":
    os.umask(0o077)   # archives contain password hashes and customer data
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    run(load_config())
