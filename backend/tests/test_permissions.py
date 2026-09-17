"""Permission catalog and resolution rules. Pure Python: no Oracle connection."""

import re
from pathlib import Path

import pytest

from app.auth import permissions
from app.auth.permissions import Permission

MODULES_TSX = Path(__file__).resolve().parents[2] / "frontend" / "src" / "modules.tsx"


def test_codes_are_unique_and_well_formed():
    codes = [p.code for p in permissions.PERMISSIONS]

    assert len(codes) == len(set(codes)) == len(permissions.ALL_CODES)
    assert all(re.fullmatch(r"[a-z][a-z_]*\.[a-z][a-z_]*", code) for code in codes)


def test_every_permission_belongs_to_a_launcher_module():
    """The admin screen groups permissions by the module keys in modules.tsx."""
    if not MODULES_TSX.exists():
        pytest.skip("frontend/src/modules.tsx is not in this checkout")
    active_lines = [
        line for line in MODULES_TSX.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    ]
    module_keys = {
        match.group(1)
        for line in active_lines
        if (match := re.search(r"\bkey:\s*'([^']+)'", line))
    }

    assert module_keys, "no module keys found in modules.tsx"
    assert {p.module for p in permissions.PERMISSIONS} <= module_keys


def test_admin_gets_every_permission_including_future_ones():
    assert permissions.effective_permissions(is_admin=True, granted=()) == permissions.ALL_CODES


def test_a_user_without_roles_gets_nothing():
    assert permissions.effective_permissions(is_admin=False, granted=()) == frozenset()


def test_issuing_receipts_brings_the_screens_it_needs():
    effective = permissions.effective_permissions(is_admin=False, granted=["ghabz.issue"])

    assert effective == {"ghabz.issue", "ghabz.view", "tally.view"}


def test_editing_a_tally_does_not_grant_deleting_it():
    effective = permissions.effective_permissions(is_admin=False, granted=["tally.edit"])

    assert effective == {"tally.edit", "tally.view"}


def test_codes_missing_from_the_catalog_never_grant_anything():
    effective = permissions.effective_permissions(
        is_admin=False, granted=["retired.code", "tally.view"]
    )

    assert effective == {"tally.view"}


def test_implication_is_transitive_and_survives_cycles():
    catalog = permissions._validate([
        Permission("a.one", "A", "m", implies=("b.two",)),
        Permission("b.two", "B", "m", implies=("c.three", "a.one")),
        Permission("c.three", "C", "m"),
    ])

    assert permissions._closure(["a.one"], catalog) == {"a.one", "b.two", "c.three"}


def test_a_mistyped_code_fails_fast():
    with pytest.raises(ValueError, match="tally.edti"):
        permissions.get("tally.edti")


def test_denial_message_names_the_missing_permission():
    message = permissions.denial_message(permissions.get("ghabz.issue"))

    assert "صدور قبض انبار" in message


@pytest.mark.parametrize(
    ("catalog", "error"),
    [
        ([Permission("Tally.View", "x", "m")], "Malformed"),
        ([Permission("tally", "x", "m")], "Malformed"),
        ([Permission("a.b", "x", "m"), Permission("a.b", "y", "m")], "Duplicate"),
        ([Permission("a.b", " ", "m")], "label"),
        ([Permission("a.b", "x", "")], "module"),
        ([Permission("a.b", "x", "m", implies=("c.d",))], "unknown code"),
        ([Permission("a.b", "x", "m", implies=("a.b",))], "implies itself"),
    ],
)
def test_catalog_validation_rejects_bad_entries(catalog, error):
    with pytest.raises(ValueError, match=error):
        permissions._validate(catalog)


PERMISSIONS_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "auth" / "permissions.ts"


def test_frontend_codes_match_the_catalog():
    """frontend/src/auth/permissions.ts types every can('...') call in the UI."""
    if not PERMISSIONS_TS.exists():
        pytest.skip("frontend/src/auth/permissions.ts is not in this checkout")
    source = PERMISSIONS_TS.read_text(encoding="utf-8")
    block = re.search(r"PERMISSION_CODES\s*=\s*\[(.*?)\]\s*as const", source, re.S)

    assert block, "PERMISSION_CODES array not found in permissions.ts"
    assert re.findall(r"'([^']+)'", block.group(1)) == [p.code for p in permissions.PERMISSIONS]
