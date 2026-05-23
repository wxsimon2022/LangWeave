"""Intent classification agent — structured output, no tools.

Classifies user intent into predefined categories and routes to
the appropriate specialist agent.
"""
from __future__ import annotations

from langweave import Agent, AgentBuilder
from langweave.config import AgentSettings

from app.schemas.intent import UserIntent
from app.constants import INTENT_AGENT

INTENT_SYSTEM_PROMPT = """你是意图识别模块。只分析用户输入，输出结构化分类结果，不要直接回答用户问题。

可选 intent（必须选一个）：
- emotional_chat: 倾诉情绪、寻求安慰、焦虑抑郁孤独、人际关系烦恼、压力大想聊聊
- general_chat: 闲聊、通用问答、打招呼（无明显情绪诉求）
- order_query: 查订单、物流、发货、退款状态
- calculation: 数学计算、换算
- unknown: 无法归类

规则：
1. confidence 为 0~1，越确定越高
2. slots 提取实体，如 order_id、expression、emotion（情绪词）；没有则 {}
3. target_agent 填写处理该意图的 agent 名称：
   - emotional_chat → emotional
   - order_query / calculation / general_chat → assistant
   - unknown → assistant
4. reasoning 用一句话说明分类依据
"""


def build_intent_agent(settings: AgentSettings | None = None) -> Agent:
    settings = settings or AgentSettings.from_env()
    return (
        AgentBuilder(settings)
        .with_name(INTENT_AGENT)
        .with_description("Classifies user intent via structured output")
        .with_system_prompt(INTENT_SYSTEM_PROMPT)
        .with_response_format(UserIntent)
        .with_tools([])
        .build()
    )
