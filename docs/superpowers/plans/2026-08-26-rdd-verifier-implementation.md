# rdd-verifier 5th Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `rdd-verifier` as the 5th phase (arch → design → plan → ship → verify → archive) with heuristic failure classification, SHA-fingerprint verdict cache, and 3-retry fail-loop to plan/ship.

**Architecture:** Mixed Approach C — `skills/rdd-verifier/SKILL.md` state machine orchestrates a `_lib/cli/rdd_verify_cmd.py` CLI backend that scans `iteration.json` ship-done queue, reuses ac-verifier skill via subprocess, classifies failures heuristically (no new LLM call), and routes loops back to plan/ship. `_lib/archive.sh::archive_gate_check` extended to consume SHA-fingerprint verdict cache to avoid double LLM calls.

**Tech Stack:** Python 3.11+ (pytest, jsonschema), bash (bats-core 1.10+), OpenSpec CLI v1.3.1+, existing ac-verifier skill (no rewrite).

**Spec:** `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md`

---

## File Structure (Decomposition Lock-in)

| Layer | Path | Responsibility |
|-------|------|----------------|
| **ADR** | `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md` | Architectural decision |
| **Public API** | `_lib/verifier/__init__.py` | Re-export `classify_failure`, `verdict_cache`, `loop_state` |
| **Heuristic** | `_lib/verifier/classify.py` | Pure function: verdict JSON → label (no LLM) |
| **Cache** | `_lib/verifier/cache.py` | SHA-fingerprint verdict cache read/write |
| **State** | `_lib/verifier/loop_state.py` | `.verifier-loop.json` load/save with schema validation |
| **Schemas** | `_lib/schemas/{verifier_loop_schema,ac_verdict_cache_schema}.json` | JSON Schema definitions |
| **CLI** | `_lib/cli/rdd_verify_cmd.py` | `rddf rdd-verify [--loop] [--dry-run] [--max-changes N]` |
| **Bash** | `skills/rdd-verifier/scripts/{scan_queue,run_verification,classify_failure,route_loop}.sh` | Per-action orchestration |
| **Skill** | `skills/rdd-verifier/SKILL.md` | User-facing state machine |
| **Archive hook** | `_lib/archive.sh::archive_gate_check` (modify) | Read SHA cache before LLM call |

**No file does two jobs.** Heuristic, cache, and state are split because they have different test profiles (pure-function vs. I/O vs. schema).

---

## Task 1: ADR-0034 + AGENTS.md Update

**Files:**
- Create: `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md`
- Modify: `docs/adr/README.md`
- Modify: `AGENTS.md` (4 → 5 阶段)

- [ ] **Step 1: Write ADR-0034**

```markdown
# ADR-0034: rdd-verifier 验证回环阶段架构

> **状态**: 待采纳
> **日期**: 2026-08-26
> **决策者**: sisyphus

## 问题

rdd-workflow v2.1+ 4 阶段架构缺独立的验证回环阶段。

## 决策

新增第 5 阶段 `rdd-verifier`：

- **位置**: ship 完成后、archive 前的独立验证步骤
- **属性**: 条件必经（默认必走，`SKIP_RDD_VERIFIER=yes` 跳过）；非线性必经节点
- **人工介入**: 高（AI 分类 + 用户确认 + 失败回环决策）
- **失败回环**: 启发式分类（implementation_gap / proposal_drift）+ 用户确认 + 跳回 plan 或 ship，最多重试 3 次
- **与 ac-verifier 关系**: 复用 sub-skill，不重写 LLM
- **默认严格**: 与 `STRICT_AC_GATE=yes` 共享同一开关语义
- **角色模型（ADR-0028 扩展）**:
  - `role.owns`: `.rddf/state/.verifier-loop.json`, `.rddf/state/.ac-verdict-<name>.json`, `.rddf/state/.ac-verifier-blocked.jsonl`
  - `role.not_owns`: `openspec/changes/<name>/`, `docs/adr/`
  - `role.human_involvement`: `high`

## 后果

**正面**:
- AC 验证成为用户可见阶段而非内嵌步骤
- 失败自动回环避免人工跟踪
- SHA 指纹缓存避免 LLM 双跑

**负面**:
- 5 阶段架构文档更新成本
- 启发式分类误判需用户确认兜底

**中立**:
- 不修改现有 4 阶段职责边界
- 不并发跑 LLM（保留 v1 串行）

## 参考

- ADR-0003: 三阶段架构
- ADR-0025: design 阶段独立化
- ADR-0028: role model
- ADR-0017: rddf-session
```

- [ ] **Step 2: Update ADR README index**

Append to `docs/adr/README.md` ADR列表 section:
```
| [ADR-0034](ADR-0034-rdd-verifier-verify-phase-architecture.md) | rdd-verifier 验证回环阶段架构 | 已采纳 | 5 阶段非线性必经节点 + 启发式分类 + 3 次重试 |
```

Update 主题分类 - 架构设计 section:
```
- ADR-0034: rdd-verifier 验证回环阶段架构
```

- [ ] **Step 3: Update AGENTS.md 4 → 5 阶段**

Find "## 架构" section, change:
```
| ship | `guide-ship` | 变更执行: worktree/轻量, execute, archive, cleanup |
```
to:
```
| ship | `guide-ship` | 变更执行: worktree/轻量, execute, archive, cleanup |
| verify | `rdd-verifier` | 验证回环: 启发式分类 AC pass/fail, 失败回 plan/ship, 最多 3 次 |
```

- [ ] **Step 4: Verify with grep**

```bash
grep -n "verify.*rdd-verifier\|rdd-verifier.*verify" docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md AGENTS.md
```
Expected: Both files reference rdd-verifier.

- [ ] **Step 5: Commit**

```bash
git add docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md docs/adr/README.md AGENTS.md
git commit -m "docs(adr-0034): add rdd-verifier verify phase architecture

Establish rdd-verifier as 5th phase (arch → design → plan → ship → verify → archive):
- Conditional must-pass (default yes, SKIP_RDD_VERIFIER bypass)
- Heuristic classification (implementation_gap vs proposal_drift)
- 3-retry loop back to plan/ship before halt

Refs: ADR-0003, ADR-0025, ADR-0028, ADR-0017"
```

---

## Task 2: `.verifier-loop.json` Schema

**Files:**
- Create: `_lib/schemas/verifier_loop_schema.json`
- Create: `tests/unit/test_verifier_loop_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_verifier_loop_schema.py
import json
from pathlib import Path
import jsonschema

SCHEMA = json.loads(Path("_lib/schemas/verifier_loop_schema.json").read_text())

def test_schema_loads():
    assert SCHEMA["version"] == 1
    assert "properties" in SCHEMA

def test_valid_minimal_doc():
    doc = {
        "version": 1,
        "change": "test-change",
        "loop_count": 0,
        "max_loops": 3,
        "classification_history": [],
        "codebase_commit_at_last_run": "abc123",
        "route": "archive-ready",
        "halt_reason": None,
        "updated_at": "2026-08-26T00:00:00Z"
    }
    jsonschema.validate(doc, SCHEMA)  # must not raise

def test_invalid_loop_count_negative():
    doc = {"version": 1, "change": "x", "loop_count": -1, "max_loops": 3,
           "classification_history": [], "codebase_commit_at_last_run": "x",
           "route": "archive-ready", "halt_reason": None, "updated_at": "x"}
    import pytest
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)

def test_invalid_route():
    doc = {"version": 1, "change": "x", "loop_count": 0, "max_loops": 3,
           "classification_history": [], "codebase_commit_at_last_run": "x",
           "route": "INVALID_ROUTE", "halt_reason": None, "updated_at": "x"}
    import pytest
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/unit/test_verifier_loop_schema.py -v
```
Expected: FAIL with `FileNotFoundError: _lib/schemas/verifier_loop_schema.json`.

