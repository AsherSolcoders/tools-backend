"""Shared rate limiter.

Keys on the real client IP. Behind nginx the TCP peer is 127.0.0.1, so we read
X-Forwarded-For. Our nginx appends the real client as the LAST entry
(`$proxy_add_x_forwarded_for`), which a client cannot spoof — so we use the last
hop, not the first.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[-1].strip()
    return get_remote_address(request)


# Generous global safety-net against floods; sensitive routes set stricter limits.
limiter = Limiter(key_func=client_ip, default_limits=["600/minute"])
