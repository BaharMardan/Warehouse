"""Permission-controlled, system-wide numeric settings.

Values here are deliberately kept separate from price catalogs: they are stable
business constants (for example VAT) that an administrator may update yearly.
Only users granted the settings permission can read or change them, so
configuration is never exposed as an ordinary base-data table.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import require_permission
from app.core.db import get_connection

router = APIRouter(prefix="/settings", tags=["settings"])

# This catalog is the contract consumed by the rest of the application. New
# durable settings are added here, seeded in the migration and rendered by the
# front-end without letting callers create arbitrary keys.
SETTINGS = {
    "tax_rate": {
        "title": "نرخ مالیات بر ارزش افزوده",
        "value": Decimal("10"),
        "unit": "درصد",
        "description": "درصد مالیات قابل اعمال به مبلغ صورتحساب.",
    },
    "freight_rate": {
        "title": "نرخ پایه باربری",
        "value": Decimal("0"),
        "unit": "ریال",
        "description": "مبلغ پایه باربری؛ مبنای محاسبهٔ باربری در بخش‌های مرتبط.",
    },
    "system_service_rate": {
        "title": "نرخ خدمات سیستمی",
        "value": Decimal("0"),
        "unit": "ریال",
        "description": "مبلغ ثابت خدمات سیستمی، قابل استفاده در صورتحساب.",
    },
}


class SettingInput(BaseModel):
    value_number: Decimal = Field(ge=0, max_digits=18, decimal_places=4)


def _serialize(key: str, row: dict | None) -> dict:
    definition = SETTINGS[key]
    value = definition["value"] if row is None else Decimal(str(row["value_number"]))
    return {
        "key": key,
        "title": definition["title"],
        "value_number": str(value),
        "unit": definition["unit"],
        "description": definition["description"],
    }


@router.get("", dependencies=[Depends(require_permission("settings.manage"))])
def list_settings() -> list[dict]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT "SETTING_KEY" AS setting_key, "VALUE_NUMBER" AS value_number '
                'FROM "FA_APP_SETTINGS"'
            )
            rows = {
                row[0]: {"value_number": row[1]}
                for row in cursor.fetchall()
                if row[0] in SETTINGS
            }
    return [_serialize(key, rows.get(key)) for key in SETTINGS]


@router.put("/{setting_key}", dependencies=[Depends(require_permission("settings.manage"))])
def update_setting(
    setting_key: str,
    payload: SettingInput,
    current_user: dict = Depends(require_permission("settings.manage")),
) -> dict:
    if setting_key not in SETTINGS:
        raise HTTPException(status_code=404, detail="تنظیمات موردنظر یافت نشد")

    definition = SETTINGS[setting_key]
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                '''MERGE INTO "FA_APP_SETTINGS" target
                   USING (SELECT :setting_key AS setting_key FROM DUAL) source
                      ON (target."SETTING_KEY" = source.setting_key)
                   WHEN MATCHED THEN UPDATE SET
                     target."VALUE_NUMBER" = :value_number,
                     target."MODIFY_AT" = SYSDATE,
                     target."MODIFY_BY" = :actor_id
                   WHEN NOT MATCHED THEN INSERT
                     ("SETTING_KEY", "TITLE", "VALUE_NUMBER", "UNIT", "DESCRIPTION", "MODIFY_AT", "MODIFY_BY")
                   VALUES
                     (:setting_key, :title, :value_number, :unit, :description, SYSDATE, :actor_id)''',
                {
                    "setting_key": setting_key,
                    "value_number": payload.value_number,
                    "title": definition["title"],
                    "unit": definition["unit"],
                    "description": definition["description"],
                    "actor_id": current_user["id"],
                },
            )
        connection.commit()
    return _serialize(setting_key, {"value_number": payload.value_number})
