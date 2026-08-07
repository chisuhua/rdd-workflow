# add-env-cache-arch-discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist auto-discovered third-party ADR/roadmap/architecture paths and pattern in `.rddf/state/.env-cache.json` so downstream consumers (`_read_arch_handoff_paths()` in `_lib/gate.py` + `_lib/loop/detectors.py`) prefer the cache over the hardcoded default — eliminating ~4 phase-entry re-scans per session in third-party projects with non-standard ADR conventions.

**Architecture:** Three independent layers, each with its own test:

1. **Cache writer layer** (`_lib/env_checks.sh::_cache_write` + `_emit_json`): extend 10 → 13 fields by appending 4 `discovered_*` keys. Atomic `.tmp` → `mv` write preserved. `env_check.sh` already calls `discover-arch-artifacts.sh::discover_adr_dir/roadmap/architecture_dir` — just needs to also call `discover_adr_pattern` (currently 3/4) and pipe the 4 globals into the writer.

2. **Read-side priority chain** (`_lib/gate.py::_read_arch_handoff_paths`): change priority from `[handoff → defaults]` to `[env-cache → handoff → defaults]` via 3-level `dict.get(field, default)` fallback. Backward-compatible for old 10-field cache files.

3. **Opt-out** (`SKIP_AUTO_DISCOVERY=yes`): check in `env_check.sh` BEFORE invoking `discover_all`; print `✅ Skip discovery (SKIP_AUTO_DISCOVERY=yes)` for visibility.

**Tech Stack:** bash 4+ (associative arrays, env-var passing), Python 3.11+ (`json` stdlib), bats-core 1.10+ for integration tests, pytest for unit tests.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-env-check/scripts/env_check.sh` | Add `discover_adr_pattern` invocation + `SKIP_AUTO_DISCOVERY` opt-out; pipe 4 discovered globals to writer |
| `_lib/env_checks.sh` | Extend `_cache_write` JSON from 10 → 13 fields (append-only); extend `_emit_json` accordingly; add 4 new keys without disturbing existing 10 |
| `_lib/gate.py` | Rewrite `_read_arch_handoff_paths` to 3-level `dict.get` fallback chain (env-cache → handoff → defaults) |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_env_check_arch_discovery.bats` | 5 scenarios: cache miss/hit/branch-switch/opt-out/backcompat |
| `tests/unit/test_gate_arch_handoff_paths.py` | 3 cases locking `_read_arch_handoff_paths` priority chain |

### Docs

| File | Responsibility |
|---|---|
| `skills/rdd-env-check/SKILL.md` | Update 10-field list → 13 fields; update boundary line to reflect new auto-discovery behavior |

---

## Task 1: Write failing test for env-cache 13-field write

**Files:**
- Create: `tests/integration/test_env_check_arch_discovery.bats`
- Modify: none (this task creates the file)

- [ ] **Step 1: Write the failing test for Scenario 1 (first-run discovery)**

