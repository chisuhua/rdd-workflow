---
SCOPE: shared
STATUS: PROPOSED
---

# Tasks: fix-debt-audit-2026-07-14

> **Goal**: 修复 2026-07-14 审计 + Metis 审查发现的债务 (4 waves, 15 tasks)
> **Risk**: Low-Medium — P0 文档修复安全,P1 涉及 CI 修改和测试删除
> **不做什么**: 不改运行时 workflow 行为 / 不改 v1.x archived change / 不修 P3 命名漂移
> **Estimated effort**: Pre-Wave: 15 min / Wave 1: 1.5 hr / Wave 2: 5-6 hr / Wave 3: 5-6 hr

---

## Pre-Wave — 修复元债务 + 基线确认

> Oracle 审查发现 `npm test` (`bats tests/`) 只跑 smoke,不跑 integration bats。这是元债务 —— 必须先修,否则开发者循环无法验证后续修复。

### Task 0.1: 修复 `npm test` 缺口 — 让 bats 递归运行

**问题**: `bats tests/` 只找顶层 `.bats` 文件,跳过 `tests/integration/` 和 `tests/_lib/` 下 50+ 测试。

**修复**: 更新 `package.json` 的 `test` 脚本:

```json
"test": "bats tests/ --recursive"
```

或改为显式 glob: `"test": "bats tests/smoke.bats tests/_lib/*.bats tests/integration/*.bats"`

**验收**:
```bash
npm test 2>&1 | grep -c "^ok "
# 期望: > 7 (原本只有 smoke 7 个;现在应包含全部)
```

### Task 0.2: 确认基线测试状态

```bash
cd /workspace/project/spec-workflow

# Python (全量)
python3 -m pytest tests/unit/ -q --tb=short
# 期望: 545 passed (含 82 DeprecationWarning — Wave 2 修复)

# Bats (全量,含 integration)
npm test 2>&1 | tail -5
# 记录: 哪些测试当前失败,哪些通过

# 重点记录 CI 静态列表中的测试状态
bats tests/integration/test_gate_report.bats 2>&1 | tail -3
bats tests/integration/test_json_safety.bats 2>&1 | tail -3
bats tests/integration/test_roadmap_skill.bats 2>&1 | tail -3
bats tests/_lib/test_skill.bats 2>&1 | tail -3
bats tests/_lib/test_state.bats 2>&1 | tail -3
# Oracle 发现 test_gate_report.bats 当前 2/4 失败 — 记录为基线
```

---

## Wave 1 — P0 立即修复 (5 Tasks)

> Oracle 建议: 将 D5 (sync_state 删除) 从 Wave 3 提升到 Wave 1,因为纯文件删除操作无 in-place 冲突,且必须先于 D7 CI 更新执行。

### Task 1.1: ADR-0013 文档引用分两路修正

**Context**: Metis 审查发现 `propose.md:463` 是 skeleton branching 语义(→ ADR-0020),不是 quality gate(→ ADR-0018)。分两路修正,不可一刀切。

**步骤 A**: `arch_quality_gate.py` 5 处 + `guide-arch.md:870` → ADR-0018

```bash
cd /workspace/project/spec-workflow
sed -i '1s/ADR-0013/ADR-0018/' skills/_lib/arch_quality_gate.py
sed -i 's/ADR-0013 §3\.1/ADR-0018 §3.1/' skills/_lib/arch_quality_gate.py
sed -i 's/ADR-0013 §3\.2/ADR-0018 §3.2/' skills/_lib/arch_quality_gate.py
sed -i 's/ADR-0013 §3\.3/ADR-0018 §3.3/' skills/_lib/arch_quality_gate.py
sed -i 's/ADR-0013 §3\.4/ADR-0018 §3.4/' skills/_lib/arch_quality_gate.py
sed -i 's/ADR-0013/ADR-0018/' skills/guide-arch.md
```

**步骤 B**: `propose.md:463` → ADR-0020 (skeleton branching)

```bash
sed -i '463s/ADR-0013/ADR-0020/' skills/propose.md
```

**步骤 C**: 测试文件 docstring 同步

```bash
# Oracle 审查发现 test_gate.py:122,134 也引 ADR-0013 (quality gate 语义)
sed -i 's/ADR-0013/ADR-0018/' tests/unit/test_arch_quality_gate.py
sed -i 's/ADR-0013/ADR-0018/' tests/unit/test_gate.py
# 注意: test_change_alignment.py:313,317,321 引用 ADR-0018→ADR-0019 lineage — 正确,不动
```

**验收**:

```bash
# quality gate 语义 0 ADR-0013
grep -c "ADR-0013" skills/_lib/arch_quality_gate.py skills/guide-arch.md tests/unit/test_arch_quality_gate.py tests/unit/test_gate.py
# → 0

# skeleton branching → ADR-0020
grep "ADR-0020" skills/propose.md | head -1
# → 1 hit (line 463)

# skills/ 下 ADR-0013 应只剩 extract-scan-state 语义
grep -rn "ADR-0013" skills/
# → scan-state 引用(如有),无 quality gate/skeleton 引用

python3 -m pytest tests/unit/test_arch_quality_gate.py tests/unit/test_gate.py -q
# → pass
```

