"""Add customs/insurance fields to every tally goods row.

The three columns are optional and preserve all existing FA_TALI_DETAILES rows:

* CUSTOMS_VALUE — customs-declared goods value
* INSURED_VALUE — insured goods value
* INSURANCE_EXPIRY_DATE — insurance expiry as an Oracle DATE

The migration is idempotent and resolves quoted table names case-insensitively.
Run it once with the API stopped:

    python add_tally_customs_insurance_columns.py
"""

from app.core.db import get_connection


REQUESTED_TABLE = "FA_TALI_DETAILES"
COLUMNS = {
    "CUSTOMS_VALUE": "NUMBER(20, 2)",
    "INSURED_VALUE": "NUMBER(20, 2)",
    "INSURANCE_EXPIRY_DATE": "DATE",
}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def main() -> None:
    added = 0
    skipped = 0
    failed: list[str] = []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
            known_tables = {
                str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()
            }
            table = known_tables.get(REQUESTED_TABLE.casefold())
            if table is None:
                print(f"FAIL: table {REQUESTED_TABLE} does not exist")
                failed.append(REQUESTED_TABLE)
            else:
                cursor.execute(
                    """
                    SELECT COLUMN_NAME, DATA_TYPE
                      FROM USER_TAB_COLUMNS
                     WHERE TABLE_NAME = :table_name
                    """,
                    {"table_name": table},
                )
                existing = {
                    str(column).casefold(): (str(column), str(data_type))
                    for column, data_type in cursor.fetchall()
                }

                for requested_column, definition in COLUMNS.items():
                    resolved = existing.get(requested_column.casefold())
                    if resolved is not None:
                        column, data_type = resolved
                        expected_type = "DATE" if definition == "DATE" else "NUMBER"
                        if data_type != expected_type:
                            print(
                                f"FAIL: {table}.{column} exists as {data_type}; "
                                f"expected {expected_type}"
                            )
                            failed.append(f"{table}.{column}")
                        else:
                            print(f"SKIP: {table}.{column} already exists as {data_type}")
                            skipped += 1
                        continue

                    try:
                        cursor.execute(
                            f"ALTER TABLE {_quote(table)} "
                            f"ADD ({_quote(requested_column)} {definition} NULL)"
                        )
                        print(f"OK  : added optional {table}.{requested_column}")
                        added += 1
                    except Exception as exc:
                        print(f"FAIL: {table}.{requested_column}: {exc}")
                        failed.append(f"{table}.{requested_column}")

        if failed:
            connection.rollback()
        else:
            connection.commit()

    print(f"Summary: added={added}, skipped={skipped}, failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
