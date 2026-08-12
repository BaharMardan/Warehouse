"""Cargo-owner management with nested representatives for legal entities.

Transport-company representatives intentionally remain a separate concern.  This
router owns only FA_PRODUCT_OWNER and FA_OWNER_REPRESENTATIVE and saves both in a
single transaction so an owner can never be left with a half-saved representative
list.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, model_validator

from app.auth.deps import get_current_user
from app.core.db import get_connection


router = APIRouter(prefix="/owners", tags=["owners"])

OWNER_TABLE = '"FA_PRODUCT_OWNER"'
REPRESENTATIVE_TABLE = '"FA_OWNER_REPRESENTATIVE"'


class OwnerRepresentativeInput(BaseModel):
    name: str | None = None
    family: str | None = None
    national_code: str | None = None
    mobile: str | None = None


class OwnerInput(BaseModel):
    type: Literal["حقیقی", "حقوقی"] = "حقیقی"
    name: str | None = None
    family: str | None = None
    national_code: str | None = None
    company_name: str | None = None
    address: str | None = None
    phone: str | None = None
    national_id: str | None = None
    economic_code: str | None = None
    representatives: list[OwnerRepresentativeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_owner_fields(self):
        national_codes = [
            representative.national_code.strip()
            for representative in self.representatives
            if representative.national_code and representative.national_code.strip()
        ]
        if len(national_codes) != len(set(national_codes)):
            raise ValueError("کد ملی نمایندگان یک صاحب کالا نباید تکراری باشد")
        return self


OWNER_SELECT = f"""
SELECT
    "ID_OWNER",
    "TYPE" AS type,
    "NAME" AS name,
    "FAMILY" AS family,
    "NATIONAL_CODE" AS national_code,
    "COMPANY_NAME" AS company_name,
    "ADDRESS" AS address,
    "PHONE" AS phone,
    "NATIONAL_ID" AS national_id,
    "ECONOMIC_CODE" AS economic_code