```bash
#!/usr/bin/env bats
# tests/integration/test_env_check_arch_discovery.bats
#
# Tests for proposal add-env-cache-arch-discovery — verifies the .env-cache.json
# extension to 13 fields (10 + 4 discovered_*) and env-check auto-discovery behavior.
#
# Companion to skills/rdd-env-check/scripts/env_check.sh and _lib/env_checks.sh.

load test_helper

setup() {
  TEST_PROJECT_ROOT="$(mktemp -d)"
  cd "$TEST_PROJECT_ROOT" || return 1
  git init -q .
  git config user.email "test@test.local"
  git config user.name  "Test"
  mkdir -p documentation/decisions
  echo "# RFC-0001-test" > documentation/decisions/RFC-0001-test.md
  mkdir -p planning
  echo "# Roadmap" > planning/roadmap.md
}

teardown() {
  rm -rf "$TEST_PROJECT_ROOT"
}

@test "env-check: first run writes 13 fields including discovered_*":
  # GIVEN: third-party project with ADR at documentation/decisions + RFC-*.md
  # WHEN: env-check runs (cold cache)
  # THEN: .env-cache.json has 13 fields, discovered_adr_dir = documentation/decisions
  source "${TEST_PROJECT_ROOT}/skills/rdd-env-check/scripts/env_check.sh" 2>/dev/null || \
    source "${HOME}/.agents/skills/rdd-env-check/scripts/env_check.sh"
  cd "$TEST_PROJECT_ROOT"
  _run_env_full_check
  [ -f .rddf/state/.env-cache.json ]
  # 13 = 10 original + 4 discovered_*
  count=$(grep -oE '"[a-z_]+":"' .rddf/state/.env-cache.json | wc -l | tr -d '[:space:]')
  [ "$count" -eq 13 ]
  grep -q '"discovered_adr_dir":"documentation/decisions"' .rddf/state/.env-cache.json
  grep -q '"discovered_roadmap_path":"planning/roadmap.md"' .rddf/state/.env-cache.json
  grep -q '"discovered_adr_pattern":"RFC-\*.md"' .rddf/state/.env-cache.json
```

- [ ] **Step 2: Verify test fails (RED)**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_env_check_arch_discovery.bats 2>&1 | tail -20
```

Expected: **FAIL** with "no .env-cache.json" or wrong field count. Capture exact failure message to confirm RED state.

---

## Task 2: Implement env_check.sh: invoke discover_adr_pattern + SKIP_AUTO_DISCOVERY opt-out

**Files:**
- Modify: `skills/rdd-env-check/scripts/env_check.sh`

- [ ] **Step 1: Modify env_check.sh to capture the 4th discovered field + opt-out**

In the `_run_env_full_check` function body (around line 35-42), change:

```bash
  # ADR-0016 工件路径发现 (仅计数; 发现逻辑保留在 guide-arch, 本脚本不缓存发现结果)。
  local discovered_adr_dir="docs/adr" discovered_roadmap="roadmap.md" discovered_arch="docs/architecture"
  if [ -f "$_LIB_DIR/discover-arch-artifacts.sh" ]; then
    source "$_LIB_DIR/discover-arch-artifacts.sh" 2>/dev/null
    discovered_adr_dir=$(discover_adr_dir 2>/dev/null || echo "$discovered_adr_dir")
    discovered_roadmap=$(discover_roadmap 2>/dev/null || echo "$discovered_roadmap")
    discovered_arch=$(discover_architecture_dir 2>/dev/null || echo "$discovered_arch")
  fi
```

To:

```bash
  # ADR-0016 工件路径发现 (add-env-cache-arch-discovery proposal): 捕获 4 个 discovered_*
  # 写入 .env-cache.json,下游消费者 (_read_arch_handoff_paths) 优先读 cache。
  local discovered_adr_dir="docs/adr" discovered_roadmap="roadmap.md" discovered_arch="docs/architecture" discovered_pattern="ADR-*.md"
  if [ "${SKIP_AUTO_DISCOVERY:-no}" = "yes" ]; then
    echo "✅ Skip discovery (SKIP_AUTO_DISCOVERY=yes)"
  elif [ -f "$_LIB_DIR/discover-arch-artifacts.sh" ]; then
    source "$_LIB_DIR/discover-arch-artifacts.sh" 2>/dev/null
    discovered_adr_dir=$(discover_adr_dir 2>/dev/null || echo "$discovered_adr_dir")
    discovered_roadmap=$(discover_roadmap 2>/dev/null || echo "$discovered_roadmap")
    discovered_arch=$(discover_architecture_dir 2>/dev/null || echo "$discovered_arch")
    discovered_pattern=$(discover_adr_pattern 2>/dev/null || echo "$discovered_pattern")
  fi
  export DISCOVERED_ADR_DIR="$discovered_adr_dir"
  export DISCOVERED_ROADMAP_PATH="$discovered_roadmap"
  export DISCOVERED_ARCHITECTURE_DIR="$discovered_arch"
  export DISCOVERED_ADR_PATTERN="$discovered_pattern"
