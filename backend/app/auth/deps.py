from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token
from app.services.base import fetch_one

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


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
    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Gate for admin-only actions (catalog import, catalog edits). FA_USERS.is_admin
    is stored 'yes'/'no' like is_active."""
    if current_user.get("is_admin") != "yes":
        raise HTTPException(status_code=403, detail="دسترسی مدیر لازم است")
    return current_user