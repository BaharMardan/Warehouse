"""Rules for user and role management, kept free of database and FastAPI imports
so they are unit-tested without Oracle (tests/test_user_admin.py).

Each *_error function returns a Persian message for the admin, or None when the
value is acceptable. Byte limits matter here: FA_USERS.USERNAME and FULL_NAME
are VARCHAR2 with BYTE semantics, and a Persian letter takes two bytes in
AL32UTF8, so a 200-byte column holds only about 100 Persian letters.
"""

import re
from collections.abc import Iterable

from app.auth import permissions

# ASCII only: usernames are typed on the login page, often on shared machines,
# and look-alike Persian or Arabic letters would make two names seem identical.
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._@-]{3,50}")
PASSWORD_MIN = 8
PASSWORD_MAX = 128               # argon2 accepts more; the cap keeps hashing cheap
FULL_NAME_MAX_BYTES = 200        # FA_USERS.FULL_NAME VARCHAR2(200 BYTE)
ROLE_TITLE_MAX = 200             # FA_ROLES.TITLE VARCHAR2(200 CHAR)
ROLE_DESCRIPTION_MAX = 1000      # FA_ROLES.DESCRIPTION VARCHAR2(1000 CHAR)


def clean_text(value: str | None) -> str | None:
    """Trim and collapse inner whitespace; an empty result becomes None."""
    if value is None:
        return None
    collapsed = " ".join(value.split())
    return collapsed or None


def username_error(username: str) -> str | None:
    if not USERNAME_PATTERN.fullmatch(username):
        return "نام کاربری باید ۳ تا ۵۰ نویسه و فقط شامل حروف انگلیسی، عدد و . _ @ - باشد"
    return None


def password_error(password: str) -> str | None:
    if len(password) < PASSWORD_MIN:
        return "رمز عبور باید دست‌کم ۸ نویسه باشد"
    if len(password) > PASSWORD_MAX:
        return "رمز عبور حداکثر می‌تواند ۱۲۸ نویسه باشد"
    return None


def full_name_error(full_name: str | None) -> str | None:
    if full_name is not None and len(full_name.encode("utf-8")) > FULL_NAME_MAX_BYTES:
        return "نام کامل طولانی‌تر از حد مجاز است"
    return None


def role_title_error(title: str | None) -> str | None:
    if not title:
        return "عنوان نقش را وارد کنید"
    if len(title) > ROLE_TITLE_MAX:
        return "عنوان نقش طولانی‌تر از حد مجاز است"
    return None


def role_description_error(description: str | None) -> str | None:
    if description is not None and len(description) > ROLE_DESCRIPTION_MAX:
        return "توضیحات نقش طولانی‌تر از حد مجاز است"
    return None


def split_permission_codes(codes: Iterable[str]) -> tuple[list[str], list[str]]:
    """(known codes in catalog order without duplicates, unknown codes in the order sent)."""
    requested = list(dict.fromkeys(codes))
    unknown = [code for code in requested if code not in permissions.ALL_CODES]
    wanted = set(requested)
    known = [p.code for p in permissions.PERMISSIONS if p.code in wanted]
    return known, unknown


def self_lockout_error(*, actor_id: int, target_id: int, is_admin: str, is_active: str) -> str | None:
    """An admin may not remove their own admin flag or deactivate their own account.

    This one rule also keeps at least one active admin in the system: whoever
    makes a change is an active admin, and stays one after it.
    """
    if actor_id == target_id and (is_admin != "yes" or is_active != "yes"):
        return "دسترسی مدیر یا فعال بودن حساب خودتان را نمی‌توانید بردارید"
    return None
