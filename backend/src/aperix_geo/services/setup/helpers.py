"""设置向导共享工具。"""

from __future__ import annotations

from typing import Any


def company_from_session(session: dict[str, Any] | None) -> str | None:
    """微观利基画像中的 company，用于写入 Subject.brand。"""
    if not session:
        return None
    profile = session.get("profile") or {}
    if not isinstance(profile, dict):
        return None
    company = str(profile.get("company") or "").strip()
    return company[:255] if company else None


def profile_summary_from_session(session: dict[str, Any] | None) -> str | None:
    if not session:
        return None
    raw = session.get("profile_summary")
    if not raw:
        return None
    text = str(raw).strip()
    return text or None
