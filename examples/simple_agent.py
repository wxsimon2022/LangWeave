"""Single agent with built-in tools."""

from langweave import AgentBuilder
from langweave.middleware import LoggingMiddleware
from langweave.tools import calculator, current_time


def main() -> None:
    agent = (
        AgentBuilder()
        .with_name("assistant")
        .with_model("openai:gpt-4o-mini")  # requires langchain-openai + OPENAI_API_KEY
        .with_system_prompt("You are a helpful assistant. Use tools when needed.")
        .with_tools([calculator, current_time])
        .with_middleware(LoggingMiddleware())
        .build()
    )

    answer = agent.chat("What is 17 * 23? Use the calculator.")
    print(answer)


if __name__ == "__main__":
    main()