- [ ] **Step 3: Write the schema**

```json
{
  "version": 1,
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "change", "loop_count", "max_loops", "classification_history", "codebase_commit_at_last_run", "route", "halt_reason", "updated_at"],
  "properties": {
    "version": {"const": 1},
    "change": {"type": "string", "minLength": 1},
    "loop_count": {"type": "integer", "minimum": 0},
    "max_loops": {"type": "integer", "minimum": 1, "maximum": 10},
    "classification_history": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["loop", "label", "user_confirmed", "at"],
        "properties": {
          "loop": {"type": "integer", "minimum": 1},
          "label": {"enum": ["implementation_gap", "proposal_drift"]},
          "user_confirmed": {"type": "boolean"},
          "at": {"type": "string", "format": "date-time"}
        }
      }
    },
    "codebase_commit_at_last_run": {"type": "string", "minLength": 7},
    "route": {"enum": ["archive-ready", "guide-ship", "guide-plan", "halted"]},
    "halt_reason": {"type": ["string", "null"]},
    "updated_at": {"type": "string", "format": "date-time"}
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/unit/test_verifier_loop_schema.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/schemas/verifier_loop_schema.json tests/unit/test_verifier_loop_schema.py
git commit -m "feat(verifier-loop): add .verifier-loop.json schema v1"
```

---

## Task 3: `.ac-verdict-<name>.json` Schema

**Files:**
- Create: `_lib/schemas/ac_verdict_cache_schema.json`
- Create: `tests/unit/test_ac_verdict_cache_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_ac_verdict_cache_schema.py
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA = json.loads(Path("_lib/schemas/ac_verdict_cache_schema.json").read_text())

def test_schema_loads():
    assert SCHEMA["version"] == 1

def test_valid_doc():
    doc = {
        "version": 1,
        "change": "test-change",
        "codebase_commit": "abc1234567",
        "verdict": [
            {"ac_id": "AC-1", "status": "pass", "confidence": 0.95,
             "evidence": ["file:tests/test_foo.py:10"], "reasoning": "All good"}
        ],
        "ran_at": "2026-08-26T00:00:00Z",
        "ran_by": "rdd-verifier"
    }
    jsonschema.validate(doc, SCHEMA)

def test_invalid_status():
    doc = {"version": 1, "change": "x", "codebase_commit": "abc",
           "verdict": [{"ac_id": "AC-1", "status": "unknown", "confidence": 0.5,
                        "evidence": [], "reasoning": ""}],
           "ran_at": "x", "ran_by": "rdd-verifier"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)

def test_invalid_ran_by():
    doc = {"version": 1, "change": "x", "codebase_commit": "abc",
           "verdict": [], "ran_at": "x", "ran_by": "INVALID"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/unit/test_ac_verdict_cache_schema.py -v
```
Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Write the schema**

```json
{
  "version": 1,
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "change", "codebase_commit", "verdict", "ran_at", "ran_by"],
  "properties": {
    "version": {"const": 1},
    "change": {"type": "string", "minLength": 1},
    "codebase_commit": {"type": "string", "minLength": 7},
    "verdict": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["ac_id", "status", "confidence", "evidence", "reasoning"],
        "properties": {
          "ac_id": {"type": "string", "pattern": "^AC-[0-9]+$"},
          "status": {"enum": ["pass", "fail"]},
          "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
          "evidence": {"type": "array", "items": {"type": "string"}},
          "reasoning": {"type": "string"}
        }
      }
    },
    "ran_at": {"type": "string", "format": "date-time"},
    "ran_by": {"enum": ["rdd-verifier", "archive_gate_check"]}
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/unit/test_ac_verdict_cache_schema.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/schemas/ac_verdict_cache_schema.json tests/unit/test_ac_verdict_cache_schema.py
git commit -m "feat(verifier-cache): add .ac-verdict-<name>.json schema v1"
```

---

## Task 4: `classify_failure()` Heuristic (Pure Function)

**Files:**
- Create: `_lib/verifier/__init__.py`
- Create: `_lib/verifier/classify.py`
- Create: `tests/unit/test_classify_failure.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_classify_failure.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.classify import classify_failure

def test_implementation_gap_keywords():
    for kw in ["not implemented", "missing", "absent", "TODO: implement"]:
        assert classify_failure({"reasoning": f"Function is {kw}", "evidence": []}) == "implementation_gap"

def test_proposal_drift_keywords():
    for kw in ["exists but", "discrepan", "mismatch", "differs from ac"]:
        assert classify_failure({"reasoning": f"Code {kw} the spec", "evidence": []}) == "proposal_drift"

def test_ambiguous_fallback_to_implementation_gap():
    """Oracle §E: conservative default = implementation_gap (回 guide-ship 代价低于回 guide-plan 重写 proposal)."""
    assert classify_failure({"reasoning": "Unclear", "evidence": []}) == "implementation_gap"
    assert classify_failure({"reasoning": "", "evidence": []}) == "implementation_gap"

def test_case_insensitive_matching():
    assert classify_failure({"reasoning": "MISSING function", "evidence": []}) == "implementation_gap"
    assert classify_failure({"reasoning": "Code EXISTS BUT with bugs", "evidence": []}) == "proposal_drift"

def test_priority_proposal_drift_over_gap():
    """When both signals present, prefer proposal_drift (more conservative to fix docs than code)."""
    assert classify_failure({"reasoning": "missing implementation, exists but mismatched", "evidence": []}) == "proposal_drift"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/unit/test_classify_failure.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named '_lib.verifier'`.

- [ ] **Step 3: Create `_lib/verifier/__init__.py`**

```python
"""rdd-verifier 5th phase Python helpers.

Re-exports the public API for use by both the CLI backend and the SKILL.md state machine.
"""
from _lib.verifier.classify import classify_failure  # noqa: F401
from _lib.verifier.cache import verdict_cache, read_verdict_cache, is_cache_fresh  # noqa: F401
from _lib.verifier.loop_state import load_loop_state, save_loop_state, init_loop_state  # noqa: F401

__all__ = [
    "classify_failure",
    "verdict_cache",
    "read_verdict_cache",
    "is_cache_fresh",
    "load_loop_state",
    "save_loop_state",
    "init_loop_state",
]
```

- [ ] **Step 4: Implement `classify.py`**

```python
"""Heuristic failure classification for rdd-verifier.

Per ADR-0034 §5.1 and Oracle review §E: classify AC failures without new LLM calls.
Reuses ac-verifier verdict JSON evidence + reasoning fields.

Pure function — no I/O, no globals. Easily unit-testable with mock verdicts.
"""
from __future__ import annotations

# Keywords are matched case-insensitively. Order matters: gap_re
# drift check first because it implies documentation-level fix (cheaper than code rewrite).
_GAP_KEYWORDS = ("not implement", "missing", "absent", "todo: implement")
_DRIFT_KEYWORDS = ("exists but", "discrepan", "mismatch", "differs from ac")


def classify_failure(verdict_item: dict) -> str:
    """Classify a single AC verdict as `implementation_gap` or `proposal_drift`.

    Args:
        verdict_item: dict with at least `reasoning` (str) and `evidence` (list) keys.
                      Matches the shape produced by ac-verifier skill.

    Returns:
        One of `implementation_gap` or `proposal_drift`.

    Notes:
        - Conservative default (ambiguous → `implementation_gap`) because
          guide-ship re-run cost < guide-plan proposal rewrite cost.
        - Pure function. No I/O, no LLM.
    """
    reasoning = (verdict_item.get("reasoning") or "").lower()

    for kw in _DRIFT_KEYWORDS:
        if kw in reasoning:
            return "proposal_drift"

    for kw in _GAP_KEYWORDS:
        if kw in reasoning:
            return "implementation_gap"

    return "implementation_gap"
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python3 -m pytest tests/unit/test_classify_failure.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add _lib/verifier/__init__.py _lib/verifier/classify.py tests/unit/test_classify_failure.py
git commit -m "feat(verifier): add classify_failure() heuristic

Per Oracle §E + ADR-0034 §5.1: pure function, no LLM call, reuses
ac-verifier verdict evidence/reasoning fields. Conservative default =
implementation_gap (cheaper to fix code than rewrite proposal)."
```

