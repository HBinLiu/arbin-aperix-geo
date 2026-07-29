"""DOM / text locators for Doubao Web (fragile — keep isolated)."""

from __future__ import annotations

import re

# Landing chat URL (new session entry).
CHAT_URL = "https://www.doubao.com/chat/"

# Role / accessible-name patterns (Playwright get_by_role / get_by_text).
NEW_CHAT_NAME = re.compile(r"新对话|新聊天|新建对话|开启新对话")
SEND_NAME = re.compile(r"^发送$|发送消息")
STOP_NAME = re.compile(r"停止生成|停止回答|停止")
SHARE_NAME = re.compile(r"^分享$")
COPY_LINK_NAME = re.compile(r"复制链接|复制分享链接|复制")
LOGIN_HINT = re.compile(r"登录|登陆|验证码|扫码")

# Search / references panel header on assistant replies.
SEARCH_PANEL_HINT = re.compile(r"搜索\s*\d+\s*个关键词")
SEARCH_PANEL_FULL = re.compile(
    r"搜索\s*(?P<nq>\d+)\s*个关键词[，,、]?\s*参考\s*(?P<nr>\d+)\s*篇资料"
)

# Composer: textarea or contenteditable (ordered fallbacks).
COMPOSER_SELECTORS = (
    "textarea[placeholder*='输入']",
    "textarea[data-testid*='chat']",
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true']",
    "textarea",
)

# Assistant message containers (best-effort; also use text extraction fallbacks).
ASSISTANT_MESSAGE_SELECTORS = (
    "[data-testid*='message'][data-role='assistant']",
    "[data-testid*='assistant']",
    "div[class*='message'][class*='assistant']",
    "div[class*='receive-message']",
)
