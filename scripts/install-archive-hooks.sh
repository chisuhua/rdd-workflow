#!/bin/sh
# scripts/install-archive-hooks.sh — idempotent installer for the archive
# post-commit hook.
#
# Created: add-archive-post-commit-hook-and-force-flag (P0, 2026-08-05).
# Idempotent: running twice produces the same state. Prints a clear
# "already installed" message on subsequent runs.
#
# Usage: scripts/install-archive-hooks.sh [project_root]
#   project_root defaults to the current git repo's toplevel.

set -e

PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
HOOK_SRC="$(cd "$(dirname "$0")/.." && pwd)/.git-hooks/post-commit"
HOOK_DST_DIR="$PROJECT_ROOT/.git-hooks"
HOOK_DST="$HOOK_DST_DIR/post-commit"

if [ ! -f "$HOOK_SRC" ]; then
    echo "❌ hook source not found: $HOOK_SRC" >&2
    echo "   ensure .git-hooks/post-commit exists in the repo" >&2
    exit 1
fi

# Idempotency check: already installed?
ALREADY=0
if [ -f "$HOOK_DST" ] && cmp -s "$HOOK_SRC" "$HOOK_DST"; then
    HOOK_INSTALLED=1
else
    HOOK_INSTALLED=0
fi
HOOKS_PATH=$(git -C "$PROJECT_ROOT" config --get core.hooksPath 2>/dev/null || true)
if [ "$HOOKS_PATH" = ".git-hooks" ] || [ "$HOOKS_PATH" = "./.git-hooks" ]; then
    HOOKS_PATH_INSTALLED=1
else
    HOOKS_PATH_INSTALLED=0
fi

if [ "$HOOK_INSTALLED" = "1" ] && [ "$HOOKS_PATH_INSTALLED" = "1" ]; then
    echo "✓ hooks already installed"
    exit 0
fi

# Install the hook file.
mkdir -p "$HOOK_DST_DIR"
cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"

# Register core.hooksPath to point at .git-hooks/ (project-local, not .git/hooks/
# which is .gitignore-prone).
git -C "$PROJECT_ROOT" config core.hooksPath .git-hooks

echo "✅ archive post-commit hook installed at $HOOK_DST"
echo "   core.hooksPath = .git-hooks"
echo "   next 'git mv + openspec archive + git commit' will auto-sync iteration.json"
