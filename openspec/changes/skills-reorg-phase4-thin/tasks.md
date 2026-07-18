# Tasks: skills-reorg-phase4-thin

> **前置条件**: `skills-reorg-phase3-core` 完成,目录结构稳定

## Task 0: 修复 Phase 3 遗留断裂路径（P0）

### 0.1: plan_queue_overview.sh state.sh 路径
```bash
# skills/guide-plan/scripts/plan_queue_overview.sh:15
# OLD: source "$(dirname "${BASH_SOURCE[0]:-$0}")/state.sh"
# NEW: source "$(dirname "${BASH_SOURCE[0]:-$0}")/../../_lib/state.sh"
```

### 0.2: propose SKILL.md validate_baseline.py 路径
```bash
# skills/propose/SKILL.md:507
# OLD: ../_lib/validate_baseline.py → NEW: scripts/validate_baseline.py
```

### 0.3: guide-ship SKILL.md $REPO_ROOT 替换
```bash
# L122: $REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh
# L426: $REPO_ROOT/skills/guide-ship/scripts/ship_review.sh
# L482: $REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh
# → 统一为 $(dirname "${BASH_SOURCE[0]:-$0}")/scripts/ship_*.sh
```

## Task 1: 提取共享 case handler

### 1.1: 创建 scripts/_case_handler.sh

从 guide-ship 的 case handler 提取 `handle_common_cases()` 函数（q/quit/exit/r/refresh/?/help/* 的统一处理）。

```bash
# skills/guide-ship/scripts/_case_handler.sh
handle_common_cases() {
  local choice="$1"
  case "$choice" in
    q|quit|exit) echo "👋 已退出" && return 1 ;;
    r|refresh) return 2 ;;
    '?') return 3 ;;
    help) return 4 ;;
    *) echo "❓ 未知选择: $choice" && return 0 ;;
  esac
}
```

### 1.2: 更新各 SKILL.md 中的 case handler

用 `source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/_case_handler.sh"` + `handle_common_cases "$choice"` 替换 guide-arch/guide-plan/guide-ship/status/roadmap/deps 中的重复 case 块。

**验证**: `bats tests/smoke.bats`

## Task 2: 提取 guide-ship.md 剩余代码

### 2.1: Phase 5 loop check → scripts/ship_done.sh

L650+ `REMAINING`/`REMAINING_WT` 计算 + 双菜单（worktree/轻量模式完成检查）。

### 2.2: Phase 4 清理 → scripts/ship_cleanup.sh

L610+ worktree + branch 批量清理 + `git stash` 提示。

**验证**: `bats tests/integration/test_guide_ship_skill.bats tests/integration/test_ship_*.bats`

## Task 3: 提取其他 SKILL.md 代码

| SKILL.md | 候选块 | 目标 helper | 节省 |
|----------|--------|------------|------|
| guide-arch | roadmap init/status/gate-report 交互 | `scripts/arch_roadmap_menu.sh` | ~50 |
| guide-plan | propose/create 菜单交互 | `scripts/plan_propose_menu.sh` | ~40 |
| status | 归档交互 | `scripts/status_archive_menu.sh` | ~30 |

每提取一个块 → 运行对应 bats 测试验证。

## Task 4: 提取 ACTIVE_CHANGES 表渲染

guide-arch/guide-plan/guide-ship 都有 ACTIVE_CHANGES 表渲染逻辑（openspec status --json + jq 格式化 + 列对齐）。提取为 `scripts/render_active_changes.sh::render_active_changes_table()`。

**验证**: `bats tests/smoke.bats`

## Task 5: 修正 state.sh STUB 标签

### 5.1: 更新 AGENTS.md

将 `state.sh` 的标签从 "STUB (无 production 调用方)" 改为 "共享工具（6 个函数，4+ 消费者）"。

### 5.2: 扫描残留引用
```bash
grep -rn "_lib/" skills/*/SKILL.md | grep -v "scripts/" | grep -v "../_lib/"
```
确认无残留的旧路径。

## Task 6: 更新文档

### 6.1: CHANGELOG.md

新增 v2.0.8 section:
```markdown
## v2.0.8 — skills/ directory reorganization

### Phase 1: Per-skill subdirectory skeleton (12 skills, 53 source paths)
### Phase 2: Single-skill helper migration (46 files to per-skill scripts/)
### Phase 3: _lib/ reorganization into core/ + loop/ subdirectories
### Phase 4: SKILL.md thinning (shared case handler, menu extraction, broken path fixes)
```

### 6.2: AGENTS.md

更新目录结构描述以反映 `skills/<name>/SKILL.md` + `scripts/` layout。

### 6.3: tests/README.md

更新技能覆盖表引用路径。

## Task 7: 全量验证

```bash
# 7.1: 快速冒烟
bats tests/smoke.bats

# 7.2: 全量 bats
bats tests/

# 7.3: 全量 Python
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short

# 7.4: 线数检查
find skills -name "SKILL.md" | while read f; do echo "$(wc -l < "$f") $f"; done | sort -rn
# 预期: 前 7 个文件 ≤ 500 行（propose/deps 可放宽至 500），其余 ≤ 300
```

**预期**: 0 failures。

## Task 8: commit

```bash
git add skills/*/scripts/ skills/*/SKILL.md AGENTS.md CHANGELOG.md tests/README.md
git commit -m "refactor(skills): Phase 4 — thin SKILL.md + fix broken paths

- Fix 3 Phase-3 broken paths (plan_queue_overview state.sh, propose validate_baseline, guide-ship \$REPO_ROOT)
- Extract shared case handler (_case_handler.sh), eliminating 6-8 duplicate case blocks
- Extract menu scripts: arch_roadmap_menu, plan_propose_menu, status_archive_menu
- Extract guide-ship: ship_done, ship_cleanup helpers
- Extract ACTIVE_CHANGES table renderer (shared across arch/plan/ship)
- Correct state.sh label from STUB to shared utility in AGENTS.md
- SKILL.md target ≤450 lines (down from ~601 average)
- Update CHANGELOG (v2.0.8), AGENTS.md, tests/README.md"