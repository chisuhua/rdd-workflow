#!/usr/bin/env bash
# rddf — spec-workflow CLI entry point
#
# Usage: rddf <command> [options]
#
# Commands:
#   rddf dashboard                全项目状态仪表盘 (7 板块)
#   rddf status                   全局概览 (changes + worktrees)
#   rddf status <name>            单 change 详情
#   rddf status --iteration       当前 sprint 表 (Mode E)
#   rddf status --roadmap         路线图阶段进度 (Mode D)
#   rddf feature                  按 feature 分组的汇总表
#   rddf feature graph            Mermaid 依赖拓扑图
#   rddf feature order            Wave 分组执行顺序
#   rddf feature status <name>    单 feature 详情
#   rddf sessions                 会话管理
#     list / show <id> / current / resume <id> / abandon <id> / gc
#   rddf guide                    无状态推荐器 (下一步建议)
#   rddf deps                     依赖分析结果展示
#   rddf monitor                  实时监控 (session + worktree + events)
#     --watch=<sec>                  周期刷新
#   rddf archive <name>           归档 change (merge → archive → cleanup)
#   rddf cleanup                  清理孤立 worktree 和 branch
#   rddf validate                 质量门控检查
#   rddf init                     安装 spec-workflow 到当前项目
#   rddf help                     显示此帮助
#
# Repository: https://github.com/chisuhua/spec-workflow
# License: MIT

set -euo pipefail

# ────────────────────────────────────────────────────────────
# 0. 路径发现
# ────────────────────────────────────────────────────────────

# rddf 脚本所在目录 (支持 symlink)
_RDDF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
_RDDF_SCRIPT="$(
  if command -v realpath >/dev/null 2>&1; then
    realpath "${BASH_SOURCE[0]:-$0}" 2>/dev/null || echo "$_RDDF_DIR/rddf"
  else
    echo "$_RDDF_DIR/rddf"
  fi
)"

# 项目根目录
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
# 关键路径 — 优先从脚本所在目录推断
SKILLS_DIR="$_RDDF_DIR"

# SKILLS_LIB 发现: 依次检查常见位置
if [ -d "$SKILLS_DIR/skills/_lib" ]; then
    SKILLS_LIB="$SKILLS_DIR/skills/_lib"
elif [ -d "$PROJECT_ROOT/skills/_lib" ]; then
    SKILLS_LIB="$PROJECT_ROOT/skills/_lib"
elif [ -d "$SKILLS_DIR/../_lib" ]; then
    SKILLS_LIB="$(cd "$SKILLS_DIR/../_lib" && pwd)"
else
    SKILLS_LIB=""
    for d in "$SKILLS_DIR"/*/_lib "$SKILLS_DIR"/skills/*/_lib; do
        if [ -d "$d" ]; then
            SKILLS_LIB="$d"
            break
        fi
    done
fi

STATE_DIR="$PROJECT_ROOT/.rddf/state"

# ────────────────────────────────────────────────────────────
# 1. 辅助函数
# ────────────────────────────────────────────────────────────

# 颜色/样式 (兼容非 tty)
if [ -t 1 ]; then
    BOLD=$(tput bold 2>/dev/null || echo '')
    DIM=$(tput dim 2>/dev/null || echo '')
    RED=$(tput setaf 1 2>/dev/null || echo '')
    GREEN=$(tput setaf 2 2>/dev/null || echo '')
    YELLOW=$(tput setaf 3 2>/dev/null || echo '')
    BLUE=$(tput setaf 4 2>/dev/null || echo '')
    MAGENTA=$(tput setaf 5 2>/dev/null || echo '')
    CYAN=$(tput setaf 6 2>/dev/null || echo '')
    RESET=$(tput sgr0 2>/dev/null || echo '')
else
    BOLD=''; DIM=''; RED=''; GREEN=''; YELLOW=''; BLUE=''; MAGENTA=''; CYAN=''; RESET=''
fi

say()  { echo -e "$@"; }
info() { say "${BLUE}ℹ${RESET} $*"; }
ok()   { say "${GREEN}✓${RESET} $*"; }
warn() { say "${YELLOW}⚠${RESET} $*" >&2; }
err()  { say "${RED}✗${RESET} $*" >&2; }
fail() { err "$@"; exit 1; }

# 分隔线
hr() { echo "────────────────────────────────────────────────────"; }

# ────────────────────────────────────────────────────────────
# 2. Python 内联执行辅助
# ────────────────────────────────────────────────────────────

# 找到 skills 包根目录 (包含 skills/_lib/ 的父目录)
_find_pkg_root() {
    local d
    for d in "$SKILLS_DIR" "$PROJECT_ROOT" "$SKILLS_DIR/.."; do
        if [ -d "$d/skills/_lib" ]; then
            (cd "$d" && pwd)
            return
        fi
    done
    echo "$PROJECT_ROOT"
}

_pkg_root="$(_find_pkg_root)"

# 执行 Python 内联脚本 (自动处理 PYTHONPATH, 抑制 schema 校验噪音)
_py() {
    PYTHONPATH="${_pkg_root}:${PYTHONPATH:-}" python3 -c "
import logging
logging.disable(logging.CRITICAL + 1)
$1
"
}

# ────────────────────────────────────────────────────────────
# 3. 各子命令实现
# ────────────────────────────────────────────────────────────

# ── 3.1 help ────────────────────────────────────────────────

rddf_help() {
    # 从本脚本顶部提取用法
    local usage
    usage=$(sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//')
    echo "${BOLD}rddf${RESET} — spec-workflow CLI"
    echo ""
    echo "${usage}"
    echo ""
    echo "${DIM}子命令速查:${RESET}"
    echo ""
    echo "  ${BOLD}status${RESET}                   全局概览 — 所有 change + worktree"
    echo "  ${BOLD}status --iteration${RESET}        当前 sprint 表"
    echo "  ${BOLD}status --roadmap${RESET}          路线图阶段进度"
    echo "  ${BOLD}status <name>${RESET}             单 change 详情"
    echo ""
    echo "  ${BOLD}feature${RESET}                   Feature 汇总表"
    echo "  ${BOLD}feature graph${RESET}              Mermaid 依赖图"
    echo "  ${BOLD}feature order${RESET}               Wave 分组执行顺序"
    echo ""
    echo "  ${BOLD}guide${RESET}                    无状态推荐器"
    echo "  ${BOLD}deps${RESET}                      依赖分析结果"
    echo "  ${BOLD}validate${RESET}                  质量门控检查"
    echo ""
    echo "  ${BOLD}session${RESET}                  rddf-session 管理 (ADR-0017)"
    echo "    list                       列出所有 session"
    echo "    show <id>                  显示 session 详情"
    echo "    resume <id>                接管 orphan session"
    echo "    abandon <id>               放弃 session"
    echo "    archive-history [--keep=N] 归档历史 session"
    echo "    stale                      列出需要关注的 orphan"
    echo ""
    echo "  ${BOLD}monitor${RESET}                  实时监控"
    echo "    --watch=<sec>              周期刷新 (Ctrl-C 退出)"
    echo ""
    echo "  ${BOLD}archive <name>${RESET}            归档 change"
    echo "  ${BOLD}cleanup${RESET}                  清理孤立 worktree/branch"
    echo "  ${BOLD}init${RESET}                      安装到当前项目"
    echo ""
}

# ── 3.2 guide ────────────────────────────────────────────────

rddf_guide() {
    local scan_script=""
    # v2.0.8: scan-state.sh moved from _lib/ to guide/scripts/
    for d in "$SKILLS_LIB/../guide/scripts" "$SKILLS_LIB"; do
        if [ -f "$d/scan-state.sh" ]; then
            scan_script="$d/scan-state.sh"
            break
        fi
    done
    [ -f "$scan_script" ] || fail "找不到 scan-state.sh (检查: $SKILLS_LIB/../guide/scripts/)"

    # shellcheck source=/dev/null
    source "$scan_script"
    scan_state "$PROJECT_ROOT"

    say ""
    say "${BOLD}🔍 项目状态扫描${RESET}"
    hr
    say "  ${DIM}roadmap.md:${RESET}         $([ -f "$PROJECT_ROOT/roadmap.md" ] && echo "${GREEN}存在${RESET}" || echo "${RED}缺失${RESET}")"
    say "  ${DIM}.arch-handoff.json:${RESET} $([ -f "$STATE_DIR/arch-handoff.json" ] && echo "${GREEN}存在${RESET}" || echo "${DIM}缺失${RESET}")"
    say "  ${DIM}.plan-handoff.json:${RESET} $([ -f "$STATE_DIR/plan-handoff.json" ] && echo "${GREEN}存在${RESET}" || echo "${DIM}缺失${RESET}")"
    say "  ${DIM}iteration.json:${RESET}     $([ -f "$STATE_DIR/iteration.json" ] && echo "${GREEN}存在${RESET}" || echo "${DIM}缺失${RESET}")"
    say "  ${DIM}worktrees:${RESET}          $(git worktree list 2>/dev/null | wc -l)"
    hr
    say "  ${BOLD}💡 建议:${RESET} ${CYAN}${RECOMMEND}${RESET}"
    say "     ${REASON}"
    say ""
}

# ── 3.3 status ───────────────────────────────────────────────

rddf_status() {
    case "${1:-}" in
        --iteration|-i|iteration)
            rddf_status_iteration
            ;;
        --roadmap|-r|roadmap)
            rddf_status_roadmap
            ;;
        --help|-h)
            echo "用法: rddf status [--iteration|--roadmap|<name>]"
            ;;
        "")
            rddf_status_overview
            ;;
        *)
            rddf_status_change "$1"
            ;;
    esac
}

