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


@pytest.mark.parametrize('value', [None, '', '0', '-1', '12.5', 'abc', '1234567890123456'])
def test_manual_requires_positive_integer(value):
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