```

The 4 globals are exported for the next task to consume via env-var (Oracle C1 safe).

- [ ] **Step 2: Verify task 1 test now partially passes (ADR_DIR/ROADMAP/PATTERN captured)**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_env_check_arch_discovery.bats 2>&1 | tail -20
```

Expected: Still fail (cache_writer not extended yet) — discovery works, but `_cache_write` doesn't write the new fields. Confirm RED with the new field names in failure msg.

---

## Task 3: Extend `_lib/env_checks.sh::_cache_write` to 13 fields

**Files:**
- Modify: `_lib/env_checks.sh`

- [ ] **Step 1: Update `_cache_write` to write 13 fields (append-only)**

In `_cache_write` function (line 78-87), change the heredoc:

From:
```bash
  cat > "$tmp" <<EOF
{"timestamp":"$(date +%s)","ttl_s":"$ttl","branch":"$_CURRENT_BRANCH","openspec_ver":"$_OPENSPEC_VER","git_clean":"$_GIT_CLEAN","build_dir":"$_BUILD_DIR","adr_count":"$_ADR_COUNT","roadmap_exists":"$_ROADMAP_EXISTS","gap_count":"$_GAP_COUNT","active_changes":"$_ACTIVE_CHANGES"}
EOF
```

To:
```bash
  # add-env-cache-arch-discovery: 13 fields total (10 original + 4 discovered_*)
  # Backward-compat: missing env vars (old writer / SKIP_AUTO_DISCOVERY) → empty string.
  cat > "$tmp" <<EOF
{"timestamp":"$(date +%s)","ttl_s":"$ttl","branch":"$_CURRENT_BRANCH","openspec_ver":"$_OPENSPEC_VER","git_clean":"$_GIT_CLEAN","build_dir":"$_BUILD_DIR","adr_count":"$_ADR_COUNT","roadmap_exists":"$_ROADMAP_EXISTS","gap_count":"$_GAP_COUNT","active_changes":"$_ACTIVE_CHANGES","discovered_adr_dir":"${DISCOVERED_ADR_DIR:-}","discovered_roadmap_path":"${DISCOVERED_ROADMAP_PATH:-}","discovered_architecture_dir":"${DISCOVERED_ARCHITECTURE_DIR:-}","discovered_adr_pattern":"${DISCOVERED_ADR_PATTERN:-}"}
EOF
```

- [ ] **Step 2: Update `_emit_json` to emit 13 lines (parallel change)**

In `_emit_json` function (line 90-101), append 4 new echo lines after `active_changes`:

```bash
  echo "discovered_adr_dir: ${DISCOVERED_ADR_DIR:-}"
  echo "discovered_roadmap_path: ${DISCOVERED_ROADMAP_PATH:-}"
  echo "discovered_architecture_dir: ${DISCOVERED_ARCHITECTURE_DIR:-}"
  echo "discovered_adr_pattern: ${DISCOVERED_ADR_PATTERN:-}"
```

- [ ] **Step 3: Verify task 1 test passes (GREEN for Scenario 1)**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_env_check_arch_discovery.bats 2>&1 | tail -10
```

Expected: **PASS** (1/1). The 13-field write now succeeds.

---

## Task 4: Add remaining 4 bats scenarios (cache hit, branch switch, opt-out, backcompat)

**Files:**
- Modify: `tests/integration/test_env_check_arch_discovery.bats`

- [ ] **Step 1: Append 4 more `@test` blocks to the bats file**

```bash
@test "env-check: SKIP_AUTO_DISCOVERY=yes preserves old behavior":
  # GIVEN: opt-out env var set
  # WHEN: env-check runs
  # THEN: discovered_* fields are empty strings (not populated)
  cd "$TEST_PROJECT_ROOT"
  SKIP_AUTO_DISCOVERY=yes bash -c '
    source "${HOME}/.agents/skills/rdd-env-check/scripts/env_check.sh" 2>/dev/null
    _run_env_full_check
  '
  grep -q '"discovered_adr_dir":""' .rddf/state/.env-cache.json
  grep -q '"discovered_adr_pattern":""' .rddf/state/.env-cache.json
  ! grep -q '"discovered_adr_dir":"documentation/decisions"' .rddf/state/.env-cache.json

