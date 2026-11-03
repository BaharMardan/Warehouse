import runpy
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.services.invoice_number import ensure_available

@pytest.fixture
def database():
    conn = sqlite3.connect(":memory:")
    conn.create_function("NVL", 2, lambda value, fallback: fallback if value is None else value, deterministic=True)
    conn.execute("CREATE TABLE FA_SORAT_HESAB_HEADER (ID_SORAT INTEGER PRIMARY KEY, INVOICE_NUMBER INTEGER NOT NULL, SORAT_IS_DELETED TEXT)")
    migration = runpy.run_path(str(Path(__file__).parents[1] / "migrations/versions/0003_reusable_invoice_numbers.py"))
    cursor = MagicMock()
    cursor.fetchone.return_value = (11,)
    migration["upgrade"](cursor)
    index_sql = next(call.args[0] for call in cursor.execute.call_args_list if "CREATE UNIQUE INDEX" in call.args[0])
    conn.execute(index_sql)
    yield conn
    conn.close()


def test_cancelled_number_can_be_reissued_without_losing_history(database):
    database.execute("INSERT INTO FA_SORAT_HESAB_HEADER VALUES (10, 77, 'yes')")
    ensure_available(database.cursor(), 77)
    database.execute("INSERT INTO FA_SORAT_HESAB_HEADER VALUES (11, 77, 'no')")
    assert database.execute("SELECT COUNT(*) FROM FA_SORAT_HESAB_HEADER WHERE INVOICE_NUMBER=77").fetchone()[0] == 2
    with pytest.raises(HTTPException) as exc:
        ensure_available(database.cursor(), 77)
    assert exc.value.status_code == 409


def test_database_rejects_concurrent_active_duplicate(database):
    database.execute("INSERT INTO FA_SORAT_HESAB_HEADER VALUES (10, 77, 'no')")
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO FA_SORAT_HESAB_HEADER VALUES (11, 77, 'no')")


def test_repeated_cancel_reissue_cycles_keep_distinct_records(database):
    for record_id in (10, 11, 12):
        ensure_available(database.cursor(), 77)
        database.execute("INSERT INTO FA_SORAT_HESAB_HEADER VALUES (?,77,'no')", (record_id,))
        database.execute("UPDATE FA_SORAT_HESAB_HEADER SET SORAT_IS_DELETED='yes' WHERE ID_SORAT=?", (record_id,))
    assert database.execute("SELECT COUNT(*) FROM FA_SORAT_HESAB_HEADER").fetchone()[0] == 3


def test_null_deleted_flag_still_reserves_number(database):
    database.execute("INSERT INTO FA_SORAT_HESAB_HEADER VALUES (10,77,NULL)")
    with pytest.raises(HTTPException):
        ensure_available(database.cursor(), 77)
