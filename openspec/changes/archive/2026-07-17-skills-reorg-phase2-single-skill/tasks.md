# Tasks: skills-reorg-phase2-single-skill

> **前置条件**: `skills-reorg-phase1-skeleton` ✓ 已完成（archive 2026-07-17-...）
> **设计依据**: `docs/adr/ADR-0021-phase2-per-skill-helper-migration.md` 4 个联合决策
> **工具**: `tools/phase2_path_migrator.py`（自带 dry-run + scope control）
> **工具修复 (Metis re-review C1/C2)**: 工具已修复 `from skills._lib import X` 模式识别 + `skills/*/scripts/` 扫描。迁移后文件内部的 Python heredoc import（如 `rddf_session_hooks.sh`、`feature_*.sh`、`deps_render_report.sh`、`_env.py` 等）现在由工具自动处理，无需手动任务。

## Task 0: 准备与全面审计（执行前必须）

### 0.1: 给所有被迁移 skill 的 `scripts/` 加 `__init__.py`

```bash
for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
  [ -d "skills/$skill/scripts" ] && touch "skills/$skill/scripts/__init__.py"
done
```

**验证**: `ls skills/*/scripts/__init__.py | wc -l` → 11

### 0.2: 用工具做全面审计（dry-run）

```bash
python3 tools/phase2_path_migrator.py audit | tee /tmp/phase2_audit.json
```

**期望**: ~230 refs total，按类型 `source_sh / import_py / prose / grep_str`。

### 0.3: 检查审计中是否有 ERROR

```bash
python3 tools/phase2_path_migrator.py audit 2>&1 | grep -E "^ERRORS:|^  " | head -10
```

**期望**: 1 个 ERROR（`guide.md:41` readlink 模式，标记手动处理）。

### 0.4: 清理 __pycache__（避免 stale .pyc）

```bash
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
```

### 0.5: 创建分支

```bash
git checkout -b openspec/skills-reorg-phase2-single-skill
```

## Task 1: 物理移动 46 个文件（move 操作，无 sed）

### 1.1: 移动 guide (1 文件)

```bash
mv skills/_lib/scan-state.sh skills/guide/scripts/
```

**验证**: `ls skills/guide/scripts/scan-state.sh` 存在

### 1.2: 移动 guide-arch (7 文件)

```bash
mv skills/_lib/arch_env_check.sh \
   skills/_lib/arch_gap_analysis.sh \
   skills/_lib/arch_done_gate.sh \
   skills/_lib/arch_quality_report.sh \
   skills/_lib/write_arch_handoff.sh \
   skills/_lib/write_arch_handoff.py \
   skills/_lib/write_arch_handoff_env.py \
   skills/guide-arch/scripts/
```

### 1.3: 移动 guide-plan (9 文件)

```bash
mv skills/_lib/plan_intake.sh \
   skills/_lib/plan_queue_overview.sh \
   skills/_lib/plan_feature_progress.sh \
   skills/_lib/plan_deps_candidates.{sh,py,env.py} \
   skills/_lib/plan_done_gate.{sh,py,env.py} \
   skills/guide-plan/scripts/
```

### 1.4: 移动 guide-ship (6 文件)

```bash
mv skills/_lib/ship_case_handler.sh \
   skills/_lib/ship_plan.sh \
   skills/_lib/ship_monitor.sh \
   skills/_lib/ship_review.sh \
   skills/_lib/ship_archive.sh \
   skills/_lib/post_archive_fill.sh \
   skills/guide-ship/scripts/
```

### 1.5: 移动 propose (3 文件)

```bash
mv skills/_lib/propose_change.sh \
   skills/_lib/propose_change.py \
   skills/_lib/validate_baseline.py \
   skills/propose/scripts/
```

### 1.6: 移动 execute (8 文件)

```bash
mv skills/_lib/select_worktree.sh \
   skills/_lib/update_roadmap_progress.{sh,py,env.py} \
   skills/_lib/execute_step7.{sh,py,env.py} \
   skills/_lib/tasks_writeback.sh \
   skills/execute/scripts/
```

### 1.7: 移动 feature (6 文件)

