import pytest

from run_local_migrations import validate_local_target


@pytest.mark.parametrize("dsn", [
    "127.0.0.1:1521/FREEPDB1", "localhost:1521/FREEPDB1",
])
def test_local_hr_is_allowed(dsn):
    validate_local_target("hr", dsn)


@pytest.mark.parametrize("user", ["WAREHOUSE_LIVE", "WAREHOUSE_RESTORE", "SYSTEM", "SYS"])
def test_other_schemas_are_refused(user):
    with pytest.raises(RuntimeError, match="HR"):
        validate_local_target(user, "127.0.0.1:1521/FREEPDB1")


@pytest.mark.parametrize("dsn", [
    "192.168.1.31:1521/FREEPDB1", "database.example.com:1521/FREEPDB1",
])
def test_remote_databases_are_refused(dsn):
    with pytest.raises(RuntimeError, match="loopback"):
        validate_local_target("HR", dsn)
