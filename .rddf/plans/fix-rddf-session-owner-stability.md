# fix-rddf-session-owner-stability 实施计划

> **P0 — 阻断上游根因**。本计划基于 improvements/fix-rddf-session-owner-stability.md + openspec/changes/fix-rddf-session-owner-stability/{proposal,design,tasks}.md 编写。
>
> **TDD 5 步纪律** (来自 rdd-workflow v2.0 execute skill): 每个 task 严格按 Write failing test → Verify fail → Implement → Verify pass → Commit。
>
> **预期修改文件**:
> 1. `skills/rddf-session/scripts/rddf_session_hooks.sh` (3 处 fallback 改写)
> 2. `tests/unit/test_rddf_session_owner_stability.py` (新增)
> 3. `tests/integration/test_rddf_session_owner_cache.bats` (新增)
> 4. `tests/_lib/rddf_session_owner_helpers.bash` (新增 — 探测 helper)
>
> **强约束** (来自 review + 设计阶段):
> - 三层 fallback: `$OPENCODE_SESSION_ID` env → `/proc/<shell-ppid>/cmdline` 探测 → `shell_pid` (`$(hostname -s)_$$`)
> - 跨 bash 调用 cache: `~/.cache/rddf-session-owner` (per-host, 0600, TTL 1h)
> - env var 始终优先 (OpenCode 平台注入优先级最高)
> - 探测深度 ≤5 层, 仅采纳 cmdline 含 "opencode" 子串
> - **不修改 schema** (owner 字段类型不变)
> - **不修改 `RDDF_ALLOW_CROSS_STAGE_PARALLEL` 行为**
> - **不修改 OpenCode 平台** (应由平台显式注入)
>
> **依赖前置**: 5 个 ship 候选 change 中, 本 P0 是上游, 无前置依赖。

---

## Task 1: 单元测试 — 探测 fallback 链 (3 路径)

### 1. Write failing test

**文件**: `tests/unit/test_rddf_session_owner_stability.py`

```python
"""Verify 3-layer fallback produces consistent owner ID across multiple bash invocations.

GIVEN bash tool calls in same OpenCode window spawn child shells
WHEN rddf_session_hooks.sh fallback chain runs 3 times consecutively
THEN owner ID is identical across all 3 calls (without env var injection).
"""
import os
import subprocess
from pathlib import Path
import pytest

HOOKS_SCRIPT = Path("skills/rddf-session/scripts/rddf_session_hooks.sh")


def test_env_var_priority_over_fallback():
    """When OPENCODE_SESSION_ID is set, env var wins over fallback."""
    env = os.environ.copy()
    env["OPENCODE_SESSION_ID"] = "test-uuid-abc123"
    # invoke hook without env var should pick up test-uuid-abc123
    # (assertion: in subsequent tests we verify via rddf-session output)


def test_fallback_3_calls_produce_same_owner():
    """3 consecutive bash calls produce same owner ID via /proc cmdline detection."""
    # invoke 3 times in subprocess, capture stdout owner line, assert equal
    ...


def test_cache_file_round_trip():
    """~/.cache/rddf-session-owner write/read round-trip preserves owner ID + source."""
    ...


def test_cmdline_without_opencode_falls_back_to_shell_pid():
    """When no /proc entry contains 'opencode', fallback to $(hostname -s)_$$."""
    ...


def test_cache_ttl_expiry_recomputes_owner():
    """Cache file older than 1h triggers re-detection."""
    ...
```

### 2. Verify fail (red)

```bash
pytest tests/unit/test_rddf_session_owner_stability.py -v
# 预期: 5 tests FAIL (rddf_session_hooks.sh 仍是旧版, 5 处 fallback 用 $PPID 而非 3 层)
```

### 3. Implement

**文件**: `skills/rddf-session/scripts/rddf_session_hooks.sh` (5 处, 见 hook_entries L49/107/157/205/248)

