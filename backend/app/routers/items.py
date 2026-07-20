from fastapi import APIRouter, Depends, HTTPException

from app.services.base import fetch_all, fetch_one, execute, insert_returning_id
from app.auth.deps import get_current_user
from app.schemas.item import ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", dependencies=[Depends(get_current_user)])
def list_items():
    sql = """
        SELECT id_kala, name_kala, unite, create_at, create_by, modify_at, modify_by
        FROM FA_KALA
        WHERE is_deleted = 'no'
        ORDER BY id_kala
    """
    return fetch_all(sql)


@router.post("", status_code=201)
def create_item(item: ItemCreate, current_user: dict = Depends(get_current_user)):
    new_id = insert_returning_id(
        """
        INSERT INTO FA_KALA (id_kala, name_kala, unite, is_deleted, create_at, create_by)
        VALUES (
            (SELECT NVL(MAX(id_kala), 0) + 1 FROM FA_KALA),
            :name_kala, :unite, 'no', SYSDATE, :create_by
        )
        RETURNING id_kala INTO :new_id
        """,
        {
            "name_kala": item.name_kala,
            "unite": item.unite,
            "create_by": current_user["id"],
        },
    )
    return fetch_one("SELECT * FROM FA_KALA WHERE id_kala = :id", {"id": new_id})


@router.put("/{id_kala}")
def update_item(
    id_kala: int, item: ItemUpdate, current_user: dict = Depends(get_current_user)
):
    affected = execute(
        """
        UPDATE FA_KALA
        SET name_kala = :name_kala,
            unite = :unite,
            modify_at = SYSDATE,
            modify_by = :modify_by
        WHERE id_kala = :id AND is_deleted = 'no'
        """,
        {
            "name_kala": item.name_kala,
            "unite": item.unite,
            "modify_by": current_user["id"],
            "id": id_kala,
        },
    )
    if affected == 0:
        raise HTTPException(status_code=404, detail="کالا یافت نشد")
    return fetch_one("SELECT * FROM FA_KALA WHERE id_kala = :id", {"id": id_kala})


@router.delete("/{id_kala}", status_code=204)
def delete_item(id_kala: int, current_user: dict = Depends(get_current_user)):
    affected = execute(
        """
        UPDATE FA_KALA
        SET is_deleted = 'yes',
            modify_at = SYSDATE,
            modify_by = :modify_by
        WHERE id_kala = :id AND is_deleted = 'no'
        """,
        {"modify_by": current_user["id"], "id": id_kala},
    )
    if affected == 0:
        raise HTTPException(status_code=404, detail="کالا یافت نشد")