"""Restore target selection and refusal to overwrite existing objects."""
import sys
import types
import importlib.util

import pytest

# Linux test environment may lack the proprietary driver. Guards never connect.
if "oracledb" not in sys.modules and importlib.util.find_spec("oracledb") is None:
    sys.modules["oracledb"] = types.ModuleType("oracledb")

import import_live_migration as restore


class Cursor:
    def __init__(self, user, objects):
        self.user, self.objects, self.sql = user, objects, []
    def execute(self, sql):
        self.sql.append(sql)
    def fetchone(self):
        return (self.user,) if self.sql[-1] == "SELECT USER FROM dual" else (self.objects,)


@pytest.mark.parametrize("name", ["WAREHOUSE_LIVE", "warehouse_restore", "WAREHOUSE_RESTORE_202610"])
def test_accepts_explicit_warehouse_schemas(name):
    assert restore.validate_target_schema(name) == name.upper()


@pytest.mark.parametrize("name", ["SYS", "SYSTEM", "HR", 'WAREHOUSE_X"; DROP USER HR', "WAREHOUSE_" + "X" * 21])
def test_rejects_unsafe_target_names(name):
    with pytest.raises(ValueError):
        restore.validate_target_schema(name)


def test_refuses_connected_user_mismatch():
    cursor = Cursor("WAREHOUSE_LIVE", 0)
    with pytest.raises(RuntimeError, match="does not match"):
        restore.ensure_empty_target(cursor, "WAREHOUSE_RESTORE")
    assert cursor.sql == ["SELECT USER FROM dual"]


def test_refuses_any_existing_object():
    cursor = Cursor("WAREHOUSE_RESTORE", 1)
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        restore.ensure_empty_target(cursor, "WAREHOUSE_RESTORE")
    assert all(sql.startswith("SELECT") for sql in cursor.sql)


def test_accepts_empty_restore_schema():
    cursor = Cursor("WAREHOUSE_RESTORE", 0)
    restore.ensure_empty_target(cursor, "WAREHOUSE_RESTORE")
    assert cursor.sql[-1] == "SELECT COUNT(*) FROM user_objects"
