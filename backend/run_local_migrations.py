"""Run versioned migrations against the local HR development database only."""
import argparse
import json
from pathlib import Path

from run_migrations import apply, discover, pending


def validate_local_target(user, dsn):
    import oracledb
    if user.upper() != "HR":
        raise RuntimeError("Local migrations require the HR development schema.")
    params = oracledb.ConnectParams()
    params.parse_connect_string(dsn)
    if params.host not in ("localhost", "127.0.0.1", "::1"):
        raise RuntimeError("Local migrations require a loopback database address.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-confirmed", action="store_true")
    args = parser.parse_args(argv)

    from app.core.config import settings
    import oracledb
    validate_local_target(settings.oracle_user, settings.oracle_dsn)
    migrations = discover(Path(__file__).with_name("migrations") / "versions")
    with oracledb.connect(user=settings.oracle_user, password=settings.oracle_password,
                          dsn=settings.oracle_dsn) as connection:
        if args.plan:
            with connection.cursor() as cursor:
                todo = pending(cursor, migrations, expected_user="HR")
            print(json.dumps({"schema": "HR", "pending": [item["name"] for item in todo]}))
        else:
            completed = apply(connection, migrations, expected_user="HR",
                              backup_confirmed=args.backup_confirmed)
            print(json.dumps({"schema": "HR", "applied": completed}))


if __name__ == "__main__":
    main()
