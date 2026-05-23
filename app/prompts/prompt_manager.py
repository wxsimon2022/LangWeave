"""Prompt manager — centralized prompt loading and management."""
from __future__ import annotations

from typing import Any


class PromptManager:
    """Manage and serve prompts to agents."""

    def __init__(self) -> None:
        self._prompts: dict[str, str] = {}

    def register(self, name: str, prompt: str) -> None:
        self._prompts[name] = prompt

    def get(self, name: str) -> str | None:
        return self._prompts.get(name)

    def format(self, name: str, **kwargs: Any) -> str:
        prompt = self.get(name)
        if prompt is None:
            msg = f"Prompt not found: {name}"
            raise KeyError(msg)
        return prompt.format(**kwargs)
