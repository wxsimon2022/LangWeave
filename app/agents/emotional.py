"""Emotional companion dialogue agent."""

from __future__ import annotations

from langweave import Agent, AgentBuilder
from langweave.config import AgentSettings

from app.agents._memory import with_conversation_memory

EMOTIONAL_SYSTEM_PROMPT = """你是一位温暖、耐心的情感陪伴助手。你的职责是倾听用户的情绪与感受，给予共情与支持，而不是急于给建议或解决问题。

交流原则：
1. 先共情：认可对方的情绪（如焦虑、难过、愤怒、孤独），用温和、不评判的语气回应
2. 多倾听：适当追问感受，避免说教、避免一次性罗列大量建议
3. 尊重边界：不替代专业心理咨询；若用户提及自伤、自杀或严重心理危机，请温和建议寻求专业帮助或拨打当地心理援助热线
4. 简洁自然：用中文口语化表达，句子不宜过长，像朋友聊天一样
5. 不编造事实：不清楚用户经历时不要虚构细节；可以问「你愿意多说说吗？」

你不处理订单、计算等事务性问题；若用户提出此类需求，可简短说明并建议他们使用通用助手。"""


def build_emotional_agent(settings: AgentSettings | None = None) -> Agent:
    settings = settings or AgentSettings.from_env()
    builder = (
        AgentBuilder(settings)
        .with_name("emotional")
        .with_description("情感陪伴与倾听，提供共情式对话支持（支持多轮记忆）")
        .with_system_prompt(EMOTIONAL_SYSTEM_PROMPT)
        .with_tools([])
    )
    return with_conversation_memory(builder, settings).build()
