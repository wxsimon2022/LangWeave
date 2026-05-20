"""Run an agent with DeepSeek (requires DEEPSEEK_API_KEY)."""

from langweave import AgentBuilder
from langweave.models import DEEPSEEK_CHAT
from langweave.tools import calculator


def main() -> None:
    agent = (
        AgentBuilder()
        .with_name("deepseek-assistant")
        .with_deepseek(DEEPSEEK_CHAT, temperature=0.3)
        .with_system_prompt("You are a helpful assistant. Use tools for math.")
        .with_tools([calculator])
        .build()
    )

    print(agent.chat("用计算器算一下 12345 * 6789"))


if __name__ == "__main__":
    main()
