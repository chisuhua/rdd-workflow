# rddf-layout-manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `.rddf/` 建立一份机器可读的布局单一真源（`RDFF_LAYOUT`），并用两个只读出口暴露它 —— `rddf layout --json`（清单视图，给消费方与第三方 CI）与 `rddf doctor --category layout`（诊断视图，给项目自检）。

**Architecture:** 清单是一个纯数据模块 `_lib/core/rddf_layout.py`（无 IO、无依赖），每个条目带 `path` / `kind` / `read_by` / `write_by` / `required_when` / `transient` / `class` / `severity` 八个字段。`class` 直接取 ADR-0026 的 `runtime-only` / `committed` 两分类，`gitignored` 由它派生。doctor checker 只读、只扫 `.rddf/` 一层；判定规则（精确 → fnmatch glob → 未登记；目录用 `<path>/.probe` 探针查 ignore）写死，不留实现自由度。

**Tech Stack:** Python 3.11+（`dataclasses` / `fnmatch` / `subprocess` 调用 `git check-ignore`）、bash + bats（doctor 集成测试）、pytest（单元测试）。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/core/rddf_layout.py` | 布局清单的**唯一声明点**：14 条 `LayoutEntry` + `as_dicts()` + 匹配/探测规则 |
| `_lib/cli/layout_cmd.py` | `rddf layout --json` 的 handler：输出 `{schema_version, tool_version, entries}`，无时间戳字段 |
| `skills/rdd-doctor/scripts/checks/layout_check.py` | doctor `layout` category 的 checker：三支判据，只扫一层，只诊断不修改 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_rddf_layout.py` | 清单不变量（字段/取值域/唯一性）+ 断言 A（defaults 与模块常量被覆盖）+ 断言 B（class 与 ignore 实况一致） |
| `tests/unit/test_layout_cmd.py` | `rddf layout --json` 输出结构、`schema_version`/`tool_version`、两次输出字节一致 |
| `tests/integration/test_doctor_layout.bats` | doctor layout 三支判据各一例 + 本仓 0 finding + `.rddf/` 缺失 0 finding |

### Docs

| File | Responsibility |
|---|---|
| `docs/architecture/rddf-layout.md` | 人读契约页：表格 + 新增顶层条目三步 + 文件级一节（以代码为源） |
| `docs/architecture/README.md` | Doc Map 索引加一行 |
| `docs/architecture/state-and-events.md` | 补链接 + **修 v3 遗留 handoff 表与 mermaid 图** |
| `docs/architecture/extension-points.md` | 补链接（不重复展开 `detectors/`/`actions/`） |
| `docs/adr/ADR-0026-internal-metadata-namespace-convention.md` | 加一句指向机器可执行形态（描述性补充，不改决策） |
| `skills/rdd-doctor/SKILL.md` | description 去固定数字 + usage 行 category 枚举同步 + category 说明表加行 |

---

### Task 1: 布局清单模块与不变量

**Files:**
- Create: `_lib/core/rddf_layout.py`
- Test: `tests/unit/test_rddf_layout.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_rddf_layout.py
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "_lib" / "core"))

from rddf_layout import (  # noqa: E402
    CLASSES, REQUIRED_WHEN, ROLES, SEVERITIES, RDFF_LAYOUT, as_dicts,
)

EXPECTED_FIELDS = {
    "path", "kind", "read_by", "write_by",
    "required_when", "transient", "class", "severity",
}


def test_every_entry_has_all_fields():
    for d in as_dicts():
        assert set(d.keys()) == EXPECTED_FIELDS, d["path"]


def test_value_domains_are_closed():
    for d in as_dicts():
        assert d["kind"] in ("dir", "file")
        assert d["class"] in CLASSES
        assert d["required_when"] in REQUIRED_WHEN
        assert d["severity"] in SEVERITIES
        for role in d["read_by"] + d["write_by"]:
            assert role in ROLES
        assert isinstance(d["transient"], bool)


def test_paths_are_unique_and_relative_to_rddf():
    paths = [d["path"] for d in as_dicts()]
    assert len(paths) == len(set(paths))
    for p in paths:
        assert not p.startswith(".rddf"), p
        assert "/" not in p.rstrip("/"), p


def test_as_dicts_is_sorted_by_path():
    paths = [d["path"] for d in as_dicts()]
    assert paths == sorted(paths)


def test_read_only_artifact_has_no_rddf_writer():
    """`reviews/` 只由 agent 写 —— read_by/write_by 必须是可观测事实。"""
    entry = next(d for d in as_dicts() if d["path"] == "reviews")
    assert entry["write_by"] == ["agent"]
    assert "rdd" not in entry["read_by"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_rddf_layout.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'rddf_layout'`

