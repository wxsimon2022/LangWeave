# LangWeave 框架参考

日常开发见 [开发指南.md](开发指南.md)；项目总览见 [README.md](../../README.md)。

---

## 架构总览

```
langweave/              ← 框架核心
├── agent.py · builder.py · registry.py · config.py · memory.py
├── models/ · middleware/ · tools/ · orchestration/ · web/

app/                    ← 业务应用
├── agents/             ← Agent 实现
├── api/v1/             ← unified、conversations
├── application/services/  ← auth、chat、intent
├── core/               ← LLM、MCP、RAG、监控
├── domain/ · infrastructure/ · interfaces/http/ · schemas/
```

---

## LangWeave 核心框架

### AgentBuilder

```python
from langweave import AgentBuilder
from langweave.tools import calculator

agent = (
    AgentBuilder()
    .with_name("my_agent")
    .with_deepseek("deepseek-chat", temperature=0.3)
    .with_tools([calculator])
    .with_system_prompt("你是助手")
    .with_response_format(MyPydanticSchema)
    .with_checkpointer(get_checkpointer())
    .build()
)
```

### Agent 调用

```python
reply = agent.chat("你好", thread_id="s1")
reply, thread_id = await agent.achat("你好")
async for chunk in agent.astream("你好"):
    yield chunk
```

### AgentRegistry · AgentSettings · Memory · Tools

见 [README.md](../../README.md) 框架章节；LLM 配置见 [app/core/llm/README.md](../../app/core/llm/README.md)。

---

## 意图路由

```
POST /api/v1/unified/stream
  → IntentService.recognize()
    → emotional_chat → emotional（research_agent_v2）
    → general_chat / order_query / calculation / unknown → assistant（general_agent_v2）
```

| 文件 | 职责 |
|------|------|
| `app/api/v1/agents_unified.py` | HTTP 入口，prefix `/api/v1` |
| `app/application/services/intent.py` | 意图识别 |
| `app/application/services/chat.py` | 路由与流式输出 |
| `app/schemas/intent.py` | `UserIntent` 结构化输出 |

同对话首次消息做意图分类；`agent_name` 持久化后后续消息直达对应 Agent。

---

## Web 层

**框架端点**

- `GET /health`
- `GET /api/v1/agents`
- `POST /api/v1/agents/{name}/chat|invoke|stream`

**业务端点**

- `POST /api/v1/unified/stream`
- `GET/POST/PATCH/DELETE /api/v1/conversations/*`
- `POST /api/v1/auth/*`
- `POST /api/v1/heartbeat/ping`
- `GET /api/v1/admin/*`

**SSE**：`X-Accel-Buffering: no` · nginx `proxy_buffering off`

**响应格式**：`{"code": 200, "message": "", "data": {...}}`

---

## 应用层

**数据表**：`c_users` · `c_conversations` · `c_messages`

**双轨记忆**：LangGraph Checkpointer + `c_messages` 持久化

**鉴权**：JWT（HS256）· PBKDF2 · Redis 黑名单 · 单设备 session

---

## Supervisor 模式

```python
from langweave.orchestration import SupervisorBuilder

supervisor = SupervisorBuilder({"math": math_agent, "search": search_agent}).build()
```

---

## 依赖

`requirements.txt` · `pyproject.toml`；可选 `langchain-deepseek`、`fastapi-swagger2`。
