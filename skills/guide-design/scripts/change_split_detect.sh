#!/usr/bin/env bash
# skills/guide-design/scripts/change_split_detect.sh — 检测 pending proposals 共享文件
# Per improve-change-splitting-strategy proposal.
#
#   PROJECT_ROOT=/path bash change_split_detect.sh [--json]
#
# 输出 (默认):
#   检测到的共享文件 + 涉及的 proposal name(s)
# 输出 (--json):
#   {"conflicts": [{"file": "...", "proposals": [...], "severity": "warn|block"}], "summary": {...}}
#
# 检测策略: 从 .rddf/improvements/*.md 的 ## 范围 节 grep 文件路径 (相对路径)。
# 同一文件出现在多个 proposal 的 ## 范围 → 共享文件警告。

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
IMPROVEMENTS_DIR="$PROJECT_ROOT/.rddf/improvements"

case "${1:-}" in
    --json) JSON_MODE=yes ;;
    "")     JSON_MODE=no ;;
    *)      echo "usage: $0 [--json]" >&2; exit 1 ;;
esac

if [ ! -d "$IMPROVEMENTS_DIR" ]; then
    if [ "$JSON_MODE" = "yes" ]; then
        echo '{"conflicts": [], "summary": {"proposals_scanned": 0, "conflicts_found": 0}}'
    else
        echo "⚠️  improvements dir not found: $IMPROVEMENTS_DIR"
    fi
    exit 0
fi

# Scan each proposal's ## 范围 section, extract file paths
declare -A FILE_TO_PROPOSALS  # file → "p1 p2 p3"
proposal_count=0

for proposal_path in "$IMPROVEMENTS_DIR"/*.md; do
    [ -f "$proposal_path" ] || continue
    proposal_name=$(basename "$proposal_path" .md)
    proposal_count=$((proposal_count + 1))

    # Extract ## 范围 section, then grep file-like paths (containing /)
    # Format: - backtick path backtick (e.g., `- 修复 \`AGENTS.md\` line 72`)
    scope_section=$(awk '/^## 范围/{flag=1; next} /^## /{flag=0} flag' "$proposal_path" \
        | grep -oE '`[^`]+`' \
        | tr -d '`' \
        | grep -E '\.[a-zA-Z]{1,5}$' \
        | sort -u)

    while IFS= read -r file; do
        [ -z "$file" ] && continue
        # Skip obvious non-file patterns
        case "$file" in
            *"<"*|*">"*) continue ;;
            v[0-9]*) continue ;;
        esac
        FILE_TO_PROPOSALS["$file"]="${FILE_TO_PROPOSALS[$file]:-} $proposal_name"
    done <<< "$scope_section"
done

# Filter to shared files (mentioned in ≥2 proposals)
conflicts_json=""
conflict_count=0
text_output=""
for file in "${!FILE_TO_PROPOSALS[@]}"; do
    proposals="${FILE_TO_PROPOSALS[$file]}"
    # Trim leading space
    proposals="${proposals# }"
    # Count words
    n=$(echo "$proposals" | wc -w | tr -d '[:space:]')
    if [ "$n" -ge 2 ]; then
        conflict_count=$((conflict_count + 1))
        proposal_arr=$(echo "$proposals" | tr ' ' '\n' | sort -u | sed 's/^/"/' | sed 's/$/"/' | paste -sd, -)
        if [ "$JSON_MODE" = "yes" ]; then
            conflicts_json="${conflicts_json}{\"file\":\"${file}\",\"proposals\":[${proposal_arr}],\"severity\":\"warn\"},"
        else
            text_output="${text_output}  ⚠️  ${file}  ←  ${proposals}"$'\n'
        fi
    fi
done

if [ "$JSON_MODE" = "yes" ]; then
    # Strip trailing comma
    conflicts_json="${conflicts_json%,}"
    printf '{"conflicts":[%s],"summary":{"proposals_scanned":%d,"conflicts_found":%d}}\n' \
        "$conflicts_json" "$proposal_count" "$conflict_count"
else
    if [ "$conflict_count" -eq 0 ]; then
        echo "✅ 无共享文件冲突 (扫描 $proposal_count 个 proposal)"
    else
        echo "⚠️  发现 $conflict_count 个共享文件:"
        echo "$text_output"
        echo ""
        echo "建议: 合并为单个 change, 或强制串行 ship 并要求精确 patch"
    fi
fi