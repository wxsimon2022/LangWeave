"""Prompt utilities."""
from __future__ import annotations

from typing import Any


def format_prompt(template: str, **kwargs: Any) -> str:
    """Simple string-formatting prompt helper."""
    return template.format(**kwargs)