@test "env-check: cache hit avoids re-scan":
  # GIVEN: cache from previous run within TTL on same branch
  # WHEN: env-check runs again
  # THEN: no re-discovery needed (no subprocess for find/ls on ADR_DIR)
  cd "$TEST_PROJECT_ROOT"
  source "${HOME}/.agents/skills/rdd-env-check/scripts/env_check.sh"
  _run_env_full_check
  original_mtime=$(stat -c %Y .rddf/state/.env-cache.json)
  sleep 2
  _run_env_check_cached  # Should NOT re-write cache
  new_mtime=$(stat -c %Y .rddf/state/.env-cache.json)
  [ "$original_mtime" = "$new_mtime" ]

@test "env-check: branch switch invalidates cache":
  # GIVEN: cache on master, current branch differs
  # WHEN: env-check runs on new branch
  # THEN: cache re-written with new branch + fresh discovery
  cd "$TEST_PROJECT_ROOT"
  source "${HOME}/.agents/skills/rdd-env-check/scripts/env_check.sh"
  _run_env_full_check
  git checkout -b feature/test 2>/dev/null || git checkout feature/test 2>/dev/null
  _run_env_full_check
  grep -q '"branch":"feature/test"' .rddf/state/.env-cache.json

@test "env-check: old 10-field cache file is backward-compatible":
  # GIVEN: pre-existing .env-cache.json with only 10 fields (no discovered_*)
  # WHEN: _read_arch_handoff_paths reads it
  # THEN: returns hardcoded defaults for missing fields (no exception)
  cd "$TEST_PROJECT_ROOT"
  cat > .rddf/state/.env-cache.json <<'EOF'
{"timestamp":"1700000000","ttl_s":"3600","branch":"master","openspec_ver":"1.4.1","git_clean":"0","build_dir":"node_modules","adr_count":"5","roadmap_exists":"yes","gap_count":"0","active_changes":"1"}
EOF
  python3 -c "
import sys, os
sys.path.insert(0, '${HOME}/.agents/skills')
from _lib.gate import _read_arch_handoff_paths
result = _read_arch_handoff_paths('$TEST_PROJECT_ROOT')
assert result['adr_dir'] == 'docs/adr', f'expected docs/adr default, got {result[\"adr_dir\"]}'
assert result['adr_pattern'] == 'ADR-*.md', f'expected ADR-*.md default, got {result[\"adr_pattern\"]}'
print('OK: backward-compat fallback works')
"
```

- [ ] **Step 2: Run all 5 tests**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_env_check_arch_discovery.bats 2>&1 | tail -10
```

Expected: **5/5 PASS**.

---

## Task 5: Write failing Python unit test for `_read_arch_handoff_paths` priority

**Files:**
- Create: `tests/unit/test_gate_arch_handoff_paths.py`

- [ ] **Step 1: Write 3 cases locking priority chain**

