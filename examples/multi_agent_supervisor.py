"""Supervisor delegates to specialist agents."""

from langweave import AgentBuilder
from langweave.orchestration import SupervisorBuilder


def build_researcher() -> AgentBuilder:
    return (
        AgentBuilder()
        .with_name("researcher")
        .with_description("Summarizes facts and explains concepts.")
        .with_system_prompt("You are a research specialist. Be concise and factual.")
    )


def build_coder() -> AgentBuilder:
    return (
        AgentBuilder()
        .with_name("coder")
        .with_description("Writes and explains code.")
        .with_system_prompt("You are a coding specialist. Prefer short examples.")
    )


def main() -> None:
    model = "openai:gpt-4o-mini"  # requires langchain-openai + OPENAI_API_KEY

    researcher = build_researcher().with_model(model).build()
    coder = build_coder().with_model(model).build()

    supervisor = SupervisorBuilder(
        {"researcher": researcher, "coder": coder},
        model=model,
    ).build()

    answer = supervisor.chat(
        "Explain what a Python decorator is, then show a minimal example."
    )
    print(answer)


if __name__ == "__main__":
    main()