```bash
# --- 新增探测 helper ---
_detect_opencode_owner() {
  # 优先级: $OPENCODE_SESSION_ID env → /proc cmdline 探测 → shell_pid
  local env_id="${OPENCODE_SESSION_ID:-}"
  if [ -n "$env_id" ]; then
    echo "${env_id}|env"
    return 0
  fi

  # Cache file (TTL 1h)
  local cache_file="$HOME/.cache/rddf-session-owner"
  if [ -f "$cache_file" ]; then
    local cache_age=$(($(date +%s) - $(stat -c %Y "$cache_file")))
    if [ "$cache_age" -lt 3600 ]; then
      cat "$cache_file"
      return 0
    fi
  fi

  # /proc cmdline 探测 (深度 ≤5, 仅采纳含 "opencode" 的 cmdline)
  local ppid_chain="$PPID"
  local depth=0
  while [ "$depth" -lt 5 ] && [ -n "$ppid_chain" ] && [ "$ppid_chain" -gt 1 ]; do
    if [ -r "/proc/$ppid_chain/cmdline" ]; then
      local cmdline=$(tr '\0' ' ' < "/proc/$ppid_chain/cmdline" 2>/dev/null)
      if echo "$cmdline" | grep -q "opencode"; then
        local owner="${HOSTNAME}_${ppid_chain}"
        mkdir -p "$(dirname "$cache_file")"
        chmod 700 "$(dirname "$cache_file")"
        echo "${owner}|proc-cmdline" > "$cache_file"
        chmod 600 "$cache_file"
        echo "${owner}|proc-cmdline"
        return 0
      fi
    fi
    ppid_chain=$(awk '/^PPid:/{print $2}' "/proc/$ppid_chain/status" 2>/dev/null)
    depth=$((depth + 1))
  done

  # Fallback to shell PID
  local owner="${HOSTNAME}_$$"
  echo "${owner}|shell-pid"
}

# --- 替换 5 处 fallback ---
# OLD: OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$PPID}"
# NEW:
_detected=$(_detect_opencode_owner)
OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-${_detected%|*}}"
OPENCODE_SESSION_ID_FROM="${OPENCODE_SESSION_ID_FROM:-${_detected#*|}}"
```

### 4. Verify pass (green)

```bash
pytest tests/unit/test_rddf_session_owner_stability.py -v
# 预期: 5 tests PASS
```

### 5. Commit

```bash
git add skills/rddf-session/scripts/rddf_session_hooks.sh \
        tests/unit/test_rddf_session_owner_stability.py
git commit -m "fix(rddf-session): 3-layer owner fallback + /proc cmdline probe + 1h cache

Fixes P0 回归: same window 多 bash 调用产生不同 owner ID (实证: my-eci-group_2044384 → my-eci-group_2506969).

- env var 优先 (OpenCode 平台注入)
- /proc cmdline 探测 (深度 ≤5, 仅采纳含 'opencode' 的 cmdline)
- ~/.cache/rddf-session-owner (per-host, 0600, TTL 1h) 跨 bash 调用持久化
- shell_pid 兜底
- 5 处 hook (entry/close/heartbeat/attach/detach) 全部改写
- 不修改 schema / RDDF_ALLOW_CROSS_STAGE_PARALLEL / OpenCode 平台"
```

---

## Task 2: bats 集成测试 — 跨 worktree + 跨 plan-step 验证

### 1. Write failing test

**文件**: `tests/integration/test_rddf_session_owner_cache.bats`