### Task 1.2: 恢复 `state.sh` 的 `safe_python_json` / `safe_python_yaml` helper

**Context**: 当前 stub 说 "no production callers",但 `propose.md` 和 `roadmap.md` 实际调用。选择恢复 helper 而非 inline,以保持与 `test_json_safety.bats` 和 `test_roadmap_skill.bats` 回归测试一致。

**步骤**: 重写 `skills/_lib/state.sh`

```bash
# skills/_lib/state.sh
# Shell helpers for safe JSON/YAML operations via python3.
# Used by propose.md and roadmap.md. Restored from stub — callers are real.

safe_python_json() {
  python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
    result = data
    for key in sys.argv[2].split('.'):
        result = result.get(key, '') if isinstance(result, dict) else result[int(key)] if isinstance(result, list) and key.isdigit() else ''
except (json.JSONDecodeError, KeyError, IndexError, ValueError):
    print('', end='')
    sys.exit(0)
print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False), end='')
" "$@"
}

safe_python_yaml() {
  python3 -c "
import yaml, sys, json
try:
    data = yaml.safe_load(sys.argv[1])
    if not isinstance(data, dict): print('', end=''); sys.exit(0)
    result = data
    for key in sys.argv[2].split('.'):
        result = result.get(key, '') if isinstance(result, dict) else ''
except Exception:
    print('', end='')
    sys.exit(0)
print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False), end='')
" "$@"
}
```

**验收**:

```bash
grep -c "safe_python_json()" skills/_lib/state.sh  # → 1
bats tests/integration/test_json_safety.bats          # → all pass
bats tests/integration/test_roadmap_skill.bats        # → all pass
# Oracle 审查: test_state.bats 期望 state.sh 是 stub → 更新测试以反映恢复后的 helpers
bats tests/_lib/test_state.bats                        # → all pass (测试已更新)
grep -c "source.*state.sh" skills/propose.md skills/roadmap.md  # → 各 1 处,不变
```

### Task 1.3: smoke.bats 动态化

替换 `tests/smoke.bats:19-30` 的 `@test "all 10 skill files exist"`:

```bash
@test "all skill files exist (dynamic)" {
  for f in skills/*.md; do
    [ -f "$f" ]
  done
}

@test "v1.x baseline skills still present (regression)" {
  [ -f "skills/INSTALL.md" ]
  [ -f "skills/guide.md" ]
  [ -f "skills/guide-arch.md" ]
  [ -f "skills/guide-plan.md" ]
  [ -f "skills/guide-ship.md" ]
  [ -f "skills/propose.md" ]
  [ -f "skills/execute.md" ]
  [ -f "skills/status.md" ]
  [ -f "skills/roadmap.md" ]
  [ -f "skills/deps.md" ]
}
```

**验收**: `bats tests/smoke.bats` → 9/9; `bats tests/integration/test_skill_metadata_consistency.bats` → pass

### Task 1.4: 文档同步 — AGENTS.md / tests/README.md skill 计数

```bash
# AGENTS.md: "12 个 .md" → "13 个 .md"
# tests/README.md skill coverage map: 补充 feature / rddf-session / spec-workflow-writing-plans
```

**验收**: `grep "个 \.md" AGENTS.md | grep -o "[0-9]\+"` → 13

### Task 1.5: 删除 sync_state.py (从 Wave 3 提升)

**Context**: Oracle 审查确认 0 生产 caller,且必须**先于 D7 CI 更新**执行,避免 CI ImportError。

**步骤**:
```bash
rm skills/_lib/sync_state.py
rm tests/unit/test_sync_state.py
```

**验收**:
```bash
grep -rn "sync_state" skills/ openspec/ --include="*.py"    # → 0
python3 -m pytest tests/unit/ -q --tb=short                   # → pass (减 sync_state)
# 注意: 文档清理 (docs/v2-api-reference.md, docs/migration/v1-to-v2.md) 移到 Wave 3 Task 3.4 审计闭环
```

---

## Wave 2 — P1 本迭代 (5 Tasks)

### Task 2.1: Python 3.14 ast 迁移

`skills/loop_engine.py` `_SAFE_NODES`: `ast.Num/Str/Bytes/NameConstant` → `ast.Constant`

**验收**:

```bash
python3 -W error::DeprecationWarning -m pytest tests/unit/test_loop_engine.py -q  # → pass, 0 warnings
python3 -m pytest tests/unit/ -q --tb=short  # → 545 passed, 0 DeprecationWarning
```

### Task 2.2: phase-gate-report 彻底删除 (含测试更新)

**Context**: 见 Decision 6。现状: writer 写 `phase-gate-report.md`(无点),reader 读 `.phase-gate-report.md`(有点),guide.md 未接入。锁定测试: `test_gate_report.bats`(CI), `test_guide_scan.bats`, `test_roadmap_skill.bats`, `test_skill.bats`。

**步骤**:

