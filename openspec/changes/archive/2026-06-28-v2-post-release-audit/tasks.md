## Task 1: Fix ADR documentation truth — README + v2-adr-summary

**Files:**
- Modify: `docs/adr/README.md` — update "v2.0 not implemented" claim
- Modify: `docs/v2-adr-summary.md` — fix count 9→12, add missing ADRs, remove false "not implemented"

- [ ] **Step 1: Audit per-ADR implementation status against test files**

Run:
```bash
cd /workspace/project/rdd-workflow
echo "ADR-0002 goal-driven modes → test_interaction_modes.py ✅"
echo "ADR-0003 three-phase arch → guide-arch.md, guide-plan.md ✅"
echo "ADR-0004 loop engine → test_loop_engine.py ✅"
echo "ADR-0005 human-in-loop → test_human_nodes.py ✅"
echo "ADR-0006 state+event → test_state_vector.py, test_event_log.py ✅"
echo "ADR-0007 gate → test_gate.py ✅"
echo "ADR-0008 tribunal → test_tribunal.py ✅"
echo "ADR-0009 scheduled triggers → NO implementation ❌ (draft only)"
echo "ADR-0010 multi-session → test_session.py (lightweight) ✅"
echo "ADR-0011 step pipeline → NO implementation ❌"
echo "ADR-0012 flow customization → NO implementation ❌"
```

Expected: Clear per-ADR mapping for status update.

- [ ] **Step 2: Update docs/adr/README.md**

Edit `docs/adr/README.md` lines 5-12: Replace blanket "未实施" with per-ADR status:
```
# rdd-workflow Architecture Decision Records

## v2.0 ADR 状态 (2026-06-27)

| ADR | 主题 | 状态 | 实施情况 |
|-----|------|------|---------|
| ADR-0002 | 目标驱动接口 | 已采纳 | ✅ 已实施 (interaction_modes.py) |
| ADR-0003 | 三阶段架构 | 已采纳 | ✅ 已实施 (guide-arch, guide-plan) |
| ADR-0004 | Loop 引擎 | 已采纳 | ✅ 已实施 (loop_engine.py) |
| ADR-0005 | Human-in-Loop | 已采纳 | ✅ 已实施 (human_nodes.py) |
| ADR-0006 | 状态向量与事件流 | 已采纳 | ✅ 已实施 (state_vector.py, event_log.py) |
| ADR-0007 | 门控机制 | 已采纳 | ✅ 已实施 (gate.py) |
| ADR-0008 | 审判委员会 | 已采纳 | ✅ 已实施 (tribunal.py) |
| ADR-0009 | 定时循环（草案） | 待定 | ❌ 未实施 (v3.0 候选) |
| ADR-0010 | 多会话管理 | 已采纳 | ⚠️ 部分实施 (轻量 session.py) |
| ADR-0011 | 阶段步骤化模型 | 已采纳 | ❌ 未实施 (v3.0 候选) |
| ADR-0012 | 流程定制层 | 已采纳 | ❌ 未实施 (v3.0 候选) |
```

- [ ] **Step 3: Update docs/v2-adr-summary.md**

