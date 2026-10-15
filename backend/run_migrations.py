"""Versioned Oracle migrations. Existing ad-hoc migration scripts are never discovered."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import runpy

TABLE = "FA_SCHEMA_MIGRATIONS"
NAME = re.compile(r"^([0-9]{4})_[a-z][a-z0-9_]*\.py$")


def discover(folder):
    result = []
    versions = set()
    for path in sorted(Path(folder).glob("*.py")):
        if path.name == "__init__.py":
            continue
        match = NAME.fullmatch(path.name)
        if not match or match[1] == "0000" or match[1] in versions:
            raise RuntimeError(f"Invalid or duplicate migration version: {path.name}")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        if not any(isinstance(node, ast.FunctionDef) and node.name == "upgrade" for node in tree.body):
            raise RuntimeError(f"Missing upgrade(cursor): {path.name}")
        versions.add(match[1])
        result.append({"version": match[1], "name": path.name, "path": path,
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return result


def history(cursor):
    cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = :name", {"name": TABLE})
    if not cursor.fetchone()[0]:
        return []
    cursor.execute(f"SELECT version, name, sha256, status FROM {TABLE} ORDER BY version")
    return list(cursor.fetchall())


def pending(cursor, migrations, expected_user="WAREHOUSE_LIVE"):
    cursor.execute("SELECT USER FROM dual")
    if cursor.fetchone()[0] != expected_user:
        raise RuntimeError("Unexpected schema; refusing migration.")
    cursor.execute("SELECT table_name FROM user_tables WHERE table_name IN ('FA_USERS', 'FA_TALI_HEADER')")
    if {row[0] for row in cursor.fetchall()} != {"FA_USERS", "FA_TALI_HEADER"}:
        raise RuntimeError("Warehouse sentinel tables missing; refusing migration.")
    applied = history(cursor)
    for index, (version, name, digest, status) in enumerate(applied):
        if status != "APPLIED":
            raise RuntimeError(f"Migration {version} is {status}; inspect/repair before retrying.")
        if index >= len(migrations):
            raise RuntimeError(f"Applied migration {version} is missing from this release.")
        source = migrations[index]
        if (version, name, digest) != (source["version"], source["name"], source["sha256"]):
            raise RuntimeError("Migration history changed or an older migration was inserted.")
    return migrations[len(applied):]


def apply(connection, migrations, expected_user="WAREHOUSE_LIVE", backup_confirmed=False):
    with connection.cursor() as cursor:
        todo = pending(cursor, migrations, expected_user)
        if not todo:
            return []
        if not backup_confirmed:
            raise RuntimeError("A verified pre-migration backup is required.")
        cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = :name", {"name": TABLE})
        if not cursor.fetchone()[0]:
            cursor.execute(f"""
                CREATE TABLE {TABLE} (
                    VERSION VARCHAR2(4 CHAR) PRIMARY KEY,
                    NAME VARCHAR2(128 CHAR) NOT NULL,
                    SHA256 VARCHAR2(64 CHAR) NOT NULL,
                    STATUS VARCHAR2(8 CHAR) NOT NULL,
                    STARTED_AT TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                    FINISHED_AT TIMESTAMP,
                    CONSTRAINT CK_FA_MIGRATION_STATUS CHECK (STATUS IN ('RUNNING','APPLIED','FAILED'))
                )
            """)
        completed = []
        for migration in todo:
            values = {key: migration[key] for key in ("version", "name", "sha256")}
            # Oracle DDL commits implicitly. Interrupted RUNNING rows block retries.
            cursor.execute(f"INSERT INTO {TABLE} (version,name,sha256,status) "
                           "VALUES (:version,:name,:sha256,'RUNNING')", values)
            connection.commit()
            try:
                upgrade = runpy.run_path(str(migration["path"]))["upgrade"]
                upgrade(cursor)
                cursor.execute("SELECT object_name, object_type FROM user_objects WHERE status='INVALID'")
                if cursor.fetchall():
                    raise RuntimeError("Migration left invalid database objects.")
                cursor.execute(f"UPDATE {TABLE} SET status='APPLIED', finished_at=SYSTIMESTAMP "
                               "WHERE version=:version", {"version": migration["version"]})
                connection.commit()
            except BaseException:
                connection.rollback()
                cursor.execute(f"UPDATE {TABLE} SET status='FAILED', finished_at=SYSTIMESTAMP "
                               "WHERE version=:version", {"version": migration["version"]})
                connection.commit()
                raise RuntimeError(f"Migration {migration['name']} failed; Oracle DDL may be committed. "
                                   "API must remain paused until reviewed.") from None
            completed.append(migration["name"])
        return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-confirmed", action="store_true")
    parser.add_argument("--target-schema", choices=("WAREHOUSE_LIVE", "WAREHOUSE_RESTORE"), default="WAREHOUSE_LIVE")
    args = parser.parse_args()
    migrations = discover(Path(__file__).with_name("migrations") / "versions")
    if os.environ.get("ORACLE_USER") != args.target_schema:
        raise SystemExit("ORACLE_USER must match --target-schema.")
    import oracledb
    with oracledb.connect(user=os.environ["ORACLE_USER"], password=os.environ["ORACLE_PASSWORD"],
                          dsn=os.environ["ORACLE_DSN"]) as connection:
        if args.plan:
            with connection.cursor() as cursor:
                todo = pending(cursor, migrations, expected_user=args.target_schema)
            print(json.dumps({"pending": [item["name"] for item in todo]}))
        else:
            completed = apply(connection, migrations, expected_user=args.target_schema, backup_confirmed=args.backup_confirmed)
            print(json.dumps({"applied": completed}))


if __name__ == "__main__":
    main()
