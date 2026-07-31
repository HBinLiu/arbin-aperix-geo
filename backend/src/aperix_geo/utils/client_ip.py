"""Extract client IP from ASGI/FastAPI request (behind Nginx)."""

from __future__ import annotations

from typing import Any


def client_ip_from_request(request: Any) -> str:
    """
    取客户端 IP。生产在 Nginx 后应设置 ``X-Forwarded-For``（只追加真实 peer），
    此处取链上第一个地址。无反代头时回退 ``request.client.host``。
    """
    headers = getattr(request, "headers", None)
    if headers is not None:
        forwarded = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
        real_ip = headers.get("x-real-ip") or headers.get("X-Real-IP")
        if real_ip and real_ip.strip():
            return real_ip.strip()

    client = getattr(request, "client", None)
    host = getattr(client, "host", None) if client is not None else None
    if host:
        return str(host)
    return "unknown"