rddf_status_overview() {
    _py "
import json, os, sys

project_root = '$PROJECT_ROOT'
state_dir = '$STATE_DIR'
iteration_path = os.path.join(state_dir, 'iteration.json')

print()
print('${BOLD}📋 项目状态概览${RESET}')
print('${DIM}━' * 50 + '${RESET}')

# 当前分支
import subprocess
try:
    branch = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, cwd=project_root).stdout.strip()
    print(f'  ${DIM}分支:${RESET}         {branch}')
except: pass

# worktree 列表
try:
    wt = subprocess.run(['git', 'worktree', 'list'], capture_output=True, text=True, cwd=project_root).stdout.strip()
    if wt:
        lines = wt.split(chr(10))
        print(f'  ${DIM}Worktrees:${RESET}      {len(lines)}')
        for l in lines:
            parts = l.split()
            if len(parts) >= 2:
                path = parts[0]
                br = parts[1] if len(parts) > 1 else '?'
                print(f'    · {os.path.basename(path):30s} {br}')
except: pass

# iteration.json 的 change 概览
if os.path.isfile(iteration_path):
    try:
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        changes = data.get('changes', [])
        active = [c for c in changes if c.get('status') not in ('archived', 'completed')]
        archived = [c for c in changes if c.get('status') in ('archived', 'completed')]
        phase = data.get('current_phase', '-')
        print(f'  ${DIM}当前阶段:${RESET}      {phase}')
        print(f'  ${DIM}活跃 changes:${RESET}  {len(active)}')
        print(f'  ${DIM}已归档:${RESET}        {len(archived)}')
        if active:
            print()
            print(f'  ${BOLD}活跃 change 列表:${RESET}')
            print(f'  {\"Name\":30s} {\"Status\":14s} {\"Phase\":12s} {\"Tasks\":8s} {\"Blocker\":16s}')
            print(f'  {\"-\"*30} {\"-\"*14} {\"-\"*12} {\"-\"*8} {\"-\"*16}')
            for c in active:
                name = c.get('name', '?')[:28]
                st = c.get('status', '?')
                ph = (c.get('phase') or '-')[:10]
                done = c.get('tasks_done', 0) or 0
                total = c.get('tasks_total', 0) or 0
                tasks = f'{done}/{total}' if total else '-'
                blocker = c.get('blocker') or '-'
                print(f'  {name:30s} {st:14s} {ph:12s} {tasks:8s} {blocker:16s}')
        print()
    except Exception as e:
        print(f'  ${DIM}(iteration.json 读取异常: {e})${RESET}')
else:
    # fallback: openspec list
    try:
        r = subprocess.run(['openspec', 'list', '--json'], capture_output=True, text=True, cwd=project_root)
        if r.returncode == 0:
            print(f'  ${DIM}(openspec list 可用)${RESET}')
    except: pass
    print(f'  ${DIM}(无 iteration.json — 运行 guide-plan 初始化)${RESET}')
"
}

rddf_status_iteration() {
    _py "
import json, os, sys

project_root = '$PROJECT_ROOT'
state_dir = '$STATE_DIR'
iteration_path = os.path.join(state_dir, 'iteration.json')

if not os.path.isfile(iteration_path):
    print('${YELLOW}iteration.json 不存在 — 请先运行 guide-plan${RESET}')
    sys.exit(0)

from skills._lib import iteration as it_mod

data = it_mod.load(project_root)
changes = data.get('changes', [])
phase = data.get('current_phase', '-')
active = [c for c in changes if c.get('status') not in ('archived', 'completed')]
archived = [c for c in changes if c.get('status') in ('archived', 'completed')]

print()
print(f'${BOLD}📊 当前 Sprint — 阶段: {phase}${RESET}')
print(f'${DIM}━' * 60 + '${RESET}')
print(f'  Active: {len(active)}  |  Archived: {len(archived)}  |  Total: {len(changes)}')
print()

if not active:
    print('  ${DIM}(无活跃 change)${RESET}')
    print()

# 活跃 changes 表格
if active:
    h = f'  {\"Name\":28s} {\"Status\":14s} {\"WG\":4s} {\"Blocker\":16s} {\"Conflict\":16s} {\"Tasks\":7s} {\"Plan\":5s}'
    print(h)
    print(f'  {\"-\"*28} {\"-\"*14} {\"-\"*4} {\"-\"*16} {\"-\"*16} {\"-\"*7} {\"-\"*5}')
    for c in active:
        name = (c.get('name') or '?')[:26]
        st = c.get('status', '?')
        wg = str(c.get('parallel_group') or '-')
        blocker = c.get('blocker') or '-'
        conflicts = ', '.join(c.get('conflicts', []) or [])[:14] or '-'
        done = c.get('tasks_done', 0) or 0
        total = c.get('tasks_total', 0) or 0
        tasks = f'{done}/{total}' if total else '-'
        plan = 'Y' if c.get('plan_path') else '-'
        print(f'  {name:28s} {st:14s} {wg:4s} {blocker:16s} {conflicts:16s} {tasks:7s} {plan:5s}')
    print()

# 已归档
if archived:
    print(f'  ${DIM}🗄️ 已归档 ({len(archived)}):${RESET}')
    for c in archived[:10]:
        print(f'    · {c.get(\"name\", \"?\")}')
    if len(archived) > 10:
        print(f'    ${DIM}... 还有 {len(archived) - 10} 个${RESET}')
    print()
"

    # 可选：feature 摘要
    _py "
import json, os, sys

project_root = '$PROJECT_ROOT'
state_dir = '$STATE_DIR'
iteration_path = os.path.join(state_dir, 'iteration.json')
if not os.path.isfile(iteration_path):
    sys.exit(0)

from skills._lib import iteration as it_mod
data = it_mod.load(project_root)
fv = data.get('feature_view')
if fv and fv.get('features'):
    feats = fv['features']
    print(f'${BOLD}📦 Feature 摘要${RESET}')
    print(f'{\"Name\":28s} {\"Status\":12s} {\"Changes\":9s} {\"Archived\":10s} {\"Wave\":5s}')
    print(f'{\"-\"*28} {\"-\"*12} {\"-\"*9} {\"-\"*10} {\"-\"*5}')
    for name in sorted(feats):
        info = feats[name]
        if name == '__ungrouped__': continue
        print(f'{name:28s} {info[\"status\"]:12s} {info[\"change_count\"]:5d}/{info[\"archived_count\"]:2d}  {info[\"archived_count\"]:3d}/{info[\"change_count\"]:2d}       {info[\"parallel_group\"]:3d}')
    print()
"
}

