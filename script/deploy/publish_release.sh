#!/usr/bin/env bash
# publish_release.sh — Create a GitHub Release and upload desktop build artifacts
#
# Prerequisites:
#   1. gh CLI installed (https://cli.github.com/)
#   2. gh auth login
#   3. Desktop builds exist in frontends/desktop/release/
#
# Usage (in project root):
#   bash script/deploy/publish_release.sh [TAG]
#
# If TAG is omitted, it auto-increments from the latest tag.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/frontends/desktop"

cd "$ROOT_DIR"

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
  done < <(find "$DESKTOP_DIR/release" -maxdepth 2 \( -name "*.dmg" -o -name "*.exe" -o -name "*.AppImage" -o -name "*.deb" \) -print0)
fi

# ---------------------------------------------------------------------------
# Create release notes
# ---------------------------------------------------------------------------
MAIN_HASH="$(git rev-parse --short HEAD)"
RELEASE_NOTES=$(cat <<EOF
## LangWeave Desktop $TAG

📦 **Desktop Client**
- macOS: \`LangWeave-$TAG.dmg\` (Intel \& Apple Silicon)
- Windows: \`LangWeave-$TAG.exe\` (64-bit installer)
- Linux: \`LangWeave-$TAG.AppImage\`

🌐 **Web App**
- [https://chat.mybfs.cn/](${TAG})

\`\`\`
Commit: $MAIN_HASH
Tag:    $TAG
\`\`\`
EOF
)

# ---------------------------------------------------------------------------
# Create or update GitHub Release
# ---------------------------------------------------------------------------
echo "Creating release $TAG on GitHub..."

if command -v gh &>/dev/null; then
  # Use gh CLI (recommended)
  RELEASE_URL=$(gh release create "$TAG" \
    --title "LangWeave $TAG" \
    --notes "$RELEASE_NOTES" \
    "${ASSETS[@]}" 2>&1)
  echo "Release created: $RELEASE_URL"
else
  echo "ERROR: gh CLI not found. Install it from https://cli.github.com/"
  echo "Then run: gh auth login"
  echo ""
  echo "Alternatively, create the release manually at:"
  echo "  https://github.com/wxsimon2022/LangWeave/releases/new?tag=$TAG"
  exit 1
fi

echo ""
echo "=== Done ==="
