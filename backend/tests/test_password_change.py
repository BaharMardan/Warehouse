from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.auth import router as api, deps
from app.auth.schemas import PasswordChangeInput
from app.core.security import hash_password, verify_password
from app.routers import admin


@pytest.fixture
def wired(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    one = MagicMock(return_value={"password_hash": hash_password("initial-pass")})
    monkeypatch.setattr(api.db, "one", one)
    return conn, cur, one


def payload(current="initial-pass", new="personal-pass"):
    return PasswordChangeInput(current_password=current, new_password=new)


def test_change_password_only_updates_authenticated_user_and_clears_temporary_flag(wired):
    conn, cur, one = wired
    api.change_password(payload(), {"id": 7, "username": "worker"})
    _, sql, params = one.call_args.args
    assert "FOR UPDATE" in sql and params == {"id": 7}
    sql, params = cur.execute.call_args.args
    assert '"MUST_CHANGE_PASSWORD" = \'no\'' in sql
    assert params["id"] == 7 and params["username"] == "worker"
    assert params["password_hash"] != "personal-pass"
    assert verify_password("personal-pass", params["password_hash"])
    assert not verify_password("initial-pass", params["password_hash"])
    conn.commit.assert_called_once()


def test_wrong_current_password_never_writes(wired):
    conn, cur, _ = wired
    with pytest.raises(HTTPException) as exc:
        api.change_password(payload(current="wrong-pass"), {"id": 7, "username": "worker"})
    assert exc.value.status_code == 400
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_inactive_or_missing_account_never_writes(wired):
    conn, cur, one = wired
    one.return_value = None
    with pytest.raises(HTTPException) as exc:
        api.change_password(payload(), {"id": 7, "username": "worker"})
    assert exc.value.status_code == 401
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_new_password_must_differ(wired):
    conn, cur, _ = wired
    with pytest.raises(HTTPException) as exc:
        api.change_password(payload(new="initial-pass"), {"id": 7, "username": "worker"})
    assert exc.value.status_code == 400
    conn.cursor.assert_not_called()
    conn.commit.assert_not_called()


def test_update_failure_never_commits(wired):
    conn, cur, _ = wired
    cur.execute.side_effect = RuntimeError("failed")
    with pytest.raises(RuntimeError):
        api.change_password(payload(), {"id": 7, "username": "worker"})
    conn.commit.assert_not_called()


@pytest.mark.parametrize("data", [
    {"current_password": "", "new_password": "valid-pass"},
    {"current_password": "initial-pass", "new_password": "short"},
    {"current_password": "initial-pass", "new_password": "x" * 129},
    {"current_password": "x" * 129, "new_password": "valid-pass"},
    {"current_password": "initial-pass", "new_password": "valid-pass", "user_id": 99},
])
def test_password_request_rejects_invalid_lengths_and_target_accounts(data):
    with pytest.raises(ValidationError):
        PasswordChangeInput(**data)


def test_passwords_are_hidden_in_model_repr():
    assert "initial-pass" not in repr(payload())
    assert "personal-pass" not in repr(payload())


def user(monkeypatch, temporary):
    monkeypatch.setattr(deps, "decode_access_token", lambda *a: "worker")
    monkeypatch.setattr(deps, "fetch_one", lambda *a: {
        "id": 7, "username": "worker", "is_active": "yes", "is_admin": "no",
        "must_change_password": "yes" if temporary else "no"})
    monkeypatch.setattr(deps, "user_permissions", lambda *a: frozenset())


@pytest.mark.parametrize("path", ["/tally/1", "/admin/users", "/invoice/list"])
def test_temporary_password_blocks_application_requests(monkeypatch, path):
    user(monkeypatch, True)
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user("token", SimpleNamespace(url=SimpleNamespace(path=path)))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "password_change_required"


@pytest.mark.parametrize("path", ["/auth/me", "/auth/password"])
def test_temporary_password_allows_profile_and_password_change(monkeypatch, path):
    user(monkeypatch, True)
    result = deps.get_current_user("token", SimpleNamespace(url=SimpleNamespace(path=path)))
    assert result["must_change_password"] is True


def test_personal_password_allows_normal_requests(monkeypatch):
    user(monkeypatch, False)
    assert deps.get_current_user("token", SimpleNamespace(url=SimpleNamespace(path="/tally/1")))["id"] == 7


def test_admin_create_and_reset_require_user_to_choose_a_personal_password():
    assert '"MUST_CHANGE_PASSWORD"' in admin.INSERT_USER_SQL
    assert "'yes'" in admin.INSERT_USER_SQL
    assert '"MUST_CHANGE_PASSWORD" = \'yes\'' in admin.SET_PASSWORD_SQL



def request(app, authenticated):
    import asyncio
    import json
    async def run():
        messages = []
        body = json.dumps({"current_password": "initial-pass", "new_password": "personal-pass"}).encode()
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}
        async def send(message):
            messages.append(message)
        scope = {"type": "http", "http_version": "1.1", "method": "PUT", "scheme": "http",
                 "path": "/auth/password", "raw_path": b"/auth/password", "query_string": b"",
                 "root_path": "", "server": ("test", 80), "client": ("test", 1234),
                 "headers": [(b"content-type", b"application/json")] +
                            ([(b"authorization", b"Bearer token")] if authenticated else [])}
        await app(scope, receive, send)
        return messages
    return asyncio.run(run())


def test_http_password_change_is_available_without_a_role(wired, monkeypatch):
    from fastapi import FastAPI
    user(monkeypatch, True)
    app = FastAPI()
    app.include_router(api.router)
    messages = request(app, True)
    assert messages[0]["status"] == 204
    assert messages[-1].get("body", b"") == b""


def test_http_missing_login_cannot_change_password():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(api.router)
    assert request(app, False)[0]["status"] == 401