rddf_status_roadmap() {
    _py "
import json, os, sys
project_root = '$PROJECT_ROOT'
iteration_path = os.path.join('$STATE_DIR', 'iteration.json')

print()
print('${BOLD}🗺️ 路线图阶段进度${RESET}')
print('${DIM}━' * 50 + '${RESET}')

# 从 iteration.json 读阶段
if os.path.isfile(iteration_path):
    try:
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        phase = data.get('current_phase', '-')
        changes = data.get('changes', [])
        phases = {}
        for c in changes:
            p = c.get('phase', 'unknown')
            st = c.get('status', 'unknown')
            if p not in phases:
                phases[p] = {'total': 0, 'archived': 0, 'active': 0}
            phases[p]['total'] += 1
            if st in ('archived', 'completed'):
                phases[p]['archived'] += 1
            else:
                phases[p]['active'] += 1

        print(f'  ${DIM}当前阶段:${RESET} ${BOLD}{phase}${RESET}')
        print()
        print(f'  {\"Phase\":20s} {\"Total\":7s} {\"Active\":8s} {\"Archived\":10s} {\"Progress\":10s}')
        print(f'  {\"-\"*20} {\"-\"*7} {\"-\"*8} {\"-\"*10} {\"-\"*10}')
        for p in sorted(phases):
            info = phases[p]
            pct = f'{info[\"archived\"] * 100 // max(info[\"total\"], 1)}%'
            marker = ' ←' if p == phase else ''
            print(f'  {p:20s} {info[\"total\"]:4d}    {info[\"active\"]:4d}     {info[\"archived\"]:4d}        {pct:>4s}{marker}')
    except Exception as e:
        print(f'  ${DIM}(读取异常: {e})${RESET}')
else:
    print('  ${DIM}(iteration.json 不存在)${RESET}')

# roadmap.md 是否存在
rm_path = os.path.join(project_root, 'roadmap.md')
if os.path.isfile(rm_path):
    print()
    print(f'  ${DIM}roadmap.md:${RESET} 存在 ({os.path.getsize(rm_path)} bytes)')
else:
    print()
    print(f'  ${YELLOW}roadmap.md 不存在 — 请先运行 guide-arch${RESET}')
print()
"
}

rddf_status_change() {
    local name="$1"
    _py "
import json, os, sys

name = '$name'
project_root = '$PROJECT_ROOT'
iteration_path = os.path.join('$STATE_DIR', 'iteration.json')

print()
print('${BOLD}📄 Change 详情: ${CYAN}' + name + '${RESET}')
print('${DIM}━' * 50 + '${RESET}')

if os.path.isfile(iteration_path):
    try:
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        changes = data.get('changes', [])
        found = [c for c in changes if c.get('name') == name]
        if not found:
            print(f'  ${YELLOW}change \"{name}\" 不在 iteration.json 中${RESET}')
        else:
            c = found[0]
            print(f'  ${DIM}名称:${RESET}         {c.get(\"name\", \"-\")}')
            print(f'  ${DIM}状态:${RESET}         {c.get(\"status\", \"-\")}')
            print(f'  ${DIM}阶段:${RESET}         {c.get(\"phase\", \"-\")}')
            print(f'  ${DIM}分类:${RESET}         {c.get(\"category\", \"-\")}')
            print(f'  ${DIM}优先级:${RESET}       {c.get(\"priority\", \"-\")}')
            print(f'  ${DIM}阻塞于:${RESET}       {c.get(\"blocker\") or \"-\"}')
            print(f'  ${DIM}并行组:${RESET}       {c.get(\"parallel_group\", \"-\")}')
            print(f'  ${DIM}冲突:${RESET}         {\", \".join(c.get(\"conflicts\", []) or []) or \"-\"}')
            print(f'  ${DIM}任务进度:${RESET}     {c.get(\"tasks_done\", 0)}/{c.get(\"tasks_total\", 0)}')
            print(f'  ${DIM}计划文件:${RESET}     {c.get(\"plan_path\") or \"-\"}')
            print(f'  ${DIM}Worktree:${RESET}     {c.get(\"worktree_path\") or \"-\"}')
            print(f'  ${DIM}Parent Feature:${RESET} {c.get(\"parent_feature\") or \"-\"}')
            print(f'  ${DIM}添加时间:${RESET}     {c.get(\"added_at\", \"-\")}')
    except Exception as e:
        print(f'  ${YELLOW}读取失败: {e}${RESET}')
else:
    print(f'  ${YELLOW}iteration.json 不存在${RESET}')
print()
"
}

# ── 3.4 feature ──────────────────────────────────────────────

rddf_feature() {
    local sub="${1:-summary}"
    shift 2>/dev/null || true
    case "$sub" in
        summary|"")    rddf_feature_summary ;;
        graph)         rddf_feature_graph ;;
        order)         rddf_feature_order ;;
        status)        rddf_feature_status "$1" ;;
        --help|-h)     echo "用法: rddf feature [summary|graph|order|status <name>]" ;;
        *)             err "未知 feature 子命令: $sub"; echo "可用: summary graph order status <name>"; exit 1 ;;
    esac
}

rddf_feature_summary() {
    _py "
import json, os, sys

project_root = '$PROJECT_ROOT'
state_dir = '$STATE_DIR'
iteration_path = os.path.join(state_dir, 'iteration.json')

if not os.path.isfile(iteration_path):
    print('${YELLOW}iteration.json 不存在 — 请先运行 guide-plan${RESET}')
    sys.exit(0)

try:
    from skills._lib import feature_view as fv
    from skills._lib import iteration as it_mod

    count = fv.update_iteration_feature_view(project_root)
    data = it_mod.load(project_root)
    features = data.get('feature_view', {}).get('features', {})

    if not features:
        print('${DIM}(无 feature — set parent_feature 或使用 feature-<name>-<part> 命名)${RESET}')
        sys.exit(0)

    print()
    print(f'${BOLD}📦 Feature 汇总${RESET}')
    print()
    h = f'  {\"Feature\":30s} {\"Status\":14s} {\"Changes\":9s} {\"Done\":7s} {\"Wave\":5s} {\"Depends On\":18s} {\"Blocks\":18s}'
    print(h)
    print('  ' + '-' * 100)
    for name in sorted(features):
        info = features[name]
        if name == '__ungrouped__':
            continue
        icon = {'blocked': '🔴', 'in_progress': '🟡', 'ready': '🟢', 'done': '✅'}.get(info['status'], '⚪')
        pct = f'{info[\"archived_count\"]}/{info[\"change_count\"]}'
        wg = str(info.get('parallel_group', '-'))
        depends = ', '.join(info.get('depends_on', [])[:2]) or '-'
        blocks = ', '.join(info.get('blocks', [])[:2]) or '-'
        print(f'  {icon} {name:27s} {info[\"status\"]:14s} {info[\"change_count\"]:3d}/{info[\"archived_count\"]:1d}     {pct:5s}   {wg:3s}   {depends:18s} {blocks:18s}')

    # 未分组
    if '__ungrouped__' in features:
        ug = features['__ungrouped__']
        print(f'  ⚪ __ungrouped__: {ug[\"change_count\"]} changes (无 parent_feature, 无 feature- 前缀)')
    print()
    print('  ${DIM}🔴 blocked  🟡 in_progress  🟢 ready  ✅ done  ⚪ ungrouped${RESET}')
    print()
except fv.NoIterationError:
    print('${YELLOW}iteration.json 无数据 — 请先运行 guide-plan${RESET}')
except ImportError as e:
    print(f'${RED}模块导入失败: {e}${RESET}')
    print('${DIM}请确认在项目根目录运行 rddf${RESET}')
"
}

