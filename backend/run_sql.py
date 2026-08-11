"""Run .sql files through python-oracledb. A stand-in for SQL*Plus.

No Oracle client install is needed: this uses the same thin-mode driver the
application already depends on. Text is UTF-8 end to end, so Persian data is
safe without setting NLS_LANG.

Rebuild a schema into a throwaway user, then load the data into it:

    python run_sql.py --user schema_test --password test sql/schema/rebuild.sql
    python run_sql.py --user schema_test --password test sql/data/load.sql

Create that user first, connecting as SYSDBA:

    python run_sql.py --user sys --password oracle --sysdba ^
        -c "CREATE USER schema_test IDENTIFIED BY test" ^
        -c "GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE TRIGGER, UNLIMITED TABLESPACE TO schema_test"

Connection defaults come from backend/.env, so --dsn is usually unnecessary;
--user and --password override the ones there.

Every error is reported with its file, line and statement, and the run
continues so one pass surfaces every problem. Pass --stop-on-error for
fail-fast instead, or --ignore ORA-00955 to tolerate "already exists" when
re-running.

## Statement parsing

Files are split on semicolons outside string literals and comments, which
matters here: Persian free-text columns can contain a semicolon, and a naive
split would cut a statement in half. PL/SQL blocks (CREATE TRIGGER, BEGIN,
DECLARE) keep their internal semicolons and end at a lone / on its own line.
SQL*Plus directives (SET, SHOW, EXIT, PROMPT) are skipped, and @@file
includes are followed relative to the including file.
"""

import argparse
import os
import re
import sys

import oracledb


DIRECTIVE_RE = re.compile(
    r"^(SET|SHOW|EXIT|QUIT|SPOOL|PROMPT|WHENEVER|DEFINE|UNDEFINE|REM|CONNECT|"
    r"COLUMN|CLEAR|TTITLE|BTITLE)\b",
    re.IGNORECASE,
)
INCLUDE_RE = re.compile(r"^@@?(.+?)\s*;?\s*$")
PLSQL_RE = re.compile(
    r"^\s*(?:"
    # DBMS_METADATA emits CREATE OR REPLACE EDITIONABLE TRIGGER. Missing the
    # EDITIONABLE keyword here silently disables PL/SQL mode, and the block is
    # then split on its internal semicolons.
    r"CREATE(?:\s+OR\s+REPLACE)?(?:\s+(?:NON)?EDITIONABLE)?"
    r"\s+(?:TRIGGER|PROCEDURE|FUNCTION|PACKAGE|TYPE)\b"
    r"|DECLARE\b|BEGIN\b"
    r")",
    re.IGNORECASE,
)


def _scan(line: str, in_string: bool, in_comment: bool):
    """Walk one line, returning its text with comments removed, the position of
    a terminating semicolon if any, and the trailing quote/comment state."""
    out = []
    terminator = None
    i = 0
    while i < len(line):
        char = line[i]
        if in_comment:
            if line.startswith("*/", i):
                in_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            out.append(char)
            if char == "'":
                in_string = False
            i += 1
            continue
        if line.startswith("--", i):
            break
        if line.startswith("/*", i):
            in_comment = True
            i += 2
            continue
        if char == "'":
            in_string = True
            out.append(char)
            i += 1
            continue
        if char == ";":
            terminator = len(out)
            out.append(char)
            i += 1
            continue
        out.append(char)
        i += 1
    return "".join(out), terminator, in_string, in_comment


def iter_statements(path: str, depth: int = 0):
    """Yield (file, line number, sql) for every statement, following includes."""
    if depth > 10:
        raise RuntimeError(f"include nesting too deep at {path}")
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    base = os.path.dirname(os.path.abspath(path))
    buffer: list[str] = []
    start_line = 0
    in_string = False
    in_comment = False
    plsql = False

    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n").rstrip("\r")
        stripped = line.strip()

        if not buffer and not in_string and not in_comment:
            if not stripped:
                continue
            if DIRECTIVE_RE.match(stripped):
                continue
            include = INCLUDE_RE.match(stripped)
            if include:
                target = os.path.join(base, include.group(1))
                if not os.path.exists(target):
                    raise FileNotFoundError(f"{path}:{number}: {target} not found")
                yield from iter_statements(target, depth + 1)
                continue

        # A lone / is always a SQL*Plus terminator, never a statement. Making
        # this unconditional rather than dependent on PL/SQL detection means a
        # missed PL/SQL keyword cannot leave the slash to be executed on its own.
        if stripped == "/":
            sql = "\n".join(buffer).strip()
            if sql:
                yield path, start_line, sql
            buffer, plsql = [], False
            continue

        text, terminator, in_string, in_comment = _scan(line, in_string, in_comment)

        if not buffer:
            if not text.strip():
                continue
            start_line = number
            plsql = bool(PLSQL_RE.match(text))

        if plsql or terminator is None:
            buffer.append(text)
            continue

        buffer.append(text[:terminator])
        sql = "\n".join(buffer).strip()
        if sql:
            yield path, start_line, sql
        buffer = []
        remainder = text[terminator + 1 :].strip()
        if remainder:
            buffer.append(remainder)
            start_line = number
            plsql = bool(PLSQL_RE.match(remainder))

    leftover = "\n".join(buffer).strip().rstrip(";").strip()
    if leftover:
        yield path, start_line, leftover


