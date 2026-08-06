#!/usr/bin/env bash
# skills/_lib/skill_root.sh — Dual-root path resolution for rdd-workflow skills.
#
# Purpose:
#   Resolve SKILL_DIR (skill installation root) independently of PROJECT_ROOT,
#   so globally-installed skills (~/.agents/skills/<name> symlinks) work from
#   ANY project directory, not just the rdd-workflow repo itself.
#
# Resolution order (project-local wins, matching OpenCode skill scope priority):
#   1. $PROJECT_ROOT/.opencode/skills/<name>   — project-local installation
#   2. $HOME/.agents/skills/<name>             — global installation
#   3. $RDD_WORKFLOW_SRC/skills/<name>         — development source checkout
#
# Usage (from SKILL.md code blocks or shell scripts):
#   source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" \
#       2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
#   GUIDE_PLAN_DIR="$(resolve_rdd_skill_dir guide-plan)"
#   source "$GUIDE_PLAN_DIR/scripts/plan_intake.sh"
#
# Note: the bootstrap source line above prefers the project-local copy of THIS
# file when present (pure project-local installs may not have a global copy).

resolve_rdd_skill_dir() {
    local name="$1"
    # 1. Project-local install (copied into .opencode/skills/)
    if [ -n "${PROJECT_ROOT:-}" ] && [ -d "$PROJECT_ROOT/.opencode/skills/$name" ]; then
        echo "$PROJECT_ROOT/.opencode/skills/$name"
        return 0
    fi
    # 2. Global install (symlinked to ~/.agents/skills/)
    if [ -n "${HOME:-}" ] && [ -d "$HOME/.agents/skills/$name" ]; then
        echo "$HOME/.agents/skills/$name"
        return 0
    fi
    # 3. Development source checkout (explicit opt-in via env var)
    if [ -n "${RDD_WORKFLOW_SRC:-}" ] && [ -d "$RDD_WORKFLOW_SRC/skills/$name" ]; then
        echo "$RDD_WORKFLOW_SRC/skills/$name"
        return 0
    fi
    echo "ERROR: Cannot resolve skill dir for '$name'" >&2
    echo "  Searched: \$PROJECT_ROOT/.opencode/skills, ~/.agents/skills, \$RDD_WORKFLOW_SRC/skills" >&2
    return 1
}

resolve_rdd_lib_dir() {
    # _lib is shared infrastructure, not a skill, but follows the same order.
    # v2.0.8+ layout: _lib/ is at the package root (next to skills/).
    if [ -n "${PROJECT_ROOT:-}" ] && [ -d "$PROJECT_ROOT/.opencode/skills/rdd-workflow/_lib" ]; then
        echo "$PROJECT_ROOT/.opencode/skills/rdd-workflow/_lib"
        return 0
    fi
    if [ -n "${HOME:-}" ] && [ -d "$HOME/.agents/_lib" ]; then
        echo "$HOME/.agents/_lib"
        return 0
    fi
    # Backward-compat: older per-project installs had _lib under skills/.
    if [ -n "${PROJECT_ROOT:-}" ] && [ -d "$PROJECT_ROOT/.opencode/skills/_lib" ]; then
        echo "$PROJECT_ROOT/.opencode/skills/_lib"
        return 0
    fi
    if [ -n "${HOME:-}" ] && [ -d "$HOME/.agents/skills/_lib" ]; then
        echo "$HOME/.agents/skills/_lib"
        return 0
    fi
    if [ -n "${RDD_WORKFLOW_SRC:-}" ] && [ -d "$RDD_WORKFLOW_SRC/_lib" ]; then
        echo "$RDD_WORKFLOW_SRC/_lib"
        return 0
    fi
    echo "ERROR: Cannot resolve _lib dir" >&2
    echo "  Searched: \$PROJECT_ROOT/.opencode/skills/rdd-workflow/_lib, ~/.agents/_lib, \$RDD_WORKFLOW_SRC/_lib" >&2
    return 1
}
