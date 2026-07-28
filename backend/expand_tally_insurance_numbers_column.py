"""Prepare FA_TALI_HEADER.NUMBER_BIMEH for multiple insurance policy numbers.

The tally header keeps insurance policy numbers as newline-separated text so
the existing single-value API and old records remain compatible. This migration
ensures the Oracle column can hold that text:

* VARCHAR2/NVARCHAR2 columns shorter than 1000 characters are expanded.
* Existing text columns with enough capacity are left untouched.
* A legacy NUMBER column is converted through a temporary VARCHAR2 column while
  preserving every existing non-null value.

Run once while the API is stopped:

    python expand_tally_insurance_numbers_column.py

The migration is idempotent and safe to run again.
"""

from app.core.db import get_connection


TABLE = "FA_TALI_HEADER"
COLUMN = "NUMBER_BIMEH"
TEMP_COLUMN = "NUMBER_BIMEH_TMP"
TARGET_LENGTH = 1000


def _column_info(cursor, column: str) -> tuple[str, int | None] | None:
    cursor.execute(
        """
        SELECT DATA_TYPE, CHAR_LENGTH
        FROM USER_TAB_COLUMNS
        WHERE TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
        """,
        {"table_name": TABLE, "column_name": column},
    )
    row = cursor.fetchone()
    return (row[0], row[1]) if row else None


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            current = _column_info(cursor, COLUMN)
            temporary = _column_info(cursor, TEMP_COLUMN)

            # Recover safely if a previous run reached the drop step but stopped
            # before renaming the temporary column.
            if current is None and temporary is not None:
                cursor.execute(
                    f'ALTER TABLE "{TABLE}" '
                    f'RENAME COLUMN "{TEMP_COLUMN}" TO "{COLUMN}"'
                )
                current = _column_info(cursor, COLUMN)
                temporary = None
                print(f"RECOVERED: renamed {TEMP_COLUMN} to {COLUMN}")

            if current is None:
                raise RuntimeError(
                    f"{TABLE}.{COLUMN} does not exist; review the schema first."
                )

            data_type, char_length = current
            normalized_type = data_type.upper()

            if normalized_type in {"VARCHAR2", "NVARCHAR2"}:
                if (char_length or 0) >= TARGET_LENGTH:
                    print(
                        f"SKIP: {TABLE}.{COLUMN} is already "
                        f"{data_type}({char_length})"
                    )
                    return

                cursor.execute(
                    f'ALTER TABLE "{TABLE}" MODIFY '
                    f'("{COLUMN}" {normalized_type}({TARGET_LENGTH}))'
                )
                print(
                    f"OK  : expanded {TABLE}.{COLUMN} "
                    f"to {normalized_type}({TARGET_LENGTH})"
                )
                return

            if normalized_type != "NUMBER":
                raise RuntimeError(
                    f"{TABLE}.{COLUMN} is {data_type}; "
                    "automatic conversion is only supported for NUMBER or text."
                )

            if temporary is not None:
                cursor.execute(
                    f'ALTER TABLE "{TABLE}" DROP COLUMN "{TEMP_COLUMN}"'
                )
                print(f"CLEANUP: dropped leftover {TABLE}.{TEMP_COLUMN}")

            cursor.execute(
                f'ALTER TABLE "{TABLE}" ADD '
                f'("{TEMP_COLUMN}" VARCHAR2({TARGET_LENGTH} CHAR))'
            )
            cursor.execute(
                f'UPDATE "{TABLE}" '
                f'SET "{TEMP_COLUMN}" = TO_CHAR("{COLUMN}") '
                f'WHERE "{COLUMN}" IS NOT NULL'
            )
            copied = cursor.rowcount
            connection.commit()

            cursor.execute(f'ALTER TABLE "{TABLE}" DROP COLUMN "{COLUMN}"')
            cursor.execute(
                f'ALTER TABLE "{TABLE}" '
                f'RENAME COLUMN "{TEMP_COLUMN}" TO "{COLUMN}"'
            )
            print(
                f"OK  : converted {TABLE}.{COLUMN} from NUMBER to "
                f"VARCHAR2({TARGET_LENGTH} CHAR); preserved {copied} value(s)"
            )

        connection.commit()


if __name__ == "__main__":
    main()
