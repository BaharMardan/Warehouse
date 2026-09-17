from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.auth import permissions
from app.core.security import decode_access_token
from app.services.base import fetch_all, fetch_one

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Permission codes a non-admin holds through roles that are not soft-deleted.
# fetch_all lowercases keys, so the alias pins the key to "permission_code".
GRANTED_PERMISSIONS_SQL = """
SELECT DISTINCT rp."PERMISSION_CODE" AS permission_code
  FROM "FA_USER_ROLES" ur
  JOIN "FA_ROLES" r
    ON r."ID" = ur."ROLE_ID"
   AND r."IS_DELETED" = 'no'
  JOIN "FA_ROLE_PERMISSIONS" rp
    ON rp."ROLE_ID" = r."ID"
 WHERE ur."USER_ID" = :user_id
"""


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = fetch_one(
        "SELECT id, username, full_name, is_admin, is_active "
        "FROM FA_USERS WHERE username = :u",
        {"u": username},
    )
    if user is None or user["is_active"] != "yes":
        raise HTTPException(status_code=401, detail="User not found or inactive")
    user["permissions"] = user_permissions(user)
    return user


def user_permissions(user: dict) -> frozenset[str]:
    """Effective permission codes, read fresh on every request, so a revoked role
    or permission stops working on the user's next click without a re-login.

    Admins get every code without touching the role tables: they pass all
    checks, including permissions added later.
    """
    if user.get("is_admin") == "yes":
        return permissions.effective_permissions(is_admin=True, granted=())
    rows = fetch_all(GRANTED_PERMISSIONS_SQL, {"user_id": user["id"]})
    return permissions.effective_permissions(
        is_admin=False,
        granted=(row["permission_code"] for row in rows),
    )


def require_permission(code: str):
    """Route guard: ``Depends(require_permission("tally.edit"))``.

    The code is looked up when the router module is imported, so a typo stops
    the API at startup instead of silently denying everyone. The dependency
    returns the current user, so it can stand in for Depends(get_current_user).
    """
    permission = permissions.get(code)

    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if permission.code not in current_user["permissions"]:
            raise HTTPException(
                status_code=403,
                detail=permissions.denial_message(permission),
            )
        return current_user

    dependency.__name__ = f"require_permission_{permission.code.replace('.', '_')}"
    dependency.required_permission = permission.code  # read by route audits
    return dependency


def require_login(current_user: dict = Depends(get_current_user)) -> dict:
    """Guard for endpoints every logged-in user may call, such as the lookup lists
    behind the dropdowns on every form.

    It behaves exactly like get_current_user. The separate name records that the
    openness is deliberate: tests/test_route_guards.py accepts this guard,
    require_permission or require_admin, and fails a route that uses
    get_current_user alone."""
    return current_user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Gate for admin-only actions (catalog import, catalog edits). FA_USERS.is_admin
    is stored 'yes'/'no' like is_active."""
    if current_user.get("is_admin") != "yes":
        raise HTTPException(status_code=403, detail="دسترسی مدیر لازم است")
    return current_user