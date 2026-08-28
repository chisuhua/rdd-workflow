#!/usr/bin/env bash
# skills/rdd-workflow-brainstorm/scripts/pre_create_brainstorm_check.sh
# Brainstorm HARD-GATE pre-create validator for .rddf/improvements/<name>.md.
#
# Enforces the <HARD-GATE> rule from rdd-workflow-brainstorm/SKILL.md at the
# file level: a proposal may only be created / re-created / registered in
# proposal-suggestions.md when the draft carries complete brainstorm output.
#
# A passing draft must satisfy ALL of:
#   1. 5 core sections : ## 架构依据 / ## 范围 / ## Capabilities / ## Impact / ## 验收标准
#      (heading whitespace is normalized, so "## 验收 标准" == "## 验收标准")
#   2. ## Why and ## What Changes headings (5-para brainstorm output structure)
#   3. ## Acceptance section containing >= 3 checkbox items ("- [ ]")
#   4. a "**主题**: <theme>" field
#   5. the **主题** value matching at least 1 roadmap theme
#
# Usage:
#   bash pre_create_brainstorm_check.sh <improvement_file> [--project-root <root>]
#   PROJECT_ROOT env var is honored when --project-root is not passed.
#
# Exit codes:
#   0 - HARD-GATE satisfied
#   1 - HARD-GATE NOT satisfied (stderr lists every failing condition)
#   2 - usage error (missing arg / improvement file not found)
set -uo pipefail

IMPROVEMENT_FILE="${1:-}"
if [[ -z "$IMPROVEMENT_FILE" ]]; then
    echo "❌ usage: pre_create_brainstorm_check.sh <improvement_file> [--project-root <root>]" >&2
    exit 2
fi

PROJECT_ROOT="${PROJECT_ROOT:-}"
if [[ "${2:-}" == "--project-root" ]]; then
    PROJECT_ROOT="${3:-}"
fi
if [[ -z "$PROJECT_ROOT" ]]; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

if [[ ! -f "$IMPROVEMENT_FILE" ]]; then
    echo "❌ brainstorm HARD-GATE: improvement file not found: $IMPROVEMENT_FILE" >&2
    exit 2
fi

# --- helpers ---------------------------------------------------------------

# section_exists <file> <heading>: true if a "## <heading>" heading is present,
# with internal whitespace normalized so "验收 标准" matches "验收标准".
section_exists() {
    local file="$1" heading="$2"
    local norm_heading="${heading//[[:space:]]/}"
    local line norm_line
    while IFS= read -r line; do
        norm_line="${line//[[:space:]]/}"
        if [[ "$norm_line" == "##${norm_heading}" ]]; then
            return 0
        fi
    done < "$file"
    return 1
}

# count_checkboxes <file>: number of markdown task-checkbox lines in the file.
count_checkboxes() {
    local file="$1"
    grep -cE '^[[:space:]]*-[[:space:]]*\[[ xX]\]' "$file" 2>/dev/null || echo 0
}

# collect_roadmap_themes <project_root>: print every roadmap theme name found in
# .rddf/roadmap/{phases,features}/*.md frontmatter ("主题: ..." line).
collect_roadmap_themes() {
    local root="$1" f
    for f in "$root"/.rddf/roadmap/phases/*.md "$root"/.rddf/roadmap/features/*.md; do
        [[ -f "$f" ]] || continue
        grep -E '^主题[[:space:]]*:' "$f" | sed -E 's/^主题[[:space:]]*:[[:space:]]*//'
    done
}

# theme_matches <theme_value> <project_root>: true if <theme_value> overlaps at
# least one roadmap theme (substring match, either direction).
theme_matches() {
    local value="$1" root="$2" t
    [[ -z "$value" ]] && return 1
    while IFS= read -r t; do
        [[ -z "$t" ]] && continue
        if [[ "$value" == *"$t"* || "$t" == *"$value"* ]]; then
            return 0
        fi
    done < <(collect_roadmap_themes "$root")
    return 1
}

# --- checks ----------------------------------------------------------------

FAILURES=()

# Check 1: 5 core sections
for sec in "架构依据" "范围" "Capabilities" "Impact" "验收标准"; do
    if ! section_exists "$IMPROVEMENT_FILE" "$sec"; then
        FAILURES+=("missing section: ## $sec")
    fi
done

# Check 2: ## Why and ## What Changes headings
for sec in "Why" "What Changes"; do
    if ! section_exists "$IMPROVEMENT_FILE" "$sec"; then
        FAILURES+=("missing section: ## $sec")
    fi
done

# Check 3: ## Acceptance section with >= 3 checkboxes
if ! section_exists "$IMPROVEMENT_FILE" "Acceptance"; then
    FAILURES+=("missing section: ## Acceptance")
fi
if [[ "$(count_checkboxes "$IMPROVEMENT_FILE")" -lt 3 ]]; then
    FAILURES+=("## Acceptance must contain at least 3 checkbox items (- [ ])")
fi

# Check 4: **主题**: field present
if ! grep -qE '^\*\*主题\*\*[[:space:]]*:' "$IMPROVEMENT_FILE"; then
    FAILURES+=("missing field: **主题**:")
fi

# Check 5: **主题** value matches at least 1 roadmap theme
THEME_VALUE="$(grep -E '^\*\*主题\*\*[[:space:]]*:' "$IMPROVEMENT_FILE" | head -n1 | sed -E 's/^\*\*主题\*\*[[:space:]]*:[[:space:]]*//')"
if ! theme_matches "$THEME_VALUE" "$PROJECT_ROOT"; then
    FAILURES+=("**主题**: value '${THEME_VALUE:-<empty>}' does not match any roadmap theme")
fi

# --- report ----------------------------------------------------------------

if [[ "${#FAILURES[@]}" -gt 0 ]]; then
    echo "❌ brainstorm HARD-GATE not satisfied, run skill_use('rdd-workflow-brainstorm') first" >&2
    for f in "${FAILURES[@]}"; do
        echo "   - $f" >&2
    done
    exit 1
fi

echo "✅ brainstorm HARD-GATE satisfied: $IMPROVEMENT_FILE"
exit 0
