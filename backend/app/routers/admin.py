"""مدیریت کاربران: users, roles and the permissions each role grants.

Every endpoint is admin-only (FA_USERS.IS_ADMIN = 'yes'). Anyone who can edit
roles can grant themselves any permission, so this is never delegated through
a permission code.

    GET    /admin/permissions           the catalog, for the role editor
    GET    /admin/roles                 active roles with their codes and user counts
    POST   /admin/roles                 create a role
    PUT    /admin/roles/{id}            rename, describe, replace its permissions
    DELETE /admin/roles/{id}            soft-delete; its user assignments are removed
    GET    /admin/users                 users with their roles, never password hashes
    POST   /admin/users                 create a user with a password and roles
    PUT    /admin/users/{id}            name, admin and active flags, replace roles
    PUT    /admin/users/{id}/password   set a new password

Users are deactivated, never deleted: other tables keep their ids in CREATE_BY
and MODIFY_BY. Usernames never change, because the login token carries the
username. Changes take effect on the affected user's next request, since
get_current_user reads the user and their permissions fresh every time.

The SQL is kept in module constants so verify_user_admin_sql.py runs the exact
same statements against the real schema.
"""

from typing import Literal

import oracledb
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth import permissions
from app.auth.deps import require_admin
from app.core.db import get_connection
from app.core.security import hash_password
from app.services import user_admin as rules

router = APIRouter(prefix="/admin", tags=["admin"])

YesNo = Literal["yes", "no"]


class RoleInput(BaseModel):
    title: str
    description: str | None = None
    permissions: list[str] = []


