"""Split goods owners and transport-company representatives into clear entities.

This migration implements the main-menu data-model changes:

* FA_PRODUCT_OWNER supports natural persons and legal entities.
* FA_OWNER_REPRESENTATIVE stores one or more representatives for legal owners.
* FA_TRANSPORT_COMPANY stores transport-company identity/contact information.
* FA_REPRESENTATIVE_COMPANY becomes the representative table and is linked to
  FA_TRANSPORT_COMPANY through ID_COMPANY.
* Existing company/representative rows are preserved and separated without
  changing representative primary keys used by historical tallies.
* Existing tally and warehouse-receipt company references are remapped to the
  new transport-company table when a legacy mapping is available.

Run once while the API is stopped (safe to run again):

    python migrate_owners_and_transport_companies.py
"""

from app.core.db import get_connection


OWNER_TABLE = "FA_PRODUCT_OWNER"
OWNER_REPRESENTATIVE_TABLE = "FA_OWNER_REPRESENTATIVE"
REPRESENTATIVE_TABLE = "FA_REPRESENTATIVE_COMPANY"
COMPANY_TABLE = "FA_TRANSPORT_COMPANY"
TALLY_TABLE = "FA_TALI_HEADER"
GHABZ_TABLE = "fa_ghabz_anbar_header"
OWNER_SEQUENCE = "SEQ_FA_PRODUCT_OWNER_MANAGED"
OWNER_REPRESENTATIVE_SEQUENCE = "SEQ_FA_OWNER_REP_MANAGED"


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = :table_name",
        {"table_name": table},
    )
    return int(cursor.fetchone()[0]) > 0


def _columns(cursor, table: str) -> set[str]:
    cursor.execute(
        "SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME = :table_name",
        {"table_name": table},
    )
    return {str(row[0]) for row in cursor.fetchall()}


def _add_column(cursor, table: str, column: str, definition: str) -> bool:
    if column in _columns(cursor, table):
        print(f"SKIP: {table}.{column} already exists")
        return False
    cursor.execute(
        f"ALTER TABLE {_q(table)} ADD ({_q(column)} {definition})"
    )
    print(f"OK  : added {table}.{column}")
    return True


def _sequence_exists(cursor, sequence: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM USER_SEQUENCES WHERE SEQUENCE_NAME = :sequence_name",
        {"sequence_name": sequence},
    )
    return int(cursor.fetchone()[0]) > 0


def _ensure_sequence(cursor, sequence: str, table: str, pk: str) -> None:
    if _sequence_exists(cursor, sequence):
        print(f"SKIP: {sequence} already exists")
        return
    cursor.execute(f'SELECT NVL(MAX({_q(pk)}), 0) + 1 FROM {_q(table)}')
    start_with = int(cursor.fetchone()[0])
    cursor.execute(
        f"CREATE SEQUENCE {_q(sequence)} START WITH {start_with} "
        "INCREMENT BY 1 NOCACHE NOCYCLE"
    )
    print(f"OK  : created {sequence}; next value is {start_with}")


def _foreign_keys(cursor, table: str, column: str) -> list[tuple[str, str]]:
    cursor.execute(
        """
        SELECT uc.CONSTRAINT_NAME, referenced.TABLE_NAME
        FROM USER_CONSTRAINTS uc
        JOIN USER_CONS_COLUMNS cols
          ON cols.CONSTRAINT_NAME = uc.CONSTRAINT_NAME
         AND cols.TABLE_NAME = uc.TABLE_NAME
        JOIN USER_CONSTRAINTS referenced
          ON referenced.CONSTRAINT_NAME = uc.R_CONSTRAINT_NAME
        WHERE uc.CONSTRAINT_TYPE = 'R'
          AND uc.TABLE_NAME = :table_name
          AND cols.COLUMN_NAME = :column_name
        """,
        {"table_name": table, "column_name": column},
    )
    return [(str(name), str(target)) for name, target in cursor.fetchall()]


