"""设置向导共享工具。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.setup.session import get_session


def _setup_session(*, user_id: str, setup_session_id: str | None) -> dict[str, Any] | None:
    if not setup_session_id or not setup_session_id.strip():
        return None
    return get_session(user_id=user_id, session_id=setup_session_id.strip())


def company_from_setup_session(*, user_id: str, setup_session_id: str | None) -> str | None:
    """微观利基画像中的 company，用于写入 Subject.brand。"""
    session = _setup_session(user_id=user_id, setup_session_id=setup_session_id)
    if not session:
        return None
    profile = session.get("profile") or {}
    if not isinstance(profile, dict):
        return None
    company = str(profile.get("company") or profile.get("company_name") or "").strip()
    return company[:255] if company else None


def profile_summary_from_setup_session(*, user_id: str, setup_session_id: str | None) -> str | None:
    session = _setup_session(user_id=user_id, setup_session_id=setup_session_id)
    if not session:
        return None
    raw = session.get("profile_summary")
    if not raw:
        return None
    text = str(raw).strip()
    return text or None
