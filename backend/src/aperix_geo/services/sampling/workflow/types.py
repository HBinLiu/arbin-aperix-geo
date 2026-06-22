"""Typed contracts for sampling workflow task results."""

from __future__ import annotations

from typing import TypedDict


class SamplingTaskResult(TypedDict, total=False):
    ok: bool
    phase: str
    skipped: bool
    reason: str
    error: str
    rate_limited: bool