- [ ] **Step 3: Write minimal implementation**

```python
# _lib/core/rddf_layout.py
"""Single source of truth for the `.rddf/` layout.

ADR-0026 defines the two storage classes (`runtime-only` / `committed`);
this module turns that decision into an executable manifest. `class` is
derived from ADR-0026 and nothing else — no third classification.

Note: the JSON key is `class`, but `class` is a Python keyword, so the
dataclass attribute is `layout_class` and `as_dicts()` maps it back.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CLASSES = ("runtime-only", "committed")
REQUIRED_WHEN = ("always", "worktree", "never")
SEVERITIES = ("WARNING", "INFO")
ROLES = ("rdd", "agent", "user", "git", "external-tool")

Kind = Literal["dir", "file"]
RequiredWhen = Literal["always", "worktree", "never"]
StorageClass = Literal["runtime-only", "committed"]


@dataclass(frozen=True)
class LayoutEntry:
    path: str
    kind: Kind
    read_by: tuple[str, ...]
    write_by: tuple[str, ...]
    required_when: RequiredWhen
    transient: bool
    layout_class: StorageClass
    severity: str


RDFF_LAYOUT: tuple[LayoutEntry, ...] = (
    LayoutEntry("state", "dir", ("rdd",), ("rdd",), "always", False, "runtime-only", "WARNING"),
    LayoutEntry("wt", "dir", ("rdd",), ("git",), "worktree", False, "runtime-only", "WARNING"),
    LayoutEntry("detectors", "dir", ("rdd",), ("user",), "never", False, "runtime-only", "INFO"),
    LayoutEntry("actions", "dir", ("rdd",), ("user",), "never", False, "runtime-only", "INFO"),
    LayoutEntry("issues", "dir", ("rdd",), ("rdd",), "never", False, "runtime-only", "INFO"),
    LayoutEntry("improvements", "dir", ("rdd",), ("rdd", "agent"), "always", False, "committed", "WARNING"),
    LayoutEntry("plans", "dir", ("rdd",), ("rdd", "agent"), "always", False, "committed", "WARNING"),
    LayoutEntry("roadmap", "dir", ("rdd",), ("agent",), "always", False, "committed", "WARNING"),
    LayoutEntry("roadmap.md", "file", ("rdd",), ("agent",), "always", False, "committed", "WARNING"),
    LayoutEntry("project.yaml", "file", ("rdd",), ("user",), "always", False, "committed", "WARNING"),
    LayoutEntry("reviews", "dir", ("agent",), ("agent",), "never", False, "committed", "INFO"),
    LayoutEntry("config", "dir", ("external-tool",), ("external-tool",), "never", False, "committed", "INFO"),
    LayoutEntry("skill-profiles", "dir", ("rdd",), ("user",), "never", False, "committed", "INFO"),
    LayoutEntry(".roadmap-migrate-backup-*", "dir", ("rdd",), ("rdd",), "never", True, "runtime-only", "INFO"),
)


def as_dicts() -> list[dict]:
    """Return the manifest as JSON-ready dicts, sorted by `path`."""
    out = []
    for e in sorted(RDFF_LAYOUT, key=lambda x: x.path):
        d = {
            "path": e.path,
            "kind": e.kind,
            "read_by": list(e.read_by),
            "write_by": list(e.write_by),
            "required_when": e.required_when,
            "transient": e.transient,
            "class": e.layout_class,
            "severity": e.severity,
        }
        out.append(d)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_rddf_layout.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 2: 断言 A（路径常量被清单覆盖）与断言 B（class 与 ignore 实况一致）

**Files:**
- Modify: `tests/unit/test_rddf_layout.py`
- Create: `_lib/core/rddf_layout.py`（追加 `matches()` 与 `is_ignored()` 辅助函数）

- [ ] **Step 1: Write the failing test**

```python
# 追加到 tests/unit/test_rddf_layout.py
def _covers(entry_path: str, target: str) -> bool:
    """前缀匹配：entry 'state' 覆盖 '.rddf/state/state-vector.json'。"""
    rel = target[len(".rddf/"):] if target.startswith(".rddf/") else target
    return rel == entry_path or rel.startswith(entry_path + "/")


