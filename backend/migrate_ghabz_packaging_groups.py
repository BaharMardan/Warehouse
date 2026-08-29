"""Allow one receipt line per goods-code + packaging and store merged locations.

Run once before deploying the matching backend:
    python migrate_ghabz_packaging_groups.py
"""

import oracledb

from app.core.config import settings


def ignorable(exc: oracledb.DatabaseError, codes: tuple[int, ...]) -> bool:
    return getattr(exc.args[0], "code", None) in codes


def main() -> None:
    with oracledb.connect(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'ALTER TABLE "FA_ghabz_anbar_DETAILES" '
                'MODIFY ("NUMBER_HAMEL" VARCHAR2(1000 CHAR))'
            )
            for column in ("SOURCE_ANBAR_NAMES", "SOURCE_TAGH_NAMES"):
                try:
                    cur.execute(
                        f'ALTER TABLE "FA_ghabz_anbar_DETAILES" '
                        f'ADD ("{column}" VARCHAR2(1000 CHAR))'
                    )
                except oracledb.DatabaseError as exc:
                    if not ignorable(exc, (1430,)):  # column already exists
                        raise

            try:
                cur.execute(
                    'ALTER TABLE "FA_ghabz_anbar_DETAILES" '
                    'DROP CONSTRAINT "FA_CON_تکرار_کدکلا"'
                )
            except oracledb.DatabaseError as exc:
                if not ignorable(exc, (2443,)):  # constraint does not exist
                    raise

            try:
                cur.execute(
                    'ALTER TABLE "FA_ghabz_anbar_DETAILES" ADD CONSTRAINT '
                    '"UQ_GHABZ_CODE_PACKAGE" UNIQUE '
                    '("ID_GHABZ_ANBAR_HEADAR", "code_kala", "TYPE_BASTEh")'
                )
            except oracledb.DatabaseError as exc:
                if not ignorable(exc, (2261, 2264)):  # key/name already exists
                    raise

        conn.commit()
    print("Ghabz packaging grouping migration completed.")


if __name__ == "__main__":
    main()