def _drop_legacy_company_fks(cursor, table: str) -> None:
    if not _table_exists(cursor, table):
        return
    for constraint_name, target_table in _foreign_keys(cursor, table, "ID_COMPANY"):
        if target_table == COMPANY_TABLE:
            continue
        cursor.execute(
            f"ALTER TABLE {_q(table)} DROP CONSTRAINT {_q(constraint_name)}"
        )
        print(
            f"OK  : removed legacy {table}.ID_COMPANY reference to {target_table}"
        )


def _create_company_table(cursor) -> None:
    if _table_exists(cursor, COMPANY_TABLE):
        print(f"SKIP: {COMPANY_TABLE} already exists")
        return
    cursor.execute(
        f"""
        CREATE TABLE {_q(COMPANY_TABLE)} (
            "ID_COMPANY"   NUMBER NOT NULL,
            "COMPANY_NAME" VARCHAR2(300 CHAR) NOT NULL,
            "ADDRESS"      VARCHAR2(1000 CHAR),
            "PHONE"        VARCHAR2(50 CHAR),
            "NATIONAL_ID"  VARCHAR2(30 CHAR),
            "ECONOMIC_CODE" VARCHAR2(40 CHAR),
            "IS_DELETED"   VARCHAR2(3 CHAR) DEFAULT 'no' NOT NULL,
            "CREATE_AT"    DATE DEFAULT SYSDATE,
            "CREATE_BY"    NUMBER,
            "MODIFY_AT"    DATE,
            "MODIFY_BY"    NUMBER,
            CONSTRAINT "PK_FA_TRANSPORT_COMPANY" PRIMARY KEY ("ID_COMPANY")
        )
        """
    )
    print(f"OK  : created {COMPANY_TABLE}")


def _prepare_owner_table(cursor) -> None:
    if not _table_exists(cursor, OWNER_TABLE):
        raise RuntimeError(f"Required table {OWNER_TABLE} was not found.")

    _add_column(cursor, OWNER_TABLE, "COMPANY_NAME", "VARCHAR2(300 CHAR)")
    phone_added = _add_column(cursor, OWNER_TABLE, "PHONE", "VARCHAR2(50 CHAR)")
    _add_column(cursor, OWNER_TABLE, "NATIONAL_ID", "VARCHAR2(30 CHAR)")
    _add_column(cursor, OWNER_TABLE, "ECONOMIC_CODE", "VARCHAR2(40 CHAR)")

    owner_columns = _columns(cursor, OWNER_TABLE)
    if "TYPE" not in owner_columns:
        _add_column(cursor, OWNER_TABLE, "TYPE", "VARCHAR2(20 CHAR)")
        owner_columns = _columns(cursor, OWNER_TABLE)

    if phone_added:
        sources = [name for name in ("MOBILE", "MOBILE_FORCE") if name in owner_columns]
        if sources:
            expression = "COALESCE(" + ", ".join(_q(name) for name in sources) + ")"
            cursor.execute(
                f"UPDATE {_q(OWNER_TABLE)} SET \"PHONE\" = {expression} "
                'WHERE "PHONE" IS NULL'
            )
            print(f"OK  : preserved phone values for {cursor.rowcount} owner row(s)")

    cursor.execute(
        f"""
        UPDATE {_q(OWNER_TABLE)}
           SET "TYPE" = CASE
               WHEN TRIM("COMPANY_NAME") IS NOT NULL THEN 'حقوقی'
               ELSE 'حقیقی'
           END
         WHERE "TYPE" IS NULL OR "TYPE" NOT IN ('حقیقی', 'حقوقی')
        """
    )
    print(f"OK  : normalized type for {cursor.rowcount} owner row(s)")


