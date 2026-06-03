"""JWT access tokens."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from aperix_geo.config import get_settings


def create_access_token(*, user_id: UUID, tenant_id: UUID, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_encrypt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_encrypt_algorithm])


def parse_user_tenant_ids(payload: dict[str, Any]) -> tuple[UUID, UUID]:
    try:
        uid = UUID(payload["sub"])
        tid = UUID(payload["tenant_id"])
    except (KeyError, ValueError) as e:
        raise JWTError("Invalid token payload") from e
    return uid, tid