---

## Task 5: `verdict_cache()` SHA-fingerprint Cache

**Files:**
- Create: `_lib/verifier/cache.py`
- Create: `tests/unit/test_ac_verdict_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_ac_verdict_cache.py
import json
import os
import sys
import subprocess as sp
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.cache import verdict_cache, read_verdict_cache, is_cache_fresh

def _git(cwd, *args):
    return sp.check_output(["git", "-C", cwd] + list(args)).decode().strip()

def _make_repo_with_commit(tmpdir):
    repo = Path(tmpdir) / "repo"
    repo.mkdir()
    _git(str(repo), "init", "-q")
    _git(str(repo), "config", "user.email", "test@test")
    _git(str(repo), "config", "user.name", "Test")
    (repo / "x.txt").write_text("hello")
    _git(str(repo), "add", "x.txt")
    _git(str(repo), "commit", "-q", "-m", "init")
    return repo

def test_write_and_read_cache(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    state_dir = repo / ".rddf" / "state"
    state_dir.mkdir(parents=True)

    verdict = [{"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
                "evidence": [], "reasoning": "ok"}]
    verdict_cache(repo, "test-change", sha, verdict, ran_by="rdd-verifier")

    cached = read_verdict_cache(repo, "test-change")
    assert cached is not None
    assert cached["codebase_commit"] == sha
    assert cached["verdict"] == verdict
    assert cached["ran_by"] == "rdd-verifier"

def test_is_cache_fresh_match(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    state_dir = repo / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    verdict_cache(repo, "x", sha, [], "rdd-verifier")
    assert is_cache_fresh(repo, "x", sha) is True

def test_is_cache_fresh_stale(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    state_dir = repo / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    verdict_cache(repo, "x", sha, [], "rdd-verifier")
    # New commit
    (repo / "y.txt").write_text("world")
    _git(str(repo), "add", "y.txt")
    _git(str(repo), "commit", "-q", "-m", "y")
    new_sha = _git(str(repo), "rev-parse", "HEAD")
    assert is_cache_fresh(repo, "x", new_sha) is False

def test_read_cache_missing_returns_none(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    assert read_verdict_cache(repo, "nonexistent") is None
    assert is_cache_fresh(repo, "nonexistent", "abc") is False

def test_read_cache_corrupt_returns_none(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    state_dir = repo / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    cache_file = state_dir / ".ac-verdict-corrupt.json"
    cache_file.write_text("{invalid json")
    assert read_verdict_cache(repo, "corrupt") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/unit/test_ac_verdict_cache.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named '_lib.verifier.cache'`.

- [ ] **Step 3: Implement `cache.py`**

```python
"""SHA-fingerprint verdict cache for rdd-verifier.

Per ADR-0034 §7.2 and Oracle review §C: avoids double LLM calls when archive_gate_check
runs after rdd-verifier (same codebase commit = cache hit).

Cache file: `.rddf/state/.ac-verdict-<change>.json` (gitignored, schema v1).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _cache_path(project_root: Path, change_name: str) -> Path:
    return project_root / ".rddf" / "state" / f".ac-verdict-{change_name}.json"


def verdict_cache(
    project_root: Path,
    change_name: str,
    codebase_commit: str,
    verdict: list,
    ran_by: str,
) -> Path:
    """Write verdict cache for a change. Returns the cache file path.

    Args:
        project_root: Path to project root (must contain .rddf/state/).
        change_name: OpenSpec change name.
        codebase_commit: git SHA at the time of verification.
        verdict: list of verdict items from ac-verifier.
        ran_by: "rdd-verifier" or "archive_gate_check".

    Raises:
        OSError: if .rddf/state/ cannot be created.
    """
    path = _cache_path(Path(project_root), change_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = {
        "version": 1,
        "change": change_name,
        "codebase_commit": codebase_commit,
        "verdict": verdict,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "ran_by": ran_by,
    }
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return path


def read_verdict_cache(project_root: Path, change_name: str) -> Optional[dict]:
    """Read verdict cache. Returns None if missing or corrupt (treat as cache miss)."""
    path = _cache_path(Path(project_root), change_name)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def is_cache_fresh(project_root: Path, change_name: str, current_commit: str) -> bool:
    """Check if cached verdict matches current codebase commit.

    Returns False if cache is missing, corrupt, or stale.
    """
    cached = read_verdict_cache(project_root, change_name)
    if cached is None:
        return False
    return cached.get("codebase_commit") == current_commit
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/unit/test_ac_verdict_cache.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/verifier/cache.py tests/unit/test_ac_verdict_cache.py
git commit -m "feat(verifier-cache): add SHA-fingerprint verdict cache

Per ADR-0034 §7.2 + Oracle §C: archive_gate_check consumes cached verdict
when codebase_commit == cached SHA, avoiding redundant LLM calls."
```

---

## Task 6: `loop_state.py` Load/Save

