from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.services.tally_numbering import choose_tally_number


def cursor(mode, *matches):
    c = MagicMock()
    c.fetchone.side_effect = [(mode,), *matches]
    c.rowcount = 1
    c.var.return_value.getvalue.return_value = [2076]
    return c


def test_manual_normalizes_digits_without_changing_counter():
    c = cursor(1, None)
    assert choose_tally_number(c, "۲۰۵۰") == '2050'
    assert not any(call.args[0].lstrip().startswith('UPDATE') for call in c.execute.call_args_list)


@pytest.mark.parametrize('value', [None, '', '0', '-1', '12..5', 'abc', '1234567890123456'])
def test_manual_rejects_invalid_number(value):
    with pytest.raises(HTTPException) as e:
        choose_tally_number(cursor(1), value)
    assert e.value.status_code == 422


def test_manual_duplicate_returns_conflict():
    with pytest.raises(HTTPException) as e:
        choose_tally_number(cursor(1, (1,)), '2050')
    assert e.value.status_code == 409


def test_automatic_ignores_client_number_and_keeps_counter():
    assert choose_tally_number(cursor(0, None), '100') == '2076'


def test_return_to_auto_skips_numbers_already_entered_manually():
    c = cursor(0, (1,), None)
    c.var.return_value.getvalue.side_effect = [[2076], [2077]]
    assert choose_tally_number(c, None) == '2077'


def test_read_mode_is_available_to_tally_editors():
    from app.routers.tally_header import router
    routes = [r for r in router.routes if r.path.endswith('/numbering')]
    assert len(routes) == 1


@pytest.mark.parametrize('value', ['0.5', '2'])
def test_numbering_setting_only_accepts_boolean_values(value):
    from app.routers.settings import update_setting, SettingInput
    with pytest.raises(HTTPException) as e:
        update_setting('manual_tally_numbering', SettingInput(value_number=value), {'id': 1})
    assert e.value.status_code == 422


def test_manual_number_lookup_executes_on_oracle(monkeypatch):
    from app.core.db import get_connection
    from app.services import tally_numbering as numbering
    monkeypatch.setattr(numbering, 'manual_numbering', lambda *a, **k: True)
    with get_connection() as connection:
        with connection.cursor() as c:
            # Read-only round trip exercises Oracle's reserved bind-name rules.
            c.execute('SELECT MAX(TO_NUMBER("TALI_NUMBER" DEFAULT NULL ON CONVERSION ERROR)) FROM "FA_TALI_HEADER"')
            unused = str(int(c.fetchone()[0] or 0) + 1)
            assert numbering.choose_tally_number(c, unused) == unused


@pytest.mark.parametrize('supplied,expected', [
    ('1941.1','1941.1'), ('۱۹۴۱.۱','1941.1'),
    ('۱۹۴۱٫۱','1941.1'), ('001941.01','1941.01'),
])
def test_manual_accepts_dotted_tally_identifiers(supplied, expected):
    c=cursor(1,None)
    assert choose_tally_number(c,supplied)==expected
    assert c.execute.call_args.args[1]['tally_number']==expected


@pytest.mark.parametrize('value',['1941.','.1','0.1','1941/1','1e3','1.2.3','123456789012345.1'])
def test_manual_rejects_malformed_dotted_identifier(value):
    with pytest.raises(HTTPException) as e:
        choose_tally_number(cursor(1),value)
    assert e.value.status_code==422


def test_manual_edit_normalizes_and_excludes_current_tally():
    from app.services.tally_numbering import editable_tally_number
    c=cursor(1,None)
    assert editable_tally_number(c,'001941.1',42)=='1941.1'
    assert c.execute.call_args.args[1]=={'tally_number':'1941.1','id':42}
    assert '"ID_TALI" <> :id' in c.execute.call_args.args[0]


def test_manual_edit_rejects_duplicate_and_auto_mode():
    from app.services.tally_numbering import editable_tally_number
    for c in (cursor(1,(1,)),cursor(0)):
        with pytest.raises(HTTPException) as exc:
            editable_tally_number(c,'1941',42)
        assert exc.value.status_code==409


def test_header_update_persists_normalized_manual_number_under_lock(monkeypatch):
    from app.services import receipt_db as db
    connection=MagicMock()
    connection.__enter__.return_value=connection
    cur=connection.cursor.return_value.__enter__.return_value
    cur.fetchone.side_effect=[(1,),None]
    cur.rowcount=1
    monkeypatch.setattr(db,'get_connection',lambda:connection)
    monkeypatch.setattr(db,'one',lambda *a: {'id_tali':42,'tali_number':'100'})
    lock=MagicMock(return_value={'id_tali':42})
    monkeypatch.setattr(db,'lock_tally',lock)
    from app.services import tally_numbering
    sync=MagicMock()
    monkeypatch.setattr(tally_numbering,'sync_receipt_numbers',sync)
    params={'id':42,'actor_id':1,'tali_number':'001941.1'}
    assert db.guarded_write('FA_TALI_HEADER','ID_TALI','update','UPDATE_NUMBER',params,
                           row_id=42,values={'tali_number':'001941.1'})==1
    lock.assert_called_once_with(cur,42)
    sync.assert_called_once_with(cur,42,'1941.1',None,1)
    assert cur.execute.call_args.args[1]['tali_number']=='1941.1'
    assert cur.execute.call_args.args[0]=='UPDATE_NUMBER'
    connection.commit.assert_called_once()
