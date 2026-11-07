import re
import sqlite3
import pytest
from app.routers.ghabz import SUMMARY_SQL

@pytest.mark.parametrize("current", ["NEW-CARNET", None])
def test_receipt_uses_current_tally_carnet_including_cleared_value(current):
    expression = re.search(r'([^\n]+) AS number_karaneh,', SUMMARY_SQL).group(1).strip()
    db = sqlite3.connect(":memory:")
    db.execute('CREATE TABLE receipt (NUMBER_KARANEH TEXT)')
    db.execute('CREATE TABLE tally (ID_TALI INT, NUMBER_KARANEH TEXT)')
    db.execute("INSERT INTO receipt VALUES ('OLD-CARNET')")
    db.execute('INSERT INTO tally VALUES (1, ?)', (current,))
    assert db.execute(f'SELECT {expression} FROM receipt h CROSS JOIN tally t').fetchone()[0] == current
    db.execute('UPDATE tally SET ID_TALI=NULL')
    assert db.execute(f'SELECT {expression} FROM receipt h CROSS JOIN tally t').fetchone()[0] == 'OLD-CARNET'
    db.close()