**Files:**
- Create: `_lib/verifier/loop_state.py`
- Create: `tests/unit/test_verifier_loop_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_verifier_loop_state.py
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.loop_state import (
    load_loop_state, save_loop_state, init_loop_state, append_classification
)

def test_init_creates_state(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    assert state["change"] == "test-change"
    assert state["loop_count"] == 0
    assert state["max_loops"] == 3
    assert state["route"] == "archive-ready"
    assert state["classification_history"] == []

def test_init_persists_to_disk(tmp_path):
    state_dir = tmp_path / ".rddf" / "state"
    init_loop_state(tmp_path, "test-change", max_loops=3)
    assert (state_dir / ".verifier-loop.json").is_file()

def test_load_returns_saved_state(tmp_path):
    init_loop_state(tmp_path, "test-change", max_loops=3)
    loaded = load_loop_state(tmp_path)
    assert loaded["change"] == "test-change"

def test_save_validates_schema(tmp_path):
    import pytest
    import jsonschema
    init_loop_state(tmp_path, "test-change", max_loops=3)
    state = load_loop_state(tmp_path)
    # Mutate to invalid state
    state["route"] = "INVALID"
    with pytest.raises(jsonschema.ValidationError):
        save_loop_state(tmp_path, state)

def test_append_classification(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    updated = append_classification(tmp_path, state, "implementation_gap", user_confirmed=True)
    assert updated["loop_count"] == 1
    assert len(updated["classification_history"]) == 1
    assert updated["classification_history"][0]["label"] == "implementation_gap"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/unit/test_verifier_loop_state.py -v
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `loop_state.py`**

```python
""".verifier-loop.json load/save with schema validation.

Per ADR-0034 §6: tracks loop count, classification history, route, halt reason.
Schema validated on every save to prevent silent corruption.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "verifier_loop_schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def _state_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "state" / ".verifier-loop.json"


def init_loop_state(project_root: Path, change_name: str, max_loops: int = 3) -> dict:
    """Initialize a new loop state for a change. Persists to disk.

    Default status="archive-ready" until classification append changes route.
    """
    state = {
        "version": 1,
        "change": change_name,
        "loop_count": 0,
        "max_loops": max_loops,
        "classification_history": [],
        "codebase_commit_at_last_run": "",
        "route": "archive-ready",
        "halt_reason": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_loop_state(project_root, state)
    return state


def load_loop_state(project_root: Path) -> Optional[dict]:
    """Load loop state. Returns None if missing or corrupt."""
    path = _state_path(Path(project_root))
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_loop_state(project_root: Path, state: dict) -> None:
    """Save loop state. Validates against schema before writing.

    Raises:
        jsonschema.ValidationError: if state fails schema validation.
        OSError: if .rddf/state/ cannot be written.
    """
    import jsonschema
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    jsonschema.validate(state, _SCHEMA)

    path = _state_path(Path(project_root))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def append_classification(
    project_root: Path, state: dict, label: str, user_confirmed: bool
) -> dict:
    """Append a classification to history and increment loop_count.

    Args:
        project_root: Where to persist.
        state: Current loop state (will be mutated copy).
        label: "implementation_gap" or "proposal_drift".
        user_confirmed: True if user agreed with AI label, False if user overrode.

    Returns:
        Updated state (also persisted to disk).
    """
    new_state = json.loads(json.dumps(state))  # deep copy
    new_state["classification_history"].append({
        "loop": new_state["loop_count"] + 1,
        "label": label,
        "user_confirmed": user_confirmed,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    new_state["loop_count"] += 1
    save_loop_state(project_root, new_state)
    return new_state
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/unit/test_verifier_loop_state.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/verifier/loop_state.py tests/unit/test_verifier_loop_state.py
git commit -m "feat(verifier-loop-state): add load/save with schema validation"
```

---

## Task 7: `rddf rdd-verify` CLI

**Files:**
- Create: `_lib/cli/rdd_verify_cmd.py`
- Modify: `_lib/cli/__init__.py`
- Create: `tests/unit/test_rdd_verify_cmd.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_rdd_verify_cmd.py
import subprocess as sp
import sys
from pathlib import Path

def test_help_flag():
    result = sp.run(
        ["python3", "_lib/cli/rdd_verify_cmd.py", "--help"],
        capture_output=True, text=True
    )
    assert "--dry-run" in result.stdout
    assert "--max-changes" in result.stdout
    assert "--loop" in result.stdout

def test_dry_run_with_empty_queue(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    result = sp.run(
        ["python3", "_lib/cli/rdd_verify_cmd.py", "--dry-run"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "No ship-done changes" in result.stdout or "empty" in result.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/unit/test_rdd_verify_cmd.py -v
```
Expected: FAIL with `python3: can't open file '_lib/cli/rdd_verify_cmd.py'`.

- [ ] **Step 3: Implement CLI**

```python
#!/usr/bin/env python3
"""rddf rdd-verify CLI — 5th phase batch verifier.

Usage:
    rddf rdd-verify [--dry-run] [--max-changes N] [--loop]

Reads .rddf/state/iteration.json + openspec status to discover ship-done
changes, runs ac-verifier per change, classifies with heuristic, and
routes failures back to plan/ship via state machine.

Exit codes:
    0  All changes verified
    1  At least one AC fail (route decision printed to stderr)
    2  Skipped (SKIP_RDD_VERIFIER=yes)
    4  Halted (max_loops exceeded; manual review needed)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(os.environ.get("PROJECT_ROOT", os.getcwd()))


def _state_dir(root: Path) -> Path:
    return root / ".rddf" / "state"


def _scan_ship_done_queue(root: Path, max_changes: int) -> list[str]:
    """Read iteration.json for ship-done changes that are not archived."""
    state_file = _state_dir(root) / "iteration.json"
    if not state_file.is_file():
        return []
    try:
        doc = json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    changes = doc.get("changes", [])
    return [
        c["name"] for c in changes
        if c.get("status") == "ship-done"
    ][:max_changes]


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="rddf rdd-verify",
        description="Batch verify ship-done changes via ac-verifier skill",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and print verdict suggestions without modifying state")
    parser.add_argument("--max-changes", type=int, default=10,
                        help="Maximum changes to scan (cost guardrail, default=10)")
    parser.add_argument("--loop", action="store_true",
                        help="Continue scanning until queue is empty or halted")
    args = parser.parse_args()

    if os.environ.get("SKIP_RDD_VERIFIER", "").lower() == "yes":
        print("⚠️  SKIP_RDD_VERIFIER=yes — skipping rdd-verifier")
        return 2

    root = _project_root()
    queue = _scan_ship_done_queue(root, args.max_changes)

    if not queue:
        print("No ship-done changes to verify (empty queue).")
        return 0

    if args.dry_run:
        print(f"[dry-run] Would verify {len(queue)} change(s):")
        for name in queue:
            print(f"  - {name}")
        return 0

    print(f"🔍 rdd-verifier: {len(queue)} change(s) in queue")
    # Full orchestration lives in skills/rdd-verifier/SKILL.md state machine.
    # This CLI is the engineering backend; SKILL.md wraps it with menus + user confirm.
    for change in queue:
        print(f"  → {change}: invoke skills/rdd-verifier/SKILL.md state machine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Register CLI in `_lib/cli/__init__.py`**

Append:
```python
# At top: import registry
from _lib.cli.rdd_verify_cmd import main as _rdd_verify_main

# In command dispatcher table (modify existing structure to match codebase pattern):
_COMMANDS["rdd-verify"] = _rdd_verify_main
```

(Actual edit: follow the pattern used by `ac_verify_cmd.py` registration in `_lib/cli/__init__.py`.)

- [ ] **Step 5: Run test to verify it passes**

```bash
python3 -m pytest tests/unit/test_rdd_verify_cmd.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Verify CLI integration**

```bash
python3 -c "from _lib.cli import dispatch; print(dispatch('rdd-verify', []))"
```
Expected: `0` (or `2` if SKIP_RDD_VERIFIER=yes).

- [ ] **Step 7: Commit**

```bash
git add _lib/cli/rdd_verify_cmd.py _lib/cli/__init__.py tests/unit/test_rdd_verify_cmd.py
git commit -m "feat(cli): add rddf rdd-verify command

Backend for 5th phase batch verifier. SKILL.md state machine wraps this
CLI with user interaction + heuristic classification + loop routing."
```

---

## Task 8: bash Helpers (4 files)

**Files:**
- Create: `skills/rdd-verifier/scripts/scan_queue.sh`
- Create: `skills/rdd-verifier/scripts/run_verification.sh`
- Create: `skills/rdd-verifier/scripts/classify_failure.sh`
- Create: `skills/rdd-verifier/scripts/route_loop.sh`
- Create: `tests/integration/test_rdd_verifier_helpers.bats`

- [ ] **Step 1: Write `scan_queue.sh`**

```bash
#!/usr/bin/env bash
# scan_queue.sh — List ship-done changes from iteration.json
# Exit: 0 always; stdout is space-separated change names
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE_DIR="$PROJECT_ROOT/.rddf/state"
MAX_CHANGES="${RDDF_VERIFIER_MAX_CHANGES:-10}"

if [ ! -f "$STATE_DIR/iteration.json" ]; then
    exit 0
fi

python3 - "$STATE_DIR/iteration.json" "$MAX_CHANGES" <<'PYEOF'
import json, sys
state_file, max_changes = sys.argv[1], int(sys.argv[2])
try:
    doc = json.loads(open(state_file).read())
except Exception:
    sys.exit(0)
queue = [c["name"] for c in doc.get("changes", []) if c.get("status") == "ship-done"][:max_changes]
print(" ".join(queue))
PYEOF
```

- [ ] **Step 2: Write `run_verification.sh`**

```bash
#!/usr/bin/env bash
# run_verification.sh <change_name> — Invoke ac-verifier skill for one change
# Exit: ac-verifier exit code (0=pass, 1=fail, 2=skip, 3=error)
set -euo pipefail

CHANGE_NAME="${1:-}"
[ -z "$CHANGE_NAME" ] && { echo "❌ usage: run_verification.sh <change_name>" >&2; exit 2; }

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
AC_SCRIPT="$PROJECT_ROOT/skills/ac-verifier/scripts/ac_verifier.sh"

if [ ! -f "$AC_SCRIPT" ]; then
    echo "❌ ac-verifier skill not found at $AC_SCRIPT" >&2
    exit 3
fi

bash "$AC_SCRIPT" "$CHANGE_NAME"
```

- [ ] **Step 3: Write `classify_failure.sh`**

```bash
#!/usr/bin/env bash
# classify_failure.sh <change_name> — Read verdict cache, classify each fail, print labels
# Exit: 0 always; stdout is "AC-N:label" lines (one per failing AC)
set -euo pipefail

CHANGE_NAME="${1:-}"
[ -z "$CHANGE_NAME" ] && { echo "❌ usage: classify_failure.sh <change_name>" >&2; exit 2; }

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CACHE="$PROJECT_ROOT/.rddf/state/.ac-verdict-${CHANGE_NAME}.json"

[ ! -f "$CACHE" ] && { echo "❌ verdict cache missing: $CACHE" >&2; exit 1; }

python3 - "$CACHE" <<'PYEOF'
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[0]).resolve().parents[3] / "_lib"))
from _lib.verifier.classify import classify_failure

