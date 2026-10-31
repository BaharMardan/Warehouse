import pytest
from fastapi import HTTPException
from app.auth.permissions import effective_permissions
from app.routers.remaining_invoice import require_remaining_access
from tests.test_route_guards import _routes, _guards


def test_each_tab_grants_module_entry_but_not_the_other_tab():
    for tab, other in [("stock", "operations"), ("operations", "stock")]:
        grants = effective_permissions(is_admin=False, granted=["non_customs." + tab])
        assert "non_customs.view" in grants
        assert "non_customs." + other not in grants
        assert "reports.stock" not in grants
        assert "invoice.issue" not in grants


def test_legacy_permissions_do_not_grant_non_customs_access():
    grants = effective_permissions(is_admin=False, granted=["reports.stock", "invoice.issue", "tally.services"])
    assert not any(code.startswith("non_customs.") for code in grants)


def test_non_customs_routes_enforce_the_matching_tab():
    for method, path, route in _routes():
        if path.startswith("/non-customs"):
            wanted = "non_customs.stock" if path == "/non-customs/stock" else "non_customs.operations"
            assert wanted in _guards(route), (method, path)


def test_non_customs_invoice_requires_operations_tab():
    with pytest.raises(HTTPException) as exc:
        require_remaining_access(True, {"permissions": {"invoice.issue"}})
    assert exc.value.status_code == 403
    user = {"permissions": {"invoice.issue", "non_customs.operations"}}
    assert require_remaining_access(True, user) is user


def test_ordinary_invoice_does_not_require_non_customs_permission():
    user = {"permissions": {"invoice.issue"}}
    assert require_remaining_access(False, user) is user


@pytest.mark.parametrize("method,path,codes", [
    ("GET", "/non-customs/stock", ["reports.stock"]),
    ("GET", "/non-customs", ["non_customs.stock"]),
    ("POST", "/non-customs/tallies/1/rows", ["non_customs.stock"]),
    ("GET", "/ghabz/1/remaining-invoice?non_customs=true", ["invoice.issue"]),
])
def test_tab_permissions_are_enforced_over_http(method, path, codes):
    import asyncio
    from urllib.parse import urlsplit
    from app.main import app
    from app.auth.deps import get_current_user
    user = {"id": 1, "permissions": effective_permissions(is_admin=False, granted=codes)}
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async def request():
            messages = []
            url = urlsplit(path)
            async def receive():
                return {"type": "http.request", "body": b"{}", "more_body": False}
            async def send(message):
                messages.append(message)
            scope = {"type": "http", "http_version": "1.1", "method": method,
                     "scheme": "http", "path": url.path, "raw_path": url.path.encode(),
                     "query_string": url.query.encode(), "root_path": "",
                     "server": ("test", 80), "client": ("test", 1234),
                     "headers": [(b"content-type", b"application/json")]}
            await app(scope, receive, send)
            return next(message["status"] for message in messages if message["type"] == "http.response.start")
        assert asyncio.run(request()) == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