rddf_feature_graph() {
    _py "
import json, os, sys

project_root = '$PROJECT_ROOT'
state_dir = '$STATE_DIR'
iteration_path = os.path.join(state_dir, 'iteration.json')

if not os.path.isfile(iteration_path):
    print('${YELLOW}iteration.json 不存在${RESET}')
    sys.exit(0)

try:
    from skills._lib import feature_view as fv
    from skills._lib import iteration as it_mod

    fv.update_iteration_feature_view(project_root)
    data = it_mod.load(project_root)
    features = data.get('feature_view', {}).get('features', {})
    exec_order = data.get('feature_view', {}).get('execution_order', [])

    if not features:
        print('${DIM}(无 feature 数据)${RESET}')
        sys.exit(0)

    # 手工构建 Mermaid (简化版)
    print()
    print('${BOLD}📊 Feature 依赖拓扑${RESET}')
    print()
    print('\`\`\`mermaid')
    print('flowchart LR')
    for name in sorted(features):
        if name == '__ungrouped__':
            continue
        info = features[name]
        status_icon = {'blocked': '🔴', 'in_progress': '🟡', 'ready': '🟢', 'done': '✅'}.get(info['status'], '⚪')
        label = f'{name}<br/>{status_icon} {info[\"status\"]} · {info[\"archived_count\"]}/{info[\"change_count\"]} · wave {info[\"parallel_group\"]}'
        safe = label.replace('\"', '&quot;')
        print(f'  {name}[\"{safe}\"]')
    for name in sorted(features):
        if name == '__ungrouped__':
            continue
        info = features[name]
        for dep in info.get('depends_on', []):
            if dep in features:
                print(f'  {dep} --> {name}')
    print('\`\`\`')
    print()

    if exec_order:
        print(f'${BOLD}执行顺序 (Wave):${RESET}')
        for i, wave in enumerate(exec_order):
            print(f'  ${DIM}Wave {i}:${RESET} {\", \".join(wave)}')
        print()
except fv.NoIterationError:
    print('${YELLOW}iteration.json 无数据${RESET}')
except ImportError as e:
    print(f'${RED}模块导入失败: {e}${RESET}')
"
}

rddf_feature_order() {
    _py "
import json, os, sys

project_root = '$PROJECT_ROOT'
state_dir = '$STATE_DIR'
iteration_path = os.path.join(state_dir, 'iteration.json')

if not os.path.isfile(iteration_path):
    print('${YELLOW}iteration.json 不存在${RESET}')
    sys.exit(0)

try:
    from skills._lib import feature_view as fv
    from skills._lib import iteration as it_mod

    fv.update_iteration_feature_view(project_root)
    data = it_mod.load(project_root)
    exec_order = data.get('feature_view', {}).get('execution_order', [])

    print()
    print('${BOLD}🔢 推荐执行顺序 (Wave 分组)${RESET}')
    print('${DIM}━' * 50 + '${RESET}')

    if not exec_order:
        print('  ${DIM}(无 feature 数据)${RESET}')
    else:
        for i, wave in enumerate(exec_order):
            print(f'')
            print(f'  ${GREEN}Wave {i}${RESET} (无阻塞依赖, 可并行)')
            print(f'  ${DIM}{\"-\"*40}${RESET}')
            for feat in wave:
                print(f'    ▶ {feat}')
    print()
    print('  ${DIM}提示: 同一 Wave 内的 feature 可以并行执行${RESET}')
    print('         Wave 高的 feature 等低 Wave 完成后才开始')
    print()
except Exception as e:
    print(f'${YELLOW}读取失败: {e}${RESET}')
"
}

rddf_feature_status() {
    local feat_name="$1"
    [ -n "$feat_name" ] || fail "用法: rddf feature status <feature-name>"

    _py "
import json, os, sys

feat_name = '$feat_name'
project_root = '$PROJECT_ROOT'
iteration_path = os.path.join('$STATE_DIR', 'iteration.json')

if not os.path.isfile(iteration_path):
    print('${YELLOW}iteration.json 不存在${RESET}')
    sys.exit(0)

try:
    from skills._lib import feature_view as fv
    from skills._lib import iteration as it_mod

    fv.update_iteration_feature_view(project_root)
    data = it_mod.load(project_root)
    features = data.get('feature_view', {}).get('features', {})

    if feat_name not in features:
        print(f'${YELLOW}Feature \"{feat_name}\" 不存在${RESET}')
        known = [n for n in features if n != '__ungrouped__']
        if known:
            print(f'  已知 features: {\", \".join(known)}')
        sys.exit(0)

    info = features[feat_name]
    change_names = info.get('change_names', [])
    all_changes = {c['name']: c for c in data.get('changes', [])}

    print()
    print(f'${BOLD}📦 Feature: ${CYAN}{feat_name}${RESET}')
    print('${DIM}━' * 50 + '${RESET}')
    print(f'  ${DIM}状态:${RESET}       {info[\"status\"]}')
    print(f'  ${DIM}进度:${RESET}       {info[\"archived_count\"]}/{info[\"change_count\"]}')
    print(f'  ${DIM}并行组:${RESET}     {info.get(\"parallel_group\", \"-\")}')
    print(f'  ${DIM}阻塞于:${RESET}     {\", \".join(info.get(\"depends_on\", [])) or \"-\"}')
    print(f'  ${DIM}阻塞:${RESET}       {\", \".join(info.get(\"blocks\", [])) or \"-\"}')
    print(f'  ${DIM}冲突:${RESET}       {\", \".join(info.get(\"conflicts_with\", [])) or \"-\"}')
    print()

    if change_names:
        print(f'  ${BOLD}包含的 changes:${RESET}')
        print(f'  {\"Name\":30s} {\"Status\":14s} {\"Phase\":14s} {\"Blocker\":16s} {\"Tasks\":8s}')
        print(f'  {\"-\"*30} {\"-\"*14} {\"-\"*14} {\"-\"*16} {\"-\"*8}')
        for cn in change_names:
            c = all_changes.get(cn, {})
            name = cn[:28]
            st = c.get('status', '?')
            ph = (c.get('phase') or '-')[:12]
            blocker = c.get('blocker') or '-'
            done = c.get('tasks_done', 0) or 0
            total = c.get('tasks_total', 0) or 0
            tasks = f'{done}/{total}' if total else '-'
            print(f'  {name:30s} {st:14s} {ph:14s} {blocker:16s} {tasks:8s}')
        print()
except Exception as e:
    print(f'${YELLOW}读取失败: {e}${RESET}')
"
}

# ── 3.5 deps ─────────────────────────────────────────────────

