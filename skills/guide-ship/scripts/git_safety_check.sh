#!/usr/bin/env bash
# skills/guide-ship/scripts/git_safety_check.sh — 检查工作树是否干净 + 仅含 ship-scope
# Per improve-commit-scope-discipline proposal.
#
#   PROJECT_ROOT=/path bash git_safety_check.sh [--strict]
#
#   Env:
#     STRICT_COMMIT_SCOPE=yes  升级 WARNING 为 block (exit 1)
#
#   行为:
#     - tracked 文件 modification → 警告 (默认 WARN, strict 模式 block)
#     - untracked 文件 (e.g., specs/<capability>/spec.md) → informational, OK
#     - 干净工作树 → exit 0
#
#   输出 (stderr):
#     "⚠️  工作树不干净, 建议先 stash 或 commit 这些改动: <file list>"
#     或 "✅ 工作树干净 (或仅 untracked), 允许 commit"

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

case "${1:-}" in
    --strict) STRICT_COMMIT_SCOPE=yes ;;
    "")       : ;;
    *)        echo "usage: $0 [--strict]" >&2; exit 1 ;;
esac

cd "$PROJECT_ROOT" || exit 1

# Separate tracked-modification vs untracked-addition
porcelain=$(git status --porcelain 2>/dev/null || true)
tracked_dirty=""
untracked=""

if [ -n "$porcelain" ]; then
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        xy="${line:0:2}"
        case "$xy" in
            "??") untracked="${untracked}${line}"$'\n' ;;
            *)    tracked_dirty="${tracked_dirty}${line}"$'\n' ;;
        esac
    done <<< "$porcelain"
fi

# Tracked modifications: always warn; strict mode blocks
if [ -n "$tracked_dirty" ]; then
    echo "⚠️  工作树不干净 (tracked 文件有 modification):" >&2
    echo "$tracked_dirty" | sed 's/^/   /' >&2
    echo "" >&2
    echo "建议: 先 git stash 或 git commit 这些改动, 再 ship 当前 change." >&2
    echo "或: 使用 'git add <specific-files>' 精确暂存, 不要 'git add -A'." >&2
    echo "" >&2
    if [ "${STRICT_COMMIT_SCOPE:-no}" = "yes" ]; then
        echo "❌ STRICT_COMMIT_SCOPE=yes, blocking commit." >&2
        exit 1
    fi
    echo "(WARNING 级, 可继续 — 但 ship 阶段会污染 commit)" >&2
    # Don't exit 1 in non-strict mode; user can override
    exit 0
fi

# Untracked only: informational
if [ -n "$untracked" ]; then
    echo "ℹ️  工作树仅含 untracked 文件 (合法 ship 阶段新增):" >&2
    echo "$untracked" | sed 's/^/   /' >&2
fi

echo "✅ 工作树干净 (或仅 untracked), 允许 commit" >&2
exit 0