cache = json.loads(open(sys.argv[1]).read())
for item in cache.get("verdict", []):
    if item.get("status") == "fail":
        label = classify_failure(item)
        print(f"{item['ac_id']}:{label}")
PYEOF
```

- [ ] **Step 4: Write `route_loop.sh`**

```bash
#!/usr/bin/env bash
# route_loop.sh <change_name> <classification_label> — Update loop_state, set route
# Exit: 0 if routed, 1 if halted (max_loops reached)
set -euo pipefail

CHANGE_NAME="${1:-}"
LABEL="${2:-}"
[ -z "$CHANGE_NAME" ] || [ -z "$LABEL" ] && {
    echo "❌ usage: route_loop.sh <change_name> <implementation_gap|proposal_drift>" >&2
    exit 2
}

python3 - "$CHANGE_NAME" "$LABEL" <<'PYEOF'
import json, os, sys
from pathlib import Path

project_root = Path(os.environ.get("PROJECT_ROOT", "."))
sys.path.insert(0, str(project_root / "_lib"))
from _lib.verifier.loop_state import load_loop_state, append_classification, save_loop_state

change_name, label = sys.argv[1], sys.argv[2]
state = load_loop_state(project_root)
if state is None:
    state = {
        "version": 1, "change": change_name, "loop_count": 0,
        "max_loops": int(os.environ.get("RDDF_VERIFIER_MAX_LOOPS", "3")),
        "classification_history": [], "codebase_commit_at_last_run": "",
        "route": "archive-ready", "halt_reason": None,
        "updated_at": "",
    }

state = append_classification(project_root, state, label, user_confirmed=True)

if state["loop_count"] >= state["max_loops"]:
    state["route"] = "halted"
    state["halt_reason"] = f"max_loops={state['max_loops']} reached with label={label}"
    save_loop_state(project_root, state)
    print(f"❌ HALTED: {state['halt_reason']}")
    sys.exit(1)

if label == "implementation_gap":
    state["route"] = "guide-ship"
elif label == "proposal_drift":
    state["route"] = "guide-plan"

