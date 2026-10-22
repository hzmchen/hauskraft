# SPDX-License-Identifier: MIT
"""E05 auth & users and E11-02 seeded demo accounts, black-box against the running stack."""

from __future__ import annotations

import uuid

import pytest

from _support.live import Api, assert_problem, unique

pytestmark = pytest.mark.live
story = pytest.mark.story


# ---------------------------------------------------------------- M0S-E11-02 seed
@story("M0S-E11-02")
@pytest.mark.parametrize(("username", "display"), [("demo", "Demo Adult"), ("alex", "Alex Adult")])
def test_seeded_adults_can_log_in(anon: Api, username: str, display: str) -> None:
    # The roles moved to M1S-E02-03 (spec v0.3 §2.3: demo is the owner, alex an adult).
    r = anon.login(username)
    assert r.status_code == 200, r.text
    user = r.json()["user"]
    assert user["username"] == username and user["display_name"] == display
    assert user["role"] in ("adult", "owner")


# ---------------------------------------------------------------- M0S-E05-02 sessions
@story("M0S-E05-02")
def test_login_sets_hardened_cookie(anon: Api) -> None:
    r = anon.login("demo")
    assert r.status_code == 200
    cookie = r.headers.get("set-cookie", "")
    assert cookie.startswith("hauskraft_session="), cookie
    low = cookie.lower()
    assert "httponly" in low and "samesite=lax" in low and "path=/" in low, cookie
    body = r.json()
    assert body["csrf_token"] and body["expires_at"] and body["user"]["username"] == "demo"


@story("M0S-E05-02")
def test_session_and_logout(anon: Api) -> None:
    anon.login("demo")
    assert anon.get("/auth/session").status_code == 200
    assert anon.post("/auth/logout").status_code == 204
    assert anon.get("/auth/session").status_code == 401


@story("M0S-E05-02")
def test_bad_credentials_are_generic(anon: Api) -> None:
    """A wrong password and an unknown user must be indistinguishable to the caller."""
    wrong_pw = assert_problem(anon.login("demo", "definitely-wrong-password"), 401, "invalid_credentials")
    no_user = assert_problem(anon.login("nobody-" + uuid.uuid4().hex[:6], "definitely-wrong-password"), 401,
                             "invalid_credentials")
    strip = lambda b: {k: v for k, v in b.items() if k not in ("request_id", "instance")}  # noqa: E731
    assert strip(wrong_pw) == strip(no_user)


@story("M0S-E05-02")
def test_login_rate_limit(anon: Api) -> None:
    name = "ratelimit-" + uuid.uuid4().hex[:8]
    for _ in range(5):
        assert anon.login(name, "wrong-password-123").status_code == 401
    assert_problem(anon.login(name, "wrong-password-123"), 429, "rate_limited")


@story("M0S-E05-02")
def test_me_reads_and_updates_locale(demo: Api) -> None:
    me = demo.get("/me")
    assert me.status_code == 200 and me.json()["username"] == "demo"
    original = me.json()["locale"]
    try:
        r = demo.patch("/me", json={"locale": "de"})
        assert r.status_code == 200 and r.json()["locale"] == "de"
        assert_problem(demo.patch("/me", json={"locale": "fr"}), 422)
    finally:
        demo.patch("/me", json={"locale": original})


@story("M0S-E05-02")
def test_protected_routes_need_a_session(anon: Api) -> None:
    for path in ("/tasks", "/me", "/plugins", "/activity", "/themes"):
        assert anon.get(path).status_code == 401, path


# ---------------------------------------------------------------- M0S-E05-03 CSRF
@story("M0S-E05-03")
def test_write_without_csrf_token_is_rejected(demo: Api) -> None:
    r = demo.http.post("/tasks", json={"title": unique("no csrf")})
    assert_problem(r, 403, "csrf_failed")


@story("M0S-E05-03")
def test_write_with_wrong_csrf_token_is_rejected(demo: Api) -> None:
    r = demo.http.post("/tasks", json={"title": unique("bad csrf")}, headers={"X-CSRF-Token": "nope"})
    assert_problem(r, 403, "csrf_failed")


@story("M0S-E05-03")
def test_write_from_foreign_origin_is_rejected(demo: Api) -> None:
    r = demo.post("/tasks", json={"title": unique("evil origin")}, headers={"Origin": "http://evil.example"})
    assert_problem(r, 403, "csrf_failed")


@story("M0S-E05-03")
def test_login_from_foreign_origin_is_rejected() -> None:
    api = Api(origin="http://evil.example")
    try:
        assert_problem(api.login("demo"), 403, "csrf_failed")
    finally:
        api.close()


# ---------------------------------------------------------------- M0S-E05-01 / M0S-E05-05 users
def _new_user(demo: Api, **overrides):
    body = {"username": "acc" + uuid.uuid4().hex[:8], "display_name": "Acceptance Adult",
            "password": "correct-horse-battery", **overrides}
    return body, demo.post("/users", json=body)


@story("M0S-E05-05")
def test_adult_can_create_second_adult(demo: Api) -> None:
    body, r = _new_user(demo)
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "adult" and r.json()["username"] == body["username"]
    other = Api()
    try:
        assert other.login(body["username"], body["password"]).status_code == 200
    finally:
        other.close()


@story("M0S-E05-05")
def test_duplicate_username_conflicts(demo: Api) -> None:
    body, r = _new_user(demo)
    assert r.status_code == 201
    assert_problem(demo.post("/users", json=body), 409, "username_taken")


@story("M0S-E05-01")
@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_password_length_policy(demo: Api, password: str) -> None:
    _, r = _new_user(demo, password=password)
    assert_problem(r, 422)


@story("M0S-E05-01")
def test_role_cannot_be_chosen(demo: Api) -> None:
    # `owner` became creatable in M1* (M1S-E02-02); roles beyond owner and adult stay disabled.
    _, r = _new_user(demo, role="kid")
    assert_problem(r, 422)
