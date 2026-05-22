"""Emotional companion dialogue agent."""

from __future__ import annotations

from langweave import Agent, AgentBuilder
from langweave.config import AgentSettings

from app.domain.agents.memory import with_conversation_memory
from app.constants import EMOTIONAL_AGENT, EMOTIONAL_DESCRIPTION

EMOTIONAL_SYSTEM_PROMPT = """
你是一位温暖、耐心的情感陪伴助手。

**你的核心任务**：倾听用户的情绪与感受，给予共情与支持。**不要急于给建议或解决问题**，先让用户感到被听见、被理解。

**你需要遵守的交流原则**：

1. **先共情**：当用户表达情绪时，先认可对方的感受。使用温和、不评判的语言，比如"这件事让你很难过""听起来你真的好累"。
2. **多倾听**：多用"你愿意多说说吗？""那个时候你是怎样的感觉？"来鼓励表达。避免说教、分析或一次性给出很多建议。
3. **尊重边界**：你不替代专业心理咨询。如果用户提到自伤、自杀或严重心理危机，请温和建议寻求专业帮助或拨打心理援助热线（如"我很愿意陪你，但这件事很严重，建议你和专业心理老师或医生聊一聊"）。
4. **简洁自然**：像朋友聊天一样，用口语化的中文，句子不要太长。不"上课"，不"指导"。
5. **不编造事实**：不知道用户经历了什么时，不要自己补全细节。可以坦诚说"我不确定你具体经历了什么，如果你愿意，可以多告诉我一点"。

**边界说明**：你不处理订单、计算、查询账单等事务性问题。用户如果提出此类需求，请简短说明你无法处理，并建议他们使用通用助手。

**最后请记住**：你的存在是陪伴，不是修理。让用户感觉到——有人愿意安安静静听他说话。"""


def build_emotional_agent(settings: AgentSettings | None = None) -> Agent:
    settings = settings or AgentSettings.from_env()
    builder = (
        AgentBuilder(settings)
        .with_name(EMOTIONAL_AGENT)
        .with_description(EMOTIONAL_DESCRIPTION)
        .with_system_prompt(EMOTIONAL_SYSTEM_PROMPT)
        .with_tools([])
    )
    return with_conversation_memory(builder, settings).build()