def test_assertion_a_defaults_paths_are_covered():
    """defaults.DEFAULTS 的路径类条目 + 5 个模块常量都必须被清单覆盖。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from _lib.core import defaults

    targets = [
        defaults.DEFAULTS["state"]["path"],
        defaults.DEFAULTS["event_log"]["path"],
        defaults.STATE_VECTOR_PATH,
        defaults.EVENT_LOG_PATH,
        defaults.MEMORY_PATH,
        defaults.DETECTOR_PLUGIN_DIR,
        defaults.ACTION_PLUGIN_DIR,
    ]
    entries = [d["path"] for d in as_dicts()]
    for t in targets:
        assert any(_covers(p, t) for p in entries), t


def test_assertion_b_class_matches_gitignore_reality():
    """每条 entry 的 class 必须与 git check-ignore 实况一致。"""
    import subprocess

    def ignored(probe: str) -> bool:
        res = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", probe],
            cwd=PROJECT_ROOT, capture_output=True,
        )
        assert res.returncode in (0, 1), res.returncode
        return res.returncode == 0

    for d in as_dicts():
        probe = f".rddf/{d['path']}/.probe" if d["kind"] == "dir" else f".rddf/{d['path']}"
        if d["class"] == "runtime-only":
            assert ignored(probe), f"{d['path']} 应被 gitignore"
        else:
            assert not ignored(probe), f"{d['path']} 不应被 gitignore"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_rddf_layout.py -q -k "assertion"`
Expected: FAIL — 断言 B 在 `detectors` / `actions` 上失败，或断言 A 因 `DETECTOR_PLUGIN_DIR` 未被覆盖而失败（清单尚无 `detectors` / `actions` 条目时）。

- [ ] **Step 3: Write minimal implementation**

若断言 A 失败，说明清单缺条目 —— 补 `detectors` / `actions`（Task 1 Step 3 已含，若失败则检查 `matches` 前缀规则是否用 `entry + "/"` 而非裸前缀，避免 `roadmap` 误吞 `roadmap.md`）。

在 `_lib/core/rddf_layout.py` 追加：

```python
def covers(entry_path: str, target: str) -> bool:
    """True when `entry_path` (relative to .rddf/) covers `target`.

    精确相等或 `target` 以 `entry_path + "/"` 开头 ⇒ 覆盖。
    注意用 `entry_path + "/"` 而不是裸前缀，否则 `roadmap` 会吞掉 `roadmap.md`。
    """
    rel = target[len(".rddf/"):] if target.startswith(".rddf/") else target
    return rel == entry_path or rel.startswith(entry_path + "/")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_rddf_layout.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit。

---

### Task 3: `rdff layout --json` 清单出口

**Files:**
- Create: `_lib/cli/layout_cmd.py`
- Modify: `_lib/cli/__init__.py`（`_ROUTES` + `_SUBCOMMAND_DESCRIPTION`）
- Modify: `_lib/cli/__main__.py`（`_NO_STATE_CHECK` 加 `layout`）
- Test: `tests/unit/test_layout_cmd.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_layout_cmd.py
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(tmp_path: Path) -> str:
    env = {"PATH": "/usr/bin:/bin", "RDDF_PROJECT_ROOT": str(tmp_path),
           "HOME": str(tmp_path), "PYTHONPATH": str(PROJECT_ROOT)}
    res = subprocess.run(
        [sys.executable, "-m", "_lib.cli", "layout", "--json"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, env=env, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return res.stdout


def test_layout_json_payload_shape(tmp_path):
    payload = json.loads(_run(tmp_path))
    assert payload["schema_version"] == 1
    assert payload["tool_version"]
    assert isinstance(payload["entries"], list)
    assert payload["entries"], "清单不应为空"
    assert payload["entries"] == sorted(payload["entries"], key=lambda e: e["path"])


def test_layout_json_has_no_timestamp(tmp_path):
    """输出确定性：两次运行字节一致，且不含时间戳字段。"""
    a = _run(tmp_path)
    b = _run(tmp_path)
    assert a == b
    assert "timestamp" not in a


def test_layout_json_is_empty_when_rddf_absent(tmp_path):
    """`.rddf/` 不存在 ⇒ 空清单，不报错。"""
    payload = json.loads(_run(tmp_path))
    assert payload["entries"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_layout_cmd.py -q`
Expected: FAIL — `rdff` 不是已知子命令（exit != 0）

- [ ] **Step 3: Write minimal implementation**

```python
# _lib/cli/layout_cmd.py
"""``rddf layout`` subcommand handler.

