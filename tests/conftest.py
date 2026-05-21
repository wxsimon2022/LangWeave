"""Ensure langweave is importable when running pytest from repo root."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def unwrap_response(response_json: dict) -> dict:
    """Extract ``data`` from unified API envelope."""
    assert "code" in response_json
    assert "message" in response_json
    assert "data" in response_json
    return response_json["data"]