```python
"""Tests for skills/_lib/gate.py::_read_arch_handoff_paths priority chain.

Verifies the 3-level fallback: env-cache (13 fields) > handoff > hardcoded defaults.
Locks behavior for backward-compat with old 10-field cache files.
"""
import json
import os
from pathlib import Path

from skills._lib.gate import _read_arch_handoff_paths


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_env_cache_hits_first_when_discovered_fields_present(tmp_path):
    """When env-cache has discovered_*, those values win over handoff."""
    rddf = tmp_path / ".rddf" / "state"
    rddf.mkdir(parents=True)

    # env-cache: discovered_* present
    _write_json(rddf / ".env-cache.json", {
        "discovered_adr_dir": "documentation/decisions",
        "discovered_roadmap_path": "planning/roadmap.md",
        "discovered_architecture_dir": "docs/arch",
        "discovered_adr_pattern": "RFC-*.md",
    })
    # handoff: DIFFERENT values
    _write_json(rddf / ".arch-handoff.json", {
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
    })

    result = _read_arch_handoff_paths(str(tmp_path))
    assert result["adr_dir"] == "documentation/decisions"
    assert result["roadmap_path"] == "planning/roadmap.md"
    assert result["architecture_dir"] == "docs/arch"
    assert result["adr_pattern"] == "RFC-*.md"


def test_handoff_hits_when_env_cache_missing_discovered_fields(tmp_path):
    """When env-cache lacks discovered_* (old 10-field), fall back to handoff."""
    rddf = tmp_path / ".rddf" / "state"
    rddf.mkdir(parents=True)

    # env-cache: 10 fields only (legacy format)
    _write_json(rddf / ".env-cache.json", {
        "timestamp": "1700000000", "branch": "master",
    })
    _write_json(rddf / ".arch-handoff.json", {
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
    })

    result = _read_arch_handoff_paths(str(tmp_path))
    assert result["adr_dir"] == "docs/adr"
    assert result["roadmap_path"] == "roadmap.md"
    assert result["adr_pattern"] == "ADR-*.md"


def test_default_hits_when_neither_cache_nor_handoff_present(tmp_path):
    """When both env-cache and handoff are missing, return hardcoded defaults."""
    result = _read_arch_handoff_paths(str(tmp_path))
    assert result["adr_dir"] == "docs/adr"
    assert result["roadmap_path"] == "roadmap.md"
    assert result["architecture_dir"] == "docs/architecture"
    assert result["adr_pattern"] == "ADR-*.md"
```

