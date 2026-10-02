import json
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.services import display_order as service
from app.crud.registry import crud_routers


def test_partial_category_reorder_preserves_other_categories():
    assert service.merge_order([1, 2, 3, 4, 5], [5, 3]) == [1, 2, 5, 4, 3]


@pytest.mark.parametrize("ids", [[1, 1], [1, 99]])
def test_unknown_or_duplicate_ids_are_rejected(ids):
    with pytest.raises(HTTPException) as exc:
        service.merge_order([1, 2, 3], ids)
    assert exc.value.status_code == 422


@pytest.mark.parametrize("ids", [[], ["1"], [True], [1.5]])
def test_request_requires_nonempty_integer_ids(ids):
    with pytest.raises(ValidationError):
        service.DisplayOrderInput(ids=ids)


def test_new_rows_append_and_removed_rows_do_not_appear():
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    assert service.apply_order(rows, "ID", [2, 99, 1]) == [rows[1], rows[0], rows[2]]
    assert rows == [{"id": 1}, {"id": 2}, {"id": 3}]


@pytest.mark.parametrize("requested,valid", [([3, 1], True), ([99], False)])
def test_save_locks_merges_and_commits_atomically(monkeypatch, requested, valid):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = ('[1,2,3]',)
    cur.description = [("ID",)]
    cur.fetchall.return_value = [(1,), (2,), (3,)]
    monkeypatch.setattr(service, "get_connection", lambda: conn)
    if valid:
        assert service.save_order('/terms', 'list query', 'ID', requested, 7) == {"ids": [3, 2, 1]}
        params = cur.execute.call_args.args[1]
        assert json.loads(params['ordering']) == [3, 2, 1]
        assert params['actor'] == 7
        conn.commit.assert_called_once()
    else:
        with pytest.raises(HTTPException):
            service.save_order('/terms', 'list query', 'ID', requested, 7)
        conn.commit.assert_not_called()
        assert cur.execute.call_count == 2
    assert 'FOR UPDATE' in cur.execute.call_args_list[0].args[0]


def test_reorder_routes_are_guarded_and_precede_dynamic_paths():
    count = 0
    for router in crud_routers:
        for index, route in enumerate(router.routes):
            if not route.path.endswith('/display-order'):
                continue
            count += 1
            assert route.methods == {'PUT'}
            assert any(getattr(dep.call, 'required_permission', None) == 'base_data.edit'
                       for dep in route.dependant.dependencies)
            assert all('{row_id}' not in earlier.path for earlier in router.routes[:index])
    assert count == 15