class UserCreateInput(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    is_admin: YesNo = "no"
    is_active: YesNo = "yes"
    role_ids: list[int] = []


class UserUpdateInput(BaseModel):
    full_name: str | None = None
    is_admin: YesNo
    is_active: YesNo
    role_ids: list[int] = []


class PasswordInput(BaseModel):
    password: str


# ------------------------------------------------------------------ roles SQL
ROLES_SQL = """
SELECT r."ID" AS id,
       r."TITLE" AS title,
       r."DESCRIPTION" AS description,
       (SELECT COUNT(*) FROM "FA_USER_ROLES" ur WHERE ur."ROLE_ID" = r."ID") AS user_count
  FROM "FA_ROLES" r
 WHERE r."IS_DELETED" = 'no'
 ORDER BY r."TITLE", r."ID"
"""

ROLE_PERMISSIONS_SQL = """
SELECT rp."ROLE_ID" AS role_id,
       rp."PERMISSION_CODE" AS permission_code
  FROM "FA_ROLE_PERMISSIONS" rp
  JOIN "FA_ROLES" r
    ON r."ID" = rp."ROLE_ID"
   AND r."IS_DELETED" = 'no'
"""

# :role_id is the role being edited, or -1 when creating (identity ids start at 1).
ROLE_TITLE_TAKEN_SQL = """
SELECT COUNT(*) AS taken
  FROM "FA_ROLES"
 WHERE "IS_DELETED" = 'no'
   AND LOWER("TITLE") = LOWER(:title)
   AND "ID" <> :role_id
"""

INSERT_ROLE_SQL = """
INSERT INTO "FA_ROLES" ("TITLE", "DESCRIPTION", "CREATE_AT", "CREATE_BY")
VALUES (:title, :description, SYSDATE, :actor_id)
RETURNING "ID" INTO :new_id
"""

UPDATE_ROLE_SQL = """
UPDATE "FA_ROLES"
   SET "TITLE" = :title,
       "DESCRIPTION" = :description,
       "MODIFY_AT" = SYSDATE,
       "MODIFY_BY" = :actor_id
 WHERE "ID" = :role_id
   AND "IS_DELETED" = 'no'
"""

DELETE_ROLE_PERMISSIONS_SQL = 'DELETE FROM "FA_ROLE_PERMISSIONS" WHERE "ROLE_ID" = :role_id'

INSERT_ROLE_PERMISSION_SQL = """
INSERT INTO "FA_ROLE_PERMISSIONS" ("ROLE_ID", "PERMISSION_CODE", "CREATE_AT", "CREATE_BY")
VALUES (:role_id, :code, SYSDATE, :actor_id)
"""

SOFT_DELETE_ROLE_SQL = """
UPDATE "FA_ROLES"
   SET "IS_DELETED" = 'yes',
       "MODIFY_AT" = SYSDATE,
       "MODIFY_BY" = :actor_id
 WHERE "ID" = :role_id
   AND "IS_DELETED" = 'no'
"""

DELETE_ROLE_ASSIGNMENTS_SQL = 'DELETE FROM "FA_USER_ROLES" WHERE "ROLE_ID" = :role_id'

# Filled with one bind per id: ACTIVE_ROLE_IDS_SQL.format(placeholders=":r0, :r1").
ACTIVE_ROLE_IDS_SQL = """
SELECT "ID"
  FROM "FA_ROLES"
 WHERE "IS_DELETED" = 'no'
   AND "ID" IN ({placeholders})
"""

# ------------------------------------------------------------------ users SQL
USERS_SQL = """
SELECT "ID" AS id,
       "USERNAME" AS username,
       "FULL_NAME" AS full_name,
       "IS_ADMIN" AS is_admin,
       "IS_ACTIVE" AS is_active
  FROM "FA_USERS"
 ORDER BY LOWER("USERNAME"), "ID"
"""

USER_ROLES_SQL = """
SELECT ur."USER_ID" AS user_id,
       r."ID" AS id,
       r."TITLE" AS title
  FROM "FA_USER_ROLES" ur
  JOIN "FA_ROLES" r
    ON r."ID" = ur."ROLE_ID"
   AND r."IS_DELETED" = 'no'
 ORDER BY r."TITLE", r."ID"
"""

# The unique constraint on USERNAME is case-sensitive; "Ali" and "ali" as two
# accounts would only confuse people, so the check here ignores case.
USERNAME_TAKEN_SQL = """
SELECT COUNT(*) AS taken
  FROM "FA_USERS"
 WHERE LOWER("USERNAME") = LOWER(:username)
"""

# FA_USERS.CREATE_BY and MODIFY_BY are VARCHAR2, unlike the NUMBER columns on
# other tables, so they record the acting admin's username.
INSERT_USER_SQL = """
INSERT INTO "FA_USERS" (
    "USERNAME", "PASSWORD_HASH", "FULL_NAME", "IS_ADMIN", "IS_ACTIVE", "CREATE_AT", "CREATE_BY"
) VALUES (
    :username, :password_hash, :full_name, :is_admin, :is_active, SYSDATE, :actor_username
)
RETURNING "ID" INTO :new_id
"""

UPDATE_USER_SQL = """
UPDATE "FA_USERS"
   SET "FULL_NAME" = :full_name,
       "IS_ADMIN" = :is_admin,
       "IS_ACTIVE" = :is_active,
       "MODIFY_AT" = SYSDATE,
       "MODIFY_BY" = :actor_username
 WHERE "ID" = :user_id
"""

DELETE_USER_ROLES_SQL = 'DELETE FROM "FA_USER_ROLES" WHERE "USER_ID" = :user_id'

INSERT_USER_ROLE_SQL = """
INSERT INTO "FA_USER_ROLES" ("USER_ID", "ROLE_ID", "CREATE_AT", "CREATE_BY")
VALUES (:user_id, :role_id, SYSDATE, :actor_id)
"""

SET_PASSWORD_SQL = """
UPDATE "FA_USERS"
   SET "PASSWORD_HASH" = :password_hash,
       "MODIFY_AT" = SYSDATE,
       "MODIFY_BY" = :actor_username
 WHERE "ID" = :user_id
"""


# ------------------------------------------------------------------ helpers
def _rows(cursor) -> list[dict]:
    columns = [column[0].lower() for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _returned_int(value) -> int:
    result = value.getvalue()
    if isinstance(result, (list, tuple)):
        result = result[0]
    return int(result)


def _reject(message: str | None, status_code: int = 400) -> None:
    if message:
        raise HTTPException(status_code=status_code, detail=message)


def load_roles(cursor, role_id: int | None = None) -> list[dict]:
    cursor.execute(ROLES_SQL)
    roles = _rows(cursor)
    cursor.execute(ROLE_PERMISSIONS_SQL)
    granted: dict[int, set[str]] = {}
    for row in _rows(cursor):
        granted.setdefault(int(row["role_id"]), set()).add(row["permission_code"])
    for role in roles:
        codes = granted.get(int(role["id"]), set())
        # Catalog order; codes no longer in the catalog grant nothing and are hidden.
        role["permissions"] = [p.code for p in permissions.PERMISSIONS if p.code in codes]
        role["user_count"] = int(role["user_count"])
    if role_id is not None:
        roles = [role for role in roles if int(role["id"]) == role_id]
    return roles


def load_users(cursor, user_id: int | None = None) -> list[dict]:
    cursor.execute(USERS_SQL)
    users = _rows(cursor)
    cursor.execute(USER_ROLES_SQL)
    roles_by_user: dict[int, list[dict]] = {}
    for row in _rows(cursor):
        roles_by_user.setdefault(int(row["user_id"]), []).append(
            {"id": int(row["id"]), "title": row["title"]}
        )
    for user in users:
        user["roles"] = roles_by_user.get(int(user["id"]), [])
    if user_id is not None:
        users = [user for user in users if int(user["id"]) == user_id]
    return users


def active_role_ids(cursor, role_ids: list[int]) -> list[int]:
    """The requested ids without duplicates; 400 if any is missing or deleted."""
    wanted = list(dict.fromkeys(int(role_id) for role_id in role_ids))
    if not wanted:
        return []
    binds = {f"r{index}": role_id for index, role_id in enumerate(wanted)}
    cursor.execute(
        ACTIVE_ROLE_IDS_SQL.format(placeholders=", ".join(f":{name}" for name in binds)),
        binds,
    )
    found = {int(row[0]) for row in cursor.fetchall()}
    if any(role_id not in found for role_id in wanted):
        raise HTTPException(status_code=400, detail="یکی از نقش‌های انتخاب‌شده وجود ندارد یا حذف شده است")
    return wanted


def replace_role_permissions(cursor, role_id: int, codes: list[str], actor_id: int) -> None:
    cursor.execute(DELETE_ROLE_PERMISSIONS_SQL, {"role_id": role_id})
    if codes:
        cursor.executemany(
            INSERT_ROLE_PERMISSION_SQL,
            [{"role_id": role_id, "code": code, "actor_id": actor_id} for code in codes],
        )


def replace_user_roles(cursor, user_id: int, role_ids: list[int], actor_id: int) -> None:
    cursor.execute(DELETE_USER_ROLES_SQL, {"user_id": user_id})
    if role_ids:
        cursor.executemany(
            INSERT_USER_ROLE_SQL,
            [{"user_id": user_id, "role_id": role_id, "actor_id": actor_id} for role_id in role_ids],
        )


def _validated_role(item: RoleInput) -> tuple[str, str | None, list[str]]:
    title = rules.clean_text(item.title)
    description = rules.clean_text(item.description)
    _reject(rules.role_title_error(title) or rules.role_description_error(description))
    codes, unknown = rules.split_permission_codes(item.permissions)
    _reject(f"دسترسی ناشناخته: {', '.join(unknown)}" if unknown else None)
    return title, description, codes  # type: ignore[return-value]


def _ensure_title_free(cursor, title: str, role_id: int) -> None:
    cursor.execute(ROLE_TITLE_TAKEN_SQL, {"title": title, "role_id": role_id})
    _reject("نقشی با همین عنوان وجود دارد" if int(cursor.fetchone()[0]) else None, status_code=409)


# ------------------------------------------------------------------ endpoints
@router.get("/permissions", dependencies=[Depends(require_admin)])
def list_permissions():
    return [
        {"code": p.code, "label": p.label, "module": p.module, "implies": list(p.implies)}
        for p in permissions.PERMISSIONS
    ]


@router.get("/roles", dependencies=[Depends(require_admin)])
def list_roles():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            return load_roles(cursor)


@router.post("/roles", status_code=201)
def create_role(item: RoleInput, admin: dict = Depends(require_admin)):
    title, description, codes = _validated_role(item)
    actor_id = int(admin["id"])
    with get_connection() as connection:
        with connection.cursor() as cursor:
            _ensure_title_free(cursor, title, role_id=-1)
            new_id = cursor.var(int)
            cursor.execute(
                INSERT_ROLE_SQL,
                {"title": title, "description": description, "actor_id": actor_id, "new_id": new_id},
            )
            role_id = _returned_int(new_id)
            replace_role_permissions(cursor, role_id, codes, actor_id)
            connection.commit()
            return load_roles(cursor, role_id)[0]


@router.put("/roles/{role_id}")
def update_role(role_id: int, item: RoleInput, admin: dict = Depends(require_admin)):
    title, description, codes = _validated_role(item)
    actor_id = int(admin["id"])
    with get_connection() as connection:
        with connection.cursor() as cursor:
            _ensure_title_free(cursor, title, role_id=role_id)
            cursor.execute(
                UPDATE_ROLE_SQL,
                {"title": title, "description": description, "actor_id": actor_id, "role_id": role_id},
            )
            _reject("نقش یافت نشد" if cursor.rowcount == 0 else None, status_code=404)
            replace_role_permissions(cursor, role_id, codes, actor_id)
            connection.commit()
            return load_roles(cursor, role_id)[0]


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: int, admin: dict = Depends(require_admin)):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(SOFT_DELETE_ROLE_SQL, {"role_id": role_id, "actor_id": int(admin["id"])})
            _reject("نقش یافت نشد" if cursor.rowcount == 0 else None, status_code=404)
            # A deleted role grants nothing already; dropping its assignments keeps
            # the user list honest and stops a later restore from re-granting silently.
            cursor.execute(DELETE_ROLE_ASSIGNMENTS_SQL, {"role_id": role_id})
            connection.commit()
    return Response(status_code=204)


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            return load_users(cursor)


@router.post("/users", status_code=201)
def create_user(item: UserCreateInput, admin: dict = Depends(require_admin)):
    username = item.username.strip()
    full_name = rules.clean_text(item.full_name)
    _reject(
        rules.username_error(username)
        or rules.password_error(item.password)
        or rules.full_name_error(full_name)
    )
    # Hash before borrowing a pooled connection: argon2 is deliberately slow.
    password_hash = hash_password(item.password)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(USERNAME_TAKEN_SQL, {"username": username})
            _reject("این نام کاربری قبلاً ثبت شده است" if int(cursor.fetchone()[0]) else None, status_code=409)
            role_ids = active_role_ids(cursor, item.role_ids)
            new_id = cursor.var(int)
            try:
                cursor.execute(
                    INSERT_USER_SQL,
                    {
                        "username": username,
                        "password_hash": password_hash,
                        "full_name": full_name,
                        "is_admin": item.is_admin,
                        "is_active": item.is_active,
                        "actor_username": admin["username"],
                        "new_id": new_id,
                    },
                )
            except oracledb.IntegrityError as exc:
                # Two admins creating the same name at the same moment.
                if "ORA-00001" in str(exc):
                    raise HTTPException(status_code=409, detail="این نام کاربری قبلاً ثبت شده است") from exc
                raise
            user_id = _returned_int(new_id)
            replace_user_roles(cursor, user_id, role_ids, int(admin["id"]))
            connection.commit()
            return load_users(cursor, user_id)[0]


@router.put("/users/{user_id}")
def update_user(user_id: int, item: UserUpdateInput, admin: dict = Depends(require_admin)):
    full_name = rules.clean_text(item.full_name)
    _reject(
        rules.full_name_error(full_name)
        or rules.self_lockout_error(
            actor_id=int(admin["id"]), target_id=user_id,
            is_admin=item.is_admin, is_active=item.is_active,
        )
    )
    with get_connection() as connection:
        with connection.cursor() as cursor:
            role_ids = active_role_ids(cursor, item.role_ids)
            cursor.execute(
                UPDATE_USER_SQL,
                {
                    "full_name": full_name,
                    "is_admin": item.is_admin,
                    "is_active": item.is_active,
                    "actor_username": admin["username"],
                    "user_id": user_id,
                },
            )
            _reject("کاربر یافت نشد" if cursor.rowcount == 0 else None, status_code=404)
            replace_user_roles(cursor, user_id, role_ids, int(admin["id"]))
            connection.commit()
            return load_users(cursor, user_id)[0]


@router.put("/users/{user_id}/password", status_code=204)
def set_password(user_id: int, item: PasswordInput, admin: dict = Depends(require_admin)):
    _reject(rules.password_error(item.password))
    password_hash = hash_password(item.password)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                SET_PASSWORD_SQL,
                {"password_hash": password_hash, "actor_username": admin["username"], "user_id": user_id},
            )
            _reject("کاربر یافت نشد" if cursor.rowcount == 0 else None, status_code=404)
            connection.commit()
    return Response(status_code=204)