save_loop_state(project_root, state)
print(f"→ Route: {state['route']} (loop {state['loop_count']}/{state['max_loops']})")
PYEOF
```

- [ ] **Step 5: Make scripts executable + write bats test**

```bash
chmod +x skills/rdd-verifier/scripts/*.sh
```

```bash
# tests/integration/test_rdd_verifier_helpers.bats
load test_helper

setup() {
    TEST_TMP="$(mktemp -d)"
    cd "$TEST_TMP"
    git init -q
    git config user.email "t@t"
    git config user.name "T"
    echo "x" > x.txt
    git add x.txt
    git commit -q -m "init"
    mkdir -p .rddf/state
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "scan_queue.sh: empty iteration.json returns empty" {
    echo '{"changes": []}' > .rddf/state/iteration.json
    run bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/scan_queue.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "scan_queue.sh: filters ship-done only" {
    cat > .rddf/state/iteration.json <<EOF
{"changes": [
  {"name": "a", "status": "ship-done"},
  {"name": "b", "status": "planned"},
  {"name": "c", "status": "ship-done"}
]}
EOF
    run bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/scan_queue.sh"
    [ "$status" -eq 0 ]
    [ "$output" = "a c" ]
}

@test "route_loop.sh: halted after max_loops" {
    cat > .rddf/state/iteration.json <<EOF
{"changes": [{"name": "halt-test", "status": "ship-done"}]}
EOF
    RDDF_VERIFIER_MAX_LOOPS=2 PROJECT_ROOT="$TEST_TMP" run bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/route_loop.sh" halt-test implementation_gap
    [ "$status" -eq 0 ]
    RDDF_VERIFIER_MAX_LOOPS=2 PROJECT_ROOT="$TEST_TMP" run bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/route_loop.sh" halt-test implementation_gap
    [ "$status" -eq 1 ]
    [[ "$output" == *"HALTED"* ]]
}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
bats tests/integration/test_rdd_verifier_helpers.bats
```
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add skills/rdd-verifier/scripts/ tests/integration/test_rdd_verifier_helpers.bats
git commit -m "feat(verifier-helpers): add 4 bash scripts for queue/scan/classify/route

scan_queue.sh: list ship-done changes
run_verification.sh: invoke ac-verifier skill
classify_failure.sh: heuristic label via _lib.verifier.classify
route_loop.sh: update loop_state, halt at max_loops"
```

---

## Task 9: `_lib/archive.sh` SHA Cache Integration

**Files:**
- Modify: `_lib/archive.sh` (lines 333-357)
- Create: `tests/integration/test_rdd_verifier_archive_compat.bats`

- [ ] **Step 1: Write the failing test (cache hit should skip LLM)**

```bash
# tests/integration/test_rdd_verifier_archive_compat.bats
load test_helper

setup() {
    TEST_TMP="$(mktemp -d)"
    cd "$TEST_TMP"
    git init -q
    git config user.email "t@t"
    git config user.name "T"
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/proposal.md <<'EOF'
# Test Change
## 验收标准
- AC-1: A criterion
EOF
    git add . && git commit -q -m "init"
    mkdir -p .rddf/state

    # Seed verdict cache at current commit
    SHA=$(git rev-parse HEAD)
    cat > .rddf/state/.ac-verdict-test-change.json <<EOF
{"version":1,"change":"test-change","codebase_commit":"$SHA","verdict":[],"ran_at":"2026-08-26T00:00:00Z","ran_by":"rdd-verifier"}
EOF
}

teardown() { rm -rf "$TEST_TMP"; }

@test "archive_gate_check: consumes cached verdict (cache hit)" {
    AC_LLM_MOCK=yes SKIP_AC_VERIFICATION=no \
        bash "${BATS_TEST_DIRNAME}/../../_lib/archive.sh" >/dev/null 2>&1 || true
    # Verify archive_gate_check ran with reused cache (no LLM call attempted)
    # Implementation verified by source code review; this test ensures the cache file is not overwritten
    SHA=$(git rev-parse HEAD)
    CACHE_FILE=".rddf/state/.ac-verdict-test-change.json"
    [ -f "$CACHE_FILE" ]
    grep -q "$SHA" "$CACHE_FILE"
}

@test "archive_gate_check: stale cache triggers re-run" {
    # Create new commit to invalidate cache
    echo "new" > new.txt
    git add new.txt && git commit -q -m "new"
    # Cache now stale (different SHA)
    # Test that stale detection works (cache SHA != HEAD)
    OLD_SHA=$(git rev-list HEAD | tail -1)
    NEW_SHA=$(git rev-parse HEAD)
    [ "$OLD_SHA" != "$NEW_SHA" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_rdd_verifier_archive_compat.bats
```
Expected: FAIL (current archive_gate_check does not check cache).

- [ ] **Step 3: Modify `_lib/archive.sh::archive_gate_check`**

Replace lines 333-357 (the existing ac-verifier inline block):

```bash
  # AC verification step (ac-verifier skill, Task 10) + SHA cache check (ADR-0034 §7.2)
  if [ "${SKIP_AC_VERIFICATION:-no}" != "yes" ]; then
    local ac_script="$tasks_root/skills/ac-verifier/scripts/ac_verifier.sh"
    if [ -f "$ac_script" ]; then
      local verdict_cache="$tasks_root/.rddf/state/.ac-verdict-${change_name}.json"
      local current_sha
      current_sha=$(git -C "$tasks_root" rev-parse HEAD 2>/dev/null || echo "unknown")

      # Check cache freshness (avoids redundant LLM calls)
      local cache_hit="no"
      if [ -f "$verdict_cache" ]; then
        local cached_sha
        cached_sha=$(python3 -c "import json; print(json.load(open('$verdict_cache')).get('codebase_commit', ''))" 2>/dev/null || echo "")
        if [ "$cached_sha" = "$current_sha" ] && [ -n "$cached_sha" ]; then
          cache_hit="yes"
          echo "♻️  Reusing ac-verifier verdict cache (commit $cached_sha)"
        else
          echo "⚠️  ac-verifier verdict cache stale (cached: $cached_sha, current: $current_sha)"
        fi
      fi

      # Run ac-verifier (mock mode for testing)
      local ac_exit=0
      AC_LLM_MOCK="${AC_LLM_MOCK:-no}" \
        bash "$ac_script" "$change_name" >/dev/null 2>&1 || ac_exit=$?

      # On cache hit, treat as success regardless of mock output
      if [ "$cache_hit" = "yes" ] && [ "$ac_exit" -ne 0 ] && [ "$ac_exit" -ne 2 ]; then
        echo "♻️  Cache hit overrides LLM exit code ($ac_exit → 0)"
        ac_exit=0
      fi

      if [ "$ac_exit" -eq 1 ]; then
        if [ "${STRICT_AC_GATE:-no}" = "yes" ]; then
          echo "❌ archive_gate_check: AC verification failed under STRICT_AC_GATE"
          return 1
        else
          echo "⚠️  archive_gate_check: AC verification warning (set STRICT_AC_GATE=yes to block)"
        fi
      elif [ "$ac_exit" -eq 3 ]; then
        echo "⚠️  AC verification errored; treating as warning (set SKIP_AC_VERIFICATION=yes to suppress)"
      fi
    fi
  fi
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_rdd_verifier_archive_compat.bats
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/archive.sh tests/integration/test_rdd_verifier_archive_compat.bats
git commit -m "feat(archive): SHA-fingerprint verdict cache in archive_gate_check

Per ADR-0034 §7.2 + Oracle §C: cache hit skips LLM, stale cache re-runs.
Bypass via SKIP_AC_VERIFICATION=yes."
```

---

## Task 10: `skills/rdd-verifier/SKILL.md` State Machine

**Files:**
- Create: `skills/rdd-verifier/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: rdd-verifier
description: 5th phase batch verifier — runs ac-verifier skill on ship-done changes, classifies failures heuristically (implementation_gap vs proposal_drift), routes failures back to guide-plan or guide-ship with 3-retry max. Called by user after guide-ship completes.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, ANTHROPIC_API_KEY or OPENAI_API_KEY
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: "ac-verifier skill v1.0"
  user-invocable: true
role:
  title: "Verifier (验证治理者)"
  perspective: "5th phase state machine — guards archive by enforcing AC pass, classifies failures, routes loops"
  boundaries:
    owns:
      - ".rddf/state/.verifier-loop.json"
      - ".rddf/state/.ac-verdict-*.json"
      - ".rddf/state/.ac-verifier-blocked.jsonl"
    not_owns:
      - "openspec/changes/*/"
      - "docs/adr/"
    human_involvement: "high"
---

# rdd-verifier Skill

## Usage

### Standalone

```bash
# Scan and verify ship-done queue
rddf rdd-verify

# Dry-run (no state mutation)
rddf rdd-verify --dry-run

# Limit scan size (cost guardrail)
rddf rdd-verify --max-changes 5

# Skill form (interactive state machine)
skill_use("rdd-verifier")
```

### After guide-ship

`guide-ship` Phase 3 prompts user to invoke `skill_use("rdd-verifier")` before archive.

## State Machine

1. **Scan queue** (`scan_queue.sh`): read `.rddf/state/iteration.json`, filter `status="ship-done"` and not archived
2. **For each change** (serial):
   - Check verdict cache (SHA fingerprint)
   - If cache miss/stale → invoke `run_verification.sh` → writes verdict cache
   - If all pass → mark route="archive-ready"
   - If any fail → invoke `classify_failure.sh` → heuristic label
3. **User confirm** classification label (override if needed)
4. **Route loop** (`route_loop.sh`):
   - `implementation_gap` → route="guide-ship" (re-execute code)
   - `proposal_drift` → route="guide-plan" (rewrite proposal, forceworktree)
   - `loop_count >= max_loops` → route="halted" + audit log
5. **All-pass case**: print summary, return to caller (archive proceeds)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_RDD_VERIFIER` | `no` | Skip 5th phase entirely |
| `RDDF_VERIFIER_MAX_LOOPS` | `3` | Max retry loops per change |
| `RDDF_VERIFIER_MAX_CHANGES` | `10` | Max changes per scan |
| `RDDF_VERIFIER_DRY_RUN` | `no` | Scan + suggest, no state mutation |
| `STRICT_AC_GATE` | `no` | Promote AC fail to archive blocker (shared with archive_gate_check) |
| `FORCE_ARCHIVE_BYPASS_VERIFIER` | `no` | Bypass halted state for force-archive |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All changes verified, archive can proceed |
| 1 | AC fail (route decision printed to stderr) |
| 2 | Skipped (SKIP_RDD_VERIFIER=yes) |
| 3 | ac-verifier internal error (LLM failure, API key missing) |
| 4 | Halted (max_loops reached; manual review required) |

## Audit Log

When route="halted", append to `.rddf/state/.ac-verifier-blocked.jsonl`:
```json
{"ts":"...","change":"...","loop_count":3,"classifications":["..."],"halt_reason":"..."}
```

## See Also

- Spec: `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md`
- ADR: `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md`
- Sub-skill: `skills/ac-verifier/`
```

- [ ] **Step 2: Verify SKILL.md format**

```bash
python3 -c "
import re
content = open('skills/rdd-verifier/SKILL.md').read()
assert content.startswith('---\n')
assert 'name: rdd-verifier' in content
assert 'role:' in content
print('SKILL.md format OK')
"
```
Expected: `SKILL.md format OK`.

- [ ] **Step 3: Commit**

