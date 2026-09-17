"""Run every SQL statement behind the user-management screens, then roll back.

The admin endpoints are tested without Oracle, so this script is the check
against the real schema. On one connection it creates a throwaway role and
user with the exact statements and helpers in app/routers/admin.py, reads them
back through the queries the screens use, edits, reassigns, deactivates,
resets the password and soft-deletes, checking each result. Then it rolls the
whole transaction back, so nothing is kept.

The two INSERTs each consume one identity value, which leaves a gap in the ids;
Oracle's identity cache already leaves gaps like that after every restart.

    python verify_user_admin_sql.py
"""

from contextlib import contextmanager

from fastapi import HTTPException

from app.auth import permissions
from app.auth.deps import GRANTED_PERMISSIONS_SQL
from app.core.db import get_connection
from app.core.security import hash_password
from app.routers import admin as A

NAME = "__verify_user_admin__"
ACTOR_ID = 0
ACTOR_USERNAME = "verify_user_admin_sql"

failures: list[str] = []


def check(label: str, ok: bool, detail: object = "") -> None:
    print(f"OK  : {label}" if ok else f"FAIL: {label} (got {detail!r})")
    if not ok:
        failures.append(label)


@contextmanager
def step(name: str):
    try:
        yield
    except Exception as exc:  # stop at the first statement Oracle rejects
        print(f"FAIL: {name}: {exc}")
        failures.append(name)
        raise


def granted(cursor, user_id: int) -> set[str]:
    cursor.execute(GRANTED_PERMISSIONS_SQL, {"user_id": user_id})
    codes = [row[0] for row in cursor.fetchall()]
    return set(permissions.effective_permissions(is_admin=False, granted=codes))


def run(connection) -> None:
    with connection.cursor() as cursor:
        with step("username check"):
            cursor.execute(A.USERNAME_TAKEN_SQL, {"username": NAME})
            check("throwaway username is free", int(cursor.fetchone()[0]) == 0)

        with step("create role"):
            A._ensure_title_free(cursor, NAME, role_id=-1)
            new_id = cursor.var(int)
            cursor.execute(A.INSERT_ROLE_SQL, {
                "title": NAME, "description": "verify", "actor_id": ACTOR_ID, "new_id": new_id,
            })
            role_id = A._returned_int(new_id)
            A.replace_role_permissions(cursor, role_id, ["tally.view", "ghabz.issue"], ACTOR_ID)
            role = A.load_roles(cursor, role_id)
            check("role reads back with catalog-ordered permissions",
                  len(role) == 1 and role[0]["permissions"] == ["tally.view", "ghabz.issue"], role)

        with step("title uniqueness"):
            cursor.execute(A.ROLE_TITLE_TAKEN_SQL, {"title": NAME.upper(), "role_id": -1})
            check("same title in other letter case is taken", int(cursor.fetchone()[0]) == 1)
            cursor.execute(A.ROLE_TITLE_TAKEN_SQL, {"title": NAME, "role_id": role_id})
            check("a role does not collide with itself", int(cursor.fetchone()[0]) == 0)

        with step("role id validation"):
            check("active role id accepted", A.active_role_ids(cursor, [role_id, role_id]) == [role_id])
            try:
                A.active_role_ids(cursor, [role_id, -5])
                check("unknown role id rejected", False, "no error")
            except HTTPException as exc:
                check("unknown role id rejected", exc.status_code == 400, exc.status_code)

        with step("create user"):
            new_id = cursor.var(int)
            cursor.execute(A.INSERT_USER_SQL, {
                "username": NAME, "password_hash": hash_password("verify-pass-1"), "full_name": "کاربر آزمایشی",
                "is_admin": "no", "is_active": "yes", "actor_username": ACTOR_USERNAME, "new_id": new_id,
            })
            user_id = A._returned_int(new_id)
            A.replace_user_roles(cursor, user_id, [role_id], ACTOR_ID)
            user = A.load_users(cursor, user_id)
            check("user reads back with the role, Persian name intact",
                  len(user) == 1 and user[0]["roles"] == [{"id": role_id, "title": NAME}]
                  and user[0]["full_name"] == "کاربر آزمایشی", user)
            check("role counts its user", A.load_roles(cursor, role_id)[0]["user_count"] == 1)
            check("login-time permissions include implied codes",
                  granted(cursor, user_id) == {"tally.view", "ghabz.issue", "ghabz.view"}, granted(cursor, user_id))

        with step("edit role"):
            cursor.execute(A.UPDATE_ROLE_SQL, {
                "title": NAME, "description": None, "actor_id": ACTOR_ID, "role_id": role_id,
            })
            check("role update touched one row", cursor.rowcount == 1, cursor.rowcount)
            A.replace_role_permissions(cursor, role_id, ["invoice.view"], ACTOR_ID)
            check("user's permissions follow the role at once", granted(cursor, user_id) == {"invoice.view"})

        with step("edit user and password"):
            cursor.execute(A.UPDATE_USER_SQL, {
                "full_name": None, "is_admin": "no", "is_active": "no",
                "actor_username": ACTOR_USERNAME, "user_id": user_id,
            })
            check("user update touched one row", cursor.rowcount == 1, cursor.rowcount)
            check("deactivation reads back", A.load_users(cursor, user_id)[0]["is_active"] == "no")
            cursor.execute(A.SET_PASSWORD_SQL, {
                "password_hash": hash_password("verify-pass-2"), "actor_username": ACTOR_USERNAME, "user_id": user_id,
            })
            check("password update touched one row", cursor.rowcount == 1, cursor.rowcount)

        with step("delete role"):
            cursor.execute(A.SOFT_DELETE_ROLE_SQL, {"role_id": role_id, "actor_id": ACTOR_ID})
            check("soft delete touched one row", cursor.rowcount == 1, cursor.rowcount)
            cursor.execute(A.DELETE_ROLE_ASSIGNMENTS_SQL, {"role_id": role_id})
            check("its assignment was removed", cursor.rowcount == 1, cursor.rowcount)
            check("deleted role is hidden", A.load_roles(cursor, role_id) == [])
            check("user no longer lists it", A.load_users(cursor, user_id)[0]["roles"] == [])
            check("user lost its permissions", granted(cursor, user_id) == set())
            cursor.execute(A.SOFT_DELETE_ROLE_SQL, {"role_id": role_id, "actor_id": ACTOR_ID})
            check("deleting again touches nothing", cursor.rowcount == 0, cursor.rowcount)


def main() -> None:
    with get_connection() as connection:
        try:
            run(connection)
        except Exception:
            pass  # already reported by step()
        finally:
            connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(A.USERNAME_TAKEN_SQL, {"username": NAME})
            check("everything was rolled back", int(cursor.fetchone()[0]) == 0)

    print(f"Summary: failed={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