rddf_deps() {
    _py "
import json, os, sys

project_root = '$PROJECT_ROOT'
deps_path = os.path.join('$STATE_DIR', 'deps-analysis.json')

print()
print('${BOLD}🔗 依赖分析结果${RESET}')
print('${DIM}━' * 60 + '${RESET}')

if not os.path.isfile(deps_path):
    print('  ${YELLOW}deps-analysis.json 不存在 — 请先运行 deps${RESET}')
    print('  ${DIM}deps 阶段在 guide-plan Phase 3 中自动执行${RESET}')
    print()
    sys.exit(0)

try:
    from skills._lib import deps_output as do
    data = do.load_analysis(project_root)
    if data is None:
        print('  ${YELLOW}deps-analysis.json 版本不兼容 (预期 v1)${RESET}')
        sys.exit(0)

    changes = data.get('changes', {})
    exec_order = data.get('execution_order', [])
    fallback = data.get('fallback', True)

    print(f'  ${DIM}模式:${RESET}       {\"AI subagent\" if not fallback else \"静态分析 (无 AI)\"}')
    print(f'  ${DIM}变更数:${RESET}     {len(changes)}')
    print()

    if changes:
        # Change 依赖表
        h = f'  {\"Name\":30s} {\"Status\":12s} {\"Group\":6s} {\"Blocker\":20s} {\"Confidence\":10s}'
        print(h)
        print('  ' + '-' * 78)
        for name, info in sorted(changes.items()):
            st = info.get('status', '?')
            grp = str(info.get('parallel_group', '-'))
            blk = info.get('blocker') or '-'
            conf = info.get('confidence', '-')
            print(f'  {name:30s} {st:12s} {grp:6s} {blk:20s} {conf:10s}')

        # 冲突警告
        conflicts_found = [(n, i.get('conflicts', [])) for n, i in changes.items() if i.get('conflicts')]
        if conflicts_found:
            print()
            print(f'  ${YELLOW}⚠ 文件冲突:${RESET}')
            for name, clist in conflicts_found:
                print(f'    · {name} 与 {\", \".join(clist)} 冲突')

        # 执行顺序
        if exec_order:
            print()
            print(f'  ${BOLD}推荐执行顺序:${RESET}')
            for i, n in enumerate(exec_order):
                marker = '▶' if i == 0 else '→'
                print(f'    {marker} {n}')
        print()
    else:
        print('  ${DIM}(无 change 数据)${RESET}')
        print()
except Exception as e:
    print(f'  ${YELLOW}读取异常: {e}${RESET}')
    print()
"
}

# ── 3.6 archive ──────────────────────────────────────────────

rddf_archive() {
    local name="${1:-}"
    [ -n "$name" ] || fail "用法: rddf archive <change-name>"

    local archive_script="$SKILLS_LIB/archive.sh"
    [ -f "$archive_script" ] || fail "找不到 archive.sh (预期: $archive_script)"

    say ""
    say "${BOLD}📦 归档 change: ${CYAN}${name}${RESET}"
    say "${DIM}━${RESET}${DIM}━${RESET}"

    # source archive.sh (内含 worktree.sh)
    # shellcheck source=/dev/null
    source "$archive_script"

    if declare -f archive_change >/dev/null 2>&1; then
        archive_change "$name"
        say ""
        ok "change ${name} 归档完成"
        say ""
    else
        warn "archive_change() 函数未定义"
        say "  ${DIM}尝试直接归档流程...${RESET}"

        # fallback: 基本归档流程
        local wt_path
        wt_path=$(wt_path_for_branch "$name" 2>/dev/null || echo "")
        local default_branch
        default_branch=$(find_default_branch 2>/dev/null || echo "master")

        if [ -n "$wt_path" ] && [ -d "$wt_path" ]; then
            say "  Worktree: $wt_path"
            say "  合并到 $default_branch..."

            # checkout default branch & merge
            git -C "$PROJECT_ROOT" checkout "$default_branch" 2>/dev/null || true
            if git -C "$PROJECT_ROOT" merge --ff-only "openspec/$name" 2>/dev/null; then
                ok "合并成功 (ff-only)"
            else
                warn "ff-only 失败，尝试 --no-ff"
                git -C "$PROJECT_ROOT" merge --no-ff "openspec/$name" -m "merge: $name" 2>/dev/null || warn "合并失败"
            fi

            # openspec archive
            if command -v openspec >/dev/null 2>&1; then
                openspec archive "$name" --yes 2>/dev/null && ok "openspec archive 完成" || warn "openspec archive 失败"
            fi

            # 清理 worktree
            git worktree remove "$wt_path" 2>/dev/null && ok "worktree 已移除" || warn "worktree 移除失败"
            git branch -d "openspec/$name" 2>/dev/null && ok "branch 已删除" || warn "branch 删除失败"
        else
            # 没有 worktree — 直接 archive
            if command -v openspec >/dev/null 2>&1; then
                openspec archive "$name" --yes && ok "openspec archive 完成" || err "openspec archive 失败"
            else
                err "openspec CLI 不可用"
                say "  手动归档: openspec archive $name --yes"
            fi
        fi
        say ""
    fi
}

# ── 3.7 cleanup ──────────────────────────────────────────────

rddf_cleanup() {
    say ""
    say "${BOLD}🧹 清理孤立 Worktree 和 Branch${RESET}"
    say "${DIM}━${RESET}${DIM}━${RESET}"

    local wt_script="$SKILLS_LIB/worktree.sh"
    [ -f "$wt_script" ] && source "$wt_script"

    # 获取所有 worktree 列表
    local wt_list
    wt_list=$(git worktree list 2>/dev/null || true)

    if [ -z "$wt_list" ]; then
        say "  ${DIM}(无 worktree)${RESET}"
    else
        # 只显示 openspec/ 分支的 worktree
        local openspec_wts
        openspec_wts=$(echo "$wt_list" | grep '\[openspec/') || true
        if [ -z "$openspec_wts" ]; then
            say "  ${DIM}(无 openspec worktree)${RESET}"
        else
            say "  发现 openspec worktree:"
            echo "$openspec_wts" | while IFS= read -r line; do
                local path br
                path=$(echo "$line" | awk '{print $1}')
                br=$(echo "$line" | awk '{print $3}' | tr -d '[]')
                local change_name="${br#openspec/}"
                say "    · ${DIM}$path${RESET} → ${br}"
            done
            say ""
            warn "使用 ${BOLD}git worktree remove${RESET} 和 ${BOLD}git branch -d${RESET} 逐个清理"
            say "  ${DIM}示例: git worktree remove .rddf/wt/<name> && git branch -d openspec/<name>${RESET}"
            say ""
        fi
    fi

    # 检查孤立 openspec/ 分支 (无对应 worktree)
    local orphan_branches
    orphan_branches=$(git branch --list 'openspec/*' 2>/dev/null | sed 's/^..//' || true)
    if [ -n "$orphan_branches" ]; then
        local active_wt_branches
        active_wt_branches=$(echo "$wt_list" | grep -o 'openspec/[^]]*' || true)
        say "  ${DIM}检查孤立分支...${RESET}"
        echo "$orphan_branches" | while IFS= read -r br; do
            if ! echo "$active_wt_branches" | grep -q "$br"; then
                say "    · ${YELLOW}孤立分支:${RESET} $br"
            fi
        done
    fi
    say ""
}

# ── 3.8 validate ─────────────────────────────────────────────

rddf_validate() {
    _py "
import json, os, sys, subprocess

project_root = '$PROJECT_ROOT'
state_dir = '$STATE_DIR'

print()
print('${BOLD}🔍 质量门控检查${RESET}')
print('${DIM}━' * 50 + '${RESET}')

# 检查 1: openspec CLI
try:
    r = subprocess.run(['openspec', '--version'], capture_output=True, text=True)
    cli_ok = r.returncode == 0
    ver = r.stdout.strip() if cli_ok else '?'
    icon = '${GREEN}✓${RESET}' if cli_ok else '${RED}✗${RESET}'
    print(f'  {icon} openspec CLI: {ver}')
except:
    print(f'  ${RED}✗${RESET} openspec CLI: 未安装')

# 检查 2: git 仓库
try:
    r = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True, text=True, cwd=project_root)
    git_ok = r.returncode == 0
    icon = '${GREEN}✓${RESET}' if git_ok else '${RED}✗${RESET}'
    print(f'  {icon} git 仓库')
except:
    print(f'  ${RED}✗${RESET} git 仓库')

