"""User and role management rules. Pure Python: no Oracle connection."""

import pytest

from app.services import user_admin as rules


@pytest.mark.parametrize("username", ["bahar", "ali.rezaei", "anbar_6", "a@b-c", "abc", "x" * 50])
def test_accepted_usernames(username):
    assert rules.username_error(username) is None


@pytest.mark.parametrize(
    "username",
    ["ab", "x" * 51, "علی", "ali rezaei", "ali;drop", "", "bahar\n"],
)
def test_rejected_usernames(username):
    assert rules.username_error(username) is not None


def test_password_length_limits():
    assert rules.password_error("1234567") is not None
    assert rules.password_error("12345678") is None
    assert rules.password_error("x" * 128) is None
    assert rules.password_error("x" * 129) is not None


def test_full_name_limit_counts_bytes_not_letters():
    """FULL_NAME is VARCHAR2(200 BYTE): 100 Persian letters fit, 101 do not."""
    assert rules.full_name_error("ب" * 100) is None
    assert rules.full_name_error("ب" * 101) is not None
    assert rules.full_name_error("b" * 200) is None
    assert rules.full_name_error(None) is None


def test_clean_text_trims_and_collapses_whitespace():
    assert rules.clean_text("  مسئول   انبار \n") == "مسئول انبار"
    assert rules.clean_text("   ") is None
    assert rules.clean_text(None) is None


def test_role_title_is_required_and_limited():
    assert rules.role_title_error(None) is not None
    assert rules.role_title_error("انباردار") is None
    assert rules.role_title_error("ن" * 200) is None
    assert rules.role_title_error("ن" * 201) is not None


def test_permission_codes_keep_catalog_order_and_report_unknown():
    known, unknown = rules.split_permission_codes(
        ["ghabz.issue", "tally.view", "retired.code", "ghabz.issue"]
    )

    assert known == ["tally.view", "ghabz.issue"]
    assert unknown == ["retired.code"]


@pytest.mark.parametrize(
    ("is_admin", "is_active", "blocked"),
    [("yes", "yes", False), ("no", "yes", True), ("yes", "no", True), ("no", "no", True)],
)
def test_admin_cannot_lock_themselves_out(is_admin, is_active, blocked):
    error = rules.self_lockout_error(actor_id=1, target_id=1, is_admin=is_admin, is_active=is_active)

    assert (error is not None) == blocked


def test_admin_may_demote_or_deactivate_someone_else():
    assert rules.self_lockout_error(actor_id=1, target_id=2, is_admin="no", is_active="no") is None
