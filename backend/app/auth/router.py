from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import verify_password, create_access_token, hash_password
from app.core.db import get_connection
from app.services import receipt_db as db
from app.services.base import fetch_one
from app.auth.deps import require_login
from app.auth.schemas import Token, UserOut, PasswordChangeInput

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = fetch_one(
        "SELECT username, password_hash, is_active FROM FA_USERS WHERE username = :u",
        {"u": form.username},
    )
    if (
        user is None
        or user["is_active"] != "yes"
        or not verify_password(form.password, user["password_hash"])
    ):
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    return Token(access_token=create_access_token(user["username"]))


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(require_login)):
    # Sorted so the payload is stable; the frontend reads it to show or hide screens.
    return {**current_user, "permissions": sorted(current_user["permissions"])}

@router.put("/password", status_code=204)
def change_password(item: PasswordChangeInput, current_user: dict = Depends(require_login)):
    current = item.current_password.get_secret_value()
    new = item.new_password.get_secret_value()
    if current == new:
        raise HTTPException(400, "رمز جدید باید با رمز فعلی متفاوت باشد")
    with get_connection() as conn:
        with conn.cursor() as cur:
            user = db.one(cur, """SELECT "PASSWORD_HASH" AS password_hash FROM "FA_USERS"
                WHERE "ID" = :id AND "IS_ACTIVE" = 'yes' FOR UPDATE""",
                {"id": current_user["id"]})
            if user is None:
                raise HTTPException(401, "حساب کاربری فعال نیست")
            if not verify_password(current, user["password_hash"]):
                raise HTTPException(400, "رمز عبور فعلی اشتباه است")
            cur.execute("""UPDATE "FA_USERS"
                SET "PASSWORD_HASH" = :password_hash, "MUST_CHANGE_PASSWORD" = 'no',
                    "MODIFY_AT" = SYSDATE, "MODIFY_BY" = :username
                WHERE "ID" = :id""",
                {"password_hash": hash_password(new), "username": current_user["username"],
                 "id": current_user["id"]})
        conn.commit()