1. 删除 `skills/roadmap.md` gate-report 命令块 (写入逻辑)
2. 删除 `skills/_lib/scan-state.sh:115-122` 优先级 4 if 块 (读取逻辑)
3. 更新 `docs/adr/ADR-0006-state-vector-event-log.md`: 移除 "死代码风险" 标注
4. 更新测试:
   - `test_gate_report.bats` → 改为 assert phase-gate-report 不再被引用 (或删除)
   - `test_guide_scan.bats` P1-3 → assert scan-state.sh 不再检查 phase-gate-report
   - `test_roadmap_skill.bats` → 移除 gate-report command 断言 (commands 6→5)
   - `test_skill.bats` → 更新 roadmap commands count (≥6 → ≥5)

**验收**:

```bash
grep -rn "phase-gate-report" skills/                                # → 0 hits
bats tests/integration/test_gate_report.bats                         # → pass (post-update)
bats tests/integration/test_guide_scan.bats                          # → pass
bats tests/integration/test_roadmap_skill.bats                       # → pass
bats tests/_lib/test_skill.bats                                      # → pass
```

### Task 2.3: rddf + archive.sh + scan-state.sh 基础 bats 测试

新建 3 个测试文件:

```bash
tests/integration/test_rddf_cli.bats   # help/status/feature/deps/session/archive/cleanup
tests/_lib/test_scan_state.bats        # scan_state 返回值 (有/无 roadmap, changes, worktree)
tests/_lib/test_archive.bats           # archive_change / find_default_branch
```

**验收**:

```bash
bats tests/integration/test_rddf_cli.bats   # → all pass
bats tests/_lib/test_scan_state.bats         # → all pass
bats tests/_lib/test_archive.bats            # → all pass
```

### Task 2.4: CI workflow 更新 — 新增测试 + gate-report 测试调整

修改 `.github/workflows/test.yml` 的 `STATIC_BATS` 列表:
- 添加新增的 3 个测试文件
- 如果 `test_gate_report.bats` 被删除/大幅改写,移除或保持更新后文件

**验收**: CI 列表中的所有 bats 文件存在且单独通过

### Task 2.5: 文档同步 — tests/README.md coverage map

补充 `feature`, `rddf-session`, `spec-workflow-writing-plans` 和新增 bats 测试到 coverage map。

---

## Wave 3 — P2 下迭代 (3 Tasks)

> sync_state 删除已移至 Wave 1 (Task 1.5)。文档清理合并到 Task 3.3 审计闭环。

### Task 3.1: atomic_write 公共 helper — 统一 5 处

创建 `skills/_lib/atomic_write.py`,替换 `validate_report.py`, `deps_output.py`, `iteration.py`, `rddf_session.py` 的 `_atomic_write` (4 处) + 评估 `state_vector.py` 的 `save()` 方法。

**验收**:

```bash
grep -n "def _atomic_write" skills/_lib/*.py   # → 0 (全部改用 import)
python3 -m pytest tests/unit/ -q --tb=short      # → all pass
```

### Task 3.2: RddfSessionCoordinator god class 拆分

402 行 class 拆为 `session_persistence.py` / `session_commands.py` / `session_binding.py` + 简化后的 `rddf_session.py` 兼容面。

**验收**: `python3 -m pytest tests/unit/test_rddf_session.py -q` → all pass

### Task 3.3: 审计闭环 — 修复合规性验收 (含 sync_state 文档清理)

**全量测试**:

```bash
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
bats tests/smoke.bats
for f in $(grep "tests/" .github/workflows/test.yml | grep "\.bats" | sed 's/.*\(tests\/.*\.bats\).*/\1/'); do bats "$f" | tail -1; done
```

**P0/P1 逐项验收**:

| 审计项 | 验收命令 | 期望 |
|--------|---------|------|
| ADR confusion | `grep -rn "ADR-0013" skills/_lib/arch_quality_gate.py skills/guide-arch.md` | 0 hits |
| skeleton ADR | `grep "ADR-0020" skills/propose.md` | 1 hit |
| state.sh | `grep -c "safe_python_json()" skills/_lib/state.sh` | 1 |
| smoke.bats | `grep -c "all 10 skill" tests/smoke.bats` | 0 |
| Python 3.14 | `python3 -W error::DeprecationWarning -m pytest tests/unit/ -q 2>&1 \| grep -c "Deprecation"` | 0 |
| phase-gate-report | `grep -rn "phase-gate-report" skills/` | 0 |
| rddf tests | `bats tests/integration/test_rddf_cli.bats` | all pass |
| sync_state | `grep -rn "sync_state" skills/ openspec/ --include="*.py"` | 0 |
| sync_state docs | `grep -rn "sync_state" docs/v2-api-reference.md docs/migration/v1-to-v2.md` | 0 |
| npm test gap | `npm test 2>&1 \| grep -c "^ok "` | > 7 (全量) |
| rddf tests | `bats tests/integration/test_rddf_cli.bats` | all pass |
| sync_state | `grep -rn "sync_state" skills/ openspec/ --include="*.py"` | 0 |

**生成报告**: `docs/audit/2026-07-14-debt-fix-compliance.md`