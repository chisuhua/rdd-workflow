# Design: skills-reorg-phase2-single-skill

> **设计依据**: `docs/adr/ADR-0021-phase2-per-skill-helper-migration.md` — 4 个联合决策
> **Phase 1 Known Traps**（必须显式处理）:
> - N1: `guide.md:41` `readlink -f` 嵌套模式 → 手工处理
> - N2: `feature.md:41-53` fallback 逻辑 5 行 → 手工处理
> - B1: ~85 test 文件硬编码 `_lib/` 路径 → 完整审计
> - B3: INSTALL.md 3 处 flat-copy 模式 → Task 7 改造
> - B4: prose 无差别 sed 破坏 git blame + ADR 历史 → scope 限定 SKILL.md

## Decision 1: 用 `tools/phase2_path_migrator.py` 替代散在 sed（ADR-0021 Decision 1 工具支撑）

工具特性：
- **dry-run** 模式：列出所有受影响行
- **type-aware**：区分 `source_sh` / `import_py` / `prose` / `check_file` / `grep_str`
- **scope 控制**：ADR/历史 plan 文档自动跳过
- **per-skill filter**：可只审计特定 skill
- 输出 JSON 摘要 + 详细报告

**用法**:
```bash
# Step 0: 全面审计
python3 tools/phase2_path_migrator.py audit

# Step 0.5: 按 skill 审计 + dry-run apply
python3 tools/phase2_path_migrator.py audit --skill guide-ship
python3 tools/phase2_path_migrator.py apply --dry-run --skill guide-ship

# Step N: 真实 apply
python3 tools/phase2_path_migrator.py apply --skill guide-ship
```

## Decision 2: 4 类 source 行转换模式

### 模式 1: `$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/` → `/scripts/`

```bash
旧: source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/ship_plan.sh"
新: source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/ship_plan.sh"
```

### 模式 2: `$SCRIPT_DIR/_lib/` → `$SCRIPT_DIR/scripts/`

### 模式 3: `$_SCRIPT_DIR/_lib/` → `$_SCRIPT_DIR/scripts/`

### 模式 4: `$REPO_ROOT/skills/_lib/X.sh` → `$REPO_ROOT/skills/<skill>/scripts/X.sh`（仅单 skill）

### 模式 5: `$(dirname "$(readlink -f ...)")/../_lib/` → `/scripts/`（**手工处理，Phase 1 N1 lesson**）

`skills/guide/SKILL.md:41` 唯一一行 readlink 嵌套，工具检测到后跳过：
```bash
旧: source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/../_lib/scan-state.sh"
新: source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/scripts/scan-state.sh"
```

## Decision 3: Python imports 重写（ADR-0021 Decision 1）

### 给 11 个 skill 的 `scripts/` 加 `__init__.py`

```bash
for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
  [ -d "skills/$skill/scripts" ] && touch "skills/$skill/scripts/__init__.py"
done
```

### `from skills._lib.X import Y` → `from skills.<skill>.scripts.X import Y`

| 旧 | 新 |
|---|---|
| `from skills._lib.feature_cli import render_summary` | `from skills.feature.scripts.feature_cli import render_summary` |
| `from skills._lib.rddf_session import RddfSessionCoordinator` | `from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator` |

**跨 skill 共享 imports 不变**: `from skills._lib.iteration import ...` 保持。

## Decision 4: `rddf-session/scripts/` 同移 `hooks.sh` + `rddf_session.py`（ADR-0021 Decision 2）

解决 N3 自相矛盾：`rddf_session_hooks.sh` 留 `_lib/` 但 import `rddf_session.py`（要移走）→ 必然 broken。

**统一移到 `rddf-session/scripts/`**。3 个调用方（guide-arch/guide-plan/guide-ship）的 SKILL.md 各加：
```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
```

## Decision 5: Prose 引用 scope 限定（ADR-0021 Decision 3）

**`skills/<name>/SKILL.md` + `skills/INSTALL.md`** → prose 更新（`scripts/X.sh`）

