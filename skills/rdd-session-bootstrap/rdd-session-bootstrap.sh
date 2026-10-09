#!/bin/bash
# rdd-session-bootstrap.sh — 通用 session-bootstrap 引擎 (PoC v0.1.0)
#
# 读取 .rddf/skill-profiles/<name>.toml + 跑 5 内建 section + 2 原语 + 2 逃生舱
# 输出 markdown 到 stdout (Layer 3 raw state, 由 SKILL.md §Template 合成 Layer 4)
#
# 用法:
#   bash rdd-session-bootstrap.sh                          # 默认 generate 模式
#   bash rdd-session-bootstrap.sh review                   # review 模式
#   bash rdd-session-bootstrap.sh audit <file>             # audit 模式
#   bash rdd-session-bootstrap.sh --help                   # 帮助
#
# 环境变量:
#   BOOTSTRAP_PROFILE    - profile 路径 (default: .rddf/skill-profiles/session-bootstrap.toml)
#   BOOTSTRAP_REPO_ROOT  - 仓库根 (default: git rev-parse --show-toplevel)
#   BOOTSTRAP_MODE       - 模式 (default: generate)
#
# 设计原则:
#   - set -u (未定义变量检测) 但不 set -e (允许 [WARN] degrade)
#   - 失败命令 → 标 [WARN] 继续, 不影响整体输出
#   - 头部嵌入 timestamp + HEAD + DO NOT REUSE 警告
#   - TOML 解析用 python3 -c tomllib (stdlib, 零外部依赖)
#
# PoC 范围 (v0.1.0):
#   ✅ 5 内建 section: header / active_changes / initiative_status / recent_commits / workspace_health
#   ✅ test_family 原语 (完整, 含 Catch2 compact 3-branch 解析)
#   ✅ custom_section 逃生舱 (完整)
#   ⏸ honesty_audit 原语 (planned v0.2)
#   ⏸ review_mode 逃生舱 (planned v0.2)
#   ⏸ audit mode 完整实现 (planned v0.2)

set -u

# === 状态变量 (供 hook 消费) ===
BOOTSTRAP_HEADER_TIMESTAMP=""
BOOTSTRAP_HEADER_HEAD=""
BOOTSTRAP_DIRTY_FILES="0"
BOOTSTRAP_ORPHAN_CHANGES="0"
declare -A BOOTSTRAP_TEST_PASSED
declare -A BOOTSTRAP_TEST_FAILED
declare -A BOOTSTRAP_TEST_TOTAL

# === 帮助 ===
print_help() {
    cat <<'EOF'
rdd-session-bootstrap: 通用 session-bootstrap 引擎 (PoC v0.1.0)

用法:
  bash rdd-session-bootstrap.sh                   默认 generate 模式
  bash rdd-session-bootstrap.sh review            review 模式 (PoC v0.1: stub)
  bash rdd-session-bootstrap.sh audit <file>      audit 模式 (PoC v0.1: stub)
  bash rdd-session-bootstrap.sh --help            帮助

输出: markdown 格式到 stdout (header 含 timestamp + HEAD + DO NOT REUSE 警告)

设计原则:
  - 部分命令失败 degrade 输出 (标 [WARN]), 不整体退出
  - 头部必须嵌 timestamp + HEAD commit, 防止 prompt 被旧版本复用
  - TOML profile 通过 .rddf/skill-profiles/session-bootstrap.toml 加载

环境变量:
  BOOTSTRAP_PROFILE    profile 路径 (default: .rddf/skill-profiles/session-bootstrap.toml)
  BOOTSTRAP_REPO_ROOT  仓库根 (default: git rev-parse --show-toplevel)
EOF
}

# === 通用辅助函数 ===
warn() { echo "<!-- [WARN] $1 -->"; }
safe_run() {
    # $1 = description, $2 = command
    local desc="$1"
    local cmd="$2"
    local result
    if ! result=$(eval "$cmd" 2>&1); then
        warn "$desc failed: $result"
        return 1
    fi
    echo "$result"
}