def _prepare_owner_representative_table(cursor) -> None:
    if not _table_exists(cursor, OWNER_REPRESENTATIVE_TABLE):
        cursor.execute(
            f"""
            CREATE TABLE {_q(OWNER_REPRESENTATIVE_TABLE)} (
                "ID_OWNER_REPRESENTATIVE" NUMBER NOT NULL,
                "ID_OWNER"                NUMBER NOT NULL,
                "NAME"                    VARCHAR2(150 CHAR) NOT NULL,
                "FAMILY"                  VARCHAR2(150 CHAR) NOT NULL,
                "NATIONAL_CODE"           VARCHAR2(30 CHAR) NOT NULL,
                "MOBILE"                  VARCHAR2(50 CHAR) NOT NULL,
                "CREATE_AT"               DATE DEFAULT SYSDATE,
                "CREATE_BY"               NUMBER,
                CONSTRAINT "PK_FA_OWNER_REPRESENTATIVE"
                    PRIMARY KEY ("ID_OWNER_REPRESENTATIVE"),
                CONSTRAINT "FK_OWNER_REPRESENTATIVE_OWNER"
                    FOREIGN KEY ("ID_OWNER")
                    REFERENCES {_q(OWNER_TABLE)} ("ID_OWNER") ON DELETE CASCADE,
                CONSTRAINT "UQ_OWNER_REP_NATIONAL"
                    UNIQUE ("ID_OWNER", "NATIONAL_CODE")
            )
            """
        )
        print(f"OK  : created {OWNER_REPRESENTATIVE_TABLE}")
    else:
        print(f"SKIP: {OWNER_REPRESENTATIVE_TABLE} already exists")

    _ensure_sequence(cursor, OWNER_SEQUENCE, OWNER_TABLE, "ID_OWNER")
    _ensure_sequence(
        cursor,
        OWNER_REPRESENTATIVE_SEQUENCE,
        OWNER_REPRESENTATIVE_TABLE,
        "ID_OWNER_REPRESENTATIVE",
    )


def _normalize_company_name(value) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _migrate_legacy_companies(cursor) -> int:
    if not _table_exists(cursor, REPRESENTATIVE_TABLE):
        raise RuntimeError(f"Required table {REPRESENTATIVE_TABLE} was not found.")

    _add_column(cursor, REPRESENTATIVE_TABLE, "ID_COMPANY", "NUMBER")
    rep_columns = _columns(cursor, REPRESENTATIVE_TABLE)
    if "COMPANY" not in rep_columns:
        print("SKIP: no legacy COMPANY column was found; no old company names to migrate")
        return 0

    address_expression = '"ADDRESS"' if "ADDRESS" in rep_columns else "NULL"
    cursor.execute(
        f"""
        SELECT "ID_REPRE_COMPANY", "COMPANY", {address_expression}
          FROM {_q(REPRESENTATIVE_TABLE)}
         WHERE TRIM("COMPANY") IS NOT NULL
         ORDER BY "ID_REPRE_COMPANY"
        """
    )
    legacy_rows = cursor.fetchall()

    cursor.execute(
        f"SELECT \"ID_COMPANY\", \"COMPANY_NAME\" FROM {_q(COMPANY_TABLE)}"
    )
    existing_rows = cursor.fetchall()
    company_by_name = {
        _normalize_company_name(name): int(company_id)
        for company_id, name in existing_rows
        if _normalize_company_name(name)
    }
    used_ids = {int(company_id) for company_id, _ in existing_rows}
    next_id = max(used_ids, default=0) + 1
    inserted = 0

    for representative_id, company_name, address in legacy_rows:
        normalized_name = _normalize_company_name(company_name)
        if not normalized_name:
            continue
        company_id = company_by_name.get(normalized_name)
        if company_id is None:
            preferred_id = int(representative_id)
            company_id = preferred_id if preferred_id not in used_ids else next_id
            while company_id in used_ids:
                next_id += 1
                company_id = next_id
            next_id = max(next_id, company_id + 1)
            cursor.execute(
                f"""
                INSERT INTO {_q(COMPANY_TABLE)} (
                    "ID_COMPANY", "COMPANY_NAME", "ADDRESS", "IS_DELETED",
                    "CREATE_AT", "CREATE_BY"
                ) VALUES (
                    :company_id, :company_name, :address, 'no', SYSDATE, 1
                )
                """,
                {
                    "company_id": company_id,
                    "company_name": str(company_name).strip(),
                    "address": address,
                },
            )
            used_ids.add(company_id)
            company_by_name[normalized_name] = company_id
            inserted += 1

        cursor.execute(
            f"""
            UPDATE {_q(REPRESENTATIVE_TABLE)}
               SET "ID_COMPANY" = :company_id
             WHERE "ID_REPRE_COMPANY" = :representative_id
            """,
            {"company_id": company_id, "representative_id": representative_id},
        )

    print(
        f"OK  : separated {len(legacy_rows)} legacy representative row(s); "
        f"created {inserted} transport company row(s)"
    )
    return inserted