```bash
mv skills/_lib/feature_summary.sh \
   skills/_lib/feature_graph.sh \
   skills/_lib/feature_status.sh \
   skills/_lib/feature_order.sh \
   skills/_lib/feature_cli.py \
   skills/_lib/feature_view.py \
   skills/feature/scripts/
```

### 1.8: 移动 status (1 文件)

```bash
mv skills/_lib/status_render_mode_a.sh skills/status/scripts/
```

### 1.9: 移动 deps (3 文件)

```bash
mv skills/_lib/deps_render_report.sh \
   skills/_lib/deps_iteration_sync.sh \
   skills/_lib/deps_output.py \
   skills/deps/scripts/
```

### 1.10: 移动 rddf-session (2 文件 — 含 hooks.sh 解决 N3 自相矛盾)

```bash
mv skills/_lib/rddf_session.py \
   skills/_lib/rddf_session_hooks.sh \
   skills/rddf-session/scripts/
```

**验证**: `find skills/_lib -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) | wc -l` → ~44（共享文件）

## Task 2: 跑工具更新所有路径（source + import + prose + check_file + grep_str）

### 2.1: Dry-run 全部 apply

```bash
python3 tools/phase2_path_migrator.py apply --dry-run 2>&1 | tail -10
```

**期望**: "Would change: ~327 lines across ~154 files"（实际数字可能略有浮动；关键看 errors 只有 1 个 readlink warning）

### 2.2: 真实 apply（无 skill filter，全 repo）

```bash
python3 tools/phase2_path_migrator.py apply
```

### 2.3: 验证无残留旧路径

```bash
# 任何 _lib/<moved-filename> 引用应该都不在了（除了 ADR/历史 plan 文档）
echo "=== Prose in scope (SKILL.md + INSTALL.md) should be 0 ==="
python3 tools/phase2_path_migrator.py audit | grep -E '"prose"' || echo "OK no prose remains"

# SKILL.md source 行都应该用 scripts/ 或 ../_lib/ 共享
echo "=== SKILL.md paths check ==="
for f in skills/*/SKILL.md; do
  bad=$(grep -E "_lib/(scan-state|ship_plan|arch_env_check|plan_intake|select_worktree|feature_summary|status_render_mode|deps_render_report|rddf_session|propose_change|write_arch_handoff)\." "$f" | grep -v "scripts/\|RDIR" | head -3)
  [ -n "$bad" ] && echo "FAIL: $f -> $bad"
done
echo "OK if no FAIL output"
```

### 2.4: Python imports dry-run check

