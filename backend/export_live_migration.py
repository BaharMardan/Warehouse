"""Private live warehouse export. Source access is read-only; bundle contains secrets."""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from decimal import Decimal


def encode(value):
    if hasattr(value, "read"):
        value = value.read()
    if value is None:
        return ["null", None]
    if isinstance(value, bytes):
        return ["bytes", base64.b64encode(value).decode("ascii")]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    if isinstance(value, dt.datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, dt.date):
        return ["date", value.isoformat()]
    if isinstance(value, dt.timedelta):
        return ["timedelta", [value.days, value.seconds, value.microseconds]]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    raise TypeError(f"Unsupported Oracle value type: {type(value).__name__}")


def decode(item):
    kind, value = item
    if kind == "null":
        return None
    if kind == "bytes":
        return base64.b64decode(value, validate=True)
    if kind == "decimal":
        return Decimal(value)
    if kind == "datetime":
        return dt.datetime.fromisoformat(value)
    if kind == "date":
        return dt.date.fromisoformat(value)
    if kind == "timedelta":
        return dt.timedelta(days=value[0], seconds=value[1], microseconds=value[2])
    if kind == "int":
        return int(value)
    if kind == "float":
        return float.fromhex(value)
    if kind in ("str", "bool"):
        return value
    raise ValueError(f"Unknown value type: {kind}")


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-paused", action="store_true")
    args = parser.parse_args()
    if not args.source_paused:
        parser.error("Pause source data entry and schema changes, then use --source-paused.")
    output = Path(args.output).resolve()
    workspace = Path(__file__).resolve().parents[1]
    if output == workspace or workspace in output.parents:
        parser.error("Private export must be outside the project repository.")
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o700)
    if os.name == "nt":
        result = subprocess.run(
            ["icacls", str(output), "/inheritance:r", "/grant:r",
             f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}:(OI)(CI)F"],
            capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError("Could not restrict export-folder permissions; export stopped.")
    rows_dir = output / "rows"
    rows_dir.mkdir()

    base = Path(__file__).resolve().parent
    subprocess.run(
        [sys.executable, str(base / "extract_schema.py"),
         "--output", str(output / "schema"), "--keep-start-with", "--skip-counts"],
        cwd=base, check=True,
    )

    import oracledb
    if hasattr(oracledb.defaults, "fetch_decimals"):
        oracledb.defaults.fetch_decimals = True
    from app.core.db import get_connection
    from extract_schema import _tables

    manifest = {
        "format": 1, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tables": [], "sequences": [], "files": {},
    }
    with get_connection() as conn:
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
                    raise RuntimeError(f"{table}: external BFILE needs a separate transfer.")
                cur.execute(
                    "SELECT column_name FROM user_cons_columns "
                    "WHERE constraint_name IN (SELECT constraint_name FROM user_constraints "
                    "WHERE table_name=:t AND constraint_type='P') ORDER BY position",
                    {"t": table},
                )
                pk = [row[0] for row in cur.fetchall()]
                sql = "SELECT " + ", ".join(quote(c["name"]) for c in columns)
                sql += " FROM " + quote(table)
                if pk:
                    sql += " ORDER BY " + ", ".join(quote(name) for name in pk)
                cur.execute(sql)
                filename = f"rows/{index:03d}.jsonl"
                count = 0
                with (output / filename).open("x", encoding="utf-8", newline="\n") as handle:
                    for row in cur:
                        handle.write(json.dumps(
                            [encode(value) for value in row],
                            ensure_ascii=False, allow_nan=False,
                        ) + "\n")
                        count += 1
                manifest["tables"].append({
                    "name": table, "columns": columns, "pk": pk,
                    "file": filename, "rows": count,
                })
                print(f"{table}: {count} rows exported")
            conn.rollback()
    for file in sorted(output.rglob("*")):
        if file.is_file():
            manifest["files"][file.relative_to(output).as_posix()] = checksum(file)
    with (output / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    total = sum(table["rows"] for table in manifest["tables"])
    print(f"EXPORT COMPLETE: {len(manifest['tables'])} tables, {total} rows")
    print(f"Private bundle: {output}")
    print("Contains password hashes and attachments. Do not commit or paste its contents.")


if __name__ == "__main__":
    main()

