#!/usr/bin/env bash
set -euo pipefail

# ============================================
#  LangWeave — GitHub 仓库发布与可发现性脚本
# ============================================
# 用法:
#   gh auth login                     # 首次：浏览器登录 GitHub
#   bash script/deploy/publish_repo.sh
#
# 该脚本会:
#   1. 更新仓库描述 (description)
#   2. 设置 GitHub Topics（让仓库出现在 topic 搜索结果页）
#   3. 设置 homepage URL（关联部署站点，提升 SEO 权重）
#   4. 验证结果
#
# 前置条件: gh CLI 已认证 (gh auth status)
# ============================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

REPO="wxsimon2022/LangWeave"
HOMEPAGE="https://chat.mybfs.cn/"

DESCRIPTION="LangChain + LangGraph Python Agents 框架与 AI 情感陪伴聊天应用。支持多 Agent 编排、流式输出、多轮对话记忆。"

TOPICS=(
  "langchain"
  "langgraph"
  "ai-agents"
  "python"
  "fastapi"
  "vue"
  "chatbot"
  "emotional-support"
  "deepseek"
  "llm"
  "agent-framework"
  "openai"
)

echo "============================================"
echo "  LangWeave — 仓库发布脚本"
echo "============================================"
echo ""

# ---- Check auth ----
echo "[1/4] 检查 GitHub 认证状态..."
if ! gh auth status &>/dev/null; then
  echo "  ❌ gh 未认证。请先运行:"
  echo "     gh auth login"
  echo ""
  echo "     或者使用 Token:"
  echo "     echo <YOUR_TOKEN> | gh auth login --with-token"
  exit 1
fi
echo "  ✅ 已认证为 $(gh api user --jq .login)"

# ---- 1. Update repo metadata ----
echo ""
echo "[2/4] 更新仓库描述 + 首页..."
gh repo edit "$REPO"   --description "$DESCRIPTION"   --homepage "$HOMEPAGE"   --enable-wiki=true   --enable-issues=true
echo "  ✅ 描述已设置"
echo "  ✅ 首页已关联: $HOMEPAGE"

# ---- 2. Set Topics ----
echo ""
echo "[3/4] 设置 GitHub Topics ($(echo "${TOPICS[@]}" | wc -w) 个)..."
TOPICS_JSON=$(printf '%s\n' "${TOPICS[@]}" | jq -R . | jq -s .)
curl -s -X PUT "https://api.github.com/repos/$REPO/topics"   -H "Authorization: token $(gh auth token)"   -H "Accept: application/vnd.github.mercy-preview+json"   -d "{\"names\": $TOPICS_JSON}" > /dev/null
echo "  ✅ Topics: ${TOPICS[*]}"

# ---- 3. Verify ----
echo ""
echo "[4/4] 验证结果..."
echo ""
echo "============================================"
gh repo view "$REPO" --json description,homepageUrl,repositoryTopics,updatedAt | \
  python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'  描述:    {d.get(\"description\")}')
print(f'  首页:    {d.get(\"homepageUrl\", \"(未设置)\")}')
topics = [t.get('name','') for t in d.get('repositoryTopics',{}).get('nodes',[])]
print(f'  Topics:  {topics if topics else \"(空)\"}')
print(f'  更新:    {d.get(\"updatedAt\")}')
"
echo ""
echo "============================================"
echo "  ✅ 仓库发布完成！"
echo "============================================"
echo ""
echo "  仓库地址: https://github.com/$REPO"
echo "  在线站点: $HOMEPAGE"
echo ""
echo "  接下来："
echo "    1. git push 确保本地文件已推送"
echo "    2. 社交媒体分享仓库链接加速收录"
echo "    3. 提交 sitemap 到搜索引擎"
echo ""

# ---- Auto commit ----
echo "自动提交本地变更..."
if git diff --quiet -- CITATION.cff .github/workflows/repo-meta.yml script/deploy/publish_repo.sh 2>/dev/null; then
  echo "  无变更，跳过"
else
  git add CITATION.cff .github/workflows/repo-meta.yml script/deploy/publish_repo.sh 2>/dev/null
  git commit -m "chore: add repo SEO metadata for discoverability" 2>/dev/null || true
  echo "  已提交。请手动推送: git push"
fi
echo "✅ 完成"