```bash
python3 -c "
import sys, importlib.util
sys.path.insert(0, '/workspace/project/rdd-workflow')

# Map: module name -> (expected skill for new path, was it moved?)
MOVED = [
    ('rddf_session', 'rddf_session'),         # rddf_session.py (special: skill name = module name)
    ('deps_output', 'deps'),
    ('feature_view', 'feature'),
    ('feature_cli', 'feature'),
    ('propose_change', 'propose'),
    ('write_arch_handoff', 'guide_arch'),     # Python identifier: dash -> underscore
    ('plan_deps_candidates', 'guide_plan'),
    ('plan_done_gate', 'guide_plan'),
    ('update_roadmap_progress', 'execute'),
    ('execute_step7', 'execute'),
    ('validate_baseline', 'propose'),
]
SHARED = ['iteration', 'state_vector', 'event_log', 'gate', 'lock', 'memory',
          'tribunal', 'sanitizer', 'session_manager', 'roadmap_state']

print('=== Moved modules (should be: old=False, new=True) ===')
for mod, skill_py in MOVED:
    old = importlib.util.find_spec(f'skills._lib.{mod}')
    new = importlib.util.find_spec(f'skills.{skill_py}.scripts.{mod}')
    status = 'OK' if (old is None and new is not None) else 'FAIL'
    print(f'  {status} {mod:30} old={old is not None} new={new is not None}')

print('=== Shared modules (should be: old=True) ===')
for mod in SHARED:
    spec = importlib.util.find_spec(f'skills._lib.{mod}')
    status = 'OK' if spec is not None else 'FAIL'
    print(f'  {status} {mod:30} old={spec is not None}')
"

## Task 3: 手工处理 5 个工具无法覆盖的语义改动

### 3.1: `skills/guide/SKILL.md:41` readlink 模式（Phase 1 N1 lesson）

```bash
sed -i 's|\$(dirname "\$(readlink -f "\${BASH_SOURCE\[0\]:-\$0}")")/../_lib/scan-state\.sh|\$(dirname "\$(readlink -f "\${BASH_SOURCE\[0\]:-\$0}")")/scripts/scan-state.sh|' skills/guide/SKILL.md
```

**验证**: `grep 'readlink.*scan-state' skills/guide/SKILL.md` 应为 `scripts/scan-state.sh`

### 3.2: `skills/feature/SKILL.md` fallback 逻辑 5 行（Phase 1 N2 lesson）

```bash
# Line 42: 检查行
sed -i 's|\$_SCRIPT_DIR/../_lib/feature_summary\.sh|$_SCRIPT_DIR/scripts/feature_summary.sh|' skills/feature/SKILL.md
# Line 44: REPO_ROOT 检查行（注意：不是 feature/scripts/，而是 guide/scripts/ —— 这是 fallback 探测）
sed -i 's|\$REPO_ROOT/skills/_lib/feature_summary\.sh|$REPO_ROOT/skills/guide/scripts/feature_summary.sh|' skills/feature/SKILL.md
# Lines 50-53: 4 个 source 行（工具已自动处理，但 verify）
grep -E '\$_SCRIPT_DIR/scripts/feature_' skills/feature/SKILL.md
```

**验证**: `grep -E '\.\./_lib/feature_' skills/feature/SKILL.md` 应为空

### 3.3: `rddf_session_hooks.sh` 移到 rddf-session/scripts/ 后，3 个 SKILL.md 各加 source

```bash
for skill in guide-arch guide-plan guide-ship; do
  if ! grep -q "../rddf-session/scripts/rddf_session_hooks.sh" skills/$skill/SKILL.md; then
    # 在第一个 source 行前插入跨 skill 引用
    sed -i '0,/^source /s|^source |source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"\n\nsource |' skills/$skill/SKILL.md
  fi
done
```

**验证**: `grep '../rddf-session/scripts/rddf_session_hooks.sh' skills/{guide-arch,guide-plan,guide-ship}/SKILL.md | wc -l` → 3

### 3.4: `feature_*.sh` 的 PYTHONPATH 重算（4 文件，ADR-0021 N2 fix）

```bash
for f in skills/feature/scripts/feature_*.sh; do
  sed -i 's|PYTHONPATH="\$_SCRIPT_DIR/\.\.|PYTHONPATH="$_SCRIPT_DIR/../..|' "$f"
done
```

**验证**: `grep '_SCRIPT_DIR/\.\./\.\.' skills/feature/scripts/feature_*.sh | wc -l` → 4

### 3.5: `plan_done_gate.sh` 内部引用 `validate_baseline.py`（cross-skill chained dep）

`plan_done_gate.sh` 移到 `guide-plan/scripts/` 后，内部 4 处 `$PROJECT_ROOT/skills/_lib/validate_baseline.py` 失效（`validate_baseline.py` 移到 `propose/scripts/`）。

```bash
# 显式 sed（I1/I2 fix per Metis re-review）
sed -i 's|\$PROJECT_ROOT/skills/_lib/validate_baseline\.py|$PROJECT_ROOT/skills/propose/scripts/validate_baseline.py|g' \
    skills/guide-plan/scripts/plan_done_gate.sh
```

**验证**:
- `grep -c 'validate_baseline.py' skills/guide-plan/scripts/plan_done_gate.sh` -> 4（1 if + 3 python calls）
- `grep 'validate_baseline.py' skills/guide-plan/scripts/plan_done_gate.sh | grep -c '_lib/validate_baseline'` -> 0（无残留旧路径）
- `bash -n skills/guide-plan/scripts/plan_done_gate.sh` -> 语法 OK

## Task 4: 修复 INSTALL.md 和 install 测试（推迟到所有 move 完成后）

### 4.1: 更新 INSTALL.md 复制循环

**位置**: `skills/INSTALL.md:99-108`（Step 3 cp 循环）

**改动**: 在已有的 `cp -f SKILL.md` 之后加 2 行复制 scripts/ 和 references/:

```bash
# 在现有 for 循环里追加（在 if [ -f "$skill_dir/SKILL.md" ]; cp ... done 之后）
# 修改 INSTALL.md 复制循环，在 cp SKILL.md 后追加：
        if [ -d "$skill_dir/scripts" ]; then
            cp -rf "$skill_dir/scripts/." "$SKILLS_DIR/skills/$skill_name/scripts/"
        fi
        if [ -d "$skill_dir/references" ]; then
            cp -rf "$skill_dir/references/." "$SKILLS_DIR/skills/$skill_name/references/"
        fi