FROM {OWNER_TABLE}
"""


def _rows(cursor) -> list[dict]:
    columns = [column[0].lower() for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _load_owners(cursor, owner_id: int | None = None) -> list[dict]:
    params: dict[str, int] = {}
    where = ""
    if owner_id is not None:
        where = ' WHERE "ID_OWNER" = :owner_id'
        params["owner_id"] = owner_id

    cursor.execute(
        OWNER_SELECT
        + where
        + " ORDER BY CASE WHEN \"TYPE\" = 'حقوقی' THEN \"COMPANY_NAME\" "
          "ELSE \"FAMILY\" END, \"ID_OWNER\"",
        params,
    )
    owners = _rows(cursor)
    if not owners:
        return []

    owner_ids = [int(owner["id_owner"]) for owner in owners]
    placeholders = ", ".join(f":owner_{index}" for index in range(len(owner_ids)))
    cursor.execute(
        f"""
        SELECT
            "ID_OWNER_REPRESENTATIVE",
            "ID_OWNER",
            "NAME" AS name,
            "FAMILY" AS family,
            "NATIONAL_CODE" AS national_code,
            "MOBILE" AS mobile
        FROM {REPRESENTATIVE_TABLE}
        WHERE "ID_OWNER" IN ({placeholders})
        ORDER BY "FAMILY", "NAME", "ID_OWNER_REPRESENTATIVE"
        """,
        {f"owner_{index}": value for index, value in enumerate(owner_ids)},
    )
    representatives = _rows(cursor)
    grouped: dict[int, list[dict]] = {owner_id_value: [] for owner_id_value in owner_ids}
    for representative in representatives:
        grouped[int(representative["id_owner"])].append(representative)
    for owner in owners:
        owner["representatives"] = grouped[int(owner["id_owner"])]
    return owners


def _normalized_payload(item: OwnerInput) -> dict:
    payload = item.model_dump(exclude={"representatives"})
    for key, value in payload.items():
        if isinstance(value, str):
            stripped = value.strip()
            payload[key] = stripped or None

    # Keep the two owner types semantically clean even if a user switches type
    # while editing an existing row.
    if payload["type"] == "حقیقی":
        payload["company_name"] = None
        payload["national_id"] = None
        payload["economic_code"] = None
    else:
        payload["name"] = None
        payload["family"] = None
        payload["national_code"] = None
    return payload


def _replace_representatives(cursor, owner_id: int, item: OwnerInput, actor_id: int) -> None:
    cursor.execute(
        f'DELETE FROM {REPRESENTATIVE_TABLE} WHERE "ID_OWNER" = :owner_id',
        {"owner_id": owner_id},
    )
    if item.type != "حقوقی":
        return

    for representative in item.representatives:
        data = representative.model_dump()
        for key, value in data.items():
            stripped = value.strip() if isinstance(value, str) else ""
            data[key] = stripped or None
        if not any(data.values()):
            continue
        cursor.execute(
            f"""
            INSERT INTO {REPRESENTATIVE_TABLE} (
                "ID_OWNER", "NAME", "FAMILY",
                "NATIONAL_CODE", "MOBILE", "CREATE_AT", "CREATE_BY"
            ) VALUES (
                :owner_id, :name, :family,
                :national_code, :mobile, SYSDATE, :actor_id
            )
            """,
            {**data, "owner_id": owner_id, "actor_id": actor_id},
        )


@router.get("", dependencies=[Depends(get_current_user)])
def list_owners():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            return _load_owners(cursor)


@router.get("/{owner_id}", dependencies=[Depends(get_current_user)])
def get_owner(owner_id: int):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            rows = _load_owners(cursor, owner_id)
    if not rows:
        raise HTTPException(status_code=404, detail="صاحب کالا یافت نشد")
    return rows[0]


@router.post("", status_code=201)
def create_owner(item: OwnerInput, current_user: dict = Depends(get_current_user)):
    payload = _normalized_payload(item)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            new_id = cursor.var(int)
            cursor.execute(
                f"""
                INSERT INTO {OWNER_TABLE} (
                    "TYPE", "NAME", "FAMILY", "NATIONAL_CODE",
                    "COMPANY_NAME", "ADDRESS", "PHONE", "NATIONAL_ID", "ECONOMIC_CODE"
                ) VALUES (
                    :type, :name, :family, :national_code,
                    :company_name, :address, :phone, :national_id, :economic_code
                )
                RETURNING "ID_OWNER" INTO :new_id
                """,
                {**payload, "new_id": new_id},
            )
            owner_id = int(new_id.getvalue()[0])
            _replace_representatives(cursor, owner_id, item, int(current_user["id"]))
            connection.commit()
            return _load_owners(cursor, owner_id)[0]


@router.put("/{owner_id}")
def update_owner(
    owner_id: int,
    item: OwnerInput,
    current_user: dict = Depends(get_current_user),
):
    payload = _normalized_payload(item)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE {OWNER_TABLE}
                   SET "TYPE" = :type,
                       "NAME" = :name,
                       "FAMILY" = :family,
                       "NATIONAL_CODE" = :national_code,
                       "COMPANY_NAME" = :company_name,
                       "ADDRESS" = :address,
                       "PHONE" = :phone,
                       "NATIONAL_ID" = :national_id,
                       "ECONOMIC_CODE" = :economic_code
                 WHERE "ID_OWNER" = :owner_id
                """,
                {**payload, "owner_id": owner_id},
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="صاحب کالا یافت نشد")
            _replace_representatives(cursor, owner_id, item, int(current_user["id"]))
            connection.commit()
            return _load_owners(cursor, owner_id)[0]


@router.delete("/{owner_id}", status_code=204)
def delete_owner(owner_id: int, current_user: dict = Depends(get_current_user)):
    del current_user  # Authentication is the intended side effect of this dependency.
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f'DELETE FROM {OWNER_TABLE} WHERE "ID_OWNER" = :owner_id',
                {"owner_id": owner_id},
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="صاحب کالا یافت نشد")
            connection.commit()
    return Response(status_code=204)