# 检查 3: 状态文件
state_files = {
    'iteration.json': os.path.join(state_dir, 'iteration.json'),
    'deps-analysis.json': os.path.join(state_dir, 'deps-analysis.json'),
    'arch-handoff.json': os.path.join(state_dir, 'arch-handoff.json'),
    'plan-handoff.json': os.path.join(state_dir, 'plan-handoff.json'),
}
for label, path in state_files.items():
    exists = os.path.isfile(path)
    icon = '${GREEN}✓${RESET}' if exists else '${DIM}−${RESET}'
    print(f'  {icon} .rddf/state/{label}')

# 检查 4: openspec validate (如果 CLI 可用)
if cli_ok and git_ok:
    try:
        r = subprocess.run(['openspec', 'validate', '--all', '--json'],
                         capture_output=True, text=True, cwd=project_root, timeout=30)
        if r.returncode == 0:
            result = json.loads(r.stdout)
            totals = result.get('summary', {}).get('totals', {})
            passed = totals.get('passed', 0)
            failed = totals.get('failed', 0)
            print(f'  ${DIM}openspec validate: {passed} passed, {failed} failed${RESET}')
        else:
            print(f'  ${YELLOW}⚠ openspec validate 返回码: {r.returncode}${RESET}')
    except Exception as e:
        print(f'  ${YELLOW}⚠ openspec validate 异常: {e}${RESET}')

print()
"
}

# ── 3.9 session (rddf-session, ADR-0017) ─────────────────────

SESSIONS_FILE="$STATE_DIR/sessions.json"

rddf_session() {
    local sub="${1:-list}"
    shift 2>/dev/null || true
    case "$sub" in
        list|"")            rddf_session_list ;;
        show)               rddf_session_show "$1" ;;
        resume)             rddf_session_resume "$1" ;;
        abandon)            rddf_session_abandon "$1" ;;
        archive-history)    rddf_session_archive_history "$@" ;;
        stale)              rddf_session_stale ;;
        --help|-h)          echo "用法: rddf session [list|show <id>|resume <id>|abandon <id>|archive-history [--keep=N]|stale]" ;;
        *)                  err "未知 session 子命令: $sub"; echo "可用: list show resume abandon archive-history stale"; exit 1 ;;
    esac
}

rddf_session_list() {
    _py "
import os, sys, datetime

project_root = '$PROJECT_ROOT'
sessions_file = os.path.join(project_root, '.rddf', 'state', 'sessions.json')

print()
print('${BOLD}📋 rddf-sessions (ADR-0017)${RESET}')
print()

try:
    from skills._lib.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=sessions_file)
    coord.check_heartbeat_timeouts()  # mark stale as orphaned
    sessions = coord.list_sessions()
except Exception as e:
    print('  ${YELLOW}读取失败: ' + str(e) + '${RESET}')
    print('  ${DIM}(是否从未运行过 guide-arch/guide-plan/guide-ship?)${RESET}')
    print()
    sys.exit(0)

if not sessions:
    print('  ${DIM}(无 rddf-session — 第一次启动 guide 时会自动创建)${RESET}')
    print()
    sys.exit(0)

now = datetime.datetime.now(datetime.timezone.utc)

h = f'  {\"Session ID\":16s} {\"Kind\":12s} {\"State\":10s} {\"Owner\":22s} {\"Age\":10s} {\"Changes\":8s}'
print(h)
print('  ' + '-' * 80)
for s in sessions:
    owner = s.owner_opencode_session_id or '<none>'
    try:
        last_hb = datetime.datetime.fromisoformat(s.last_heartbeat)
        age_s = (now - last_hb).total_seconds()
        if age_s < 60: age = f'{int(age_s)}s'
        elif age_s < 3600: age = f'{int(age_s/60)}m'
        else: age = f'{int(age_s/3600)}h'
    except: age = '?'
    state_icon = {'active': '${GREEN}●${RESET}', 'orphaned': '${YELLOW}○${RESET}',
                  'completed': '${DIM}✓${RESET}', 'failed': '${RED}✗${RESET}',
                  'abandoned': '${DIM}⊘${RESET}'}.get(s.state, '?')
    kind_color = {'stage_arch': '${CYAN}', 'stage_plan': '${BLUE}', 'stage_ship': '${MAGENTA}'}.get(s.kind, '')
    print(f'  {s.session_id:<16s} {kind_color}{s.kind:<12s}${RESET} {state_icon} {s.state:<8s} {owner[:22]:22s} {age:10s} {len(s.attached_changes):<8d}')
print()

n_active = sum(1 for s in sessions if s.state == 'active')
n_orphaned = sum(1 for s in sessions if s.state == 'orphaned')
if n_orphaned > 0:
    resume_hint = 'rddf session resume <id>'
    print(f'  ${YELLOW}⚠ {n_orphaned} orphaned session(s) — 运行 {resume_hint} 接管${RESET}')
if n_active > 0:
    print(f'  ${GREEN}● {n_active} active${RESET}')
print()
"
}

rddf_session_show() {
    local sid="${1:-}"
    [ -n "$sid" ] || fail "用法: rddf session show <session-id>"

    _py "
import os, sys, json
from datetime import datetime, timezone

sid = '$sid'
sessions_file = os.path.join('$PROJECT_ROOT', '.rddf', 'state', 'sessions.json')

print()
print('${BOLD}📄 rddf-session: ${CYAN}' + sid + '${RESET}')
print()

try:
    from skills._lib.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=sessions_file)
    s = coord.find_session(sid)
except Exception as e:
    print('${RED}读取失败: ' + str(e) + '${RESET}')
    sys.exit(1)

if not s:
    print('  ${YELLOW}Session 不存在: ' + sid + '${RESET}')
    sys.exit(0)

d = s.to_dict()
now = datetime.now(timezone.utc)
try:
    last_hb = datetime.fromisoformat(d['last_heartbeat'])
    age = int((now - last_hb).total_seconds())
    age_s = f'{age}s ago' if age < 60 else (f'{age // 60}m ago' if age < 3600 else f'{age // 3600}h ago')
except: age_s = 'unknown'

print(f'  ${DIM}Kind:${RESET}        {d[\"kind\"]}')
print(f'  ${DIM}State:${RESET}       {d[\"state\"]}')
print(f'  ${DIM}Owner:${RESET}       {d.get(\"owner_opencode_session_id\") or \"<none>\"}')
print(f'  ${DIM}Parent:${RESET}      {d.get(\"parent_session_id\") or \"-\"}')
print(f'  ${DIM}Heartbeat:${RESET}   {age_s}')
print(f'  ${DIM}Started:${RESET}     {d.get(\"started_at\", \"\")}')
print(f'  ${DIM}Ended:${RESET}       {d.get(\"ended_at\") or \"-\"}')
if d.get('end_reason'): print(f'  ${DIM}Reason:${RESET}       {d[\"end_reason\"]}')
print(f'  ${DIM}Changes:${RESET}     {len(d.get(\"attached_changes\", []))}')
for cn in d.get('attached_changes', []):
    print(f'    · {cn}')
print(f'  ${DIM}Context:${RESET}     {d.get(\"context_pointer\") or \"-\"}')
print(f'  ${DIM}Goal:${RESET}')
goal = d.get('goal', {})
if goal:
    for k, v in goal.items():
        print(f'    {k}: {v}')
else:
    print('    ${DIM}(none)${RESET}')
print()
"
}

rddf_session_resume() {
    local sid="${1:-}"
    [ -n "$sid" ] || fail "用法: rddf session resume <session-id>"

    local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
    _py "
import os, sys
sid = '$sid'
new_owner = '$owner'
sessions_file = os.path.join('$PROJECT_ROOT', '.rddf', 'state', 'sessions.json')

try:
    from skills._lib.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=sessions_file)
    s = coord.find_session(sid)
    if not s:
        print('${YELLOW}Session 不存在: ' + sid + '${RESET}')
        sys.exit(1)
    if s.state == 'orphaned':
        coord.update_session_status(sid, 'active')
        print(f'${GREEN}✓${RESET} state: orphaned → active')
    elif s.state == 'active':
        print(f'${DIM}已为 active, 仅转移所有权${RESET}')
    else:
        print('${RED}✗ 无法 resume, 当前 state=' + s.state + '${RESET}')
        sys.exit(1)
    coord.transfer_ownership(sid, new_owner)
    print(f'${GREEN}✓${RESET} ownership transferred to {new_owner}')
    print(f'${GREEN}✓${RESET} heartbeat refreshed')
