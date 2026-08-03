"""Make every operator-entered warehouse field nullable in Oracle.

The application no longer marks or validates data-entry fields as mandatory.  This
idempotent migration removes the matching database-level NOT NULL restrictions so an
empty value is accepted all the way through the API.  Primary keys, audit columns,
server-generated tally numbers, and hidden parent links remain required because they
are application infrastructure rather than fields entered by an operator.

Run with the API stopped after the other project migrations:

    python make_user_fields_optional.py

The script resolves quoted Oracle identifiers case-insensitively, skips tables/columns
that are not present in an older installation, and is safe to run again.
"""

from app.core.db import get_connection


# Table -> operator-editable columns.  Hidden relationship columns such as
# ID_HEADERS_TALI, TALI_ID on service rows, and ID_GHABZ_ANBAR_HEADAR are deliberately
# excluded: the frontend supplies them from the current parent record automatically.
OPTIONAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "FA_KALA": ("NAME_KALA", "UNITE"),
    "FA_ANBAR": ("NAME_ANBAR", "ADDRESS", "NAME_MASOL", "PHONE"),
    "FA_PRODUCT_OWNER": (
        "NAME", "FAMILY", "NATIONAL_CODE", "COMPANY_NAME", "ADDRESS", "PHONE",
        "NATIONAL_ID", "ECONOMIC_CODE",
    ),
    "FA_OWNER_REPRESENTATIVE": ("NAME", "FAMILY", "NATIONAL_CODE", "MOBILE"),
    "FA_TRANSPORT_COMPANY": (
        "COMPANY_NAME", "ADDRESS", "PHONE", "NATIONAL_ID", "ECONOMIC_CODE",
    ),
    "FA_REPRESENTATIVE_COMPANY": (
        "ID_COMPANY", "NAME", "FAMILY", "NATIONAL_CODE", "MOBILE",
    ),
    "FA_TAGH_ANBAR": ("NAME_TAGH", "ID_ANBAR", "DESCRIPTION"),
    "FA_SYS_TERMS": ("SYS_TERM_VALUE",),
    "fa_kala_price": (
        "id_kala", "CODE", "goods_group", "storage_price", "price_30_day",
        "price_60_day", "price_90_day", "price_unloding", "DESCRIPTION",
        "IS_DANGEROUS",
    ),
    "fa_kala_dangerous": (
        "code", "TITLE", "storage_price", "price_30_day", "price_60_day",
        "price_90_day", "price_unloding", "DESCRIPTION",
    ),
    "fa_kala_diamound": (
        "code", "title", "price_gher_edari", "price_holiday", "DESCRIPTION",
    ),
    "fa_kala_other_service": ("code", "title", "price", "DESCRIPTION"),
    "fa_kala_strip": (
        "code", "title", "normal", "non_standard", "dangerous", "DESCRIPTION",
    ),
    "fa_kala_time_stop_vehicle": ("code", "title", "price", "DESCRIPTION"),
    "fa_kala_vehicle_enter_price": ("code", "title", "price", "DESCRIPTION"),
    "FA_COMMODITY_CATALOG": (
        "HS_CODE", "DESCRIPTION_FA", "DESCRIPTION_NORM", "UNIT", "CUSTOMS_DUTY",
        "COMMERCIAL_PROFIT", "STORAGE_GROUP_ID",
    ),
    "FA_TALI_HEADER": (
        "NUMBER_KARANEH", "RADEF_MARZE", "DATE_ENTER_MARZE", "DATE_UNLOADING",
        "ID_MARZE", "ID_COMPANY", "ID_RESPONS_COMPANY", "ID_PRODUCT_OWNEAR",
        "OWNER_NATIONAL_CODE", "ID_COUNTRY", "NUMBER_BIMEH", "NAME_ARZYAB",
        "NUMBER_BARNAMEH", "IS_BIMEH", "NAME_ANBARDAR", "ACCEPTED_GOMROK",
        "COMPANY_BIMEH", "DESCRIPTION",
    ),
    "FA_TALI_DETAILES": (
        "ID_ANBAR", "ID_TAGH_ANBAR", "NUMBER_GHABZE_ANBAR", "CODE_GROUPE_KALA",
        "DESCRIPTION_KALA", "HSCODE", "TYPE_BASTEM", "NUMBER_KALA",
        "NUMBER_PALLET", "VALUE_KALA", "CUSTOMS_VALUE", "INSURED_VALUE",
        "INSURANCE_EXPIRY_DATE", "WEIGHTE", "TYPE_NUMBER_KANTINER",
        "NUMBER_GHABZE_BSKOL", "WEIGHTE_BASKOL", "NUMBER_HAMEL", "ZARIB_MAHAL",
        "CONTAINER_TYPE", "CONTAINER_NUMBER",
    ),
    "fa_tali_kala_diamound": (
        "kala_diamound_id", "code", "NUMBER_SERVICE", "pricing_type", "DESCRIPTION",
    ),
    "fa_tali_kala_price": ("kala_price_id", "code", "DESCRIPTION"),
    "fa_tali_kala_dangerous": ("kala_dangerous_id", "code", "DESCRIPTION"),
    "fa_tali_kala_other_service": (
        "kala_other_service_id", "code", "NUMBER_SERVICE", "DESCRIPTION",
    ),
    "fa_tali_kala_strip": (
        "kala_strip_id", "code", "NUMBER_SERVICE", "pricing_type", "DESCRIPTION",
    ),
    "fa_tali_kala_time_stop_vehicle": (
        "kala_time_stop_vehicle_id", "code", "NUMBER_SERVICE", "DESCRIPTION",
    ),
    "fa_tali_kala_vehicle_enter_price": (
        "kala_vehicle_enter_price_id", "code", "NUMBER_SERVICE", "DESCRIPTION",
    ),
    "fa_ghabz_anbar_header": (
        "number_ghabz", "number_ghabz_uniqe", "NUMBER_KARANEH", "NUMBER_tali",
        "number_royea", "number_kantiner", "number_mantaghe_azad", "DATE_UNLOADING",
        "number_mojavez_uuloading", "ID_MARZE", "number_MARZE", "DATE_ENTER_MARZE",
        "ID_COUNTRY", "weight", "number_sanad", "DATE_SANAD", "number_pigiri_anbar",
        "status_BIMEH", "NUMBER_BIMEH", "ID_COMPANY_bimeh", "ID_anbar",
        "ID_tagh_anbara", "ID_anbar_response", "ID_COMPANY", "ID_PRODUCT_OWNEAR",
        "asnad_rasmi", "NAME_ANBARDAR", "NAME_maneger", "COMPANY_BIMEH", "TALI_ID",
    ),
    "FA_ghabz_anbar_DETAILES": (
        "code_kala", "code_kala_kantiner", "DESCRIPTION_KALA", "TYPE_BASTEh",
        "NUMBER_KALA", "NUMBER_KAntiner", "WEIGHTE_asnad", "WEIGHTE_BASKOL",
        "NUMBER_HAMEL", "ID_TAGH_ANBAR",
    ),
}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _known_tables(cursor) -> dict[str, str]:
    cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
    return {str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()}