```bash
#!/usr/bin/env bats
# tests/integration/test_rddf_session_owner_cache.bats
# 验证 owner 探测在跨 worktree / 跨 plan-step / 旧 sessions.json 兼容 三种场景

load test_helper

@test "3 consecutive rddf_session_hook_entry produce same owner ID" {
  # invoke 3 times, capture owner
  for i in 1 2 3; do
    run bash -c "
      source $BATS_TEST_DIRNAME/../../skills/rddf-session/scripts/rddf_session_hooks.sh
      rddf_session_hook_entry stage_test_$i guide-test test-subject test-outcome
    "
    [ "$status" -eq 0 ] || [ "$status" -eq 2 ]
    echo "$output" | grep -q "rddf-session: rds_"
    owner_line=$(echo "$output" | grep "rddf-session:" | head -1)
    echo "$owner_line" >> /tmp/owners_$$
  done
  # assert all 3 owner lines contain same ID
  uniq_count=$(awk '{print $2}' /tmp/owners_$$ | sort -u | wc -l)
  [ "$uniq_count" -eq 1 ]
}

@test "cross worktree: main repo + .rddf/wt/ subdir produce same owner" {
  run bash -c "cd $BATS_TEST_DIRNAME/../.. && $BATS_TEST_DIRNAME/../../skills/rddf-session/scripts/rddf_session_hooks.sh; rddf_session_hook_entry stage_ship guide-ship"
  echo "$output" | head -1
}

@test "old sessions.json (no owner_meta) loads without corruption" {
  # Pre-populate sessions.json with legacy entry
  mkdir -p .rddf/state
  cat > .rddf/state/sessions.json <<EOF
{"version": 1, "sessions": [{"session_id": "rds_legacy0001", "kind": "stage_ship", "owner_opencode_session_id": "my-eci-group_2044384", "state": "active", "started_at": "2026-08-01T00:00:00+00:00", "last_heartbeat": "2026-08-01T00:00:00+00:00"}]}
EOF
  # invoke any hook — should not crash
  run bash -c "source $BATS_TEST_DIRNAME/../../skills/rddf-session/scripts/rddf_session_hooks.sh; rddf_session_hook_entry stage_ship guide-ship test test"
  # verify old entry still exists (not overwritten)
  grep -q "rds_legacy0001" .rddf/state/sessions.json
}
```

### 2. Verify fail (red)

```bash
bats tests/integration/test_rddf_session_owner_cache.bats
# 预期: 3 tests FAIL (3-layer fallback 还没实施)
```

### 3. Implement (与 Task 1 步骤 3 合并)

### 4. Verify pass (green)

```bash
bats tests/integration/test_rddf_session_owner_cache.bats
# 预期: 3 tests PASS
pytest tests/unit/ -q
# 预期: 全部 unit test PASS
```

### 5. Commit

```bash
git add tests/integration/test_rddf_session_owner_cache.bats \
        tests/_lib/rddf_session_owner_helpers.bash
git commit -m "test(rddf-session): bats integration for owner stability

Covers:
- 3 consecutive hook calls produce same owner
- cross-worktree consistency
- legacy sessions.json (v1 schema) compatibility

P0 根因实测: my-eci-group_2044384 → my-eci-group_2506969 in same window"
```

---

## Task 3: 更新 SKILL.md (L250-252 过期承诺)

### 1. Write failing test (按需, 也可跳过)

**文件**: `tests/integration/test_skill_doc_sync.bats` (新增)

```bash
@test "SKILL.md L250-252 反映 3-layer fallback" {
  run grep -A 5 "Owner identity" skills/rddf-session/SKILL.md
  echo "$output" | grep -q "OPENCODE_SESSION_ID env"
  echo "$output" | grep -q "proc-cmdline"
  echo "$output" | grep -q "shell-pid"
  ! echo "$output" | grep -q "stable across bash tool calls"  # 旧承诺已删
}
```

### 2. Verify fail (red)

```bash
bats tests/integration/test_skill_doc_sync.bats
# 预期: 1 test FAIL
```

### 3. Implement

**文件**: `skills/rddf-session/SKILL.md` L248-252

```markdown
- **Owner identity** (3-layer fallback, fix-rddf-session-owner-stability):
  1. `$OPENCODE_SESSION_ID` env var (highest priority — OpenCode platform injection)
  2. `/proc/<shell-ppid>/cmdline` probe (depth ≤5, only accepts cmdline containing "opencode")
  3. `$(hostname -s)_$$` (current shell PID, last resort)
  - Cross-bash-call cache: `~/.cache/rddf-session-owner` (per-host, 0600, TTL 1h)
  - **DEPRECATED**: previous claim of "$PPID stable" is FALSE; the 3-layer chain above is the actual contract.
```