Read-only: prints the `.rddf/` layout manifest (RDFF_LAYOUT) as JSON.
The payload carries no timestamp, so two runs over the same tree are
byte-identical (consumers may diff them).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCHEMA_VERSION = 1


def cmd_layout(args: list[str]) -> int:
    """Handle ``rddf layout [--json]``."""
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd())
    sys.path.insert(0, str(project_root))

    from _lib.core.rddf_layout import as_dicts

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": _tool_version(),
        "entries": as_dicts(),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _tool_version() -> str:
    pkg = Path(__file__).resolve().parents[2] / "package.json"
    try:
        return json.loads(pkg.read_text(encoding="utf-8")).get("version", "0.0.0")
    except (OSError, ValueError):
        return "0.0.0"
```

注册（`_lib/cli/__init__.py`）：

```python
    "layout": "_lib.cli.layout_cmd:cmd_layout",
```
并在 `_SUBCOMMAND_DESCRIPTION` 加：
```python
    "layout": "Print the .rddf/ layout manifest as JSON (read-only)",
```
`_lib/cli/__main__.py` 的 `_NO_STATE_CHECK` 集合加 `"layout"`（`.rddf/` 不存在时也要能跑）。

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_layout_cmd.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit。

---

### Task 4: doctor `layout` category —— 三支判据

**Files:**
- Create: `skills/rdd-doctor/scripts/checks/layout_check.py`
- Modify: `skills/rdd-doctor/scripts/doctor_main.py`（`_CHECKERS` 加一行）
- Test: `tests/integration/test_doctor_layout.bats`

- [ ] **Step 1: Write the failing test**

```bash
# tests/integration/test_doctor_layout.bats
#!/usr/bin/env bats
# Doctor category "layout": three judgement branches + zero-finding invariants.

setup() {
    REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../.." && pwd)"
    TMP="$(mktemp -d)"
    export RDDF_PROJECT_ROOT="$TMP"
    mkdir -p "$TMP/.rddf/state" "$TMP/.rddf/improvements" "$TMP/.rddf/plans" \
             "$TMP/.rddf/roadmap" "$TMP/.rddf/wt"
    : > "$TMP/.rddf/roadmap.md"
    : > "$TMP/.rddf/project.yaml"
    printf '.rddf/state/\n.rddf/wt/\n.rddf/detectors/\n.rddf/actions/\n.rddf/issues/\n' > "$TMP/.gitignore"
    cd "$TMP"
    git init -q . && git config user.email t@t && git config user.name t
}

teardown() { rm -rf "$TMP"; }

run_doctor() {
    run python3 "$REPO_ROOT/skills/rdd-doctor/scripts/doctor_main.py" \
        --project-root "$TMP" --category layout --json
}

@test "layout: missing always-entry yields WARNING" {
    rm -rf "$TMP/.rddf/improvements"
    run_doctor
    [ "$status" -eq 1 ]
    echo "$output" | grep -q '"severity": "WARNING"'
}

@test "layout: unregistered top-level entry yields INFO" {
    mkdir -p "$TMP/.rddf/unknown-dir"
    run_doctor
    echo "$output" | grep -q '"severity": "INFO"'
}

