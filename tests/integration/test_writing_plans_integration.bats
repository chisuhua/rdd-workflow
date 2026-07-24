#!/usr/bin/env bats
#
# test_writing_plans_integration.bats — v2.0 自包含集成测试
# 覆盖范围:
#   - rdd-workflow-writing-plans 存在 + 元数据 + TDD 5 步结构
#   - execute.md 整合 TDD 5 步纪律
#   - prometheus-planning.md 已删除
#   - guide-ship.md 直接调用 rdd-workflow-writing-plans (无中间检测层)
#   - package.json 不再依赖 oh-my-opencode / superpowers / prometheus-start-work
#   - README.md 反映 v2.0 自包含架构
#   - 执行契约保留:.rddf/plans/<name>.md
#   - SKIP_PROMETHEUS_PLANNING=yes 行为保留

load ../test_helper

setup() {
    load_lib skill
}

REPO_ROOT_ORIGIN="${REPO_ROOT}"

# === 1. 新内置 skills 存在性 ===

@test "rdd-workflow-writing-plans.md exists in skills/" {
    assert_file_exists "$REPO_ROOT_ORIGIN/skills/rdd-workflow-writing-plans/SKILL.md"
}

@test "rdd-workflow-writing-plans.md has valid frontmatter (v2.0 self-contained)" {
    local f="$REPO_ROOT_ORIGIN/skills/rdd-workflow-writing-plans/SKILL.md"
    [ -f "$f" ]
    grep -qE '^name:[[:space:]]*rdd-workflow-writing-plans' "$f"
    grep -qE '^description:' "$f"
    grep -qE '^[[:space:]]+version:[[:space:]]*"[0-9]+\.[0-9]+"' "$f"
    grep -qE 'no external|无外部' "$f"
}

@test "rdd-workflow-writing-plans.md enforces TDD 5-step structure" {
    local f="$REPO_ROOT_ORIGIN/skills/rdd-workflow-writing-plans/SKILL.md"
    grep -q 'Write the failing test' "$f"
    grep -q 'Run test to verify it fails' "$f"
    grep -q 'Write minimal implementation' "$f"
    grep -q 'Run test to verify it passes' "$f"
    grep -q 'Commit' "$f"
}

@test "rdd-workflow-writing-plans.md contract: .rddf/plans/<name>.md output path" {
    local f="$REPO_ROOT_ORIGIN/skills/rdd-workflow-writing-plans/SKILL.md"
    grep -qE '\.rddf/plans/<CHANGE_NAME>\.md' "$f"
}

@test "rdd-workflow-writing-plans.md prohibits placeholders (TDD rigor)" {
    local f="$REPO_ROOT_ORIGIN/skills/rdd-workflow-writing-plans/SKILL.md"
    grep -q '禁止的占位符' "$f"
    grep -q 'TBD' "$f"
    grep -q 'TODO' "$f"
}

@test "execute.md has TDD 5-step discipline integrated (merged from executing-plans)" {
    local f="$REPO_ROOT_ORIGIN/skills/execute/SKILL.md"
    # TDD 5 步结构
    grep -q 'Write the failing test' "$f"
    grep -q 'Run test to verify it fails' "$f"
    grep -q 'Write minimal implementation' "$f"
    grep -q 'Run test to verify it passes' "$f"
    # Review 机制
    grep -q 'Review checklist' "$f"
    grep -q 'Spec 覆盖' "$f"
    grep -q '占位符扫描' "$f"
    # Stop 条件
    grep -q '立即停止' "$f"
}

# === 2. prometheus-planning.md 已彻底删除 ===

@test "prometheus-planning.md is fully removed (v2.0 self-contained)" {
    ! test -f "$REPO_ROOT_ORIGIN/skills/prometheus-planning.md"
}