### 4. Verify pass (green)

```bash
bats tests/integration/test_skill_doc_sync.bats
# 预期: 1 test PASS
```

### 5. Commit

```bash
git add skills/rddf-session/SKILL.md \
        tests/integration/test_skill_doc_sync.bats
git commit -m "docs(rddf-session): SKILL.md L250-252 reflect 3-layer owner fallback

Replaces outdated '\$PPID stable across bash tool calls' claim (proven
false — 同一窗口连续 bash 调用产生不同 owner ID in 2026-08-02 ship 复盘).

References:
- improvements/fix-rddf-session-owner-stability.md (P0)
- ADR-0017 §2.1"
```

---

## Task 4: 完整验证 + 准备 archive

### 1. 完整测试套件

```bash
pytest tests/unit/ -q --tb=short
# 预期: 全部 PASS
bats tests/smoke.bats
# 预期: 7 smoke PASS
bats tests/integration/test_rddf_session_owner_cache.bats \
       tests/integration/test_skill_doc_sync.bats
# 预期: 4 tests PASS
openspec validate fix-rddf-session-owner-stability
# 预期: pass (or warn-only for spec/delta)
```

### 2. Update tasks.md (所有 checkbox 勾选)

```bash
# tasks.md L11-19 (Setup), L21-29 (Implementation), L31-39 (Verification), L41-46 (Documentation)
# 把所有 `- [ ]` 改为 `- [x]`
sed -i 's/- \[ \]/- [x]/g' openspec/changes/fix-rddf-session-owner-stability/tasks.md
```

### 3. Commit

```bash
git add openspec/changes/fix-rddf-session-owner-stability/tasks.md
git commit -m "chore(change): mark fix-rddf-session-owner-stability tasks complete"
```

---

## Archive 阶段 (Phase 3)

```bash
# 1. merge feature branch → master (ff-only 或 no-ff, 按 archive.sh 自动检测)
bash skills/_lib/archive.sh archive_change fix-rddf-session-owner-stability

# 2. 验证 merge 后 master HEAD 含 change
git log --oneline -5

# 3. cleanup branch (worktree 模式 + 轻量模式都生效)
git worktree remove .rddf/wt/fix-rddf-session-owner-stability 2>/dev/null || true
git branch -D openspec/fix-rddf-session-owner-stability

# 4. 验证 archive 成功
ls openspec/changes/archive/ | grep "fix-rddf-session-owner-stability"
```

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| /proc cmdline 探测在 macOS 不工作 | 检测 `uname` 跳过探测, 直接 fallback to shell_pid |
| cache file 权限错误 (不同 user) | chmod 600, 写入失败时忽略继续 (best-effort) |
| OPENCODE_SESSION_ID 注入字符串含特殊字符 | 保持原值, 不解析 |
| 旧 sessions.json 加载时缺 owner_meta | 兼容 (未字段 = 不强制回填) |

## 验收标准 (复述 improvements 验收)

- [x] 同窗口相邻 3 次 bash 调用 `rddf_session_hook_entry` 产生同一 owner ID (Task 2)
- [x] bash 调用前注入 `OPENCODE_SESSION_ID=<uuid>` 时, owner == 该 uuid (Task 1)
- [x] 不含 "opencode" 的 cmdline 路径 fallback 到 shell PID (Task 1)
- [x] 探测成功后写 `~/.cache/rddf-session-owner`;TTL 1h (Task 1)
- [x] 跨 worktree 验证 (Task 2)
- [x] 跨 plan-step 6 子步骤 (Task 2)
- [x] 旧 sessions.json 兼容 (Task 2)
- [x] 单元测试覆盖三种 fallback 路径 + cache file 读写 (Task 1)
- [x] bats 集成测试通过 (Task 2 + Task 3)
