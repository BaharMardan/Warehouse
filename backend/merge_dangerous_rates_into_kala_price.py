"""Merge dangerous-goods rows into the کالا group-code table.

Both catalogs have the same user-facing columns:

    کد | گروه کالا / عنوان | انبارداری | تخلیه و بارگیری

This migration copies every active row from ``fa_kala_dangerous`` into
``fa_kala_price`` by code. It does not add a type/status column and it does not
delete the legacy source rows, because old tally records may still reference
their primary keys.

Idempotent: rerunning updates the same target codes instead of inserting
duplicates.

Run from the backend virtual environment:
    python merge_dangerous_rates_into_kala_price.py
"""

from app.core.db import get_connection


REQUIRED_COLUMNS = {
    "fa_kala_price": {
        "id_kala_price",
        "CODE",
        "goods_group",
        "storage_price",
        "price_30_day",
        "price_60_day",
        "price_90_day",
        "price_unloding",
        "DESCRIPTION",
        "IS_DELETED",
        "CREATE_AT",
        "CREATE_BY",
        "MODIFY_AT",
        "MODIFY_BY",
    },
    "fa_kala_dangerous": {
        "id_kala_dangerous",
        "code",
        "TITLE",
        "storage_price",
        "price_30_day",
        "price_60_day",
        "price_90_day",
        "price_unloding",
        "DESCRIPTION",
        "IS_DELETED",
    },
}


def _existing_columns(cur, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM user_tab_columns
        WHERE table_name = :table_name
        """,
        {"table_name": table},
    )
    return {str(row[0]) for row in cur.fetchall()}


def _validate_schema(cur) -> None:
    missing_messages: list[str] = []
    for table, required in REQUIRED_COLUMNS.items():
        missing = sorted(required - _existing_columns(cur, table))
        if missing:
            missing_messages.append(f'{table}: {", ".join(missing)}')
    if missing_messages:
        raise RuntimeError(
            "Required columns are missing. Run the existing tariff migrations first:\n"
            + "\n".join(missing_messages)
        )


def main() -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        _validate_schema(cur)

        cur.execute(
            """
            SELECT
                d."code",
                d.TITLE,
                d."storage_price",
                d."price_30_day",
                d."price_60_day",
                d."price_90_day",
                d."price_unloding",
                d.DESCRIPTION
            FROM "fa_kala_dangerous" d
            WHERE d.IS_DELETED = 'no'
            ORDER BY d."code", d."id_kala_dangerous"
            """
        )
        source_rows = cur.fetchall()
        if not source_rows:
            print("No active dangerous-goods rows were found; nothing changed.")
            return

        inserted = 0
        updated = 0
        seen_codes: set[str] = set()

        for (
            code,
            title,
            storage_price,
            price_30_day,
            price_60_day,
            price_90_day,
            price_unloding,
            description,
        ) in source_rows:
            normalized_code = "" if code is None else str(code).strip()
            if not normalized_code:
                raise RuntimeError("An active dangerous-goods row has no code.")
            if normalized_code in seen_codes:
                raise RuntimeError(
                    f'Duplicate active dangerous-goods code "{normalized_code}" found. '
                    "Resolve the duplicate before rerunning this migration."
                )
            seen_codes.add(normalized_code)

            values = {
                "code": normalized_code,
                "goods_group": title,
                "storage_price": storage_price,
                "price_30_day": price_30_day,
                "price_60_day": price_60_day,
                "price_90_day": price_90_day,
                "price_unloding": price_unloding,
                "description": description,
            }

            cur.execute(
                'SELECT COUNT(*) FROM "fa_kala_price" WHERE CODE = :code',
                {"code": normalized_code},
            )
            target_count = int(cur.fetchone()[0])
            if target_count > 1:
                raise RuntimeError(
                    f'Multiple کالا group rows already use code "{normalized_code}". '
                    "Resolve the duplicate before rerunning this migration."
                )

            if target_count == 1:
                cur.execute(
                    """
                    UPDATE "fa_kala_price"
                    SET
                        "goods_group" = :goods_group,
                        "storage_price" = :storage_price,
                        "price_30_day" = :price_30_day,
                        "price_60_day" = :price_60_day,
                        "price_90_day" = :price_90_day,
                        "price_unloding" = :price_unloding,
                        DESCRIPTION = :description,
                        IS_DELETED = 'no',
                        MODIFY_AT = SYSDATE,
                        MODIFY_BY = 1
                    WHERE CODE = :code
                    """,
                    values,
                )
                updated += 1
                continue

            cur.execute(
                """
                INSERT INTO "fa_kala_price" (
                    "id_kala_price",
                    CODE,
                    "goods_group",
                    "storage_price",
                    "price_30_day",
                    "price_60_day",
                    "price_90_day",
                    "price_unloding",
                    DESCRIPTION,
                    IS_DELETED,
                    CREATE_AT,
                    CREATE_BY
                )
                VALUES (
                    (SELECT COALESCE(MAX("id_kala_price"), 0) + 1 FROM "fa_kala_price"),
                    :code,
                    :goods_group,
                    :storage_price,
                    :price_30_day,
                    :price_60_day,
                    :price_90_day,
                    :price_unloding,
                    :description,
                    'no',
                    SYSDATE,
                    1
                )
                """,
                values,
            )
            inserted += 1

        conn.commit()
        print(
            f"Merged {len(source_rows)} dangerous-goods row(s): "
            f"{updated} updated, {inserted} inserted."
        )
        print(
            "The legacy source rows were retained for historical tally references."
        )


if __name__ == "__main__":
    main()
