#!/usr/bin/env bash
# resolve_skill_name.sh - resolve short skill names to full names
# Usage: source resolve_skill_name.sh; resolve_skill_name <short_name> [skill_list_file]

resolve_skill_name() {
    local short_name="$1"
    local skill_file="${2:-/dev/stdin}"

    if [ ! -f "$skill_file" ] && [ "$skill_file" != "/dev/stdin" ]; then
        echo "ERROR: Skill list file not found: $skill_file"
        return 1
    fi

    local exact_match
    exact_match=$(grep -F "/$short_name" "$skill_file" 2>/dev/null || echo "")
    local exact_count
    exact_count=$(echo "$exact_match" | grep -c . 2>/dev/null | head -n1 || echo 0)
    [ -z "$exact_count" ] && exact_count=0
    if [ "$exact_count" -eq 1 ]; then
        echo "$exact_match"
        return 0
    fi

    local matches
    matches=$(grep -E "(^|/)$short_name$" "$skill_file" 2>/dev/null || echo "")
    local match_count
    match_count=$(echo "$matches" | grep -c . 2>/dev/null | head -n1 || echo 0)
    [ -z "$match_count" ] && match_count=0

    if [ "$match_count" -eq 0 ]; then
        local suggestions
        suggestions=$(grep -i "${short_name%%/*}" "$skill_file" 2>/dev/null | head -5 || echo "")
        echo "ERROR: No skill matches '$short_name'"
        if [ -n "$suggestions" ]; then
            echo "Did you mean?"
            echo "$suggestions"
        fi
        return 1
    elif [ "$match_count" -eq 1 ]; then
        echo "$matches"
        return 0
    else
        echo "ERROR: Ambiguous match for '$short_name':"
        echo "$matches"
        return 1
    fi
}