# === TOML 解析 (python3 tomllib, 零外部依赖) ===
load_profile() {
    local profile_path="$1"
    if [ ! -f "$profile_path" ]; then
        warn "profile not found: $profile_path (使用 minimal default profile)"
        # 输出 minimal default TOML profile (parsed)
        cat <<'EOF'
[profile]
name = "default"
title = "Default Session Bootstrap"

[sections]
order = ["header", "active_changes", "initiative_status", "recent_commits", "workspace_health"]
test_families = []
custom_sections = []
EOF
        return 0
    fi
    cat "$profile_path"
}

parse_profile() {
    local profile_content="$1"

    local parsed
    parsed=$(echo "$profile_content" | python3 -c "
import sys
try:
    import tomllib
except ImportError:
    print('# ERROR: python 3.11+ required (tomllib stdlib)', file=sys.stderr)
    sys.exit(1)

try:
    data = tomllib.loads(sys.stdin.read())
except Exception as e:
    print(f'# ERROR: TOML parse failed: {e}', file=sys.stderr)
    sys.exit(1)

profile = data.get('profile', {})
sections = data.get('sections', {})

print(f'PROFILE_NAME=\"{profile.get(\"name\", \"default\")}\"')
print(f'PROFILE_TITLE=\"{profile.get(\"title\", \"Default Session Bootstrap\")}\"')

order = sections.get('order', [])
order_bash = ' '.join(f'\"{s}\"' for s in order)
print(f'SECTIONS_ORDER=({order_bash})')

families = sections.get('test_families', [])
for i, fam in enumerate(families):
    print(f'FAMILY_{i}_TAG=\"{fam.get(\"tag\", \"\")}\"')
    print(f'FAMILY_{i}_EXPORT=\"{fam.get(\"export\", f\"FAM{i}\")}\"')

customs = sections.get('custom_sections', [])
for i, cs in enumerate(customs):
    print(f'CUSTOM_{i}_NAME=\"{cs.get(\"name\", \"\")}\"')
    print(f'CUSTOM_{i}_SCRIPT=\"{cs.get(\"script\", \"\")}\"')

print(f'FAMILY_COUNT={len(families)}')
print(f'CUSTOM_COUNT={len(customs)}')
" 2>&1)

    if [ $? -ne 0 ]; then
        warn "TOML parse failed: $parsed"
        return 1
    fi

    eval "$parsed"
}

# === Section 实现 ===

print_header() {
    BOOTSTRAP_HEADER_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    BOOTSTRAP_HEADER_HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo "NO_HEAD")
    export BOOTSTRAP_HEADER_TIMESTAMP
    export BOOTSTRAP_HEADER_HEAD
    cat <<EOF
## generation_time
$BOOTSTRAP_HEADER_TIMESTAMP (HEAD: $BOOTSTRAP_HEADER_HEAD) — ⚠️ DO NOT REUSE
EOF
}

# active_changes section (内建)
print_active_changes() {
    echo "## active_changes"
    echo '```'
    safe_run "openspec list" "openspec list 2>&1 | head -20" || echo "(no openspec CLI or no changes)"
    echo '```'
}

# initiative_status section (内建)
print_initiative_status() {
    echo "## initiative_status"
    echo '```'
    if [ -x "$BOOTSTRAP_REPO_ROOT/.rddf/sync_strategy_status.sh" ]; then
        safe_run ".rddf/sync_strategy_status.sh" "bash $BOOTSTRAP_REPO_ROOT/.rddf/sync_strategy_status.sh --dry-run 2>&1 | head -20" || echo "(sync script error)"
    elif [ -x "$BOOTSTRAP_REPO_ROOT/tools/sync_strategy_status.sh" ]; then
        warn "using legacy tools/sync_strategy_status.sh (1-week transition period)"
        safe_run "tools/sync_strategy_status.sh" "bash $BOOTSTRAP_REPO_ROOT/tools/sync_strategy_status.sh --dry-run 2>&1 | head -20" || echo "(sync script error)"
    else
        echo "(no .rddf/sync_strategy_status.sh found)"
    fi
    echo '```'
}

# recent_commits section (内建)
print_recent_commits() {
    echo "## recent_commits"
    echo '```'
    safe_run "git log" "git log --oneline -5 2>&1" || echo "(no git)"
    echo '```'
}