def _known_columns(cursor, table: str) -> dict[str, tuple[str, str]]:
    cursor.execute(
        """
        SELECT COLUMN_NAME, NULLABLE
          FROM USER_TAB_COLUMNS
         WHERE TABLE_NAME = :table_name
        """,
        {"table_name": table},
    )
    return {
        str(column).casefold(): (str(column), str(nullable))
        for column, nullable in cursor.fetchall()
    }


def main() -> None:
    changed = 0
    skipped = 0
    missing = 0
    failures: list[str] = []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            tables = _known_tables(cursor)
            for requested_table, requested_columns in OPTIONAL_COLUMNS.items():
                table = tables.get(requested_table.casefold())
                if table is None:
                    print(f"SKIP: table {requested_table} does not exist")
                    missing += 1
                    continue

                columns = _known_columns(cursor, table)
                for requested_column in requested_columns:
                    resolved = columns.get(requested_column.casefold())
                    if resolved is None:
                        print(f"SKIP: {table}.{requested_column} does not exist")
                        missing += 1
                        continue

                    column, nullable = resolved
                    if nullable == "Y":
                        print(f"SKIP: {table}.{column} is already optional")
                        skipped += 1
                        continue

                    try:
                        cursor.execute(
                            f"ALTER TABLE {_quote(table)} "
                            f"MODIFY ({_quote(column)} NULL)"
                        )
                        print(f"OK  : {table}.{column} is now optional")
                        changed += 1
                    except Exception as exc:  # keep checking so the report is complete
                        message = f"{table}.{column}: {exc}"
                        print(f"FAIL: {message}")
                        failures.append(message)

        connection.commit()

    print(
        f"done — changed={changed}, already_optional={skipped}, "
        f"missing_on_this_installation={missing}, failed={len(failures)}"
    )
    if failures:
        raise RuntimeError(
            "Some columns could not be made optional:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    main()