def _compile_statement(object_type: str, name: str) -> str:
    if object_type == "PACKAGE BODY":
        return f'ALTER PACKAGE "{name}" COMPILE BODY'
    if object_type == "TYPE BODY":
        return f'ALTER TYPE "{name}" COMPILE BODY'
    return f'ALTER {object_type} "{name}" COMPILE'


def _invalid_objects(cursor) -> list[tuple[str, str]]:
    cursor.execute(
        """
        SELECT OBJECT_TYPE, OBJECT_NAME
        FROM USER_OBJECTS
        WHERE STATUS = 'INVALID'
        ORDER BY OBJECT_TYPE, OBJECT_NAME
        """
    )
    return [(row[0], row[1]) for row in cursor.fetchall()]


def _defaults():
    """Connection details from backend/.env, when it is readable."""
    try:
        from app.core.config import settings

        return settings.oracle_user, settings.oracle_password, settings.oracle_dsn
    except Exception:  # noqa: BLE001 - .env is optional when args are explicit
        return None, None, None


def _first_line(text: str) -> str:
    line = text.strip().splitlines()[0]
    return line[:100] + ("..." if len(line) > 100 else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="one or more .sql files to run")
    parser.add_argument(
        "-c", "--command", action="append", default=[], help="run a statement inline"
    )
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--dsn")
    parser.add_argument(
        "--sysdba", action="store_true", help="connect with SYSDBA privilege"
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help="abort at the first failure"
    )
    parser.add_argument(
        "--ignore",
        nargs="+",
        default=[],
        metavar="ORA-NNNNN",
        help="treat these error codes as success, e.g. ORA-00955 ORA-01408",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="parse and count, execute nothing"
    )
    args = parser.parse_args()

    if not args.files and not args.command:
        parser.error("give at least one .sql file or -c statement")

    env_user, env_password, env_dsn = _defaults()
    user = args.user or env_user
    password = args.password or env_password
    dsn = args.dsn or env_dsn
    if not (user and password and dsn):
        parser.error("--user, --password and --dsn are required (no usable .env)")

    statements = []
    for path in args.command:
        statements.append(("<command line>", 0, path.strip().rstrip(";")))
    for path in args.files:
        if not os.path.exists(path):
            parser.error(f"{path} not found")
        statements.extend(iter_statements(path))

    print(f"{len(statements)} statement(s) parsed")
    if args.dry_run:
        for source, line, sql in statements[:10]:
            print(f"  {os.path.basename(source)}:{line}  {_first_line(sql)}")
        if len(statements) > 10:
            print(f"  ... and {len(statements) - 10} more")
        return

    mode = oracledb.AUTH_MODE_SYSDBA if args.sysdba else oracledb.AUTH_MODE_DEFAULT
    try:
        connection = oracledb.connect(user=user, password=password, dsn=dsn, mode=mode)
    except Exception as exc:  # noqa: BLE001
        print(f"\nCould not connect as {user} to {dsn}")
        print(f"  {str(exc).splitlines()[0]}")
        sys.exit(1)
    print(f"Connected as {user}{' AS SYSDBA' if args.sysdba else ''} to {dsn}\n")

    ignore = tuple(code.upper() for code in args.ignore)
    ok = 0
    ignored = 0
    failures = []

    with connection:
        cursor = connection.cursor()
        for index, (source, line, sql) in enumerate(statements, start=1):
            try:
                cursor.execute(sql)
                ok += 1
            except Exception as exc:  # noqa: BLE001 - collected and reported
                message = str(exc).splitlines()[0]
                if ignore and message.upper().startswith(ignore):
                    ignored += 1
                    continue
                failures.append((source, line, sql, message))
                print(f"  ! {os.path.basename(source)}:{line}  {message}")
                print(f"    {_first_line(sql)}")
                if args.stop_on_error:
                    break
            if index % 1000 == 0:
                print(f"  ... {index:,} / {len(statements):,}")

        # A trigger or package body can be created successfully and still be
        # INVALID. That raises nothing here, but every later DML on the table
        # fails with ORA-04098, so it must be surfaced. Note that DDL on a table
        # marks its dependent triggers invalid even when they are perfectly
        # good, so try a recompile before treating this as a real problem.
        invalid = []
        if not args.sysdba:
            try:
                invalid = _invalid_objects(cursor)
                for object_type, name in invalid:
                    try:
                        cursor.execute(_compile_statement(object_type, name))
                    except Exception:  # noqa: BLE001 - re-checked below
                        pass
                invalid = _invalid_objects(cursor)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! could not check for invalid objects: {exc}")
        connection.commit()

    if invalid:
        print("\nStill invalid after recompiling:")
        for object_type, name in invalid:
            print(f"  ! {object_type} {name}")

    print()
    print(f"  succeeded: {ok:,}")
    if ignored:
        print(f"  ignored:   {ignored:,}")
    print(f"  failed:    {len(failures):,}")

    if failures or invalid:
        print("\nFAILED")
        sys.exit(1)
    print("\nOK")


if __name__ == "__main__":
    main()