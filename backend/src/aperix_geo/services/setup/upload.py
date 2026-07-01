"""Setup 上传文件纯文本提取。"""

from __future__ import annotations

import zipfile
from io import BytesIO
from xml.etree import ElementTree

ALLOWED_UPLOAD_SUFFIXES = frozenset({".txt", ".md", ".docx"})
DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def upload_suffix(filename: str) -> str:
    name = (filename or "").strip().lower()
    for suffix in ALLOWED_UPLOAD_SUFFIXES:
        if name.endswith(suffix):
            return suffix
    return ""


def extract_upload_text(*, filename: str, content: bytes) -> str:
    suffix = upload_suffix(filename)
    if suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="replace").strip()
    if suffix == ".docx":
        return _extract_docx_text(content)
    raise ValueError("仅支持 .docx、.md、.txt 文件")


def _extract_docx_text(content: bytes) -> str:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        with archive.open("word/document.xml") as handle:
            tree = ElementTree.parse(handle)
    parts: list[str] = []
    for node in tree.findall(".//w:t", DOCX_NS):
        if node.text:
            parts.append(node.text)
    text = "".join(parts).strip()
    if not text:
        raise ValueError("未能从 docx 中提取文本")
    return text
