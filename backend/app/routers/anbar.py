from fastapi import APIRouter, Depends, HTTPException

from app.services.base import fetch_all, fetch_one, execute, insert_returning_id
from app.auth.deps import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/anbar", tags=["anbar"])


class AnbarInput(BaseModel):
    name_anbar: str | None = None
    address: str | None = None
    responsible: str | None = None
    phone: str | None = None


@router.get("", dependencies=[Depends(get_current_user)])
def list_anbar():
    return fetch_all("""
        SELECT id_anbar, name_anbar, address, name_masol AS responsible, phone
        FROM FA_ANBAR
        WHERE is_deleted = 'no'
        ORDER BY id_anbar
    """)


@router.post("", status_code=201)
def create_anbar(item: AnbarInput, current_user: dict = Depends(get_current_user)):
    new_id = insert_returning_id("""
        INSERT INTO FA_ANBAR (id_anbar, name_anbar, address, name_masol, phone, is_deleted, create_at, create_by)
        VALUES (
            (SELECT NVL(MAX(id_anbar), 0) + 1 FROM FA_ANBAR),
            :name_anbar, :address, :name_masol, :phone, 'no', SYSDATE, :create_by
        )
        RETURNING id_anbar INTO :new_id
    """, {
        "name_anbar": item.name_anbar,
        "address": item.address,
        "name_masol": item.responsible,
        "phone": item.phone,
        "create_by": current_user["id"],
    })
    return fetch_one("SELECT * FROM FA_ANBAR WHERE id_anbar = :id", {"id": new_id})


@router.put("/{id_anbar}")
def update_anbar(id_anbar: int, item: AnbarInput, current_user: dict = Depends(get_current_user)):
    affected = execute("""
        UPDATE FA_ANBAR
        SET name_anbar = :name_anbar, address = :address,
            name_masol = :name_masol, phone = :phone,
            modify_at = SYSDATE, modify_by = :modify_by
        WHERE id_anbar = :id AND is_deleted = 'no'
    """, {
        "name_anbar": item.name_anbar, "address": item.address,
        "name_masol": item.responsible, "phone": item.phone,
        "modify_by": current_user["id"], "id": id_anbar,
    })
    if affected == 0:
        raise HTTPException(status_code=404, detail="انبار یافت نشد")
    return fetch_one("SELECT * FROM FA_ANBAR WHERE id_anbar = :id", {"id": id_anbar})


@router.delete("/{id_anbar}", status_code=204)
def delete_anbar(id_anbar: int, current_user: dict = Depends(get_current_user)):
    affected = execute("""
        UPDATE FA_ANBAR
        SET is_deleted = 'yes', modify_at = SYSDATE, modify_by = :modify_by
        WHERE id_anbar = :id AND is_deleted = 'no'
    """, {"modify_by": current_user["id"], "id": id_anbar})
    if affected == 0:
        raise HTTPException(status_code=404, detail="انبار یافت نشد")