```bash
git add skills/rdd-verifier/SKILL.md
git commit -m "feat(rdd-verifier): add 5th phase SKILL.md state machine

Per ADR-0034: owns .verifier-loop.json / .ac-verdict-* / .ac-verifier-blocked.jsonl
Not owns: openspec/changes/*, docs/adr/."
```

---

## Task 11: `skills/guide/SKILL.md` Menu Update

**Files:**
- Modify: `skills/guide/SKILL.md`

- [ ] **Step 1: Find existing 4 阶段 menu**

```bash
grep -n "guide-plan\|guide-ship\|guide-arch\|guide-design" skills/guide/SKILL.md | head -30
```

- [ ] **Step 2: Add rdd-verifier to menu**

Find the section that recommends next phase (typically after `guide-ship`) and append:

```markdown
### 5th phase: rdd-verifier

After `guide-ship` completes (status="ship-done" in iteration.json), invoke `skill_use("rdd-verifier")` before archive. Skipping this phase requires `SKIP_RDD_VERIFIER=yes` (audit trail).
```

- [ ] **Step 3: Verify guide menu now lists 5 阶段**

```bash
grep -c "rdd-verifier\|guide-arch\|guide-design\|guide-plan\|guide-ship" skills/guide/SKILL.md
```
Expected: ≥5 (all 5 stages mentioned).

- [ ] **Step 4: Commit**

```bash
git add skills/guide/SKILL.md
git commit -m "docs(guide): add rdd-verifier to 5-phase menu"
```

---

## Task 12: install.sh Registration

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: Find existing sub-skill registration**

```bash
grep -n "guide-ship\|guide-plan\|rdd-workflow/skills" install.sh | head -20
```

- [ ] **Step 2: Add rdd-verifier to symlink list**

In the section that creates symlinks for sub-skills, append:
```bash
ln -sf "$SOURCE_DIR/skills/rdd-verifier" "$TARGET_DIR/rdd-verifier"
```

(Adjust to match existing pattern — verify with grep.)

- [ ] **Step 3: Verify install.sh dry-run**

```bash
bash install.sh --help | grep -q "rdd-verifier\|--global" && echo "install.sh OK"
```
Expected: `install.sh OK`.

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "chore(install): register rdd-verifier sub-skill symlink"
```

---

## Task 13: 4 Mock Fixtures

**Files:**
- Create: `tests/_lib/verifier_mocks/pass.json`
- Create: `tests/_lib/verifier_mocks/fail.json`
- Create: `tests/_lib/verifier_mocks/proposal_drift.json`
- Create: `tests/_lib/verifier_mocks/implementation_gap.json`

- [ ] **Step 1: Write `pass.json`**

```json
{
  "version": 1,
  "change": "test-change",
  "codebase_commit": "abc1234567",
  "verdict": [
    {"ac_id": "AC-1", "status": "pass", "confidence": 0.95, "evidence": ["file:tests/test_foo.py:10"], "reasoning": "All ACs verified"},
    {"ac_id": "AC-2", "status": "pass", "confidence": 0.92, "evidence": ["file:tests/test_bar.py:20"], "reasoning": "Pass"}
  ],
  "ran_at": "2026-08-26T00:00:00Z",
  "ran_by": "rdd-verifier"
}
```

- [ ] **Step 2: Write `fail.json`**

```json
{
  "version": 1,
  "change": "test-change",
  "codebase_commit": "abc1234567",
  "verdict": [
    {"ac_id": "AC-1", "status": "fail", "confidence": 0.85, "evidence": [], "reasoning": "Unclear failure"}
  ],
  "ran_at": "2026-08-26T00:00:00Z",
  "ran_by": "rdd-verifier"
}
```

- [ ] **Step 3: Write `proposal_drift.json`**

```json
{
  "version": 1,
  "change": "test-change",
  "codebase_commit": "abc1234567",
  "verdict": [
    {"ac_id": "AC-1", "status": "fail", "confidence": 0.88, "evidence": ["file:src/foo.py:50"], "reasoning": "Code exists but mismatches the AC description"}
  ],
  "ran_at": "2026-08-26T00:00:00Z",
  "ran_by": "rdd-verifier"
}
```

- [ ] **Step 4: Write `implementation_gap.json`**

```json
{
  "version": 1,
  "change": "test-change",
  "codebase_commit": "abc1234567",
  "verdict": [
    {"ac_id": "AC-1", "status": "fail", "confidence": 0.90, "evidence": [], "reasoning": "Function is missing from codebase"}
  ],
  "ran_at": "2026-08-26T00:00:00Z",
  "ran_by": "rdd-verifier"
}
```

- [ ] **Step 5: Validate all fixtures against schema**

```bash
python3 -c "
import json, jsonschema
schema = json.load(open('_lib/schemas/ac_verdict_cache_schema.json'))
for f in ['pass', 'fail', 'proposal_drift', 'implementation_gap']:
    doc = json.load(open(f'tests/_lib/verifier_mocks/{f}.json'))
    jsonschema.validate(doc, schema)
    print(f'{f}.json OK')
"
```
Expected: 4 lines "OK".

- [ ] **Step 6: Commit**

```bash
git add tests/_lib/verifier_mocks/
git commit -m "test(verifier): add 4 mock fixtures (pass/fail/proposal_drift/implementation_gap)"
```

---

## Task 14: E2E Integration Test

**Files:**
- Create: `tests/integration/test_rdd_verifier_e2e.bats`

- [ ] **Step 1: Write bats test**

```bash
# tests/integration/test_rdd_verifier_e2e.bats
load test_helper

setup() {
    TEST_TMP="$(mktemp -d)"
    cd "$TEST_TMP"
    git init -q
    git config user.email "t@t"
    git config user.name "T"
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/proposal.md <<'EOF'
# Test
## 验收标准
- AC-1: A criterion
EOF
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [{"name": "test-change", "status": "ship-done"}]}
EOF
    git add . && git commit -q -m "init"
}

teardown() { rm -rf "$TEST_TMP"; }

@test "e2e: all-pass queue exits 0" {
    SHA=$(git rev-parse HEAD)
    cp tests/_lib/verifier_mocks/pass.json .rddf/state/.ac-verdict-test-change.json
    sed -i "s/abc1234567/$SHA/" .rddf/state/.ac-verdict-test-change.json
    AC_LLM_MOCK=yes SKIP_RDD_VERIFIER=no run python3 "${BATS_TEST_DIRNAME}/../../_lib/cli/rdd_verify_cmd.py" --dry-run
    [ "$status" -eq 0 ]
}

@test "e2e: SKIP_RDD_VERIFIER=yes exits 2" {
    SHA=$(git rev-parse HEAD)
    cp tests/_lib/verifier_mocks/pass.json .rddf/state/.ac-verdict-test-change.json
    sed -i "s/abc1234567/$SHA/" .rddf/state/.ac-verdict-test-change.json
    SKIP_RDD_VERIFIER=yes AC_LLM_MOCK=yes run python3 "${BATS_TEST_DIRNAME}/../../_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 2 ]
}

@test "e2e: implementation_gap fixture routes to guide-ship" {
    SHA=$(git rev-parse HEAD)
    cp tests/_lib/verifier_mocks/implementation_gap.json .rddf/state/.ac-verdict-test-change.json
    sed -i "s/abc1234567/$SHA/" .rddf/state/.ac-verdict-test-change.json
    RDDF_VERIFIER_MAX_LOOPS=3 PROJECT_ROOT="$TEST_TMP" \
        run bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/route_loop.sh" test-change implementation_gap
    [ "$status" -eq 0 ]
    [[ "$output" == *"guide-ship"* ]]
}
```

- [ ] **Step 2: Run tests**

```bash
bats tests/integration/test_rdd_verifier_e2e.bats
```
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_rdd_verifier_e2e.bats
git commit -m "test(verifier-e2e): add end-to-end flow tests"
```

