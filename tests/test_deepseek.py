"""DeepSeek integration tests (no live API)."""

from __future__ import annotations

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from langweave import AgentBuilder
from langweave.config import AgentSettings, load_dotenv
from langweave.models.deepseek import model_id


def test_load_dotenv_reads_project_env() -> None:
    load_dotenv()
    settings = AgentSettings.from_env()
    # When .env exists in repo, key should be populated (CI may omit it)
    if settings.deepseek_api_key:
        assert settings.deepseek_api_key.startswith("sk-")


def test_model_id_prefix() -> None:
    assert model_id("deepseek-chat") == "deepseek:deepseek-chat"
    assert model_id("deepseek:deepseek-reasoner") == "deepseek:deepseek-reasoner"


def test_settings_model_kwargs_deepseek_key() -> None:
    settings = AgentSettings(
        model="deepseek:deepseek-chat",
        deepseek_api_key="test-key",
        temperature=0.5,
    )
    kwargs = settings.model_kwargs()
    assert kwargs["api_key"] == "test-key"
    assert kwargs["temperature"] == 0.5


def test_builder_with_deepseek_uses_prefixed_model() -> None:
    fake = FakeMessagesListChatModel(responses=[AIMessage(content="ok")])
    agent = (
        AgentBuilder()
        .with_deepseek("deepseek-chat")
        .with_model(fake)
        .build()
    )
    assert agent.chat("hi") == "ok"


def test_builder_deepseek_string_model() -> None:
    builder = AgentBuilder().with_deepseek("deepseek-reasoner", temperature=0.1)
    assert builder._model == "deepseek:deepseek-reasoner"
    assert builder._model_kwargs["temperature"] == 0.1
