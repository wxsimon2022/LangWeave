"""LLM 使用指南 — 如何配置与切换模型提供商

## 环境变量配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `LANGWEAVE_MODEL` | 默认模型 ID | `deepseek:deepseek-chat` |
| `LANGWEAVE_TEMPERATURE` | 采样温度 | `0.3` |
| `LANGWEAVE_MAX_TOKENS` | 最大生成 token | `4096` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxx` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-xxx` |

## 支持的模型提供商

- **DeepSeek**: `deepseek:deepseek-chat`, `deepseek:deepseek-reasoner`
- **OpenAI**: `openai:gpt-4o`, `openai:gpt-4o-mini`, `openai:gpt-4-turbo`

## 代码中使用

```python
from app.core.llm import create_llm

llm = create_llm("deepseek:deepseek-chat", temperature=0.3)
```
"""
