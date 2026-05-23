#!/usr/bin/env bash
# publish_release.sh — Create a GitHub Release and upload desktop build artifacts
#
# Prerequisites:
#   1. gh CLI installed (https://cli.github.com/) OR
#      GITHUB_TOKEN environment variable set (GitHub Personal Access Token)
#   2. Desktop builds exist in frontends/desktop/release/
#
# Usage (in project root):
#   bash script/deploy/publish_release.sh [TAG]
#
# If TAG is omitted, it auto-increments from the latest tag.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/frontends/desktop"
REPO="wxsimon2022/LangWeave"

cd "$ROOT_DIR"

# 使用国内镜像加速 Electron / electron-builder 下载
export ELECTRON_MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}"
export ELECTRON_BUILDER_BINARIES_MIRROR="${ELECTRON_BUILDER_BINARIES_MIRROR:-https://npmmirror.com/mirrors/electron-builder-binaries/}"

# ---------------------------------------------------------------------------
# Determine tag
# ---------------------------------------------------------------------------
if [[ $# -ge 1 ]]; then
  TAG="$1"
else
  TAG="v1.0.1"
  LATEST_TAG="$(git tag --sort=-v:refname 2>/dev/null | head -1)"
  if [[ -n "$LATEST_TAG" && "$LATEST_TAG" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
    TAG="v${MAJOR}.${MINOR}.$((PATCH + 1))"
  fi
fi

echo "=== Publishing GitHub Release $TAG ==="

# ---------------------------------------------------------------------------
# Ensure tag exists and is pushed
# ---------------------------------------------------------------------------
if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG does not exist. Creating and pushing..."
  git tag "$TAG"
  git push origin "$TAG"
fi

# ---------------------------------------------------------------------------
# Collect desktop build artifacts
# ---------------------------------------------------------------------------
ASSETS=()
if [ -d "$DESKTOP_DIR/release" ]; then
  while IFS= read -r -d '' f; do
    ASSETS+=("$f")
  done < <(find "$DESKTOP_DIR/release" -maxdepth 2 \( -name "*.dmg" -o -name "*.exe" -o -name "*.AppImage" \) -print0)
fi

echo "Found ${#ASSETS[@]} desktop build artifact(s):"
for a in "${ASSETS[@]}"; do
  echo "  - $a"
done

# ---------------------------------------------------------------------------
# Create release notes
# ---------------------------------------------------------------------------
MAIN_HASH="$(git rev-parse --short HEAD)"
RELEASE_NOTES=$(cat <<EOF
## LangWeave Desktop $TAG

📦 **Desktop Client**
- macOS: \`LangWeave-$TAG.dmg\` (Intel & Apple Silicon)
- Windows: \`LangWeave-$TAG.exe\` (64-bit installer)
- Linux: \`LangWeave-$TAG.AppImage\`

🌐 **Web App**
- [https://chat.mybfs.cn/](https://chat.mybfs.cn/)

\`\`\`
Commit: $MAIN_HASH
Tag:    $TAG
\`\`\`
EOF
)

# ---------------------------------------------------------------------------
# Create GitHub Release
# ---------------------------------------------------------------------------
echo "Creating release $TAG on GitHub ($REPO)..."

if command -v gh &>/dev/null; then
  # ── Method 1: gh CLI ──
  echo "Using gh CLI..."
  RELEASE_URL=$(gh release create "$TAG" \
    --repo "$REPO" \
    --title "LangWeave $TAG" \
    --notes "$RELEASE_NOTES" \
    "${ASSETS[@]}" 2>&1)
  echo "Release created: $RELEASE_URL"

elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
  # ── Method 2: GitHub API via curl ──
  echo "Using GitHub API with GITHUB_TOKEN..."

  API_URL="https://api.github.com/repos/$REPO/releases"

  # Create release
  RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$(cat <<PAYLOAD
{
  "tag_name": "$TAG",
  "name": "LangWeave $TAG",
  "body": $(echo "$RELEASE_NOTES" | jq -Rs '.'),
  "draft": false,
  "prerelease": false
}
PAYLOAD
  )")

  RELEASE_ID=$(echo "$RESPONSE" | jq -r '.id // empty')
  RELEASE_HTML_URL=$(echo "$RESPONSE" | jq -r '.html_url // empty')

  if [[ -z "$RELEASE_ID" ]]; then
    echo "ERROR: Failed to create release:"
    echo "$RESPONSE" | jq .
    exit 1
  fi

  echo "Release created: $RELEASE_HTML_URL (id: $RELEASE_ID)"

  # Upload each asset
  for asset in "${ASSETS[@]}"; do
    BASENAME=$(basename "$asset")
    echo "Uploading $BASENAME..."
    UPLOAD_URL="https://uploads.github.com/repos/$REPO/releases/$RELEASE_ID/assets?name=$BASENAME"
    curl -s -X POST "$UPLOAD_URL" \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Content-Type: application/octet-stream" \
      --data-binary @"$asset" > /dev/null
    echo "  ✓ $BASENAME uploaded"
  done

else
  echo "ERROR: No authentication method available."
  echo ""
  echo "Install gh CLI and run 'gh auth login', or set GITHUB_TOKEN environment variable."
  echo ""
  echo "Get a token at: https://github.com/settings/tokens"
  echo ""
  echo "Or create the release manually at:"
  echo "  https://github.com/$REPO/releases/new?tag=$TAG"
  exit 1
fi

echo ""
echo "=== Done ==="
