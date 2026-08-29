"""Shared rate limiter.

One Limiter for the whole app — a per-router instance would give every router
its own bucket. Limits are keyed on the authenticated user so that everyone
behind a shared IP (or a reverse proxy that does not forward the client
address) gets their own allowance. Unauthenticated endpoints such as login and
register carry no token and fall back to the remote address.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services import auth_service


def user_or_ip(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = auth_service.decode_token(auth[len("Bearer "):])
        if payload and payload.get("type") == "access" and payload.get("sub"):
            return f"user:{payload['sub']}"
    return get_remote_address(request)


limiter = Limiter(key_func=user_or_ip, default_limits=[])
