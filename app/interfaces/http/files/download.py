"""File download routes — serve generated documents from the docs/ directory."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/v1/files", tags=["files"])

# Documents are written to the project's docs/ directory
DOCS_DIR = Path(__file__).resolve().parents[4] / "docs"  # app/interfaces/http/files/ → project root


@router.get(
    "/{path:path}",
    summary="下载生成的文件",
    responses={
        200: {"description": "文件内容", "content": {"application/octet-stream": {}}},
        404: {"description": "文件不存在"},
    },
)
async def download_file(path: str):
    """下载 docs/ 目录下由文件助手生成的文件。"""
    # Security: prevent path traversal
    safe_path = (DOCS_DIR / path).resolve()
    if not str(safe_path).startswith(str(DOCS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=safe_path,
        filename=safe_path.name,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_path.name}"',
        },
    )