- [ ] **Step 2: Verify test fails (RED)**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_gate_arch_handoff_paths.py -q --tb=short 2>&1 | tail -20
```

Expected: **3 FAIL** (current `_read_arch_handoff_paths` only reads handoff, not env-cache).

---

## Task 6: Implement `_read_arch_handoff_paths` priority chain

**Files:**
- Modify: `_lib/gate.py`

- [ ] **Step 1: Replace `_read_arch_handoff_paths` with 3-level fallback**

Find `_read_arch_handoff_paths` in `_lib/gate.py` (around line 76-104). Replace the body:

From (current implementation):
```python
def _read_arch_handoff_paths(project_root: str) -> dict:
    """Read .arch-handoff.json with fallback to v2.0 defaults.

    ADR-0016 Layer 3. Returns dict with keys: adr_dir, roadmap_path,
    architecture_dir, adr_pattern. All paths relative to project_root.
    """
    handoff_path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
    if not handoff_path.exists():
        return {
            "adr_dir": _DEFAULT_ADR_DIR,
            "roadmap_path": _DEFAULT_ROADMAP_PATH,
            "architecture_dir": _DEFAULT_ARCHITECTURE_DIR,
            "adr_pattern": _DEFAULT_ADR_PATTERN,
        }
    try:
        data = json.loads(handoff_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {
            "adr_dir": _DEFAULT_ADR_DIR,
            "roadmap_path": _DEFAULT_ROADMAP_PATH,
            "architecture_dir": _DEFAULT_ARCHITECTURE_DIR,
            "adr_pattern": _DEFAULT_ADR_PATTERN,
        }
    return {
        "adr_dir": data.get("adr_dir", _DEFAULT_ADR_DIR),
        "roadmap_path": data.get("roadmap_path", _DEFAULT_ROADMAP_PATH),
        "architecture_dir": data.get("architecture_dir", _DEFAULT_ARCHITECTURE_DIR),
        "adr_pattern": data.get("adr_pattern", _DEFAULT_ADR_PATTERN),
    }
```

To:
```python
def _read_arch_handoff_paths(project_root: str) -> dict:
    """Read paths from env-cache → handoff → defaults (3-level fallback).

    ADR-0016 Layer 3 + add-env-cache-arch-discovery extension.
    Priority chain:
      1. .rddf/state/.env-cache.json "discovered_*" fields (auto-discovered by rdd-env-check)
      2. .rddf/state/.arch-handoff.json (arch-done contract)
      3. Hardcoded v2.0 defaults

    Backward-compat: env-cache files lacking discovered_* fall through to handoff.
    Empty-string discovered_* fields are treated as missing → fall through.
    Returns dict with keys: adr_dir, roadmap_path, architecture_dir, adr_pattern.
    """
    pr = Path(project_root)
    env_cache = pr / ".rddf" / "state" / ".env-cache.json"
    handoff = pr / ".rddf" / "state" / ".arch-handoff.json"

    def _from_env_cache() -> dict | None:
        if not env_cache.exists():
            return None
        try:
            data = json.loads(env_cache.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        # Read discovered_* fields; treat empty/missing as "no value here"
        result = {}
        for cache_key, out_key in (
            ("discovered_adr_dir", "adr_dir"),
            ("discovered_roadmap_path", "roadmap_path"),
            ("discovered_architecture_dir", "architecture_dir"),
            ("discovered_adr_pattern", "adr_pattern"),
        ):
            val = data.get(cache_key, "")
            if val:  # non-empty string
                result[out_key] = val
        return result or None  # None if no discovered_* fields at all

    def _from_handoff() -> dict | None:
        if not handoff.exists():
            return None
        try:
            data = json.loads(handoff.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        return {
            "adr_dir": data.get("adr_dir", _DEFAULT_ADR_DIR),
            "roadmap_path": data.get("roadmap_path", _DEFAULT_ROADMAP_PATH),
            "architecture_dir": data.get("architecture_dir", _DEFAULT_ARCHITECTURE_DIR),
            "adr_pattern": data.get("adr_pattern", _DEFAULT_ADR_PATTERN),
        }

    env_vals = _from_env_cache()
    handoff_vals = _from_handoff()
    defaults = {
        "adr_dir": _DEFAULT_ADR_DIR,
        "roadmap_path": _DEFAULT_ROADMAP_PATH,
        "architecture_dir": _DEFAULT_ARCHITECTURE_DIR,
        "adr_pattern": _DEFAULT_ADR_PATTERN,
    }

    # Priority: env-cache wins per-field; missing → handoff → defaults
    return {
        k: (env_vals or {}).get(k) or (handoff_vals or {}).get(k) or defaults[k]
        for k in defaults
    }
```

- [ ] **Step 2: Verify task 5 test passes (GREEN)**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_gate_arch_handoff_paths.py -q --tb=short 2>&1 | tail -10
```

Expected: **3/3 PASS**.

---

## Task 7: Update SKILL.md (docs sync)

**Files:**
- Modify: `skills/rdd-env-check/SKILL.md`

- [ ] **Step 1: Update 10-field list to 13 fields**

Find the line:
```
- 固定 10 字段: `timestamp` `ttl_s` `branch` `openspec_ver` `git_clean` `build_dir` `adr_count` `roadmap_exists` `gap_count` `active_changes`
```

Replace with:
```
- 固定 13 字段: `timestamp` `ttl_s` `branch` `openspec_ver` `git_clean` `build_dir` `adr_count` `roadmap_exists` `gap_count` `active_changes` `discovered_adr_dir` `discovered_roadmap_path` `discovered_architecture_dir` `discovered_adr_pattern`
```

- [ ] **Step 2: Update boundary line**

Find the line:
```
- 不缓存 ADR-0016 工件发现 (discover-arch-artifacts.sh 由 guide-arch 每次运行)
```

Replace with:
```
- 自动缓存 ADR-0016 工件发现到 `discovered_*` 字段（opt-out via `SKIP_AUTO_DISCOVERY=yes`）
```

---

## Task 8: Run full test suite for regression

**Files:** none

- [ ] **Step 1: Quick mode (bats smoke + pytest unit, ~75s)**

```bash
cd /workspace/project/rdd-workflow
./test.sh --quick 2>&1 | tail -30
```

Expected: all green (no new failures introduced).

- [ ] **Step 2: Targeted regression check (per add-full-regression-gate)**

```bash
cd /workspace/project/rdd-workflow
./test.sh --full --regression 2>&1 | tail -30
```

Expected: all green or only KNOWN_FAILURES baseline failures. Any new failure = regression introduced by this change → fix and re-run.

- [ ] **Step 3: Manual third-party simulation**

```bash
TMP=$(mktemp -d)
cd "$TMP"
git init -q .
mkdir -p documentation/decisions
echo "# RFC-0001-foo" > documentation/decisions/RFC-0001-foo.md
SKILL_ROOT="$HOME/.agents/skills"
SKIP_ARCH_HANDOFF=yes bash -c "
  source '${SKILL_ROOT}/rdd-env-check/scripts/env_check.sh'
  _run_env_full_check
  cat .rddf/state/.env-cache.json
"
echo "expected discovered_adr_dir = documentation/decisions"
echo "expected discovered_adr_pattern = RFC-*.md"
cd / && rm -rf "$TMP"
```

---

## Task 9: Aggregate commit on branch

- [ ] **Step 1: Stage and commit (worktree commit flow, single commit per change)**

```bash
cd /workspace/project/rdd-workflow
git add -A
git status --short
git commit -m "feat(env-check): auto-cache ADR-0016 discoveries on env-check (P2)

- skills/rdd-env-check/scripts/env_check.sh: capture 4th discovered_* via
  discover_adr_pattern; respect SKIP_AUTO_DISCOVERY=yes opt-out; export
  4 globals via env-var pattern (Oracle C1 safe)
- _lib/env_checks.sh: extend _cache_write and _emit_json from 10 → 13 fields
  (pure append, zero behavior change for existing consumers)
- _lib/gate.py::_read_arch_handoff_paths: 3-level fallback
  env-cache > handoff > defaults; backward-compat with old 10-field cache
  files via dict.get fallback
- skills/rdd-env-check/SKILL.md: 10-field list → 13 fields; boundary line
  updated to reflect auto-discovery behavior
- tests/integration/test_env_check_arch_discovery.bats: 5 scenarios
  (cache miss/hit/branch-switch/opt-out/backcompat)
- tests/unit/test_gate_arch_handoff_paths.py: 3 cases locking priority chain

Refs: improvements/add-env-cache-arch-discovery (proposal-approved P2)"
git log -1 --oneline
```

- [ ] **Step 2: Verify single commit on branch**

```bash
git log master..HEAD --oneline
```

Expected: exactly 1 commit.

---

## Task 10: Archive change (Phase 3 — merge + openspec archive)

- [ ] **Step 1: Switch to master, merge branch**

```bash
cd /workspace/project/rdd-workflow
git checkout master
git merge --no-ff openspec/add-env-cache-arch-discovery -m "merge: add-env-cache-arch-discovery (P2)"
```

- [ ] **Step 2: Archive via openspec CLI**

```bash
cd /workspace/project/rdd-workflow
openspec archive add-env-cache-arch-discovery --yes 2>&1 | tail -20
```

Expected: change moves to `openspec/changes/archive/YYYY-MM-DD-add-env-cache-arch-discovery/`.

- [ ] **Step 3: Cleanup branch**

```bash
cd /workspace/project/rdd-workflow
git branch -d openspec/add-env-cache-arch-discovery
git log --oneline -3
```

- [ ] **Step 4: Mark proposal completed**

The `mark_approved_completed` helper should auto-trigger when the change moves to `archive/`. Verify:

```bash
cd /workspace/project/rdd-workflow
grep "add-env-cache-arch-discovery" proposal-approved.md
```

Expected: entry moved to `## 已实施` section.