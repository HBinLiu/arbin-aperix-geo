"""Doubao samantha Web completion protocol constants (not OpenAI schema)."""

from __future__ import annotations

import json
import uuid
from typing import Any

# Default free-chat bot id used by doubao.com web (overridable via DOUBAO_WEB_BOT_ID).
DEFAULT_BOT_ID = "7338286299411103781"

SAMANTHA_COMPLETION_URL = "https://www.doubao.com/samantha/chat/completion"

SAMANTHA_BASE_PARAMS: dict[str, str] = {
    "aid": "497858",
    "device_platform": "web",
    "language": "zh",
    "pc_version": "2.41.0",
    "pkg_type": "release_version",
    "real_aid": "497858",
    "region": "CN",
    "samantha_web": "1",
    "sys_region": "CN",
    "use-olympus-account": "1",
    "version_code": "20800",
}


def completion_body(
    prompt: str,
    *,
    conversation_id: str = "0",
    bot_id: str = DEFAULT_BOT_ID,
) -> dict[str, Any]:
    need_create = conversation_id in ("", "0")
    payload: dict[str, Any] = {
        "messages": [
            {
                "content": json.dumps({"text": prompt}, ensure_ascii=False),
                "content_type": 2001,
                "attachments": [],
                "references": [],
            }
        ],
        "completion_option": {
            "is_regen": False,
            "with_suggest": True,
            "need_create_conversation": need_create,
            "launch_stage": 1,
            "is_replace": False,
            "is_delete": False,
            "message_from": 0,
            "action_bar_skill_id": 0,
            "use_deep_think": False,
            "use_auto_cot": True,
            "resend_for_regen": False,
            "enable_commerce_credit": False,
            "event_id": "0",
        },
        "evaluate_option": {"web_ab_params": ""},
        "conversation_id": "0" if need_create else conversation_id,
        "local_conversation_id": f"local_{uuid.uuid4().hex}",
        "local_message_id": str(uuid.uuid4()),
    }
    if not need_create:
        payload["bot_id"] = bot_id
    return payload
