"""Permission catalog: every capability the API checks, defined in one place.

A permission only means something when an endpoint enforces it, so the list
lives in code. Roles (FA_ROLES) are rows an admin builds from these codes, and
FA_ROLE_PERMISSIONS stores the codes as text.

Adding a feature for specific roles:
  1. Add a Permission below.
  2. Guard its endpoints with Depends(require_permission("<code>")).
  3. Gate its screen or button in the frontend with the same code.
  4. Tick it on the roles in the admin screen. No migration.

Renaming or removing a code: grants stored under the old code stop counting
immediately (unknown codes are ignored), so update FA_ROLE_PERMISSIONS in the
same change if those grants should carry over.

No database or FastAPI imports here, so this is unit-tested without Oracle
(tests/test_permissions.py).
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Permission:
    code: str                      # "<area>.<action>", stored in FA_ROLE_PERMISSIONS
    label: str                     # Persian; shown in the admin screen and in 403 messages
    module: str                    # key of the owning module in frontend/src/modules.tsx
    implies: tuple[str, ...] = ()  # granted automatically together with this one


# Display order for the admin screen: grouped by module, view before actions.
PERMISSIONS: tuple[Permission, ...] = (
    Permission("kartabl.view", "مشاهده کارتابل", "kartabl"),

    Permission("base_data.edit", "ویرایش اطلاعات پایه", "base-data"),
    Permission("commodity.manage", "مدیریت کاتالوگ کالاها", "base-data"),

    Permission("tally.view", "مشاهده تالی", "tally"),
    Permission("tally.edit", "ثبت و ویرایش تالی", "tally", implies=("tally.view",)),
    Permission("tally.delete", "حذف تالی", "tally", implies=("tally.view",)),
    # The warehouse keeper's part of a tally: the five service sections, the
    # volumetric question and sending the tally back to the operator.
    Permission("tally.services", "تکمیل خدمات تالی", "tally", implies=("tally.view", "ghabz.view")),

    Permission("ghabz.view", "مشاهده قبض انبار", "ghabz"),
    # Receipts are issued from the tally detail page (GhabzIssueModal), so the
    # issuer must be able to open the tally.
    Permission(
        "ghabz.issue", "صدور قبض انبار", "ghabz",
        implies=("ghabz.view", "tally.view"),
    ),
    Permission("ghabz.edit", "ویرایش قبض انبار", "ghabz", implies=("ghabz.view",)),

    Permission("invoice.view", "مشاهده صورتحساب", "invoice"),
    Permission("invoice.issue", "صدور صورتحساب", "invoice", implies=("invoice.view", "ghabz.view")),
    Permission("settings.manage", "مدیریت تنظیمات سامانه", "settings"),
)

_CODE_PATTERN = re.compile(r"^[a-z][a-z_]*\.[a-z][a-z_]*$")


def _validate(catalog: Iterable[Permission]) -> dict[str, Permission]:
    """Index the catalog by code, rejecting entries that would misbehave later."""
    by_code: dict[str, Permission] = {}
    for permission in catalog:
        if not _CODE_PATTERN.match(permission.code):
            raise ValueError(
                f"Malformed permission code {permission.code!r}: use '<area>.<action>'"
            )
        if permission.code in by_code:
            raise ValueError(f"Duplicate permission code {permission.code!r}")
        if not permission.label.strip() or not permission.module.strip():
            raise ValueError(f"Permission {permission.code!r} needs a label and a module")
        by_code[permission.code] = permission

    for permission in by_code.values():
        for implied in permission.implies:
            if implied == permission.code:
                raise ValueError(f"Permission {permission.code!r} implies itself")
            if implied not in by_code:
                raise ValueError(
                    f"Permission {permission.code!r} implies unknown code {implied!r}"
                )
    return by_code


_BY_CODE = _validate(PERMISSIONS)
ALL_CODES: frozenset[str] = frozenset(_BY_CODE)


def get(code: str) -> Permission:
    """The catalog entry for ``code``; ValueError if the code is not defined."""
    permission = _BY_CODE.get(code)
    if permission is None:
        raise ValueError(
            f"Unknown permission code {code!r}: add it to PERMISSIONS in "
            "app/auth/permissions.py"
        )
    return permission


def _closure(codes: Iterable[str], by_code: Mapping[str, Permission]) -> frozenset[str]:
    """Known codes plus everything they imply, transitively."""
    result: set[str] = set()
    pending = [code for code in codes if code in by_code]
    while pending:
        code = pending.pop()
        if code not in result:
            result.add(code)
            pending.extend(by_code[code].implies)
    return frozenset(result)


def effective_permissions(*, is_admin: bool, granted: Iterable[str]) -> frozenset[str]:
    """What a user may do.

    Admins get every code, including codes added later. Everyone else gets the
    codes granted through their active roles plus everything those imply. Codes
    missing from the catalog (renamed or removed, but still stored on a role)
    are ignored, so a stale row can never grant anything.
    """
    if is_admin:
        return ALL_CODES
    return _closure(granted, _BY_CODE)


def denial_message(permission: Permission) -> str:
    """Persian 403 detail that names the missing permission, so the user knows what to ask for."""
    return f"دسترسی «{permission.label}» برای شما تعریف نشده است"
