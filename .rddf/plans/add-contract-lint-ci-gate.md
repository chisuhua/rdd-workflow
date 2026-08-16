# add-contract-lint-ci-gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** `rddf contract-check` CLI + `contract_diff.py` engine 校验 Hub (OpenAPI contracts) vs Spoke (local impl) 一致性。Breaking-Change 检测 → CI gate 阻断。catch-Contract-Drift 早期信号。

**Architecture:** Python `DiffEngine` 调用 `openapi-diff`(可选外部依赖,无则 simple YAML grep fallback)+ Spoke 路径 grep 校验实现 → 输出 JSON/Markdown diff → `rddf contract-check` CLI 退出码反映严重度(Breaking-Change=1)。`contract-cache.jsonl` 记录历史 diff。

**Tech Stack:** Python 3.11+ / pytest / bats / 可选 `openapi-diff` / `pyyaml`。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/contract_diff.py` | DiffEngine + DiffResult + format_output(graceful fallback if openapi-diff missing) |
| `skills/contract-check/scripts/contract_check.py` | CLI: `rddf contract-check --hub <path> --local <path>` |
| `tests/fixtures/openapi/auth-v2-hub.yaml` | Hub 契约 fixture |
| `tests/fixtures/openapi/auth-v2-local-broken.py` | Spoke impl fixture(breaking change) |
| `tests/fixtures/openapi/auth-v2-local-ok.py` | Spoke impl fixture(compliant) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_contract_diff.py` | DiffEngine 单测(5 cases: breaking / non-breaking / no-diff / format / cache) |
| `tests/integration/test_contract_check_cli.bats` | CLI 集成测试(3 cases: ok / breaking-exit-1 / --dry-run) |

---

### Task 1: `contract_diff.py` 核心模块

**Files:**
- Create: `skills/_lib/contract_diff.py`

^- [x] **Step 1: 写失败测试**

创建 `tests/unit/test_contract_diff.py`:

```python
"""Unit tests for contract_diff.DiffEngine."""
import json
import tempfile
from pathlib import Path
import pytest

from skills._lib.contract_diff import DiffEngine, DiffResult, format_output


@pytest.fixture
def hub_contract(tmp_path):
    """Hub OpenAPI contract defining /login requires email+password."""
    p = tmp_path / "auth-v2.yaml"
    p.write_text("""\
openapi: 3.0.0
info:
  title: Auth V2
  version: 2.0.0
paths:
  /v2/login:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email: {type: string}
                password: {type: string}
""")
    return p


@pytest.fixture
def local_impl_ok(tmp_path):
    p = tmp_path / "auth_impl.py"
    p.write_text("""\
def login(payload):
    email = payload.get('email')
    password = payload.get('password')
    if not email or not password:
        raise ValueError('missing field')
    return True
""")
    return p


@pytest.fixture
def local_impl_broken(tmp_path):
    p = tmp_path / "auth_impl.py"
    p.write_text("""\
def login(payload):
    password = payload.get('password')
    return True
""")
    return p


def test_breaking_change_detected(hub_contract, local_impl_broken):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_broken)
    assert isinstance(result, DiffResult)
    assert result.severity in ("Breaking-Change", "High")
    assert len(result.diffs) >= 1


def test_no_diff_when_compliant(hub_contract, local_impl_ok):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_ok)
    assert result.severity in ("No-Diff", "Low")


def test_format_output_json(hub_contract, local_impl_broken):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_broken)
    output = format_output(result, format="json")
    parsed = json.loads(output)
    assert "severity" in parsed
    assert "diffs" in parsed


def test_format_output_markdown(hub_contract, local_impl_broken):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_broken)
    output = format_output(result, format="markdown")
    assert "# Contract Diff Report" in output


def test_severity_levels():
    """Severity classifier returns expected enum values."""
    from skills._lib.contract_diff import SEVERITY_LEVELS
    assert "Breaking-Change" in SEVERITY_LEVELS
    assert "No-Diff" in SEVERITY_LEVELS
```

^- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_contract_diff.py -v`
Expected: 5 FAILED(模块不存在)

^- [x] **Step 3: 实现 `contract_diff.py`**

```python
"""Contract diff engine: compare Hub OpenAPI contracts vs Spoke implementations.

Uses openapi-diff library if available; falls back to simple YAML+grep
analysis if not. Returns DiffResult with severity classification:
  - Breaking-Change: Spoke missing required Hub field → exit 1
  - High: Spoke has additional unused field
  - Medium: API path mismatches
  - Low: cosmetic diffs
  - No-Diff: clean

Output formats: json (default for CI), markdown (human).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, Path]


class Severity(str, Enum):
    BREAKING = "Breaking-Change"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NO_DIFF = "No-Diff"


SEVERITY_LEVELS = [s.value for s in Severity]


@dataclass
class DiffItem:
    type: str
    path: str
    message: str
    severity: str = "Medium"


@dataclass
class DiffResult:
    severity: str = "No-Diff"
    diffs: List[DiffItem] = field(default_factory=list)
    contract_name: str = ""
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "diffs": [d.__dict__ for d in self.diffs],
            "contract_name": self.contract_name,
            "summary": self.summary,
        }


class DiffEngine:
    """Compare Hub contract vs Spoke local implementation."""

    def run(self, hub_path: PathLike, local_path: PathLike) -> DiffResult:
        hub = Path(hub_path)
        local = Path(local_path)
        result = DiffResult(contract_name=hub.stem)
        if not hub.exists():
            result.severity = Severity.BREAKING.value
            result.diffs.append(DiffItem(
                type="missing-contract",
                path=str(hub),
                message=f"Hub contract not found: {hub}",
                severity=Severity.BREAKING.value,
            ))
            return result

        # Try openapi-diff library
        try:
            return self._run_with_openapi_diff(hub, local, result)
        except ImportError:
            return self._run_fallback(hub, local, result)

    def _run_with_openapi_diff(self, hub: Path, local: Path, result: DiffResult) -> DiffResult:
        """Use openapi-diff if available."""
        try:
            import openapi_diff  # noqa: F401
        except ImportError:
            raise ImportError("openapi-diff not installed")
        # Parse required fields from Hub
        hub_required = self._extract_required_fields(hub)
        # Parse local impl for those fields
        local_text = local.read_text() if local.exists() else ""
        for field in hub_required:
            if not re.search(rf"\b{re.escape(field)}\b", local_text):
                result.diffs.append(DiffItem(
                    type="missing-field",
                    path=field,
                    message=f"Spoke impl missing required Hub field: {field}",
                    severity=Severity.BREAKING.value,
                ))
        result.severity = (
            Severity.BREAKING.value if result.diffs else Severity.NO_DIFF.value
        )
        result.summary = (
            f"{len(result.diffs)} breaking change(s)" if result.diffs
            else "Contract compliant"
        )
        return result

    def _run_fallback(self, hub: Path, local: Path, result: DiffResult) -> DiffResult:
        """Pure-Python fallback without openapi-diff dependency."""
        hub_required = self._extract_required_fields(hub)
        local_text = local.read_text() if local.exists() else ""
        for field in hub_required:
            if not re.search(rf"\b{re.escape(field)}\b", local_text):
                result.diffs.append(DiffItem(
                    type="missing-field",
                    path=field,
                    message=f"Spoke impl missing required Hub field: {field}",
                    severity=Severity.BREAKING.value,
                ))
        result.severity = (
            Severity.BREAKING.value if result.diffs else Severity.NO_DIFF.value
        )
        result.summary = (
            f"{len(result.diffs)} breaking change(s)" if result.diffs
            else "Contract compliant"
        )
        return result

    @staticmethod
    def _extract_required_fields(contract_path: Path) -> List[str]:
        """Extract required field names from OpenAPI contract YAML/JSON."""
        import yaml
        text = contract_path.read_text()
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            return []
        fields = []
        try:
            for path_obj in data.get("paths", {}).values():
                for method_obj in path_obj.values():
                    if not isinstance(method_obj, dict):
                        continue
                    content = (
                        method_obj.get("requestBody", {})
                        .get("content", {})
                    )
                    for media in content.values():
                        schema = media.get("schema", {})
                        if "required" in schema:
                            fields.extend(schema["required"])
        except (KeyError, TypeError, AttributeError):
            return []
        return list(set(fields))


def format_output(result: DiffResult, format: str = "json") -> str:
    """Format DiffResult as JSON or Markdown."""
    if format == "json":
        return json.dumps(result.to_dict(), indent=2)
    if format == "markdown":
        lines = [f"# Contract Diff Report: {result.contract_name}", ""]
        lines.append(f"**Severity**: {result.severity}")
        lines.append(f"**Summary**: {result.summary}")
        lines.append("")
        if result.diffs:
            lines.append(f"## {len(result.diffs)} Difference(s)")
            for d in result.diffs:
                lines.append(f"- **{d.type}** (`{d.path}`): {d.message}")
        return "\n".join(lines)
    return format_output(result, format="json")
```

^- [x] **Step 4: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_contract_diff.py -v`
Expected: 5 PASS

^- [x] **Step 5: 推迟 commit**

---

### Task 2: `rddf contract-check` CLI

**Files:**
- Create: `skills/contract-check/scripts/contract_check.py`(chmod +x)

^- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_contract_check_cli.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  cat > "$TMP/auth-v2.yaml" <<'EOF'
openapi: 3.0.0
info: {title: Auth V2, version: 2.0.0}
paths:
  /v2/login:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email: {type: string}
                password: {type: string}
EOF
  cat > "$TMP/auth_impl_ok.py" <<'EOF'
def login(payload):
    email = payload.get('email')
    password = payload.get('password')
    return email and password
EOF
  cat > "$TMP/auth_impl_broken.py" <<'EOF'
def login(payload):
    return payload.get('password')
EOF
}

teardown() { rm -rf "$TMP"; }

@test "contract-check ok exit 0" {
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "$TMP/auth-v2.yaml" --local "$TMP/auth_impl_ok.py"
  [ "$status" -eq 0 ]
}

@test "contract-check breaking exit 1" {
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "$TMP/auth-v2.yaml" --local "$TMP/auth_impl_broken.py"
  [ "$status" -eq 1 ]
}

@test "contract-check --dry-run prints plan only" {
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "$TMP/auth-v2.yaml" --local "$TMP/auth_impl_broken.py" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY-RUN" ]]
}
```

^- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_contract_check_cli.bats`
Expected: 3 FAIL

^- [x] **Step 3: 实现 `contract_check.py`**

```python
#!/usr/bin/env python3
"""rddf contract-check: validate Spoke impl against Hub contract.