**`docs/adr/`, `docs/superpowers/`, `docs/audit/`, `openspec/changes/`** → **不变**（历史快照）

工具通过 NEVER_TOUCH_SCOPES + PROSE_UPDATE_SCOPES 配置自动执行。

## Decision 6: INSTALL.md 改造推迟到 Task 7（ADR-0021 Decision 4）

原计划 Task 1 改 INSTALL.md → 在所有 move 完成前会有"中间态"。改为：

- Task 2-5：移文件（不碰 INSTALL.md）
- Task 6：清理 `__pycache__/`
- **Task 7**: 改 INSTALL.md（所有 scripts/ 已就位）+ 改 test_install_lib_distribution.bats
- Task 8：commit

## Decision 7: `feature_*.sh` 的 PYTHONPATH 重算（ADR-0021 N2）

当前 `feature_summary.sh:5-7`:
```bash
_SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]:-$0}")"
PYTHONPATH="$_SCRIPT_DIR/..${PYTHONPATH:+:$PYTHONPATH}" python3 -c "..."
```

`_SCRIPT_DIR/..` 当前 = `skills/` （因为 _SCRIPT_DIR = `skills/_lib/`）

移到 `skills/feature/scripts/` 后 `_SCRIPT_DIR/..` = `skills/feature/`，**需要双跳**:
```bash
PYTHONPATH="$_SCRIPT_DIR/../..${PYTHONPATH:+:$PYTHONPATH}" python3 -c "..."
```

4 个 `feature_*.sh` 文件全部手工修改此行（不能用工具 — 因为语义层面）。

## Decision 8: 验证门控（每 task 后立即跑）

### 每个 skill 移完后立即验证（不是 Task 6 才跑全量）

```bash
# Task 2 后（guide-ship）
bats tests/integration/test_ship_*_extraction.bats \
     tests/integration/test_guide_ship_skill.bats \
     tests/integration/test_guide_ship_line_count.bats \
     tests/_lib/test_scan_state.bats
python3 -m pytest tests/unit/test_propose_change.py tests/unit/test_plan_done_gate.py tests/unit/test_feature_view.py -q
bash -n skills/guide-ship/scripts/*.sh
```

### 5 个强制 regression 测试（Task 5）
1. `test_phase2_layout.bats` — 锁定 per-skill scripts/ 布局
2. `test_phase2_install_full.bats` — 真实跑 INSTALL.md 复制
3. `test_phase2_python_imports.py` — 参数化检查 11 个 moved + N 个 shared
4. `test_phase2_no_broken_refs.bats` — 53 处 source + 74 import 全部可解析
5. `test_phase2_readlink_fallback.bats` — guide.md + feature.md 手工路径验证

### Task 6 全量验证
```bash
bats tests/  # 8 min
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short  # 1 min
```

## 回滚方案（per-skill 原子回滚）

```bash
# Task 2 失败时单独回滚 guide-ship
for f in skills/guide-ship/scripts/*.{sh,py,env.py}; do
  [ -e "$f" ] && mv "$f" skills/_lib/
done
rmdir skills/guide-ship/scripts 2>/dev/null
git checkout HEAD -- skills/guide-ship/SKILL.md
git checkout HEAD -- tests/integration/test_*ship*.bats tests/integration/test_*guide_ship*.bats

# 全量回滚（任务链断裂时）
git checkout HEAD -- skills/ tests/
find skills/*/scripts -name __init__.py -delete 2>/dev/null
```

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 工具 regex 漏匹配 | dry-run 先 grep 全部匹配，列人工 review |
| `feature_*.sh` PYTHONPATH 错（runtime 才暴露）| Task 5 加 `python3 -c "from skills.feature.scripts.feature_view import ..."` smoke |
| INSTALL.md Task 7 改动太大 | 实际只是 +2 行 `cp -rf scripts/` 复制循环 |
| rddf-session 跨 3 skill source | Task 3/4/5 各加 1 行 SKILL.md source 即可 |
| `__init__.py` 影响 sys.path | 不影响 — `skills/` 已在 sys.path（Python test conftest 自动加）|