@test "no skill references prometheus-planning in command names" {
    local f
    for f in "$REPO_ROOT_ORIGIN"/skills/*.md; do
        ! grep -qE 'skill_use\("prometheus-planning"\)' "$f" || {
            echo "DEPRECATION: $(basename $f) still calls skill_use('prometheus-planning')"
            return 1
        }
    done
}

# === 3. guide-ship.md 直接调用 (无中间层) ===

@test "guide-ship.md directly calls skill_use('rdd-workflow-writing-plans')" {
    # v3.0: skill_use call moved to ship_plan.sh helper script
    # Accept either inline in .md or in scripts/ship_plan.sh
    local md_file="$REPO_ROOT_ORIGIN/skills/guide-ship/SKILL.md"
    local sh_file="$REPO_ROOT_ORIGIN/skills/guide-ship/scripts/ship_plan.sh"

    if grep -qE 'skill_use.*rdd-workflow-writing-plans' "$md_file" 2>/dev/null; then
        return 0
    fi

    if [ -f "$sh_file" ] && grep -qE 'skill_use.*rdd-workflow-writing-plans' "$sh_file" 2>/dev/null; then
        return 0
    fi

    echo "skill_use('rdd-workflow-writing-plans') not found in guide-ship/SKILL.md or scripts/ship_plan.sh"
    return 1
}

@test "guide-ship.md no longer has detection chain (no PROMETHEUS_MODE builtin/external/none)" {
    local f="$REPO_ROOT_ORIGIN/skills/guide-ship/SKILL.md"
    ! grep -qE 'PROMETHEUS_MODE.*builtin|PROMETHEUS_MODE.*external|PROMETHEUS_MODE.*none' "$f" || {
        echo "guide-ship.md still references PROMETHEUS_MODE (v2.0 should be removed)"
        return 1
    }
}

@test "guide-ship.md version is at least 3.0 (v3.0 rename per ADR-0023)" {
    local f="$REPO_ROOT_ORIGIN/skills/guide-ship/SKILL.md"
    local ver
    ver=$(skill_meta_field "$f" version)
    # v3.0.0 renamed from spec-workflow to rdd-workflow (ADR-0023)
    # Accept any 3.0.x in case of future patch bumps.
    [[ "$ver" == 3.0* ]]
}

# === 4. package.json 简化依赖 ===

@test "package.json no longer declares engines.oh-my-opencode (v2.0 self-contained)" {
    local f="$REPO_ROOT_ORIGIN/package.json"
    ! grep -qE '"oh-my-opencode"' "$f"
}

@test "package.json no longer declares peerDependenciesMeta.superpowers (v2.0 self-contained)" {
    local f="$REPO_ROOT_ORIGIN/package.json"
    ! grep -qE '"superpowers":' "$f"
}

@test "package.json no longer lists prometheus-planning in skills array" {
    local f="$REPO_ROOT_ORIGIN/package.json"
    ! grep -qE '"prometheus-planning"' "$f"
}

@test "package.json lists rdd-workflow-writing-plans in skills array" {
    local f="$REPO_ROOT_ORIGIN/package.json"
    grep -qE '"rdd-workflow-writing-plans"' "$f"
}

@test "package.json version is 3.0.0 (v3.0 rename per ADR-0023)" {
    local f="$REPO_ROOT_ORIGIN/package.json"
    grep -qE '"version":[[:space:]]*"3\.0\.0"' "$f"
}

# === 5. README.md 反映 v2.0 自包含架构 ===

@test "README.md does not actively recommend prometheus-planning (changelog mentions OK)" {
    local f="$REPO_ROOT_ORIGIN/README.md"
    # 不应在主体说明中推荐 prometheus-planning
    # 但变更说明 (changelog) 中可以提及
    ! grep -qE 'skill_use\("prometheus-planning"\)' "$f" || {
        echo "README.md actively recommends skill_use('prometheus-planning')"
        return 1
    }
}

@test "README.md does not actively recommend oh-my-opencode (changelog mentions OK)" {
    local f="$REPO_ROOT_ORIGIN/README.md"
    # 不应在 prerequisite 章节推荐 oh-my-opencode
    ! grep -qE 'npm install.*oh-my-opencode' "$f" || {
        echo "README.md actively recommends oh-my-opencode"
        return 1
    }
}

@test "README.md does not mention superpowers/writing-plans as fallback" {
    local f="$REPO_ROOT_ORIGIN/README.md"
    ! grep -qE 'superpowers/writing-plans.*回退|superpowers/writing-plans.*fallback' "$f"
}

@test "README.md mentions rdd-workflow-writing-plans (v2.0 self-contained)" {
    local f="$REPO_ROOT_ORIGIN/README.md"
    grep -qE 'rdd-workflow-writing-plans' "$f"
}

@test "README.md describes v2.0 self-contained architecture (no external deps)" {
    local f="$REPO_ROOT_ORIGIN/README.md"
    grep -qE '完全自包含|self-contained' "$f"
    grep -qE 'v2\.0' "$f"
}

# === 6. INSTALL.md 注册新 skills ===

@test "INSTALL.md registers 13 skills including rdd-workflow-writing-plans" {
    local f="$REPO_ROOT_ORIGIN/skills/INSTALL.md"
    grep -qE '全部 13 个子技能' "$f"
    grep -qE 'rdd-workflow-writing-plans' "$f"
    ! grep -qE 'rdd-workflow-executing-plans' "$f"
    ! grep -qE 'prometheus-planning' "$f"
}

# === 7. 执行契约保留(.rddf/plans/<name>.md) ===

@test "execute.md still references .rddf/plans/<name>.md as contract path" {
    local f="$REPO_ROOT_ORIGIN/skills/execute/SKILL.md"
    grep -qE '\.rddf/plans/' "$f"
    grep -qE '\.rddf/plans/[$]CHANGE_NAME' "$f"
}

@test "status.md still references .rddf/plans/<name>.md for progress tracking" {
    local f="$REPO_ROOT_ORIGIN/skills/status/SKILL.md"
    grep -qE '\.rddf/plans/' "$f"
    grep -qE '\- \[x\]' "$f"
}

@test "SKIP_PROMETHEUS_PLANNING=yes escape hatch still works in actions.py" {
    local f="$REPO_ROOT_ORIGIN/skills/_lib/loop/actions.py"
    grep -q 'SKIP_PROMETHEUS_PLANNING' "$f"
    grep -qE 'Placeholder|placeholder' "$f"
}

@test "actions.py no longer references PROMETHEUS_PLANNING_MODE env var (v2.0 simplified)" {
    local f="$REPO_ROOT_ORIGIN/skills/_lib/loop/actions.py"
    ! grep -qE 'PROMETHEUS_PLANNING_MODE.*builtin|PROMETHEUS_PLANNING_MODE.*external|PROMETHEUS_PLANNING_MODE.*none' "$f" || {
        echo "actions.py still has PROMETHEUS_PLANNING_MODE branches"
        return 1
    }
}

@test "actions.py now references rdd-workflow-writing-plans (v2.0 self-contained)" {
    local f="$REPO_ROOT_ORIGIN/skills/_lib/loop/actions.py"
    grep -q 'rdd-workflow-writing-plans' "$f"
}

# === 8. 现有 superpowers plan 文件向后兼容 ===

@test "existing v2-core-foundation plan still works with new architecture" {
    local f="$REPO_ROOT_ORIGIN/docs/superpowers/plans/2026-06-25-v2-core-foundation.md"
    assert_file_exists "$f"
    grep -q 'Write the failing test' "$f"
    grep -q 'Run test to verify it fails' "$f"
    grep -q 'Commit' "$f"
}

@test "existing v2-beta-release plan still works" {
    local f="$REPO_ROOT_ORIGIN/docs/superpowers/plans/2026-06-26-v2-beta-release.md"
    assert_file_exists "$f"
    grep -qE 'Step [0-9]+' "$f"
}

# === 9. 总行数缩减 (代码简化指标) ===

@test "v2.0 rdd-workflow-writing-plans is shorter than old prometheus-planning (481)" {
    local size
    size=$(wc -l < "$REPO_ROOT_ORIGIN/skills/rdd-workflow-writing-plans/SKILL.md")
    [[ "$size" -lt 481 ]] || {
        echo "v2.0 writing-plans ($size lines) >= v1.3 prometheus-planning (481)"
        return 1
    }
}