except Exception as e:
    print('${RED}失败: ' + str(e) + '${RESET}')
    sys.exit(1)
"
}

rddf_session_abandon() {
    local sid="${1:-}"
    [ -n "$sid" ] || fail "用法: rddf session abandon <session-id>"

    _py "
import os, sys
sid = '$sid'
sessions_file = os.path.join('$PROJECT_ROOT', '.rddf', 'state', 'sessions.json')

try:
    from skills._lib.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=sessions_file)
    coord.abandon(sid)
    print(f'${GREEN}✓${RESET} session {sid} 已标记为 abandoned')
except Exception as e:
    print('${RED}失败: ' + str(e) + '${RESET}')
    sys.exit(1)
"
}

rddf_session_archive_history() {
    local keep=20
    while [ $# -gt 0 ]; do
        case "$1" in
            --keep=*)  keep="${1#*=}" ;;
            --keep)    shift; keep="${1:-20}" ;;
            *) shift ;;
        esac
        shift || break
    done

    _py "
import os, sys
keep = int('$keep')
sessions_file = os.path.join('$PROJECT_ROOT', '.rddf', 'state', 'sessions.json')

try:
    from skills._lib.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=sessions_file)
    n = coord.archive_history(keep=keep)
    print(f'${GREEN}✓${RESET} 归档了 {n} 个 session (保留最近 {keep} 个 terminal + 所有 active/orphaned)')
except Exception as e:
    print('${RED}失败: ' + str(e) + '${RESET}')
    sys.exit(1)
"
}

rddf_session_stale() {
    # 直接复用 list 的逻辑，但只展示 non-terminal + 上次心跳 > 5 分钟的
    _py "
import os, sys, datetime

project_root = '$PROJECT_ROOT'
sessions_file = os.path.join(project_root, '.rddf', 'state', 'sessions.json')
THRESHOLD_SECONDS = 5 * 60  # 5 分钟未心跳即视为 stale

print()
print('${BOLD}⚠ Stale rddf-sessions (心跳 > 5 min)${RESET}')
print()

try:
    from skills._lib.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=sessions_file)
    coord.check_heartbeat_timeouts()
    sessions = coord.list_sessions()
except Exception as e:
    print('${RED}读取失败: ' + str(e) + '${RESET}')
    sys.exit(1)

now = datetime.datetime.now(datetime.timezone.utc)
stale = []
for s in sessions:
    try:
        last_hb = datetime.datetime.fromisoformat(s.last_heartbeat)
        age = (now - last_hb).total_seconds()
    except: continue
    if s.state in ('active', 'orphaned') and age > THRESHOLD_SECONDS:
        stale.append((s, age))

if not stale:
    print('  ${GREEN}✓${RESET} 无 stale session')
    print()
    sys.exit(0)

stale.sort(key=lambda x: -x[1])
for s, age in stale:
    owner = s.owner_opencode_session_id or '<none>'
    print(f'  ${YELLOW}○${RESET} {s.session_id}  state={s.state}  age={int(age/60)}m  owner={owner[:24]}')
print()
print(f'  ${DIM}操作:${RESET}')
print(f'    rddf session resume {stale[0][0].session_id}    # 接管')
print(f'    rddf session abandon {stale[0][0].session_id}   # 放弃')
print()
"
}

# ── 3.10 monitor (实时监控) ────────────────────────────────

rddf_monitor() {
    local watch_interval=0
    local rest_args=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --watch=*)  watch_interval="${1#*=}" ;;
            --watch)    shift; watch_interval="${1:-5}" ;;
            --no-color) rest_args+=("$1") ;;
            *)          rest_args+=("$1") ;;
        esac
        shift || break
    done

    # 验证间隔
    if [ -n "$watch_interval" ] && [ "$watch_interval" != "0" ]; then
        if ! [[ "$watch_interval" =~ ^[0-9]+$ ]]; then
            err "无效的 --watch 值: $watch_interval (应为秒数, e.g. --watch=5)"
            exit 1
        fi
        say ""
        say "${DIM}监控模式 — ${watch_interval}s 刷新 (Ctrl-C 退出)${RESET}"
        say ""
        # trap for cleanup
        trap 'say ""; say "${DIM}退出监控.${RESET}"; exit 0' INT TERM
        while true; do
            rddf_monitor_render
            sleep "$watch_interval"
        done
    else
        rddf_monitor_render
    fi
}

rddf_monitor_render() {
    _py "
import os, sys, datetime, subprocess

project_root = '$PROJECT_ROOT'
state_dir = os.path.join(project_root, '.rddf', 'state')

# 清屏 (watch 模式才有意义，但默认无副作用)
print('\x1b[2J\x1b[H', end='')

now = datetime.datetime.now(datetime.timezone.utc)
ts = now.strftime('%Y-%m-%d %H:%M:%S UTC')
print()
print(f'${BOLD}📡 spec-workflow 实时监控${RESET}  ${DIM}(更新于 {ts})${RESET}')
print()

# 1. Session 状态
print(f'${BOLD}── rddf-sessions (ADR-0017) ──${RESET}')
try:
    from skills._lib.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=os.path.join(state_dir, 'sessions.json'))
    coord.check_heartbeat_timeouts()
    sessions = coord.list_sessions()
except Exception as e:
    sessions = None

if sessions is None:
    print(f'  ${YELLOW}(sessions.json 不可读: {e})${RESET}')
elif not sessions:
    print(f'  ${DIM}(无活跃 session)${RESET}')
else:
    n_active = sum(1 for s in sessions if s.state == 'active')
    n_orphaned = sum(1 for s in sessions if s.state == 'orphaned')
    n_terminal = len(sessions) - n_active - n_orphaned
    print(f'  Active: ${GREEN}{n_active}${RESET}  Orphaned: ${YELLOW}{n_orphaned}${RESET}  Terminal: {n_terminal}  Total: {len(sessions)}')

    # 列出 active + orphaned
    active_or_orphan = [s for s in sessions if s.state in ('active', 'orphaned')]
    if active_or_orphan:
        for s in active_or_orphan[:5]:
            try:
                last_hb = datetime.datetime.fromisoformat(s.last_heartbeat)
                age_s = int((now - last_hb).total_seconds())
                age_str = f'{age_s // 60}m{age_s % 60}s' if age_s >= 60 else f'{age_s}s'
            except: age_str = '?'
            icon = '${GREEN}●${RESET}' if s.state == 'active' else '${YELLOW}○${RESET}'
            print(f'    {icon} {s.session_id}  {s.kind}  age={age_str}  changes={len(s.attached_changes)}')