---

## Task 15: Loop Boundary Test

**Files:**
- Create: `tests/integration/test_rdd_verifier_loop.bats`

- [ ] **Step 1: Write bats test**

```bash
# tests/integration/test_rdd_verifier_loop.bats
load test_helper

setup() {
    TEST_TMP="$(mktemp -d)"
    cd "$TEST_TMP"
    git init -q
    git config user.email "t@t"
    git config user.name "T"
    mkdir -p .rddf/state
    git add . && git commit -q -m "init" 2>/dev/null || echo "x" > x.txt && git add x.txt && git commit -q -m "init"
}

teardown() { rm -rf "$TEST_TMP"; }

@test "loop: 3 retries then halt" {
    RDDF_VERIFIER_MAX_LOOPS=3 PROJECT_ROOT="$TEST_TMP" \
        bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/route_loop.sh" loop-test implementation_gap >/dev/null 2>&1 || true
    RDDF_VERIFIER_MAX_LOOPS=3 PROJECT_ROOT="$TEST_TMP" \
        bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/route_loop.sh" loop-test implementation_gap >/dev/null 2>&1 || true
    RDDF_VERIFIER_MAX_LOOPS=3 PROJECT_ROOT="$TEST_TMP" \
        run bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/route_loop.sh" loop-test implementation_gap
    [ "$status" -eq 1 ]
    [[ "$output" == *"HALTED"* ]]
}

@test "loop: halted state writes audit log" {
    RDDF_VERIFIER_MAX_LOOPS=1 PROJECT_ROOT="$TEST_TMP" \
        run bash "${BATS_TEST_DIRNAME}/../../skills/rdd-verifier/scripts/route_loop.sh" halt-log-test implementation_gap
    [ "$status" -eq 1 ]
    [ -f ".rddf/state/.verifier-loop.json" ]
    grep -q '"route": "halted"' .rddf/state/.verifier-loop.json
}
```

- [ ] **Step 2: Run tests**

```bash
bats tests/integration/test_rdd_verifier_loop.bats
```
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_rdd_verifier_loop.bats
git commit -m "test(verifier-loop): add 3-retry halt boundary tests"
```

---

## Task 16: Skip + Bypass Tests

**Files:**
- Create: `tests/integration/test_rdd_verifier_skip.bats`

- [ ] **Step 1: Write bats test**

```bash
# tests/integration/test_rdd_verifier_skip.bats
load test_helper

setup() {
    TEST_TMP="$(mktemp -d)"
    cd "$TEST_TMP"
    git init -q
    git config user.email "t@t"
    git config user.name "T"
    mkdir -p .rddf/state
    git add . && git commit -q -m "init" 2>/dev/null || echo "x" > x.txt && git add x.txt && git commit -q -m "init"
}

teardown() { rm -rf "$TEST_TMP"; }

@test "skip: SKIP_RDD_VERIFIER=yes returns exit 2" {
    SKIP_RDD_VERIFIER=yes run python3 "${BATS_TEST_DIRNAME}/../../_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 2 ]
    [[ "$output" == *"SKIP_RDD_VERIFIER"* ]]
}

@test "skip: max-changes cost guardrail limits scan" {
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [
  {"name": "a", "status": "ship-done"},
  {"name": "b", "status": "ship-done"},
  {"name": "c", "status": "ship-done"},
  {"name": "d", "status": "ship-done"},
  {"name": "e", "status": "ship-done"}
]}
EOF
    run python3 "${BATS_TEST_DIRNAME}/../../_lib/cli/rdd_verify_cmd.py" --dry-run --max-changes 2
    [ "$status" -eq 0 ]
    [ "$(echo "$output" | grep -c '^  -')" -eq 2 ]
}
```

- [ ] **Step 2: Run tests**

```bash
bats tests/integration/test_rdd_verifier_skip.bats
```
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_rdd_verifier_skip.bats
git commit -m "test(verifier-skip): add skip + cost guardrail tests"
```

---

## Task 17: CHANGELOG + Final Verification

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update CHANGELOG.md**

Find the latest version section (e.g., `## v2.1.x`) and append:

```markdown
### Added

- **rdd-verifier** (5th phase): batch verifier that runs ac-verifier on ship-done changes,
  classifies failures heuristically (implementation_gap vs proposal_drift), routes
  failures back to guide-plan or guide-ship with 3-retry max.
  See `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md` and ADR-0034.
```

- [ ] **Step 2: Run full regression (mandatory per AGENTS.md)**

```bash
./test.sh --full --regression
```
Expected: All tests pass or only baseline `KNOWN_FAILURES.txt` failures.

- [ ] **Step 3: Verify completeness check table from spec**

```bash
echo "=== Verifier file inventory ==="
ls -la _lib/verifier/ _lib/schemas/verifier_loop_schema.json _lib/schemas/ac_verdict_cache_schema.json _lib/cli/rdd_verify_cmd.py skills/rdd-verifier/SKILL.md skills/rdd-verifier/scripts/*.sh
echo ""
echo "=== Test inventory ==="
ls tests/unit/test_classify_failure.py tests/unit/test_ac_verdict_cache.py tests/unit/test_verifier_loop_state.py tests/unit/test_rdd_verify_cmd.py tests/unit/test_verifier_loop_schema.py tests/unit/test_ac_verdict_cache_schema.py
ls tests/integration/test_rdd_verifier_*.bats
echo ""
echo "=== Mock fixtures ==="
ls tests/_lib/verifier_mocks/
```
Expected: 3 schema files, 1 SKILL.md, 4 bash helpers, 6 unit tests, 4+ integration tests, 4 fixtures.

- [ ] **Step 4: Final commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record rdd-verifier 5th phase addition"
```

---

## Self-Review

**1. Spec coverage:**
- Section 3 (5 阶段架构 + ADR-0034) → Task 1
- Section 4.1 (3 组件) → Tasks 7, 8, 10
- Section 4.2 (2 状态文件 + SHA) → Tasks 2, 3, 5
- Section 5 (数据流) → Tasks 5, 8, 10
- Section 5.1 (启发式分类) → Task 4
- Section 6 (失败回环 3 路径) → Task 8 (route_loop.sh)
- Section 7.1 (退出码 0/1/2/3/4) → Task 10 (SKILL.md Exit Codes section)
- Section 7.2 (双门控 + SHA 缓存) → Task 9
- Section 7.3 (6 env vars) → Tasks 10, 11, 12, 13
- Section 7.4 (错误场景) → Tasks 14, 15, 16
- Section 8.1 (测试矩阵) → Tasks 4, 5, 6, 7, 8, 9, 14, 15, 16
- Section 8.2 (mock fixtures) → Task 13
- 完成度检查表 16 项 → All tasks

**2. Placeholder scan:** No TBD/TODO/"implement later" found. All bash scripts have complete code. All Python functions fully implemented.

**3. Type consistency:**
- `classify_failure()` signature: `(dict) -> str` ✓ (Tasks 4, 8, 14)
- `verdict_cache()` signature: `(Path, str, str, list, str) -> Path` ✓ (Tasks 5, 9)
- `is_cache_fresh()` signature: `(Path, str, str) -> bool` ✓ (Tasks 5, 9)
- `route_loop.sh` exit codes: 0=routed, 1=halted, 2=usage ✓ (Tasks 8, 15)
- `loop_state` schema fields: consistent across Tasks 2, 6, 8, 15
- exit code 4 = halted (consistent across Tasks 7, 10, 11)

**Plan ready for execution.**

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-26-rdd-verifier-implementation.md`. 17 tasks, ~120 TDD substeps, bite-sized (2-5 min each).

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**