@test "layout: class mismatch with .gitignore yields WARNING" {
    sed -i '/\.rddf\/state\//d' "$TMP/.gitignore"
    run_doctor
    echo "$output" | grep -q '"severity": "WARNING"'
}

@test "layout: no .rddf directory yields zero findings" {
    rm -rf "$TMP/.rddf"
    run_doctor
    echo "$output" | grep -q '"findings": \[\]'
}

@test "layout: this repository yields zero findings" {
    export RDDF_PROJECT_ROOT="$REPO_ROOT"
    run python3 "$REPO_ROOT/skills/rdd-doctor/scripts/doctor_main.py" \
        --project-root "$REPO_ROOT" --category layout --json
    echo "$output" | grep -q '"findings": \[\]'
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_doctor_layout.bats`
Expected: FAIL — `checks.layout_check.run` 不存在（checker 未注册）

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/checks/layout_check.py
"""Cat: `.rddf/` layout — the manifest (RDFF_LAYOUT) is the single source of truth.

Three judgement branches:
  ① required_when=always entry missing            -> WARNING
  ② unregistered (and non-transient) top-level    -> INFO
  ③ class disagrees with .gitignore reality       -> WARNING

Read-only; scans exactly one level of `.rddf/` (never recurses — `.rddf/wt/<name>/`
is a full checkout). Never emits CRITICAL: this category must not break
`rddf doctor` for a third-party project (exit code 1, never 2).
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity  # noqa: E402
from _lib.core.rddf_layout import RDFF_LAYOUT  # noqa: E402


def _match(name: str) -> object | None:
    """Exact match first, then fnmatch glob — never the reverse."""
    for e in RDFF_LAYOUT:
        if e.path == name:
            return e
    for e in RDFF_LAYOUT:
        if any(c in e.path for c in "*?["):
            if fnmatch.fnmatchcase(name, e.path):
                return e
    return None


def _is_ignored(repo_root: Path, entry) -> bool | None:
    """True=ignored / False=not ignored / None=cannot tell (no git, no .gitignore)."""
    if not (repo_root / ".gitignore").is_file():
        return None
    probe = f".rddf/{entry.path}/.probe" if entry.kind == "dir" else f".rddf/{entry.path}"
    res = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", probe],
        cwd=repo_root, capture_output=True,
    )
    if res.returncode == 0:
        return True
    if res.returncode == 1:
        return False
    return None  # 128: not a git repository


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []
    rddf = project_root / ".rddf"
    if not rddf.is_dir():
        return findings  # 项目尚未启用 rdd — 不该被诊断

    present = {p.name for p in rddf.iterdir()}

    # ① required entries missing
    for e in RDFF_LAYOUT:
        if e.required_when != "always":
            continue
        if e.path in present:
            continue
        findings.append(Finding(
            severity=Severity.WARNING,
            category="layout.missing-required",
            file=str(rddf),
            line=None,
            snippet=f"required entry '{e.path}' is missing",
            fix_hint=f"create .rddf/{e.path}/ (see docs/architecture/rddf-layout.md)",
        ))

    # ② unregistered top-level entries
    for name in sorted(present):
        if _match(name) is not None:
            continue
        if any(e.transient and fnmatch.fnmatchcase(name, e.path) for e in RDFF_LAYOUT):
            continue
        findings.append(Finding(
            severity=Severity.INFO,
            category="layout.unregistered",
            file=str(rddf / name),
            line=None,
            snippet=f"top-level entry '{name}' is not in RDFF_LAYOUT",
            fix_hint="add it to _lib/core/rddf_layout.py, or move it out of .rddf/",
        ))

    # ③ class vs .gitignore reality
    for e in RDFF_LAYOUT:
        ignored = _is_ignored(project_root, e)
        if ignored is None:
            continue
        expect_ignored = e.layout_class == "runtime-only"
        if ignored == expect_ignored:
            continue
        findings.append(Finding(
            severity=Severity.WARNING,
            category="layout.class-mismatch",
            file=str(project_root / ".gitignore"),
            line=None,
            snippet=(
                f"'{e.path}' is class={e.layout_class} but is "
                f"{'ignored' if ignored else 'not ignored'} by git"
            ),
            fix_hint="align .gitignore with the ADR-0026 class of this entry",
        ))
    return findings
```

注册（`skills/rdd-doctor/scripts/doctor_main.py` 的 `_CHECKERS`）加一行：
```python
    "layout": "checks.layout_check.run",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_doctor_layout.bats`
Expected: PASS (5 passed)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit。

---

### Task 5: 文档页与索引

**Files:**
- Create: `docs/architecture/rddf-layout.md`
- Modify: `docs/architecture/README.md`（Doc Map 表加一行）

- [ ] **Step 1: Write the failing test**

```bash
# 追加到 tests/integration/test_doctor_layout.bats
@test "layout: architecture doc exists and is indexed" {
    [ -f "$REPO_ROOT/docs/architecture/rddf-layout.md" ]
    grep -q "rddf-layout.md" "$REPO_ROOT/docs/architecture/README.md"
    grep -q "rddf layout --json" "$REPO_ROOT/docs/architecture/rddf-layout.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_doctor_layout.bats -f "architecture doc"`
Expected: FAIL — `docs/architecture/rddf-layout.md` 不存在

- [ ] **Step 3: Write minimal implementation**

`docs/architecture/rddf-layout.md` 至少含三节：
1. **真源声明**：「真源 = `_lib/core/rddf_layout.py`；本页为解释。对外出口 = `rddf layout --json`（清单）与 `rddf doctor --category layout`（诊断）」
2. **布局表**：14 条（`path` / `kind` / `read_by` / `write_by` / `required_when` / `class`）
3. **新增顶层条目三步**：① 路径必须是 `.rddf/<category>/` ② 定 `class`（runtime-only ⇒ 加 .gitignore；committed ⇒ 不写进 gitignore）③ 在 `_lib/core/rddf_layout.py` 登记
4. **文件级一节**（以代码为源）：`_lib/verifier/state_paths.py:34-41` 的 6 条 verifier 文件名 + `_lib/builder_deps.py:42`（`.planner-handoff.json`）+ `_lib/builder_feedback_router.py:31`（`.planner-feedback.json`）+ `_lib/adr_catalog.py:127`（`.arch-handoff.json`）
5. **schema_version 演进策略**：同版本只允许「增字段 / 增 entry」；改 entry 语义或删 entry ⇒ 升版本；消费方须忽略未知字段、按 `path` 做集合比较

`docs/architecture/README.md` 的 Doc Map 表加一行：
```
| [rddf-layout.md](rddf-layout.md) | `.rddf/` 布局单一真源（机读清单 + doctor layout category） | 0026 |
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_doctor_layout.bats`
Expected: PASS (6 passed)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit。

---

### Task 6: 散文补链与修正

**Files:**
- Modify: `docs/architecture/state-and-events.md`
- Modify: `docs/architecture/extension-points.md`
- Modify: `docs/adr/ADR-0026-internal-metadata-namespace-convention.md`

- [ ] **Step 1: Write the failing test**

```bash
# 追加到 tests/integration/test_doctor_layout.bats
@test "layout: state-and-events handoff table uses v4 names" {
    run grep -nE "guide-design|guide-plan|guide-ship|\.design-handoff\.json|\.plan-handoff\.json" \
        "$REPO_ROOT/docs/architecture/state-and-events.md"
    [ "$status" -ne 0 ]
}

@test "layout: ADR-0026 points at the machine-readable form" {
    grep -q "rddf layout --json" "$REPO_ROOT/docs/adr/ADR-0026-internal-metadata-namespace-convention.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_doctor_layout.bats -f "v4 names"`
Expected: FAIL — `state-and-events.md` 仍含 `guide-design` / `.plan-handoff.json`

- [ ] **Step 3: Write minimal implementation**

`docs/architecture/state-and-events.md`：
- Layer 3 表格（`:53-55`）与 mermaid 图（`:14-16`）改为 v4 命名 —— 文件名 `.arch-handoff.json` / `.planner-handoff.json` / `.planner-feedback.json`；写入方 `rdd-arch` / `rdd-planner` / `rdd-builder`
- 段末加链接：「布局单一真源见 [rddf-layout.md](rddf-layout.md)」

`docs/architecture/extension-points.md`：在 `:29-30` 那段后加一行链接，不重复展开目录说明。

`docs/adr/ADR-0026-internal-metadata-namespace-convention.md`：在「路径分类规则」表格后加一句「机器可执行形态见 `rdff layout --json` 与 `rdff doctor --category layout`（清单源 `_lib/core/rddf_layout.py`）」—— **纯描述性补充，不改变该 ADR 的任何决策**。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_doctor_layout.bats`
Expected: PASS (8 passed)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit。

---

### Task 7: `rdd-doctor/SKILL.md` 去漂移

**Files:**
- Modify: `skills/rdd-doctor/SKILL.md`

- [ ] **Step 1: Write the failing test**

```bash
# 追加到 tests/integration/test_doctor_layout.bats
@test "layout: rdd-doctor SKILL.md carries no hardcoded category count" {
    run grep -nE "[0-9]+ (file )?categories" "$REPO_ROOT/skills/rdd-doctor/SKILL.md"
    [ "$status" -ne 0 ]
}

@test "layout: rdd-doctor usage line lists every registered category" {
    python3 - "$REPO_ROOT" <<'PY'
import re, sys
root = sys.argv[1]
src = open(f"{root}/skills/rdd-doctor/scripts/doctor_main.py", encoding="utf-8").read()
block = re.search(r"_CHECKERS: dict\[str, Union\[str, Callable\]\] = \{(.*?)\n\}", src, re.S).group(1)
registered = set(re.findall(r'"([a-z0-9\-]+)":\s*"checks\.', block))
skill = open(f"{root}/skills/rdd-doctor/SKILL.md", encoding="utf-8").read()
usage = re.search(r"--category \{([^}]*)\}", skill).group(1)
listed = {x.strip() for x in usage.split(",")}
missing = registered - listed
sys.exit(1 if missing else 0)
PY
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_doctor_layout.bats -f "hardcoded category count"`
Expected: FAIL — `SKILL.md:4` 仍写「13 file categories」

- [ ] **Step 3: Write minimal implementation**

- `:4` 的 description：改为「Manual read-only diagnostic tool for workflow state files.」（去掉「13 file categories」）
- `:10` 的「Default: read-only; 13 categories; ...」改为「Default: read-only; multi-category; ...」
- `:26` 的 usage 行 category 枚举：补齐 `layout` 与已漏的 `baseline-freshness`
- `:74` 起的 category 说明表：加一行 `| layout | .rddf/ 布局单一真源校验（必需缺失 / 未登记 / class 与 .gitignore 不符）—— advisory only，永不 CRITICAL | |`

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_doctor_layout.bats`
Expected: PASS (10 passed)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit。

---

### Task 8: 全量回归与遗留清扫

**Files:**
- (无新增文件；回归与清扫)

- [ ] **Step 1: 跑全量快速回归**

Run: `./test.sh --quick`
Expected: 无新增失败（smoke + pytest unit）

- [ ] **Step 2: 跑 doctor 全量，确认 layout 不引入新 finding**

Run: `bash skills/rdd-doctor/scripts/doctor.sh`
Expected: layout category 无 finding；总 finding 数与基线一致（基线：1 CRITICAL = roadmap-feature iteration-drift，59 WARNING，4 INFO）

- [ ] **Step 3: 遗留清扫**

检查本次范围内无：TODO / 半截实现 / 注释掉的代码 / 临时调试日志 / 被 skip 的测试 / 未替换的 mock / 临时代码与 fallback。

```bash
git diff --stat HEAD~1
grep -rn "TODO\|FIXME\|XXX\|print(" _lib/core/rddf_layout.py _lib/cli/layout_cmd.py \
    skills/rdd-doctor/scripts/checks/layout_check.py || echo "(clean)"
```

- [ ] **Step 4: 确认无越界改动**

Run: `git diff --stat -- src/ openspec/specs/ skills/rdd-doctor/scripts/doctor_render.py`
Expected: 空 —— 未把现有路径引用改成读常量；未改共享 `doctor_render.py`；未动 `openspec/specs/`（顶层主 spec 是 archive 阶段的产物）

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。
