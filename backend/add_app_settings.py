"""Create the shared application-settings table and seed its initial values.

Run once against Oracle with the API stopped:

    python add_app_settings.py
"""

from app.core.db import get_connection
from app.routers.settings import SETTINGS


TABLE = "FA_APP_SETTINGS"


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM USER_TABLES WHERE TABLE_NAME = :table_name", {"table_name": TABLE})
            if cursor.fetchone() is None:
                cursor.execute('''CREATE TABLE "FA_APP_SETTINGS" (
                    "SETTING_KEY" VARCHAR2(100 CHAR) PRIMARY KEY,
                    "TITLE" VARCHAR2(250 CHAR) NOT NULL,
                    "VALUE_NUMBER" NUMBER(18,4) NOT NULL,
                    "UNIT" VARCHAR2(50 CHAR),
                    "DESCRIPTION" VARCHAR2(1000 CHAR),
                    "MODIFY_AT" DATE,
                    "MODIFY_BY" NUMBER
                )''')
                print(f"OK: created {TABLE}")
            else:
                print(f"SKIP: {TABLE} already exists")

            # This setting was intentionally removed from the product settings.
            cursor.execute(f'DELETE FROM "{TABLE}" WHERE "SETTING_KEY" = :setting_key', {
                "setting_key": "invoice_due_days",
            })

            for key, setting in SETTINGS.items():
                cursor.execute(
                    f'''INSERT INTO "{TABLE}" ("SETTING_KEY", "TITLE", "VALUE_NUMBER", "UNIT", "DESCRIPTION")
                        SELECT :setting_key, :title, :value_number, :unit, :description FROM DUAL
                         WHERE NOT EXISTS (
                           SELECT 1 FROM "{TABLE}" WHERE "SETTING_KEY" = :setting_key
                         )''',
                    {
                        "setting_key": key,
                        "title": setting["title"],
                        "value_number": setting["value"],
                        "unit": setting["unit"],
                        "description": setting["description"],
                    },
                )
            connection.commit()
            print(f"OK: ensured {len(SETTINGS)} application settings")


if __name__ == "__main__":
    main()
