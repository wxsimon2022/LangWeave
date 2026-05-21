"""Unified API response envelope tests."""

from __future__ import annotations

from langweave.web.response import ApiResponse


def test_api_response_ok() -> None:
    r = ApiResponse.ok({"x": 1})
    assert r.code == 200
    assert r.message == ""
    assert r.data == {"x": 1}


def test_api_response_fail() -> None:
    r = ApiResponse.fail(404, "not found")
    assert r.code == 404
    assert r.message == "not found"
    assert r.data is None