```

### 4.2: 同样修改 `install-rdd-workflow.sh` 模板（INSTALL.md L195 附近）

### 4.3: 修复 `test_install_lib_distribution.bats:45` 断言

旧断言检查 `skills/_lib/*.sh` ≥ 4 个 -> 改为按新布局**严格**验证（per Metis I3 fix）：

```bash
@test "install_lib: per-skill scripts/ has files to distribute" {
  # Phase 2 后：46 个 helper 移到 per-skill scripts/，至少 45 个文件应被分发
  # 覆盖 .sh 和 .py 两种类型（feature/propose/rddf-session 部分 skill 只有 .py）
  local total_moved=0
  for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
    local n
    n=$(find "skills/$skill/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) 2>/dev/null | wc -l)
    total_moved=$((total_moved + n))
  done
  [ "$total_moved" -ge 45 ] || {
    echo "FAIL: expected at least 45 files across per-skill scripts/, got $total_moved"
    return 1
  }
}

@test "install_lib: _lib/ retains shared files only (35-50)" {
  local count
  count=$(find skills/_lib -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) | wc -l)
  [ "$count" -ge 35 ] && [ "$count" -le 50 ] || {
    echo "FAIL: expected 35-50 shared files in _lib/, got $count"
    return 1
  }
}
```

## Task 5: 新增 5 个 Phase 2 regression 测试

### 5.1: `tests/integration/test_phase2_layout.bats` — 锁定新布局

```bash
@test "phase2: 47 files moved out of _lib/ to scripts/" {
  local moved_count=0
  for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
    local n
    n=$(find "skills/$skill/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) 2>/dev/null | wc -l)
    moved_count=$((moved_count + n))
  done
  [ "$moved_count" -ge 45 ]
}

@test "phase2: per-skill scripts/__init__.py present" {
  for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
    [ -f "skills/$skill/scripts/__init__.py" ] || return 1
  done
}

@test "phase2: SKILL.md source lines use scripts/ for moved files" {
  grep -q 'scripts/ship_plan' skills/guide-ship/SKILL.md
  grep -q 'scripts/arch_env_check' skills/guide-arch/SKILL.md
  grep -q 'scripts/feature_summary' skills/feature/SKILL.md
  grep -q 'scripts/scan-state' skills/guide/SKILL.md
}

@test "phase2: readlink pattern in guide.md updated" {
  grep -q 'scripts/scan-state' skills/guide/SKILL.md
  ! grep -qE 'readlink.*_lib/scan-state' skills/guide/SKILL.md
}

@test "phase2: feature.md fallback updated" {
  grep -q 'scripts/feature_summary' skills/feature/SKILL.md
  ! grep -qE '\.\./_lib/feature_' skills/feature/SKILL.md
}

@test "phase2: rddf-session has both rddf_session.py and hooks.sh" {
  [ -f "skills/rddf-session/scripts/rddf_session.py" ]
  [ -f "skills/rddf-session/scripts/rddf_session_hooks.sh" ]
}
```

### 5.2: `tests/integration/test_phase2_install_full.bats` — 真实跑 INSTALL.md 复制

### 5.3: `tests/integration/test_phase2_python_imports.py` — 参数化检查

### 5.4: `tests/integration/test_phase2_no_broken_refs.bats` — 53 source + 74 import 全可解析

### 5.5: `tests/integration/test_phase2_readlink_fallback.bats` — 手工路径验证

（**模板由 tasks.md 模板生成器提供**：参考 `skills/rdd-workflow-writing-plans.md`）

## Task 6: 全量验证

```bash
# 单元测试
python3 -m pytest tests/unit/ -q --tb=short  # 期望 654-656 pass（2 个 perf flakes 已知）

# 集成测试
bats tests/smoke.bats
bats tests/integration/test_skill_metadata_consistency.bats
bats tests/integration/test_install_lib_distribution.bats  # 修复后

# 全量
bats tests/  # 包括所有 5 个 Phase 2 regression tests

# 路径解析验证（Author's final gate）
python3 -c "
import os, re, sys
sys.path.insert(0, '/workspace/project/rdd-workflow')
errors = 0
for f in os.listdir('skills'):
    if f in ('_lib', '__pycache__', 'INSTALL.md'): continue
    sk = os.path.join('skills', f, 'SKILL.md')
    if not os.path.isfile(sk): continue
    text = open(sk).read()
    for m in re.finditer(r'source\s+[\"\\']([^\"\\']+)[\"\\']', text):
        path = m.group(1)
        if '\$(readlink' in path: continue  # manual
        # Expand $(dirname ...) etc
        path = path.replace('\$(dirname \"\${BASH_SOURCE[0]:-\$0}\")', f'/workspace/project/rdd-workflow/skills/{f}')
        path = path.replace('\$REPO_ROOT', '/workspace/project/rdd-workflow')
        if not os.path.isabs(path):
            path = os.path.join('/workspace/project/rdd-workflow/skills', f, path.lstrip('./'))
        if not os.path.isfile(path):
            print(f'❌ BROKEN: {sk} → {m.group(0)} → {path}')
            errors += 1
sys.exit(errors)
"
```

## Task 7: 归档与提交

### 7.1: 归档（per `guide-ship` archive 流程）

```bash
openspec validate skills-reorg-phase2-single-skill --skip-specs 2>&1 | head -10
openspec archive skills-reorg-phase2-single-skill --skip-specs --yes --no-validate
```

### 7.2: 提交

```bash
git add skills/ tests/ docs/adr/ADR-0021-*.md tools/phase2_path_migrator.py
git commit -m "refactor(skills): Phase 2 — move 46 single-skill helpers to per-skill scripts/

Per ADR-0021:
- 10 skills/scripts/ dirs populated + 10 __init__.py added (rddf-session has 2 files)
- Python imports: from skills._lib.X → from skills.<skill>.scripts.X (~248 sites detected, ~202 transformed)
- Bash source lines: ../_lib/X.sh → scripts/X.sh (~219 sites detected, ~150 transformed)
- check_file + grep_str patterns: 87 + 115 sites transformed
- \$REPO_ROOT paths: skills/_lib/X.sh → skills/<skill>/scripts/X.sh
- Readlink pattern (guide.md:41) and feature.md fallback manually fixed
- rddf_session + hooks.sh both moved to rddf-session/scripts/ (N3 fix)
- feature_*.sh PYTHONPATH recalc to ../.. (N2 fix)
- INSTALL.md scripts/ copy logic added (B4 fix)
- plan_done_gate.sh cross-skill validate_baseline.py path updated (I1/I2 fix)
- test_install_lib_distribution.bats assertion updated (strict bounds)
- 5 new regression tests added (layout/install/python_imports/no_broken_refs/readlink)
- ADR-0021 documents the 4 coupled decisions
- tools/phase2_path_migrator.py — type-aware path migration with dry-run
- docs/adr/* and docs/superpowers/* UNCHANGED (ADR immutability)

Verified:
- 654/656 Python unit tests pass (2 known perf flakes)
- All bats smoke + consistency + integration tests pass
- Path resolution: 0 broken refs
- Tool audit: 678 refs total, 2 TRANSFORM_FAILED (justified edge cases)"
```

### 7.3: Merge to master + delete branch

```bash
git checkout master
git merge openspec/skills-reorg-phase2-single-skill --ff-only
git branch -d openspec/skills-reorg-phase2-single-skill
```

## Task 8: 回滚模板（如需）

```bash
# 全量回滚（任何 Task 2-5 失败）
git checkout HEAD -- skills/ tests/
find skills/*/scripts -name __init__.py -delete 2>/dev/null || true
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
# 重跑 smoke 确认回到 Phase 1 完成状态
bats tests/smoke.bats
```