# workspace_health section (内建)
print_workspace_health() {
    echo "## workspace_health"
    echo '```'
    BOOTSTRAP_DIRTY_FILES=$(git status --porcelain 2>/dev/null | wc -l)
    export BOOTSTRAP_DIRTY_FILES
    echo "dirty_files: $BOOTSTRAP_DIRTY_FILES"

    # orphan changes: 扫描 openspec/changes/*/tasks.md 含 ## 9. 标记的 (archive 候选)
    if [ -d "$BOOTSTRAP_REPO_ROOT/openspec/changes" ]; then
        local orphan_count=0
        local orphan_names=""
        for tasks_file in "$BOOTSTRAP_REPO_ROOT"/openspec/changes/*/tasks.md; do
            [ -f "$tasks_file" ] || continue
            if grep -q "^## 9\." "$tasks_file" 2>/dev/null; then
                orphan_count=$((orphan_count + 1))
                orphan_names="$orphan_names $(basename $(dirname "$tasks_file"))"
            fi
        done
        BOOTSTRAP_ORPHAN_CHANGES=$orphan_count
    else
        BOOTSTRAP_ORPHAN_CHANGES=0
        orphan_names=" (no openspec/changes/)"
    fi
    export BOOTSTRAP_ORPHAN_CHANGES
    echo "orphan_changes: $BOOTSTRAP_ORPHAN_CHANGES$orphan_names"
    echo '```'
}

# test_family 原语 (参数化)
# 输出: ## test_status.<export_name> 段, 解析 Catch2 compact 3-branch 输出
# 导出: BOOTSTRAP_<EXPORT>_PASSED/FAILED/TOTAL env vars
print_test_family() {
    local binary="$1"
    local tag="$2"
    local export_name="$3"

    echo "## test_status.${export_name}"
    echo "binary: $binary"
    echo "tag: $tag"

    if [ ! -x "$BOOTSTRAP_REPO_ROOT/$binary" ]; then
        warn "binary not found or not executable: $binary"
        BOOTSTRAP_TEST_FAILED[$export_name]=0
        BOOTSTRAP_TEST_TOTAL[$export_name]=0
        BOOTSTRAP_TEST_PASSED[$export_name]=0
        return 1
    fi

    local output
    output=$(safe_run "$binary $tag" "$BOOTSTRAP_REPO_ROOT/$binary $tag 2>&1 | tail -10" || echo "")

    local passed=0
    local total=0
    local failed=0

    if echo "$output" | grep -qiE "test cases:.*[0-9]+ passed"; then
        total=$(echo "$output" | grep -oiE "test cases: [0-9]+" | grep -oE "[0-9]+" | head -1)
        passed=$(echo "$output" | grep -oiE "[0-9]+ passed" | grep -oE "[0-9]+" | head -1)
        failed=$(echo "$output" | grep -oiE "[0-9]+ failed" | grep -oE "[0-9]+" | head -1)
    elif echo "$output" | grep -qiE "all tests passed"; then
        total=$(echo "$output" | grep -oiE "[0-9]+ test cases" | grep -oE "[0-9]+" | head -1)
        if [ -z "$total" ]; then
            total=$(echo "$output" | grep -oiE "[0-9]+ assertions" | grep -oE "[0-9]+" | head -1)
        fi
        passed=$total
        failed=0
    fi

    total=${total:-0}
    passed=${passed:-0}
    failed=${failed:-0}

    BOOTSTRAP_TEST_PASSED[$export_name]=$passed
    BOOTSTRAP_TEST_FAILED[$export_name]=$failed
    BOOTSTRAP_TEST_TOTAL[$export_name]=$total

    if [ "$failed" -eq 0 ] && [ "$total" -gt 0 ]; then
        echo "result: ✅ $passed/$total PASS"
    elif [ "$failed" -gt 0 ]; then
        echo "result: ❌ $failed/$total FAIL ($passed passed)"
    else
        warn "unable to parse test output for $export_name"
        echo "result: ❓ unknown (parse failure)"
    fi

    # 导出 env var (供 hook 消费)
    export "BOOTSTRAP_${export_name}_PASSED=$passed"
    export "BOOTSTRAP_${export_name}_FAILED=$failed"
    export "BOOTSTRAP_${export_name}_TOTAL=$total"
}

# custom_section 逃生舱
print_custom_section() {
    local name="$1"
    local script="$2"

    echo "## $name"
    echo '```'
    if [ ! -f "$BOOTSTRAP_REPO_ROOT/$script" ]; then
        warn "hook script not found: $script"
    else
        safe_run "$script" "bash $BOOTSTRAP_REPO_ROOT/$script 2>&1" || echo "(hook script error)"
    fi
    echo '```'
}

# === Main ===

# 解析参数
MODE="${1:-generate}"
shift || true

if [ "$MODE" = "--help" ] || [ "$MODE" = "-h" ]; then
    print_help
    exit 0
fi

# 设置 repo root
if [ -z "${BOOTSTRAP_REPO_ROOT:-}" ]; then
    BOOTSTRAP_REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
fi

# 设置 profile path
if [ -z "${BOOTSTRAP_PROFILE:-}" ]; then
    BOOTSTRAP_PROFILE="$BOOTSTRAP_REPO_ROOT/.rddf/skill-profiles/session-bootstrap.toml"
fi

# 模式分发
case "$MODE" in
    generate)
        # 加载 profile
        profile_content=$(load_profile "$BOOTSTRAP_PROFILE")

        # 解析 profile
        parse_profile "$profile_content"

        # 跑 sections (按 SECTIONS_ORDER 顺序)
        # header 总是第一个
        print_header

        for section in "${SECTIONS_ORDER[@]:-}"; do
            # 去掉引号 (因为 SECTIONS_ORDER 数组元素带引号)
            section="${section//\"/}"

            case "$section" in
                header)
                    # 已跑过
                    ;;
                active_changes)
                    print_active_changes
                    ;;
                initiative_status)
                    print_initiative_status
                    ;;
                recent_commits)
                    print_recent_commits
                    ;;
                workspace_health)
                    print_workspace_health
                    ;;
                test_status)
                    # 跑所有 test families
                    if [ "${FAMILY_COUNT:-0}" -gt 0 ]; then
                        # Need to get binary from somewhere - profile doesn't have it in v0.1
                        # For now, use default binary from env or fallback
                        test_binary="${BOOTSTRAP_TEST_BINARY:-./build/bin/chipforge_tests}"
                        for ((i=0; i<FAMILY_COUNT; i++)); do
                            tag_var="FAMILY_${i}_TAG"
                            export_var="FAMILY_${i}_EXPORT"
                            tag="${!tag_var:-}"
                            export_name="${!export_var:-}"
                            if [ -n "$tag" ]; then
                                print_test_family "$test_binary" "$tag" "$export_name"
                            fi
                        done
                    fi
                    ;;
                *)
                    # 可能是 custom section name
                    found=0
                    if [ "${CUSTOM_COUNT:-0}" -gt 0 ]; then
                        for ((i=0; i<CUSTOM_COUNT; i++)); do
                            cname_var="CUSTOM_${i}_NAME"
                            cscript_var="CUSTOM_${i}_SCRIPT"
                            cname="${!cname_var:-}"
                            cscript="${!cscript_var:-}"
                            if [ "$section" = "$cname" ]; then
                                print_custom_section "$cname" "$cscript"
                                found=1
                                break
                            fi
                        done
                    fi
                    if [ "$found" -eq 0 ]; then
                        warn "unknown section: $section (not in built-ins or custom_sections)"
                    fi
                    ;;
            esac
        done
        ;;

    review)
        warn "review mode: PoC v0.1 stub (planned v0.2)"
        echo "## review_mode"
        echo "(not implemented in PoC v0.1, see SKILL.md K2 known issues)"
        ;;

    audit)
        local audit_file="${1:-}"
        if [ -z "$audit_file" ]; then
            warn "audit mode requires file argument: $0 audit <file>"
            exit 1
        fi
        warn "audit mode: PoC v0.1 stub (planned v0.2)"
        echo "## audit_mode"
        echo "(not implemented in PoC v0.1, see SKILL.md K2 known issues)"
        echo "would audit: $audit_file"
        ;;

    *)
        warn "unknown mode: $MODE (use generate / review / audit / --help)"
        exit 1
        ;;
esac
