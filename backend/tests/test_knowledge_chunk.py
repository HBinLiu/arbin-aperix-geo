"""Tests for knowledge text chunking."""

from __future__ import annotations

from aperix_geo.services.knowledge.chunk import chunk_text, estimate_token_count


def test_chunk_text_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_short_single_chunk() -> None:
    chunks = chunk_text("短文本", chunk_size=500, overlap=64)
    assert len(chunks) == 1
    assert chunks[0].text == "短文本"
    assert chunks[0].char_start == 0
    assert chunks[0].char_end == 3


def test_chunk_text_respects_overlap_and_order() -> None:
    text = "A" * 900
    chunks = chunk_text(text, chunk_size=500, overlap=64, max_chunks=10)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[0].char_start == 0
    assert chunks[1].char_start == chunks[0].char_end - 64


def test_chunk_text_max_chunks_cap() -> None:
    text = "字" * 10_000
    chunks = chunk_text(text, chunk_size=100, overlap=10, max_chunks=3)
    assert len(chunks) == 3


def test_estimate_token_count() -> None:
    assert estimate_token_count("") == 0
    assert estimate_token_count("abcd") >= 1
