#!/usr/bin/env bash
# skills/guide-design/scripts/design_done_check.sh — design-done gate 前缀匹配版本
# 替换 SKILL.md Phase 4 内联精确比较,允许 status 带后缀如 "已批准 (date)" / "延迟 (reason)"

check_design_done_gate() {
    local input="${1:-.}"
    local suggestions_file="$input"
    if [ -d "$input" ]; then
        suggestions_file="$input/proposal-suggestions.md"
    fi
    [ -f "$suggestions_file" ] || return 0

    local pending=""
    while IFS= read -r line; do
        # skip header & separator rows
        [[ "$line" =~ \|\ 提案\ \| ]] && continue
        [[ "$line" =~ \|--- ]] && continue
        [[ "$line" =~ ^\| ]] || continue
        local status
        status=$(echo "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/,"",$(NF-1)); print $(NF-1)}')
        case "$status" in
            已批准*|已拒绝*|延迟*) : ;;  # valid decision
            *) pending="$pending [empty-or-unknown: $status]" ;;
        esac
    done < "$suggestions_file"

    if [ -n "$pending" ]; then
        echo "❌ design-done 失败: 以下提案尚无决策:$pending"
        return 1
    fi
    echo "✅ 所有提案已有决策，design-done 门控通过"
    return 0
}
