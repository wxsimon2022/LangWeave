"""File operation tools for the file assistant agent.

These tools operate on local files within the project's working directory.
Includes read, list, search, and summary operations.
"""

from __future__ import annotations

import os
import fnmatch
from pathlib import Path

from langchain_core.tools import tool

# Restrict file operations to the project root for safety
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # app/domain/tools/ → project root


def _safe_path(path: str) -> Path:
    """Resolve a path and ensure it's within PROJECT_ROOT."""
    resolved = (PROJECT_ROOT / path).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT.resolve())):
        msg = f"Access denied: path outside project directory ({path})"
        raise ValueError(msg)
    return resolved


@tool
def list_directory(path: str = ".") -> str:
    """List files and directories under the given path (relative to project root).

    Args:
        path: Directory path relative to project root, e.g. "app", "langweave", ".".
    """
    target = _safe_path(path)
    if not target.is_dir():
        return f"Error: '{path}' is not a directory"

    entries = []
    for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
        icon = "📁" if entry.is_dir() else "📄"
        size = entry.stat().st_size if entry.is_file() else ""
        size_str = f" ({_fmt_size(size)})" if size else ""
        entries.append(f"{icon} {entry.name}{size_str}")

    total = len(entries)
    result = "\n".join(entries)
    return f"📂 {path}/ — {total} items\n\n{result}"


@tool
def read_file(path: str) -> str:
    """Read the full contents of a text file.

    Args:
        path: File path relative to project root, e.g. "app/constants.py".
    """
    target = _safe_path(path)
    if not target.is_file():
        return f"Error: file not found: {path}"
    try:
        content = target.read_text(encoding="utf-8")
        lines = content.count("\n") + 1
        if lines > 200:
            return (
                f"📄 {path} ({lines} lines, showing first 200)\n\n"
                + "\n".join(content.split("\n")[:200])
                + f"\n\n... ({lines - 200} more lines truncated. Use read_file with line range for full view.)"
            )
        return f"📄 {path} ({lines} lines)\n\n{content}"
    except UnicodeDecodeError:
        return f"Error: '{path}' is a binary file and cannot be displayed as text"


@tool
def read_file_range(path: str, start_line: int = 1, end_line: int | None = None) -> str:
    """Read a specific range of lines from a file.

    Args:
        path: File path relative to project root.
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (inclusive). Defaults to start_line.
    """
    target = _safe_path(path)
    if not target.is_file():
        return f"Error: file not found: {path}"
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
        total = len(lines)
        end = end_line or start_line
        start_idx = max(0, start_line - 1)
        end_idx = min(total, end)

        if start_idx >= total:
            return f"Error: file has only {total} lines"
        selected = lines[start_idx:end_idx]
        result = "\n".join(
            f"{i + 1:4d} | {line}"
            for i, line in enumerate(selected, start=start_idx + 1)
        )
        return f"📄 {path} lines {start_line}–{end_idx}/{total}\n\n{result}"
    except UnicodeDecodeError:
        return f"Error: '{path}' is a binary file"


@tool
def search_files(pattern: str, path: str = ".") -> str:
    """Search for files matching a glob/wildcard pattern under the given path.

    Args:
        pattern: Glob pattern, e.g. "*.py", "test_*.py", "*.md".
        path: Directory path relative to project root, e.g. "app", ".".
    """
    target = _safe_path(path)
    if not target.is_dir():
        return f"Error: directory not found: {path}"

    matches = []
    for root, _dirs, files in os.walk(target):
        for fname in files:
            if fnmatch.fnmatch(fname, pattern):
                rel = Path(root).relative_to(PROJECT_ROOT)
                matches.append(str(rel / fname))

    matches.sort()
    if not matches:
        return f"No files matching '{pattern}' found under {path}/"
    return f"🔍 Found {len(matches)} files matching '{pattern}' under {path}/\n\n" + "\n".join(
        f"  {m}" for m in matches
    )


@tool
def file_info(path: str) -> str:
    """Show metadata for a file or directory.

    Args:
        path: Path relative to project root, e.g. "main.py", "app/".
    """
    target = _safe_path(path)
    if not target.exists():
        return f"Error: not found: {path}"

    stat = target.stat()
    info = {
        "name": target.name,
        "path": str(target.relative_to(PROJECT_ROOT)) if target.resolve() != PROJECT_ROOT.resolve() else ".",
        "type": "directory" if target.is_dir() else "file",
        "size": _fmt_size(stat.st_size),
        "modified": _fmt_time(stat.st_mtime),
        "created": _fmt_time(stat.st_ctime),
    }
    icon = "📁" if target.is_dir() else "📄"
    return (
        f"{icon} {info['path']}\n"
        f"  类型: {info['type']}\n"
        f"  大小: {info['size']}\n"
        f"  修改: {info['modified']}"
    )


def _fmt_size(bytes_: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f}{unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f}TB"


def _fmt_time(timestamp: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get_file_tools() -> list:
    """Return all file operation tools."""
    return [
        list_directory,
        read_file,
        read_file_range,
        write_file,
        search_files,
        file_info,
    ]


@tool
def write_file(path: str, content: str, overwrite: bool = False) -> str:
    """Write text content to a file. Creates the file and any missing parent directories.

    Args:
        path: File path relative to project root, e.g. "docs/architecture.md".
        content: Text content to write.
        overwrite: Set to True to overwrite an existing file. Defaults to False.
    """
    target = _safe_path(path)

    if target.is_dir():
        return f"Error: '{path}' is a directory, cannot write"

    if target.exists() and not overwrite:
        return (
            f"⚠️ 文件已存在: {path}\n"
            f"如需覆盖请设置 overwrite=True，或选择其他文件名"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    size = _fmt_size(target.stat().st_size)
    action = "覆盖" if target.exists() and overwrite else "新建"
    download_url = f"/api/v1/files/{target.relative_to(PROJECT_ROOT / 'docs')}" if (PROJECT_ROOT / 'docs') in target.parents or target.parent == (PROJECT_ROOT / 'docs') else ""
    if download_url:
        return f"✅ 已{action}文件: {path} ({size})\n📥 下载链接: {download_url}\n点击链接或复制到浏览器下载"
    return f"✅ 已{action}文件: {path} ({size})"