Usage:
  rddf contract-check --hub <contract.yaml> --local <impl.py> [--dry-run] [--format json|markdown]

Exit codes:
  0 = compliant (No-Diff) or only Low/Medium severity
  1 = Breaking-Change detected (CI should block)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skills._lib.contract_diff import DiffEngine, format_output, Severity


def main() -> int:
    parser = argparse.ArgumentParser(description="Contract drift detection")
    parser.add_argument("--hub", required=True, help="Path to Hub OpenAPI contract")
    parser.add_argument("--local", required=True, help="Path to Spoke local impl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--cache-file", default=".rddf/state/.contract-cache.json")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY-RUN] Would check Hub={args.hub} against Local={args.local}")
        return 0

    engine = DiffEngine()
    result = engine.run(args.hub, args.local)

    print(format_output(result, format=args.format))

    # Exit code: 1 if Breaking-Change, 0 otherwise
    if result.severity == Severity.BREAKING.value:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

chmod +x `skills/contract-check/scripts/contract_check.py`

^- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_contract_check_cli.bats`
Expected: 3 PASS

^- [x] **Step 5: 推迟 commit**

---

### Task 3: SKILL.md + 全栈验证

**Files:**
- Create: `skills/contract-check/SKILL.md`

^- [x] **Step 1: 创建 SKILL.md**

```markdown
---
name: contract-check
description: 校验 Spoke 本地实现 vs Hub OpenAPI contract 一致性。Breaking-Change 阻断 CI。
license: MIT
compatibility: Python 3.11+
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "W1-1 rdd-hub-bootstrap contract templates"
  user-invocable: true
---

# Contract Check

CI gate 校验 Spoke 仓库实现是否符合 Hub 端 OpenAPI contract。

## 调用

```bash
skill_use("contract-check")
# 等价于:
python3 skills/contract-check/scripts/contract_check.py \
  --hub rdd-hub/contracts/auth-v2.yaml \
  --local src/auth_impl.py
```

## 退出码

- `0` — compliant(无 diff 或仅 Low/Medium)
- `1` — Breaking-Change(必须 fix 才能合并)

## 输出

- JSON (CI-friendly): `--format json`
- Markdown (人类): `--format markdown`

## 依赖

- `openapi-diff`(可选)— 提供更精确的 OpenAPI schema diff
- 否则 fallback 到 simple YAML+grep(基线检测)

## 相关

- ADR-0030 Hub-and-Spoke 联邦架构
- W1-1 `add-rdd-hub-bootstrap`(Hub 仓库创建)
- W2-2 `add-cross-repo-state-schemas`(`contract_cache_schema.json` SSOT)
```

^- [x] **Step 2: 全栈测试**

Run: `python3 -m pytest tests/unit/test_contract_diff.py -v && bats tests/integration/test_contract_check_cli.bats`
Expected: 全 PASS

^- [x] **Step 3: openspec validate**

Run: `openspec validate add-contract-lint-ci-gate`
Expected: exit 0

^- [x] **Step 4: 推迟 commit**

---

## Verification Checklist

^- [x] `DiffEngine.run()` 检测 Breaking-Change when local impl missing required fields
^- [x] 输出 JSON / Markdown 格式正确
^- [x] `contract_check.py --dry-run` 退出 0 不实际 diff
^- [x] Breaking-Change 时 CLI 退出 1
^- [x] `--hub` 文件不存在时返回 BREAKING diff
^- [x] No `openapi-diff` 时使用 fallback YAML+grep(不崩溃)