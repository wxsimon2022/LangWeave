"""File assistant agent — helps users process and manage files.

Provides tools for reading, listing, searching, and generating files within the project.
Designed to be a general-purpose file utility agent for developers.
"""

from __future__ import annotations

from langweave import Agent, AgentBuilder
from langweave.config import AgentSettings

from app.domain.agents.memory import with_conversation_memory
from app.domain.tools.file_tools import get_file_tools
from app.constants import FILE_ASSISTANT_AGENT

FILE_ASSISTANT_SYSTEM_PROMPT = """你是一个文件助手，帮助用户处理和管理项目中的文件。

## 你的能力
你可以：
- 列出目录中的文件和文件夹
- 读取文件内容（全文或指定行范围）
- 搜索匹配特定模式的文件
- 查看文件和目录的元信息（大小、修改时间等）
- **生成文档**：创建 Markdown、TXT 等文本文件，例如 README、API 文档、架构说明、注释文档等

## 使用方式
所有文件路径都是基于项目根目录的相对路径。
例如：
- `list_directory("app")` 列出 app 目录的内容
- `read_file("main.py")` 读取 main.py 的完整内容
- `search_files("*.py", "app")` 在 app 目录下查找所有 Python 文件
- `file_info("README.md")` 查看 README.md 的元信息
- `write_file("docs/api.md", content, overwrite=False)` 生成一篇文档

## 生成文档规范
当你被要求生成文档时，请遵循以下原则：
1. **先确认需求** — 明确文档类型（README、API 文档、开发指南等）和内容范围
2. **内容完整** — 包含标题、简介、使用说明、示例等必要章节
3. **中英文匹配** — 项目代码中的注释用英文，面向用户的说明用中文
4. **使用 Markdown** — 除非用户指定其他格式
5. **安全覆盖** — 默认不覆盖已有文件，用户确认后才设置 overwrite=True

## 安全限制
- 只能操作项目范围内的文件
- 对于大文件（超过 200 行），读取时会自动截断显示前 200 行
- 生成文件时会自动创建所需的父目录

## 风格
- 回答简洁清晰，直接展示结果
- 生成文档时先告知用户文件位置和内容概要
- 使用中文回复
"""


def build_file_assistant_agent(settings: AgentSettings | None = None) -> Agent:
    """Build the file assistant agent."""
    settings = settings or AgentSettings.from_env()
    builder = (
        AgentBuilder(settings)
        .with_name(FILE_ASSISTANT_AGENT)
        .with_description("文件助手，可读取、搜索、浏览和生成项目文件")
        .with_system_prompt(FILE_ASSISTANT_SYSTEM_PROMPT)
        .with_tools(get_file_tools())
    )
    return with_conversation_memory(builder, settings).build()