# 2. Worktree 状态
print()
print(f'${BOLD}── 工作 Worktree ──${RESET}')
try:
    r = subprocess.run(['git', '-C', project_root, 'worktree', 'list'],
                      capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        lines = r.stdout.strip().split('\n')
        openspec_lines = [l for l in lines if 'openspec/' in l]
        if not openspec_lines:
            print(f'  ${DIM}(无 openspec worktree)${RESET}')
        else:
            for l in openspec_lines:
                parts = l.split()
                if len(parts) >= 3:
                    wt_path = parts[0]
                    wt_br = parts[3].strip('[]') if '[' in l else '?'
                    wt_name = os.path.basename(wt_path)
                    print(f'    ${CYAN}↻${RESET} {wt_name:<30s} {wt_br}')

                    # 检查 worktree 的 tasks.md 进度
                    tasks_path = os.path.join(project_root, wt_path.lstrip('./'), '.openspec-change', 'tasks.md')
                    possible = [
                        os.path.join(wt_path, '.openspec-change', 'tasks.md'),
                        os.path.join(wt_path, 'openspec', 'changes', wt_name.lstrip('openspec/'), 'tasks.md'),
                    ]
                    tasks_file = None
                    for p in possible:
                        if os.path.isfile(p):
                            tasks_file = p; break
                    if tasks_file:
                        with open(tasks_file) as f:
                            content = f.read()
                        done = content.count('[x]') + content.count('[X]')
                        todo = content.count('[ ]')
                        if todo or done:
                            pct = int(done * 100 / max(done + todo, 1))
                            print(f'        tasks: {done}/{done + todo} ({pct}%)')
except Exception as e:
    print(f'  ${YELLOW}(git worktree 异常: {e})${RESET}')

# 3. 当前分支 & 变更
print()
print(f'${BOLD}── 当前激活 Stage ──${RESET}')
try:
    r = subprocess.run(['git', '-C', project_root, 'branch', '--show-current'],
                      capture_output=True, text=True, timeout=5)
    br = r.stdout.strip() if r.returncode == 0 else '?'
    print(f'  ${DIM}Branch:${RESET} {br}')

    # 尝试读 iteration.json
    it_path = os.path.join(state_dir, 'iteration.json')
    if os.path.isfile(it_path):
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        phase = data.get('current_phase', '?')
        n_active = sum(1 for c in data.get('changes', []) if c.get('status') not in ('archived', 'completed'))
        n_archived = sum(1 for c in data.get('changes', []) if c.get('status') in ('archived', 'completed'))
        print(f'  ${DIM}Phase:${RESET}  {phase}')
        print(f'  ${DIM}Active:${RESET} {n_active}  Archived: {n_archived}')
except Exception as e:
    print(f'  ${YELLOW}(stage 检测异常: {e})${RESET}')

# 4. Event log 最近事件
print()
print(f'${BOLD}── 近期事件 (event-log.jsonl) ──${RESET}')
event_file = os.path.join(state_dir, 'event-log.jsonl')
if os.path.isfile(event_file):
    try:
        with open(event_file) as f:
            lines = f.readlines()
        recent = lines[-8:] if len(lines) >= 8 else lines
        if recent:
            for line in recent:
                try:
                    e = json.loads(line)
                    sev = e.get('severity', 'info')
                    icon = {'error': '${RED}✗${RESET}', 'warning': '${YELLOW}⚠${RESET}',
                            'info': '${DIM}ℹ${RESET}'}.get(sev, '${DIM}ℹ${RESET}')
                    ts_short = e.get('timestamp', '?')[:19]
                    msg = e.get('message', '')[:60]
                    print(f'    {icon} {ts_short}  {msg}')
                except: pass
        else:
            print(f'  ${DIM}(空 event log)${RESET}')
    except Exception as e:
        print(f'  ${YELLOW}事件日志读取失败: {e}${RESET}')
else:
    print(f'  ${DIM}(event-log.jsonl 不存在)${RESET}')

print()
print('${DIM}↑ use --watch=N for periodic refresh (e.g. --watch=5)${RESET}')
print()
"
}

# ── 3.11 init ────────────────────────────────────────────────

rddf_init() {
    local target="${1:-$PROJECT_ROOT}"

    say ""
    say "${BOLD}📦 安装 spec-workflow 到项目${RESET}"
    say "${DIM}━${RESET}${DIM}━${RESET}"
    say "  ${DIM}目标:${RESET} $target"

    # 找技能包源目录
    local src_skills=""
    if [ -d "$SKILLS_DIR/skills" ] && ls "$SKILLS_DIR/skills/"*.md >/dev/null 2>&1; then
        src_skills="$SKILLS_DIR/skills"
    elif [ -d "$PROJECT_ROOT/skills" ] && ls "$PROJECT_ROOT/skills/"*.md >/dev/null 2>&1; then
        src_skills="$PROJECT_ROOT/skills"
    else
        fail "找不到技能源目录 (在 $SKILLS_DIR/skills/ 或 $PROJECT_ROOT/skills/)"
    fi

    # 目标: .opencode/skills/spec-workflow/
    local dest="$target/.opencode/skills/spec-workflow"
    mkdir -p "$dest/skills"
    mkdir -p "$dest/_lib"

    # 复制 .md 技能文件
    cp -f "$src_skills/"*.md "$dest/skills/" 2>/dev/null
    local md_count
    md_count=$(ls -1 "$dest/skills/"*.md 2>/dev/null | wc -l)

    # 复制 _lib 工具库
    local src_lib="${SKILLS_LIB:-$src_skills/../_lib}"
    if [ -d "$src_lib" ]; then
        cp -rf "$src_lib"/* "$dest/_lib/" 2>/dev/null
    fi

    # 复制 rddf 自身
    cp -f "$0" "$dest/rddf" 2>/dev/null
    chmod +x "$dest/rddf" 2>/dev/null

    # 复制 package.json
    if [ -f "$SKILLS_DIR/package.json" ]; then
        cp -f "$SKILLS_DIR/package.json" "$dest/"
    elif [ -f "$PROJECT_ROOT/package.json" ]; then
        cp -f "$PROJECT_ROOT/package.json" "$dest/"
    fi

    say ""
    ok "安装完成!"
    say "  ${DIM}技能文件:${RESET} $md_count 个"
    say "  ${DIM}工具库:${RESET}  \$(_lib $(ls "$dest/_lib/" 2>/dev/null | wc -l) 文件)"
    say "  ${DIM}CLI:${RESET}    $dest/rddf"
    say ""
    say "  ${DIM}可用命令: ${CYAN}cd $target && ./rddf help${RESET}"
    say ""
}

# ────────────────────────────────────────────────────────────
# 4. 主分发
# ────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────
# 3.0 委托到新 Python CLI（已模块化的命令）
# ────────────────────────────────────────────────────────────
_rddf_cli() {
    PYTHONPATH="${_pkg_root}:${PYTHONPATH:-}" RDDF_PROJECT_ROOT="${PROJECT_ROOT}" python3 -m skills._lib.cli "$@"
}

main() {
    [ $# -ge 1 ] || { rddf_help; exit 0; }

    local cmd="$1"
    shift

    case "$cmd" in
        help|--help|-h)     rddf_help ;;
        # ── 新 Python CLI（已模块化 + 有测试覆盖）──
        dashboard)          _rddf_cli dashboard "$@" ;;
        status)             _rddf_cli status "$@" ;;
        feature)            _rddf_cli feature "$@" ;;
        sessions)           _rddf_cli sessions "$@" ;;
        session)            _rddf_cli sessions "$@" ;;   # 别名 session → sessions
        deps)               _rddf_cli deps "$@" ;;        # v3: migrated
        cleanup)            _rddf_cli cleanup "$@" ;;     # v3: migrated
        validate)           _rddf_cli validate "$@" ;;    # v3: migrated
        monitor)            _rddf_cli monitor "$@" ;;     # v3: migrated
        # ── 旧 bash 实现（待后续迁移到 Python CLI）──
        guide)              rddf_guide ;;
        archive)            rddf_archive "$@" ;;
        init)               rddf_init "$@" ;;
        version|--version|-v)
            local ver="2.0.0"
            [ -f "$SKILLS_DIR/package.json" ] && ver=$(grep -m1 '"version"' "$SKILLS_DIR/package.json" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' 2>/dev/null || echo "$ver")
            echo "rddf v$ver — spec-workflow CLI"
            ;;
        *)
            err "未知命令: $cmd"
            echo "可用命令: status feature guide deps session monitor archive cleanup validate init help"
            exit 1
            ;;
    esac
}

main "$@"
