"""DOM / text locators for Doubao Web (fragile — keep isolated)."""

from __future__ import annotations

import re

# Landing chat URL (new session entry).
CHAT_URL = "https://www.doubao.com/chat/"

# Role / accessible-name patterns (Playwright get_by_role / get_by_text).
NEW_CHAT_NAME = re.compile(r"新对话|新聊天|新建对话|开启新对话")
# Landing /chat may default to「工作」; sample/probe must switch to「对话」first.
CHAT_TAB_NAME = re.compile(r"^对话$")
WORK_TAB_NAME = re.compile(r"^工作$")
WORK_LANDING_HINT = re.compile(r"今天有什么工作要处理")
# Transient Doubao toast; page often loses the composer until reload.
SYSTEM_ERROR_HINT = re.compile(r"系统异常")
SEND_NAME = re.compile(r"发送消息|^\s*发送\s*$")
STOP_NAME = re.compile(r"停止生成|停止回答|停止输出|^停止$|Stop generating")
SHARE_NAME = re.compile(r"^\s*分享\s*$")
# Overflow menu rows often include 置顶/重命名 next to 分享 (sanity check).
SHARE_MENU_HINT = re.compile(r"置顶|重命名|举报|删除")
# Header "⋯" / more actions (share lives inside this menu on current Doubao Web).
MORE_MENU_NAME = re.compile(r"更多|更多操作|更多选项|菜单|More")
COPY_LINK_NAME = re.compile(r"复制链接|复制分享链接|^复制$")
# Delete current thread (heartbeat probe must remove its own chat).
DELETE_CHAT_NAME = re.compile(r"^删除$|删除对话|删除聊天|删除会话")
CONFIRM_DELETE_NAME = re.compile(r"^确定$|^确认$|确认删除|删除对话")
LOGIN_HINT = re.compile(r"登录|登陆|验证码|扫码")
# Assistant message toolbar (copy / 朗读 / …). First direct ``button`` copies Markdown body.
MESSAGE_ACTION_BAR = ".message-action-button-main"
READ_ALOUD_NAME = re.compile(r"朗读")

# Search / references panel header on assistant replies (outside md-box-root).
SEARCH_PANEL_HINT = re.compile(r"搜索\s*\d+\s*个关键词")
SEARCH_PANEL_FULL = re.compile(
    r"搜索\s*(?P<nq>\d+)\s*个关键词[，,、]?\s*参考\s*(?P<nr>\d+)\s*篇资料"
)
SEARCH_PANEL_TAIL = re.compile(r"^[^\n]{0,40}参考\s*\d+\s*篇资料\s*")

# Quoted keywords inside the expanded search panel (fan-out).
QUOTED_QUERY = re.compile(r"[“「『\"]([^”」』\"]{1,200})[”」』\"]")

# Share dialog / clipboard evidence path shapes.
SHARE_PATH = re.compile(r"/(?:share|thread)/", re.IGNORECASE)

# Behavior captcha / 人机验证（must be human-solved; never auto-bypass）.
CAPTCHA_TEXT = re.compile(
    r"拖拽到这里|请选择所有符合|行为验证|人机验证|安全验证|滑动验证|"
    r"选中所有|拖拽到下方|完成验证后继续|"
    r"换个网络|更换网络|切换网络|请更换网络|请切换网络|"
    r"图片加载失败"
)
CAPTCHA_DOM_SELECTORS = (
    "text=拖拽到这里",
    "text=请选择所有符合上文描述的图片",
    "text=行为验证",
    "text=人机验证",
    "text=安全验证",
    "text=换个网络",
    "text=更换网络",
    "text=图片加载失败",
)

# Composer: textarea or contenteditable (ordered fallbacks).
COMPOSER_SELECTORS = (
    "textarea[placeholder*='输入']",
    "textarea[data-testid*='chat']",
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true']",
    "textarea",
)

# Assistant reply body: Doubao renders Markdown into md-box-root (data-streaming).
# Fan-out / references live outside this node — do not scrape the whole chat shell.
MD_BOX_SELECTORS = (
    ".md-box-root",
    "[data-streaming].md-box-root",
    "div[data-streaming='false']",
    "div[data-streaming='true']",
)

# Legacy fallbacks only when md-box is missing.
ASSISTANT_MESSAGE_SELECTORS = (
    "[data-testid*='message'][data-role='assistant']",
    "[data-testid*='assistant']",
    "div[class*='message'][class*='assistant']",
    "div[class*='receive-message']",
)

# Chrome / shell lines to strip from fallback plain-text paths.
UI_CHROME_LINE = re.compile(
    r"^(AI\s*生成可能有误.*|下载电脑版|下载客户端|新对话|开启新对话|登录|登陆|"
    r"置顶|重命名|举报|删除|复制|分享)$"
)
