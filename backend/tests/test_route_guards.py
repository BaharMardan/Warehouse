"""Every API route declares who may call it.

A route passes when its dependencies include require_permission(...),
require_admin or require_login, or when it is listed in PUBLIC. Guarding a
route with get_current_user alone fails: it works, but nobody decided who
should reach it. Write methods need a permission or admin; a login is not
enough, so no one can open changes to every logged-in user by accident.

Imports the real application, so it needs the same .env as the API (like
test_tally_tracking_procedure.py). No request is sent and no row is read.

Print the whole access map from backend/:

    python -m tests.test_route_guards
"""

import pytest
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.auth import permissions
from app.auth.deps import require_admin, require_login
from app.crud.factory import CrudAccess, make_crud_router
from app.main import app

# (method, path) pairs anyone may call without logging in.
PUBLIC = {
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/health/db"),
    ("POST", "/auth/login"),
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _dependency_calls(dependant):
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


def _guards(route: APIRoute) -> set[str]:
    """Readable guard names on a route: permission codes, 'admin', 'login'."""
    found = set()
    for call in _dependency_calls(route.dependant):
        code = getattr(call, "required_permission", None)
        if code:
            found.add(code)
        elif call is require_admin:
            found.add("admin")
        elif call is require_login:
            found.add("login")
    return found


def _api_routes(routes):
    """APIRoute objects, whether FastAPI flattened included routers into the app
    (older releases) or kept each one wrapped with an original_router (newer
    releases). If a future release hides them another way, the audit sees too
    few routes and test_public_list_has_no_stale_entries fails loudly.
    main.py adds no prefix or dependencies at include time; those would not be
    visible through original_router."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        else:
            original = getattr(route, "original_router", None)
            if original is not None:
                yield from _api_routes(original.routes)


def _routes():
    for route in _api_routes(app.routes):
        for method in sorted(route.methods):
            yield method, route.path, route


def test_every_route_declares_who_may_call_it():
    unguarded = [
        f"{method} {path}"
        for method, path, route in _routes()
        if (method, path) not in PUBLIC and not _guards(route)
    ]

    assert unguarded == [], (
        "Routes without require_permission / require_admin / require_login "
        f"(or add them to PUBLIC on purpose): {unguarded}"
    )


def test_changes_need_a_permission_not_just_a_login():
    too_open = [
        f"{method} {path}"
        for method, path, route in _routes()
        if method in WRITE_METHODS
        and (method, path) not in PUBLIC
        and _guards(route) <= {"login"}
    ]

    assert too_open == [], f"Write routes open to every logged-in user: {too_open}"


def test_public_list_has_no_stale_entries():
    existing = {(method, path) for method, path, _ in _routes()}

    assert PUBLIC <= existing, f"PUBLIC lists routes that no longer exist: {PUBLIC - existing}"


def test_every_permission_is_enforced_somewhere():
    """A permission no route checks would be a checkbox that protects nothing."""
    enforced = {guard for _, _, route in _routes() for guard in _guards(route)}

    assert permissions.ALL_CODES - enforced == set()


def test_crud_access_typo_fails_when_the_router_is_built():
    class Row(BaseModel):
        name: str | None = None

    with pytest.raises(ValueError, match="tally.edti"):
        make_crud_router(
            prefix="/probe", table="PROBE", pk="ID", model=Row, tag="probe",
            access=CrudAccess.read_write(read="tally.view", write="tally.edti"),
        )


def test_crud_router_without_access_is_rejected():
    class Row(BaseModel):
        name: str | None = None

    with pytest.raises(TypeError, match="access"):
        make_crud_router(prefix="/probe", table="PROBE", pk="ID", model=Row, tag="probe")


if __name__ == "__main__":
    for method, path, route in sorted(_routes(), key=lambda r: (r[1], r[0])):
        guard = "PUBLIC" if (method, path) in PUBLIC else ", ".join(sorted(_guards(route))) or "UNGUARDED"
        print(f"{method:7} {path:50} {guard}")
