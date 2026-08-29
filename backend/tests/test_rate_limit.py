"""Tests for the rate-limit key function — limits follow the user, not the IP."""
from starlette.requests import Request

from app.rate_limit import user_or_ip
from app.services import auth_service


def make_request(authorization: str | None = None, ip: str = "10.0.0.1") -> Request:
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return Request({"type": "http", "headers": headers, "client": (ip, 51234)})


def test_keys_on_user_id_from_a_valid_access_token():
    token = auth_service.create_access_token(42)

    assert user_or_ip(make_request(f"Bearer {token}")) == "user:42"


def test_two_users_behind_one_ip_get_separate_keys():
    one = make_request(f"Bearer {auth_service.create_access_token(1)}")
    two = make_request(f"Bearer {auth_service.create_access_token(2)}")

    assert user_or_ip(one) != user_or_ip(two)


def test_falls_back_to_ip_without_a_token():
    """Login and register carry no token and stay rate-limited per IP."""
    assert user_or_ip(make_request(ip="203.0.113.7")) == "203.0.113.7"


def test_falls_back_to_ip_for_a_refresh_token():
    """A refresh token must not unlock an access-token-scoped bucket."""
    token = auth_service.create_refresh_token(42)

    assert user_or_ip(make_request(f"Bearer {token}", ip="203.0.113.7")) == "203.0.113.7"


def test_falls_back_to_ip_for_a_malformed_token():
    assert user_or_ip(make_request("Bearer not-a-jwt", ip="203.0.113.7")) == "203.0.113.7"


def test_ignores_a_non_bearer_authorization_header():
    assert user_or_ip(make_request("Basic dXNlcjpwYXNz", ip="203.0.113.7")) == "203.0.113.7"
