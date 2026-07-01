"""Tests for setup upload text extraction."""

from __future__ import annotations

import zipfile
from io import BytesIO

import pytest

from aperix_geo.services.setup.upload import extract_upload_text


def _minimal_docx(text: str) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
</w:document>""",
        )
    return buf.getvalue()


def test_extract_txt_and_md() -> None:
    assert extract_upload_text(filename="a.txt", content="hello".encode()) == "hello"
    assert extract_upload_text(filename="b.md", content="# Title".encode()) == "# Title"


def test_extract_docx() -> None:
    content = _minimal_docx("品牌介绍正文")
    assert extract_upload_text(filename="c.docx", content=content) == "品牌介绍正文"


def test_reject_legacy_doc() -> None:
    with pytest.raises(ValueError, match="docx"):
        extract_upload_text(filename="legacy.doc", content=b"binary")