def _remap_header_companies(cursor, table: str) -> None:
    if not _table_exists(cursor, table) or "ID_COMPANY" not in _columns(cursor, table):
        return
    cursor.execute(
        f"""
        UPDATE {_q(table)} target
           SET "ID_COMPANY" = (
               SELECT legacy."ID_COMPANY"
                 FROM {_q(REPRESENTATIVE_TABLE)} legacy
                WHERE legacy."ID_REPRE_COMPANY" = target."ID_COMPANY"
           )
         WHERE EXISTS (
               SELECT 1
                 FROM {_q(REPRESENTATIVE_TABLE)} legacy
                WHERE legacy."ID_REPRE_COMPANY" = target."ID_COMPANY"
                  AND legacy."ID_COMPANY" IS NOT NULL
                  AND legacy."ID_COMPANY" <> target."ID_COMPANY"
         )
        """
    )
    print(f"OK  : remapped {cursor.rowcount} company reference(s) in {table}")


def _ensure_fk(
    cursor,
    table: str,
    column: str,
    constraint_name: str,
) -> None:
    if not _table_exists(cursor, table) or column not in _columns(cursor, table):
        return
    if any(target == COMPANY_TABLE for _, target in _foreign_keys(cursor, table, column)):
        print(f"SKIP: {table}.{column} already references {COMPANY_TABLE}")
        return

    cursor.execute(
        f"""
        SELECT COUNT(*)
          FROM {_q(table)} source
         WHERE source.{_q(column)} IS NOT NULL
           AND NOT EXISTS (
               SELECT 1
                 FROM {_q(COMPANY_TABLE)} company
                WHERE company."ID_COMPANY" = source.{_q(column)}
           )
        """
    )
    orphan_count = int(cursor.fetchone()[0])
    if orphan_count:
        print(
            f"WARN: {table}.{column} has {orphan_count} unresolved legacy value(s); "
            "the foreign key was not added"
        )
        return

    cursor.execute(
        f"""
        ALTER TABLE {_q(table)}
        ADD CONSTRAINT {_q(constraint_name)}
        FOREIGN KEY ({_q(column)})
        REFERENCES {_q(COMPANY_TABLE)} ("ID_COMPANY")
        """
    )
    print(f"OK  : linked {table}.{column} to {COMPANY_TABLE}")


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            _prepare_owner_table(cursor)
            _prepare_owner_representative_table(cursor)
            _create_company_table(cursor)
            _migrate_legacy_companies(cursor)

            _drop_legacy_company_fks(cursor, TALLY_TABLE)
            _drop_legacy_company_fks(cursor, GHABZ_TABLE)
            _remap_header_companies(cursor, TALLY_TABLE)
            _remap_header_companies(cursor, GHABZ_TABLE)

            _ensure_fk(
                cursor,
                REPRESENTATIVE_TABLE,
                "ID_COMPANY",
                "FK_REPRESENTATIVE_TRANSPORT",
            )
            _ensure_fk(cursor, TALLY_TABLE, "ID_COMPANY", "FK_TALLY_TRANSPORT_COMPANY")
            _ensure_fk(cursor, GHABZ_TABLE, "ID_COMPANY", "FK_GHABZ_TRANSPORT_COMPANY")

        connection.commit()

    print(
        "done — owners, owner representatives, transport companies, "
        "and transport representatives are ready"
    )


if __name__ == "__main__":
    main()