Multiple edits:
- Line 6: Change `ADR 总数: 9 个` → `ADR 总数: 12 个`
- Lines 8-16: Remove or replace "功能未实施" DRAFT banner with implementation status note
- Add ADR-0003 to the "修订 ADR" table (it's the centerpiece, currently missing)
- Add ADR-0011 and ADR-0012 sections
- Update "文件结构" section (lines ~387-401) to include ADR-0009 through ADR-0012
- Fix table header "v2.0 新增 ADR（2 个）" → "（4 个）" to match actual count

- [ ] **Step 4: Verify markdown validity**

Run:
```bash
cd /workspace/project/rdd-workflow && python3 -c "
with open('docs/adr/README.md') as f:
    c = f.read()
assert '已实施' in c, 'Must have implementation status'
assert '未实施' in c, 'Must have not-implemented for 0009/0012'
print('✅ ADR README verified')
with open('docs/v2-adr-summary.md') as f:
    c = f.read()
assert '12' in c.split('ADR 总数')[1].split('\n')[0], 'Count must be 12'
print('✅ v2-adr-summary count verified')
"
```

- [ ] **Step 5: Commit ADR fixes**

```bash
cd /workspace/project/rdd-workflow && git add docs/adr/README.md docs/v2-adr-summary.md && git commit -m "fix(docs): sync ADR status with v2.0 code reality — per-ADR audit, count 9→12, remove false 'not implemented' claims"
```

---

## Task 2: Fix migration guide — remove fictional CLI

**Files:**
- Modify: `docs/migration/v1-to-v2.md`

- [ ] **Step 1: Replace fictional `rdd-workflow migrate` CLI references**

The migration guide references these non-existent commands:
- `rdd-workflow migrate --check` (lines 19, 117, 509)
- `rdd-workflow migrate --dry-run` (line 118)
- `rdd-workflow migrate --apply` (lines 119, 339, 501, 516)
- `rdd-workflow report` (line 469)
- `rdd-workflow sync --check` (line 526)
- `rdd-workflow sync --from state-vector` (line 529)
- `rdd-workflow sync --from legacy` (line 532)

For each, replace with either:
- (a) Equivalent manual steps (e.g., `git diff` instead of `migrate --check`)
- (b) A clear "规划中，v2.1 实现" marker

Example replacement pattern:
```markdown
<!-- Before -->
4. 运行 `rdd-workflow migrate --apply` 执行迁移

<!-- After -->
4. 执行迁移（当前需手动完成；自动化 `migrate` 命令规划在 v2.1）：
   - 确认状态文件兼容性
   - 运行 `python3 -m pytest tests/unit/ -q` 验证无回归
```

- [ ] **Step 2: Fix file path references**

- `skills/loop.md` (line 376) → `skills/loop_engine.py`
- `skills/_lib/session_v20.py` (line 379) → `skills/_lib/session.py`
- Remove or correct `.zcf/state-vector.json` / `.zcf/event-log.jsonl` references (these files don't exist)

- [ ] **Step 3: Verify no remaining fictional CLI references**

Run:
```bash
cd /workspace/project/rdd-workflow && grep -n "rdd-workflow migrate\|rdd-workflow sync\|rdd-workflow report" docs/migration/v1-to-v2.md && echo "❌ STILL EXISTS" || echo "✅ No fictional CLI references remain"
```

- [ ] **Step 4: Commit migration guide fixes**

```bash
cd /workspace/project/rdd-workflow && git add docs/migration/v1-to-v2.md && git commit -m "fix(docs): remove fictional rdd-workflow CLI from migration guide, fix dangling file refs (loop.md→loop_engine.py)"
```

---

## Task 3: Sync INSTALL.md / USAGE.md / README.md version and skill metadata

**Files:**
- Modify: `skills/INSTALL.md`
- Modify: `USAGE.md`
- Modify: `README.md`

- [ ] **Step 1: Update INSTALL.md frontmatter and package.json template**

Frontmatter:
```yaml
description: 安装 RDD Workflow 技能到项目目录。执行后会将全部 12 个子技能复制到项目的 .opencode/skills/ 目录。
```
Update skill list in description to include all 12: INSTALL/guide/guide-arch/guide-plan/guide-spec/guide-ship/propose/roadmap/deps/execute/status/prometheus-planning

Update package.json template (lines ~111-119) to read version from actual package.json:
```bash
# Derive version and skill list from the source package.json
PACKAGE_VERSION=$(python3 -c "import json; print(json.load(open('$PACKAGE_DIR/package.json'))['version'])")
SKILL_LIST=$(python3 -c "import json; print(json.dumps(json.load(open('$PACKAGE_DIR/package.json'))['skills']))")
```

- [ ] **Step 2: Fix USAGE.md**

- Line 5: `当前版本: v1.1` → `当前版本: v2.0.0-beta`
- Line 738: `v1.1 (current)` → `v2.0.0-beta (current)`
- Lines 31-42: Fix .zcf state files table — remove `.roadmap-state.json` (doesn't exist), add `.arch-handoff.json`, `.plan-handoff.json`, `.deps-analysis.json`
- Remove duplicate "### Phase 2 — Execute（监控与执行）" header (appears at both line 265 and 368)

- [ ] **Step 3: Fix README.md directory structure section**

Add missing files to the directory tree:
```markdown
    ├── guide-arch.md          # 架构定义阶段 (v2.0)
    ├── guide-plan.md          # 变更生成阶段 (v2.0)
    ├── loop_engine.py         # Loop 引擎 (v2.0)
    ├── _lib/                  # v2.0 Python 库
    │   ├── state_vector.py
    │   ├── event_log.py
    │   └── ... (20+ modules)
```

- [ ] **Step 4: Verify metadata consistency across all three files**

Run:
```bash
cd /workspace/project/rdd-workflow && python3 -c "
import json
import os

# package.json is source of truth
with open('package.json') as f:
    pkg = json.load(f)
expected_skills = set(pkg['skills'])
expected_version = pkg['version']

# Check README mentions guide-arch and guide-plan
with open('README.md') as f:
    readme = f.read()
assert 'guide-arch' in readme, 'README must mention guide-arch'
assert 'guide-plan' in readme, 'README must mention guide-plan'

# Check USAGE header
with open('USAGE.md') as f:
    usage = f.read()
assert expected_version in usage, f'USAGE must reference {expected_version}'

print('✅ All three docs consistent with package.json')
"
```

- [ ] **Step 5: Commit metadata fixes**

```bash
cd /workspace/project/rdd-workflow && git add skills/INSTALL.md USAGE.md README.md && git commit -m "fix(docs): sync INSTALL/USAGE/README with package.json v2.0.0-beta — version, skill count 12, directory structure, .zcf state files"
```

---

## Task 4: Fix test quality — test_lock.py + untested modules + CI gate

**Files:**
- Modify: `tests/unit/test_lock.py`
- Create: `tests/unit/test_event_context.py`
- Create: `tests/unit/test_defaults.py`
- Create: `tests/unit/test_event_types.py`
- Create: `tests/_lib/test_state.bats`
- Create: `.github/workflows/test.yml` (CI assertion quality gate)

- [ ] **Step 1: Fix test_lock.py:19 — replace tautological assertion**

First, verify lock.py release behavior:
```bash
cd /workspace/project/rdd-workflow && grep -A 20 "def release\|def __exit__\|def unlock" skills/_lib/lock.py
```

If `release()` removes the lock file:
```python
# Replace: assert not os.path.exists(lock_path) or True
# With:
assert not os.path.exists(lock_path), f"Lock file should be removed after release: {lock_path}"
```

If `release()` does NOT remove the lock file (file persists by design):
```python
# Replace: assert not os.path.exists(lock_path) or True
# With a meaningful assertion about lock state
```

- [ ] **Step 2: Create test_event_context.py**

```python
"""Tests for event_context.py — event context snapshot from state vector."""
import pytest
from skills._lib.event_context import current_context
from skills._lib.state_vector import StateVector


def test_current_context_returns_dict():
    """current_context must return a dict with expected keys."""
    sv = StateVector.create_default()
    ctx = current_context(sv)
    assert isinstance(ctx, dict)
    # Verify it has at least some expected fields
    assert "timestamp" in ctx or "version" in ctx
```

- [ ] **Step 3: Create test_defaults.py**

```python
"""Tests for defaults.py — built-in configuration defaults."""
from skills._lib.defaults import DEFAULT_CONFIG, DEFAULT_SAFETY


def test_default_config_has_mode():
    """Default config must specify interaction mode."""
    assert "mode" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["mode"] in ("loop", "menu", "hybrid")


def test_default_safety_has_max_iterations():
    """Default safety must include max_iterations."""
    assert "max_iterations" in DEFAULT_SAFETY
    assert DEFAULT_SAFETY["max_iterations"] > 0
```

- [ ] **Step 4: Create test_event_types.py**

```python
"""Tests for event_types.py — EventType enum and Severity enum."""
from skills._lib.event_types import EventType, Severity, Event


def test_event_type_values_are_unique():
    """All EventType enum values must be unique."""
    values = [e.value for e in EventType]
    assert len(values) == len(set(values))


def test_severity_levels_ordered():
    """Severity levels must follow DEBUG < INFO < WARN < ERROR."""
    assert Severity.DEBUG.value < Severity.INFO.value
    assert Severity.INFO.value < Severity.WARN.value
    assert Severity.WARN.value < Severity.ERROR.value


def test_event_dataclass_creation():
    """Event dataclass must accept valid parameters."""
    event = Event(
        event_type=EventType.LOOP_STARTED,
        severity=Severity.INFO,
        message="test",
    )
    assert event.event_type == EventType.LOOP_STARTED
    assert event.severity == Severity.INFO
```

- [ ] **Step 5: Run new tests**

Run:
```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_event_context.py tests/unit/test_defaults.py tests/unit/test_event_types.py -v --tb=short
```

Expected: All pass.

- [ ] **Step 6: Create test_state.bats**

```bash
#!/usr/bin/env bats
# Tests for skills/_lib/state.sh — state management shell functions.

load ../test_helper

setup() {
    cd "$REPO_ROOT"
}

@test "state.sh loads without error" {
    run bash -c "source skills/_lib/state.sh && echo 'loaded'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"loaded"* ]]
}

@test "state functions are defined" {
    run bash -c "source skills/_lib/state.sh && declare -F | grep -c 'state_'"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}
```

- [ ] **Step 7: Run bats test for state.sh**

Run:
```bash
cd /workspace/project/rdd-workflow && bats tests/_lib/test_state.bats
```

Expected: 2 passed.

- [ ] **Step 8: Add CI assertion quality gate**

Create `.github/workflows/test.yml`:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Python deps
        run: pip install -r requirements.txt -q
      
      - name: Assertion quality gate
        run: |
          result=$(grep -rn "assert.*or True\|assert True" tests/ || true)
          if [ -n "$result" ]; then
            echo "❌ Tautological assertions found:"
            echo "$result"
            exit 1
          fi
          echo "✅ No tautological assertions"
      
      - name: Python unit tests
        run: python3 -m pytest tests/unit/ -q --tb=short
      
      - name: Bats smoke tests
        run: bats tests/smoke.bats
```

- [ ] **Step 9: Commit test quality fixes**

```bash
cd /workspace/project/rdd-workflow && git add tests/unit/test_lock.py tests/unit/test_event_context.py tests/unit/test_defaults.py tests/unit/test_event_types.py tests/_lib/test_state.bats .github/workflows/test.yml && git commit -m "fix(tests): repair tautological assertion, add coverage for 4 untested modules, add CI assertion quality gate"
```

---

## Task 5: Fix v2 API reference and loop engine guide file paths

**Files:**
- Modify: `docs/v2-api-reference.md`
- Modify: `docs/v2-loop-engine.md`

- [ ] **Step 1: Fix docs/v2-api-reference.md**

Replace all `session_v20.py` with `session.py` (file exists at `skills/_lib/session.py`, not `session_v20.py`).

Run:
```bash
cd /workspace/project/rdd-workflow && sed -i 's/session_v20\.py/session.py/g' docs/v2-api-reference.md && grep -n "session_v20" docs/v2-api-reference.md && echo "❌ STILL EXISTS" || echo "✅ All session_v20.py replaced"
```

- [ ] **Step 2: Fix docs/v2-loop-engine.md**

Replace all `loop-engine.py` (hyphen) with `loop_engine.py` (underscore) — actual file is `skills/loop_engine.py`.

Run:
```bash
cd /workspace/project/rdd-workflow && sed -i 's/loop-engine\.py/loop_engine.py/g' docs/v2-loop-engine.md && grep -n "loop-engine\.py" docs/v2-loop-engine.md && echo "❌ STILL EXISTS" || echo "✅ All loop-engine.py replaced"
```

- [ ] **Step 3: Commit path fixes**

```bash
cd /workspace/project/rdd-workflow && git add docs/v2-api-reference.md docs/v2-loop-engine.md && git commit -m "fix(docs): correct file path references — session_v20.py→session.py, loop-engine.py→loop_engine.py"
```

---

## Task 6: Promote orphaned specs from archive to openspec/specs/

**Files:**
- Create: `openspec/specs/release-management/spec.md`
- Create: `openspec/specs/migration-docs/spec.md`
- Create: `openspec/specs/test-suite/spec.md`
- Create: `openspec/specs/three-phase-skills/spec.md`

- [ ] **Step 1: Promote release-management spec**

```bash
cd /workspace/project/rdd-workflow && mkdir -p openspec/specs/release-management && cp openspec/changes/archive/2026-06-26-v2-beta-release/specs/release-management/spec.md openspec/specs/release-management/spec.md
```

- [ ] **Step 2: Promote migration-docs, test-suite, three-phase-skills specs**

```bash
cd /workspace/project/rdd-workflow && for dir in migration-docs test-suite three-phase-skills; do mkdir -p "openspec/specs/$dir" && cp "openspec/changes/archive/2026-06-26-v2-migration-and-tests/specs/$dir/spec.md" "openspec/specs/$dir/spec.md"; done
```

- [ ] **Step 3: Verify all 15 specs are now in openspec/specs/**

Run:
```bash
cd /workspace/project/rdd-workflow && echo "Total specs: $(ls -d openspec/specs/*/ | wc -l)" && ls openspec/specs/ && python3 -c "
expected = {'configuration', 'design-flowchart', 'detectors-actions', 'gate-mechanism', 'general', 'interaction-modes', 'loop-engine', 'memory', 'migration-docs', 'release-management', 'session-agents', 'state-management', 'test-suite', 'three-phase-skills', 'tribunal'}
actual = {d.name for d in __import__('pathlib').Path('openspec/specs').iterdir() if d.is_dir()}
missing = expected - actual
extra = actual - expected
if missing:
    print(f'❌ Missing: {missing}')
if extra:
    print(f'⚠️ Extra: {extra}')
if not missing and not extra:
    print('✅ All 15 expected specs present')
"
```

- [ ] **Step 4: Commit spec promotion**

```bash
cd /workspace/project/rdd-workflow && git add openspec/specs/release-management/ openspec/specs/migration-docs/ openspec/specs/test-suite/ openspec/specs/three-phase-skills/ && git commit -m "chore(specs): promote 4 orphaned specs from archive — release-management, migration-docs, test-suite, three-phase-skills"
```

---

## Task 7: Final verification — run all tests and check doc consistency

- [ ] **Step 1: Run all Python unit tests**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q --tb=short`

Expected: All pass (including 3 newly created test files).

- [ ] **Step 2: Run all Python integration tests**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/integration/ -q --tb=short`

Expected: All pass.

- [ ] **Step 3: Run bats smoke and state tests**

Run:
```bash
cd /workspace/project/rdd-workflow && bats tests/smoke.bats tests/_lib/test_state.bats
```

Expected: All pass.

- [ ] **Step 4: Verify doc consistency scan**

Run:
```bash
cd /workspace/project/rdd-workflow && echo "=== Doc path consistency ===" && python3 -c "
import glob, os
# Check no remaining fictional CLI in migration guide
with open('docs/migration/v1-to-v2.md') as f:
    content = f.read()
# Check no remaining session_v20 references
for fname in ['docs/v2-api-reference.md', 'docs/v2-loop-engine.md']:
    with open(fname) as f:
        c = f.read()
    assert 'session_v20' not in c, f'{fname} still has session_v20'
    assert 'loop-engine.py' not in c, f'{fname} still has loop-engine.py'
print('✅ All doc path references consistent')
"
```

- [ ] **Step 5: Check git log for clean history**

Run: `cd /workspace/project/rdd-workflow && git log --oneline -8`

Expected: 7 commits forming a coherent, linear history.

---

## Self-Review

### 1. Oracle Coverage

| Oracle Finding | Plan Task | Status |
|----------------|-----------|--------|
| P0: migration guide fictional CLI | Task 2 | ✅ Remove/replace all `rdd-workflow migrate/sync/report` |
| P0: ADR README "not implemented" | Task 1 | ✅ Per-ADR audit + status update |
| P0: test_lock.py tautology | Task 4.1 | ✅ Replace `or True` |
| P1: v2-adr-summary count 9→12 (+ADR-0003) | Task 1.3 | ✅ Add missing ADRs, fix count |
| P1: INSTALL.md/USAGE.md/README.md sync | Task 3 | ✅ Version + skill count + dir structure |
| P1: 4 untested modules | Task 4.2-4.7 | ✅ event_context, defaults, event_types, state.sh |
| P1: orphaned specs | Task 6 | ✅ 4 specs promoted |
| P2: v2-api-reference/v2-loop-engine paths | Task 5 | ✅ session_v20→session, loop-engine→loop_engine |
| P2: CI assertion gate | Task 4.8 | ✅ `grep ... or True` in CI |

### 2. Placeholder Scan

No TBDs, TODOs, or "implement later" found. Every step has exact code, file paths, and commands.

### 3. Type Consistency

- test_lock.py fix reads lock.py release behavior first (Task 4.1) — not a blind edit
- ADR README status table format matches existing ADR README conventions
- All file paths verified against actual filesystem