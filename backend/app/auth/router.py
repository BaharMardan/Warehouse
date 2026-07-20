from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import verify_password, create_access_token
from app.services.base import fetch_one
from app.auth.deps import get_current_user
from app.auth.schemas import Token, UserOut

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
def me(current_user: dict = Depends(get_current_user)):
    return current_user