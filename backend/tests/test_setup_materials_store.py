"""Tests for setup materials store."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from aperix_geo.services.setup.materials_store import save_setup_materials


@patch("aperix_geo.services.setup.materials_store.update_session", return_value=True)
@patch("aperix_geo.services.setup.materials_store.get_session")
def test_save_setup_materials_requires_at_least_one_field(mock_get_session, mock_update) -> None:
    mock_get_session.return_value = {"subject_type": "brand", "upload_files": []}

    save_setup_materials(
        user_id="u1",
        session_id="s1",
        brand_intro="简短介绍",
        website_url="",
    )
    save_setup_materials(
        user_id="u1",
        session_id="s1",
        brand_intro="",
        website_url="https://example.com",
    )
    mock_update.assert_called_with(
        user_id="u1",
        session_id="s1",
        patch={"brand_intro": "", "website_url": "https://example.com", "materials_saved": True},
    )
    save_setup_materials(
        user_id="u1",
        session_id="s1",
        brand_intro="",
        website_url="geo.example.com/about",
    )
    mock_update.assert_called_with(
        user_id="u1",
        session_id="s1",
        patch={
            "brand_intro": "",
            "website_url": "geo.example.com/about",
            "materials_saved": True,
        },
    )
    mock_get_session.return_value = {
        "subject_type": "brand",
        "upload_files": [{"id": "f1", "name": "a.txt", "extracted_text": "内容"}],
    }
    save_setup_materials(user_id="u1", session_id="s1", brand_intro="", website_url="")

    mock_get_session.return_value = {"subject_type": "brand", "upload_files": []}
    with pytest.raises(HTTPException) as exc:
        save_setup_materials(user_id="u1", session_id="s1", brand_intro="", website_url="")
    assert exc.value.status_code == 400
    assert "至少" in str(exc.value.detail)

    with pytest.raises(HTTPException) as exc:
        save_setup_materials(user_id="u1", session_id="s1", brand_intro="", website_url="not-a-url")
    assert exc.value.status_code == 400
    assert "品牌 URL" in str(exc.value.detail)
