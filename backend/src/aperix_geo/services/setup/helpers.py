"""设置向导共享工具。"""

from __future__ import annotations

from aperix_geo.services.setup.session import get_session


def profile_summary_from_setup_session(*, user_id: str, setup_session_id: str | None) -> str | None:
    if not setup_session_id or not setup_session_id.strip():
        return None
    session = get_session(user_id=user_id, session_id=setup_session_id.strip())
    if not session:
        return None
    raw = session.get("profile_summary")
    if not raw:
        return None
    text = str(raw).strip()
    return text or None
