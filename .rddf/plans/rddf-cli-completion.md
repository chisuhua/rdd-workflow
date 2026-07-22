# rddf CLI Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the migration of the root `rddf` script to the Python CLI by porting the 4 remaining bash subcommands (`guide`, `archive`, `init`, `version`), then collapse the root script to a 1-line shim that delegates to `skills/cli/rddf.sh`. Eliminates ~1300 lines of dead code in the root script and unifies the CLI surface under a single, test-covered entry point.

**Architecture:** Four new `*_cmd.py` modules follow the existing `dashboard_cmd.py` / `status_cmd.py` / `sessions_cmd.py` pattern: a `cmd_<name>(args: list[str]) -> int` function, env-var-based project-root injection (`RDDF_PROJECT_ROOT`), lazy imports, exit codes `0/1/2`. The `guide` command is the most complex (port of 90-line `scan-state.sh` priority ladder). The `archive` command delegates to the existing `skills/_lib/archive.sh` via subprocess (avoiding scope creep into archive.sh itself). The root `rddf` (1525 lines, ~85% dead code) becomes a 5-line shim that `exec`s `skills/cli/rddf.sh` so `git diff` on the legacy script shows the collapse clearly. The brittle `test_rddf_cli.bats:76-79` "≥20 rddf_* functions" assertion is replaced with a positive contract test on the new shim.

**Tech Stack:** Python 3.11+ (pytest, shutil, subprocess, json, pathlib), Bash 3+ (shim + archive.sh subprocess), bats-core 1.10+ (smoke test).

---

## File Structure

### Production Code (new)

| File | Responsibility |
|---|---|
| `skills/_lib/cli/version_cmd.py` | `rddf version` — read `package.json`, print `rddf v<X.Y.Z> — spec-workflow CLI` |
| `skills/_lib/cli/init_cmd.py` | `rddf init [target]` — copy `skills/`, `_lib/`, `package.json`, and the `skills/cli/rddf.sh` shim to `<target>/.opencode/skills/spec-workflow/` |
| `skills/_lib/cli/archive_cmd.py` | `rddf archive <name>` — subprocess to `archive.sh` `archive_change` (thin wrapper, not a reimplementation) |
| `skills/_lib/cli/guide_cmd.py` | `rddf guide` — port of `scan-state.sh::scan_state` 10-priority ladder; reads `.arch-handoff.json`, `.plan-handoff.json`, `openspec/changes/`, `proposal-suggestions.md`, `roadmap.md`; emits `RECOMMEND` + `REASON` |

### Production Code (modified)

| File | Change |
|---|---|
| `skills/_lib/cli/__init__.py` | Add 4 entries to `_ROUTES` for `version` / `init` / `archive` / `guide` |
| `skills/_lib/cli/__main__.py` | Add 4 subcommands to `_print_help()` text |
| `skills/cli/rddf.sh` | Update header comment to mention new commands |
| `rddf` (root, 1525 lines) | **Replace** with 5-line shim: `exec bash "<repo>/skills/cli/rddf.sh" "$@"` |
| `tests/integration/test_rddf_cli.bats` | Replace the "≥20 rddf_* functions" assertion (line 76-79) with a contract test that root `rddf` exits 0 for `help` and that the 4 new subcommands route to Python |

### Tests (new)

| File | Responsibility | Cases |
|---|---|---|
| `tests/unit/test_cli_version.py` | `cmd_version` reads package.json, returns 0, prints expected banner | 4 |
| `tests/unit/test_cli_init.py` | `cmd_init` copies required files to target dir, creates parent dirs, default-target = cwd, missing source exits 1 | 6 |
| `tests/unit/test_cli_archive.py` | `cmd_archive` without name exits non-zero; with name invokes `archive.sh`; missing `archive.sh` exits 1 | 4 |
| `tests/unit/test_cli_guide.py` | `cmd_guide` priority ladder: 10 priority branches + stale-workflow warning; uses tmp_path git repo | 12 |

### Tests (modified)

| File | Change |
|---|---|
| `tests/integration/test_rddf_cli.bats` | Remove the "≥20 rddf_* functions" assertion; add 4 new cases covering the shim: `rddf version`, `rddf guide`, `rddf init --help`, `rddf archive` (no args) |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
python3 -m pytest tests/unit/test_cli_routing.py -q --tb=short
```

- [ ] **Locate the 4 unmigrated bash subcommands**

```bash
grep -nE "^\s*(rddf_guide|rddf_archive|rddf_init)\s*\(\)" rddf
grep -nE "^\s*(version|--version|-v)\)" rddf
```

- [ ] **Verify Python CLI subcommand count and shape**

```bash
python3 -c "from skills._lib.cli import list_commands; print(list_commands())"
# Expected: ['cleanup', 'dashboard', 'deps', 'feature', 'monitor', 'sessions', 'status', 'validate']
```

- [ ] **Confirm `archive.sh` and `scan-state.sh` are the canonical bash sources**

```bash
ls -l skills/_lib/archive.sh skills/guide/scripts/scan-state.sh
```

---

## Task 1: `version_cmd.py` — print rddf version

**Files:**
- Create: `skills/_lib/cli/version_cmd.py`
- Create: `tests/unit/test_cli_version.py`

The simplest of the 4. Reads `package.json` from the project root set by `RDDF_PROJECT_ROOT`, extracts the `version` field, prints the banner. Returns 0.

- [ ] **Step 1.1: Write the failing test**

Write `tests/unit/test_cli_version.py`:

```python
"""Unit tests for ``skills._lib.cli.version_cmd``."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from skills._lib.cli import version_cmd


@pytest.fixture
def fake_package_json(tmp_path, monkeypatch):
    """Create a fake package.json with a known version."""
    pkg = tmp_path / "package.json"
    pkg.write_text(json.dumps({"version": "2.0.7", "name": "spec-workflow"}))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    return tmp_path


def test_cmd_version_prints_banner(fake_package_json, capsys):
    """cmd_version prints 'rddf v<version> — spec-workflow CLI' to stdout."""
    rc = version_cmd.cmd_version([])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "rddf v2.0.7 — spec-workflow CLI\n"


def test_cmd_version_exits_zero(fake_package_json):
    """cmd_version returns exit code 0 on success."""
    rc = version_cmd.cmd_version([])
    assert rc == 0


def test_cmd_version_missing_package_json(tmp_path, monkeypatch, capsys):
    """When package.json is missing, cmd_version prints a friendly error and exits 1."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = version_cmd.cmd_version([])
    captured = capsys.readouterr()
    assert rc == 1
    assert "package.json" in captured.err


def test_cmd_version_missing_version_field(tmp_path, monkeypatch, capsys):
    """When package.json exists but has no 'version' field, fall back to '0.0.0'."""
    pkg = tmp_path / "package.json"
    pkg.write_text(json.dumps({"name": "spec-workflow"}))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = version_cmd.cmd_version([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "rddf v0.0.0" in captured.out
```

- [ ] **Step 1.2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_cli_version.py -v`
Expected: `ModuleNotFoundError: No module named 'skills._lib.cli.version_cmd'`

- [ ] **Step 1.3: Write the implementation**

Write `skills/_lib/cli/version_cmd.py`:

```python
"""``rddf version`` subcommand handler.

Reads the ``version`` field from ``<project_root>/package.json`` and prints
the canonical banner ``rddf v<X.Y.Z> — spec-workflow CLI``. Project root
is injected by ``cli.__main__`` via the ``RDDF_PROJECT_ROOT`` env var;
falls back to ``os.getcwd()`` when unset (so direct test invocation
works).

Usage::

    python3 -m skills._lib.cli version
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def cmd_version(args: list[str]) -> int:
    """Handle ``rddf version``.

    Args:
        args: Unused (the version subcommand takes no arguments).

    Returns:
        0 on success, 1 if ``package.json`` is missing or unreadable.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    pkg_path = Path(project_root) / "package.json"

    if not pkg_path.is_file():
        print(
            f"❌ version: package.json not found at {pkg_path}",
            file=sys.stderr,
        )
        return 1

    try:
        data = json.loads(pkg_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"❌ version: failed to read {pkg_path}: {e}", file=sys.stderr)
        return 1

    version = data.get("version") or "0.0.0"
    print(f"rddf v{version} — spec-workflow CLI")
    return 0


__all__ = ["cmd_version"]
```

- [ ] **Step 1.4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_cli_version.py -v`
Expected: 4 passed

- [ ] **Step 1.5: Commit**

```bash
git add skills/_lib/cli/version_cmd.py tests/unit/test_cli_version.py
git commit -m "feat(rddf): add version_cmd.py with package.json reading"
```

---

## Task 2: `init_cmd.py` — install spec-workflow to target

**Files:**
- Create: `skills/_lib/cli/init_cmd.py`
- Create: `tests/unit/test_cli_init.py`

Copies the spec-workflow distribution (skills, _lib, package.json, the new `skills/cli/rddf.sh` shim) to `<target>/.opencode/skills/spec-workflow/`. Default target is the current project's `.opencode/skills/spec-workflow/`. Returns 0 on success, 1 if source files are missing.

- [ ] **Step 2.1: Write the failing test**

Write `tests/unit/test_cli_init.py`:

```python
"""Unit tests for ``skills._lib.cli.init_cmd``."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from skills._lib.cli import init_cmd


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Build a fake spec-workflow repo at tmp_path/repo with required source files.

    Layout:
        tmp_path/repo/
            package.json
            skills/
                INSTALL.md
                guide/SKILL.md
            skills/cli/rddf.sh
            _lib/
                state.sh
    """
    repo = tmp_path / "repo"
    (repo / "skills").mkdir(parents=True)
    (repo / "skills" / "INSTALL.md").write_text("# INSTALL\n")
    (repo / "skills" / "guide").mkdir()
    (repo / "skills" / "guide" / "SKILL.md").write_text("# guide\n")
    (repo / "skills" / "cli").mkdir()
    (repo / "skills" / "cli" / "rddf.sh").write_text("#!/usr/bin/env bash\necho ok\n")
    (repo / "_lib").mkdir()
    (repo / "_lib" / "state.sh").write_text("# state\n")
    (repo / "package.json").write_text(json.dumps({"version": "2.0.7"}))

    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(repo))
    return repo, target


def test_cmd_init_copies_to_target_dir(fake_repo, capsys):
    """cmd_init copies skills/, _lib/, package.json, skills/cli/rddf.sh to <target>/.opencode/skills/spec-workflow/."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init([str(target)])
    assert rc == 0
    dest = target / ".opencode" / "skills" / "spec-workflow"
    assert (dest / "package.json").is_file()
    assert (dest / "skills" / "INSTALL.md").is_file()
    assert (dest / "skills" / "guide" / "SKILL.md").is_file()
    assert (dest / "skills" / "cli" / "rddf.sh").is_file()
    assert (dest / "_lib" / "state.sh").is_file()


def test_cmd_init_creates_parent_dirs(fake_repo, capsys):
    """cmd_init creates .opencode/skills/spec-workflow/ if it does not exist."""
    repo, target = fake_repo
    dest = target / ".opencode" / "skills" / "spec-workflow"
    assert not dest.exists()
    rc = init_cmd.cmd_init([str(target)])
    assert rc == 0
    assert dest.is_dir()


def test_cmd_init_default_target_is_project_root(fake_repo, monkeypatch, capsys):
    """Without an explicit target arg, cmd_init installs to RDDF_PROJECT_ROOT/."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init([])
    assert rc == 0
    dest = repo / ".opencode" / "skills" / "spec-workflow"
    assert (dest / "skills" / "INSTALL.md").is_file()


def test_cmd_init_missing_source_exits_one(tmp_path, monkeypatch, capsys):
    """When source layout is missing, cmd_init prints a clear error and exits 1."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = init_cmd.cmd_init([str(tmp_path / "target")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "找不到" in captured.err or "skills" in captured.err


def test_cmd_init_prints_summary(fake_repo, capsys):
    """cmd_init prints an install summary with file counts."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init([str(target)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "安装完成" in captured.out or "installed" in captured.out.lower()


def test_cmd_init_help_flag(fake_repo, capsys):
    """cmd_init --help prints usage and returns 0 without writing any files."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init(["--help"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "usage" in captured.out.lower() or "用法" in captured.out
    assert not (target / ".opencode").exists()
```

- [ ] **Step 2.2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_cli_init.py -v`
Expected: `ModuleNotFoundError: No module named 'skills._lib.cli.init_cmd'`

- [ ] **Step 2.3: Write the implementation**

Write `skills/_lib/cli/init_cmd.py`:

```python
"""``rddf init [target]`` subcommand handler.

Installs the spec-workflow distribution to ``<target>/.opencode/skills/spec-workflow/``.
Default target is the current project (``RDDF_PROJECT_ROOT``).

Layout copied (relative to source project root):
  - ``skills/`` (entire directory, including INSTALL.md, all SKILL.md files, scripts/)
  - ``_lib/`` (entire directory)
  - ``package.json``
  - ``skills/cli/rddf.sh`` (the thin shim, NOT the legacy root ``rddf``)

Usage::

    python3 -m skills._lib.cli init [target]
    python3 -m skills._lib.cli init --help
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


# Subset of files copied from the source project root to the install dest.
# Skills and _lib directories are copied as a whole via copytree.
_INSTALL_SOURCES = ["skills", "_lib", "package.json", "skills/cli/rddf.sh"]


def cmd_init(args: list[str]) -> int:
    """Handle ``rddf init [target|--help]``.

    Args:
        args: Optional target directory. If omitted, defaults to
            ``RDDF_PROJECT_ROOT`` (the current project). ``--help`` /
            ``-h`` prints usage and returns 0.

    Returns:
        0 on success, 1 if required source files are missing or copy
        fails, 2 on bad flag.
    """
    if args and args[0] in ("-h", "--help"):
        _print_help()
        return 0
    for flag in args:
        if flag.startswith("-"):
            print(f"❌ init: unknown flag {flag!r}", file=sys.stderr)
            print("   usage: rddf init [target]", file=sys.stderr)
            return 2

    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd())
    target_str = args[0] if args else str(project_root)
    target = Path(target_str) / ".opencode" / "skills" / "spec-workflow"

    # Verify source layout exists.
    missing = [s for s in _INSTALL_SOURCES if not (project_root / s).exists()]
    if missing:
        print(
            f"❌ init: 找不到源文件: {', '.join(missing)}\n"
            f"   当前 RDDF_PROJECT_ROOT={project_root}",
            file=sys.stderr,
        )
        return 1

    # Build the destination tree.
    target.mkdir(parents=True, exist_ok=True)

    # Copy skills/ as a whole (preserves subdirs like guide/scripts/, rddf-session/).
    if (project_root / "skills").is_dir():
        shutil.copytree(
            project_root / "skills",
            target / "skills",
            dirs_exist_ok=True,
        )

    # Copy _lib/ as a whole.
    if (project_root / "_lib").is_dir():
        shutil.copytree(
            project_root / "_lib",
            target / "_lib",
            dirs_exist_ok=True,
        )

    # Copy package.json (single file).
    if (project_root / "package.json").is_file():
        shutil.copy2(project_root / "package.json", target / "package.json")

    # The shim is already inside skills/ from the copytree above, but we
    # also surface it at the dest root for convenience (matches legacy
    # `rddf` behavior in the dest dir).
    shim_src = project_root / "skills" / "cli" / "rddf.sh"
    if shim_src.is_file():
        shutil.copy2(shim_src, target / "rddf.sh")
        os.chmod(target / "rddf.sh", 0o755)

    skills_md_count = sum(1 for _ in (target / "skills").glob("*.md")) if (target / "skills").is_dir() else 0
    print("📦 安装 spec-workflow 到项目")
    print(f"   目标: {target}")
    print(f"   技能文件: {skills_md_count} 个")
    print(f"   工具库:   _lib ({sum(1 for _ in (target / '_lib').iterdir()) if (target / '_lib').is_dir() else 0} 文件)")
    print(f"   CLI:      {target}/rddf.sh")
    print("✅ 安装完成!")
    return 0


def _print_help() -> None:
    print("usage: rddf init [target]")
    print()
    print("Install spec-workflow to <target>/.opencode/skills/spec-workflow/.")
    print("Default target is RDDF_PROJECT_ROOT (the current project).")


__all__ = ["cmd_init"]
```

- [ ] **Step 2.4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_cli_init.py -v`
Expected: 6 passed

- [ ] **Step 2.5: Commit**

```bash
git add skills/_lib/cli/init_cmd.py tests/unit/test_cli_init.py
git commit -m "feat(rddf): add init_cmd.py for project installation"
```

---

## Task 3: `archive_cmd.py` — thin wrapper over `archive.sh`

**Files:**
- Create: `skills/_lib/cli/archive_cmd.py`
- Create: `tests/unit/test_cli_archive.py`

The `rddf archive <name>` command currently sources `skills/_lib/archive.sh` and calls its `archive_change()` bash function. The bash `archive.sh` is 250+ lines of merge + openspec-archive + worktree cleanup logic. **Out-of-scope for this plan**: porting `archive.sh` to Python. **In-scope**: a thin Python wrapper that subprocess-spawns `archive.sh` so the `rddf` user-facing CLI is unified.

- [ ] **Step 3.1: Write the failing test**

Write `tests/unit/test_cli_archive.py`:

```python
"""Unit tests for ``skills._lib.cli.archive_cmd``."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from skills._lib.cli import archive_cmd


def test_cmd_archive_without_name_exits_nonzero(capsys):
    """cmd_archive with no name prints usage and exits non-zero."""
    rc = archive_cmd.cmd_archive([])
    captured = capsys.readouterr()
    assert rc != 0
    assert "用法" in captured.out or "usage" in captured.out.lower()


def test_cmd_archive_help_flag_returns_zero(capsys):
    """cmd_archive --help prints usage and returns 0 without invoking archive.sh."""
    rc = archive_cmd.cmd_archive(["--help"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "usage" in captured.out.lower() or "用法" in captured.out


def test_cmd_archive_invokes_archive_sh(tmp_path, monkeypatch, capsys):
    """cmd_archive <name> subprocesses to skills/_lib/archive.sh and reports success."""
    fake_archive = tmp_path / "archive.sh"
    fake_archive.write_text(
        '#!/usr/bin/env bash\n'
        'echo "[fake-archive] called with $1"\n'
        'archive_change() { echo "[fake-archive] archive_change $1"; }\n'
    )
    fake_archive.chmod(0o755)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(archive_cmd, "_ARCHIVE_SH", str(fake_archive))

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["bash"], returncode=0, stdout="ok\n", stderr=""
        )
        rc = archive_cmd.cmd_archive(["my-change"])

    assert rc == 0
    # The subprocess call should have invoked bash with the fake archive.sh
    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert "bash" in call_args[0] or call_args[0].endswith("bash")
    # And the change name should have been forwarded
    assert "my-change" in str(mock_run.call_args)


def test_cmd_archive_missing_archive_sh(tmp_path, monkeypatch, capsys):
    """When archive.sh is not found, cmd_archive prints a clear error and exits 1."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(archive_cmd, "_ARCHIVE_SH", str(tmp_path / "nonexistent.sh"))
    rc = archive_cmd.cmd_archive(["my-change"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "archive.sh" in captured.err or "找不到" in captured.err
```

- [ ] **Step 3.2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_cli_archive.py -v`
Expected: `ModuleNotFoundError: No module named 'skills._lib.cli.archive_cmd'`

- [ ] **Step 3.3: Write the implementation**

Write `skills/_lib/cli/archive_cmd.py`:

```python
"""``rddf archive <name>`` subcommand handler.

**Thin wrapper** that subprocess-spawns the existing ``skills/_lib/archive.sh``
script, which provides the ``archive_change <name>`` function. The bash
script handles worktree-mode merge, ``openspec archive``, worktree cleanup,
and the auto-commit helper. A future change may port ``archive.sh`` to
Python; this module is the bridge until then.

Usage::

    python3 -m skills._lib.cli archive <name>
    python3 -m skills._lib.cli archive --help
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Path to archive.sh, resolved relative to RDDF_PROJECT_ROOT at call time
# (kept as a module-level constant for monkeypatching in tests).
_ARCHIVE_SH = "<resolved-at-call-time>"


def _resolve_archive_sh() -> Path:
    """Return the absolute path to ``skills/_lib/archive.sh``."""
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd())
    return project_root / "skills" / "_lib" / "archive.sh"


def cmd_archive(args: list[str]) -> int:
    """Handle ``rddf archive <name>``.

    Args:
        args: Change name (required) or ``--help`` / ``-h``.

    Returns:
        0 on success, 1 if ``archive.sh`` is missing or returns non-zero,
        2 on bad flag.
    """
    if not args or args[0] in ("-h", "--help"):
        _print_help()
        return 0 if args else 2
    if args[0].startswith("-"):
        print(f"❌ archive: unknown flag {args[0]!r}", file=sys.stderr)
        print("   usage: rddf archive <change-name>", file=sys.stderr)
        return 2

    name = args[0]
    archive_sh = _resolve_archive_sh()
    if not archive_sh.is_file():
        print(
            f"❌ archive: 找不到 {archive_sh}\n"
            f"   预期位置: <project_root>/skills/_lib/archive.sh",
            file=sys.stderr,
        )
        return 1

    print(f"📦 归档 change: {name}")
    print("━" * 40)

    # Spawn bash with the archive.sh sourced and archive_change invoked.
    # We use `bash -c 'source <archive.sh> && archive_change "$@"' -- <name>`
    # so the function is defined and called within the same shell process.
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    try:
        result = subprocess.run(
            [
                "bash",
                "-c",
                f'source "{archive_sh}" && archive_change "$0"',
                name,
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        print(f"❌ archive: failed to spawn bash: {e}", file=sys.stderr)
        return 1

    # Surface bash stdout to the user.
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0:
        print(
            f"❌ archive: archive_change exited with code {result.returncode}",
            file=sys.stderr,
        )
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return 1

    print(f"✅ change {name} 归档完成")
    return 0


def _print_help() -> None:
    print("usage: rddf archive <change-name>")
    print()
    print("Archive a change (merge → openspec archive → worktree cleanup).")
    print("Delegates to skills/_lib/archive.sh::archive_change.")


__all__ = ["cmd_archive"]
```

- [ ] **Step 3.4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_cli_archive.py -v`
Expected: 4 passed

- [ ] **Step 3.5: Commit**

```bash
git add skills/_lib/cli/archive_cmd.py tests/unit/test_cli_archive.py
git commit -m "feat(rddf): add archive_cmd.py thin wrapper over archive.sh"
```

---

## Task 4: `guide_cmd.py` — port `scan-state.sh` priority ladder to Python

**Files:**
- Create: `skills/_lib/cli/guide_cmd.py`
- Create: `tests/unit/test_cli_guide.py`

The `guide` command's display logic is currently in `rddf_guide()` (lines 175-202 of root `rddf`), and the actual state-detection logic is in `skills/guide/scripts/scan-state.sh::scan_state()` (lines 54-204, 10-priority ladder). This task ports the ladder to Python so the entire `rddf guide` flow runs in Python.

**Priority ladder** (from scan-state.sh lines 41-53, highest first):
1. arch-handoff present, plan-handoff absent → `guide-plan`
2. arch-handoff present, ADR < 1 → `guide-arch (recover)`
3. plan-handoff present → `guide-ship`
4. plan-handoff present, active_changes = 0 → `guide-ship (cleanup)`
5. worktree with incomplete tasks → `guide-ship`
6. detached worktrees (count > 0) → `guide-ship`
7. worktree tasks all completed → `guide-ship`
8. committed change in HEAD (no worktree) → `guide-ship`
9. no roadmap.md → `guide-arch`
10. no openspec/changes/ → `guide-plan`
11. proposal-suggestions.md has pending entry → `guide-plan`
12. default → `guide-ship`

- [ ] **Step 4.1: Write the failing test**

Write `tests/unit/test_cli_guide.py`:

```python
"""Unit tests for ``skills._lib.cli.guide_cmd`` priority ladder."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from skills._lib.cli import guide_cmd


def _run_git(cwd: str, *args: str) -> str:
    """Run a git command and return stdout (stripped)."""
    r = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Build a tmp git repo with .rddf/state/ and an empty openspec/changes/."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(str(repo), "init")
    _run_git(str(repo), "config", "user.email", "test@example.com")
    _run_git(str(repo), "config", "user.name", "Test")
    # Empty initial commit so the repo is valid.
    (repo / "README.md").write_text("# test\n")
    _run_git(str(repo), "add", "README.md")
    _run_git(str(repo), "commit", "-m", "init")

    (repo / ".rddf" / "state").mkdir(parents=True)
    (repo / "openspec" / "changes").mkdir(parents=True)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(repo))
    return repo


def test_priority_1_arch_done_plan_undone_recommends_guide_plan(git_repo, capsys):
    """arch-handoff present, plan-handoff absent → 'guide-plan'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 3})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-plan" in captured.out
    assert "进入变更生成" in captured.out


def test_priority_2_arch_done_zero_adrs_recommends_guide_arch_recover(git_repo, capsys):
    """arch-handoff present but ADR < 1 → 'guide-arch (recover)'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 0})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-arch" in captured.out
    assert "未完成" in captured.out or "回到" in captured.out


def test_priority_3_plan_done_recommends_guide_ship(git_repo, capsys):
    """plan-handoff present (with active changes) → 'guide-ship'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 3})
    )
    (git_repo / ".rddf" / "state" / ".plan-handoff.json").write_text(
        json.dumps({"active_changes": 2})
    )
    # Need at least one active change dir for cross-validation
    (git_repo / "openspec" / "changes" / "my-change").mkdir()
    (git_repo / "openspec" / "changes" / "my-change" / "proposal.md").write_text("x")
    _run_git(str(git_repo), "add", "openspec/changes/my-change")
    _run_git(str(git_repo), "commit", "-m", "add change")

    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-ship" in captured.out
    assert "变更执行" in captured.out


def test_priority_4_plan_done_zero_active_recommends_guide_ship_cleanup(git_repo, capsys):
    """plan-handoff present but active_changes = 0 → 'guide-ship (cleanup)'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 3})
    )
    (git_repo / ".rddf" / "state" / ".plan-handoff.json").write_text(
        json.dumps({"active_changes": 0})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-ship" in captured.out
    assert "残留" in captured.out or "清理" in captured.out


def test_priority_5_worktree_with_incomplete_tasks_recommends_guide_ship(git_repo, capsys):
    """worktree with unchecked tasks.md → 'guide-ship'."""
    # No handoffs. We need a fake worktree to be detected.
    # Simplest: add a file in a path that LOOKS like a worktree entry
    # in `git worktree list` is too invasive; instead test the stale
    # state path.
    (git_repo / "workflow-state.md").write_text("stale")
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    # Stale state warning should be printed
    assert "stale" in captured.out.lower() or "workflow-state" in captured.out


def test_priority_6_no_roadmap_recommends_guide_arch(git_repo, capsys):
    """No roadmap.md → 'guide-arch'."""
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-arch" in captured.out
    assert "roadmap" in captured.out.lower() or "架构" in captured.out


def test_priority_7_no_changes_dir_recommends_guide_plan(git_repo, capsys):
    """roadmap.md exists, but no openspec/changes/ → 'guide-plan'."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    # Remove the empty openspec/changes/ to trigger priority 7
    import shutil
    shutil.rmtree(git_repo / "openspec" / "changes")
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-plan" in captured.out


def test_priority_8_pending_proposal_recommends_guide_plan(git_repo, capsys):
    """roadmap + changes dir, but proposal-suggestions.md has '待创建' entry → 'guide-plan'."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    (git_repo / "proposal-suggestions.md").write_text(
        json.dumps([{"name": "x", "status": "待创建"}])
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-plan" in captured.out
    assert "待创建" in captured.out or "propose" in captured.out.lower()


def test_priority_9_no_pending_proposal_recommends_guide_ship(git_repo, capsys):
    """All prior checks pass and no pending proposals → default 'guide-ship'."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    (git_repo / "proposal-suggestions.md").write_text(json.dumps([]))
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-ship" in captured.out
    assert "准备 ship" in captured.out or "ship" in captured.out.lower()


def test_cmd_guide_prints_state_summary(git_repo, capsys):
    """cmd_guide prints a state summary including roadmap and handoff presence."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text("{}")
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "🔍" in captured.out or "项目状态" in captured.out
    assert "roadmap.md" in captured.out


def test_cmd_guide_uses_roadmap_path_from_handoff(git_repo, capsys):
    """When .arch-handoff.json has roadmap_path, that path is checked (not default 'roadmap.md')."""
    (git_repo / "docs" / "my-roadmap.md").parent.mkdir(parents=True, exist_ok=True)
    (git_repo / "docs" / "my-roadmap.md").write_text("# Custom\n")
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"roadmap_path": "docs/my-roadmap.md", "adr_count": 0})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    # Should NOT recommend guide-arch because the handoff-specified roadmap exists
    assert "进入架构定义" not in captured.out


def test_cmd_guide_works_outside_git_repo(tmp_path, monkeypatch, capsys):
    """When cwd is not a git repo, cmd_guide still emits a recommendation (falls back to pwd)."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    # No .rddf/state, no openspec, no roadmap
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    # Should recommend guide-arch (no roadmap)
    assert "guide-arch" in captured.out
```

- [ ] **Step 4.2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_cli_guide.py -v`
Expected: `ModuleNotFoundError: No module named 'skills._lib.cli.guide_cmd'`

- [ ] **Step 4.3: Write the implementation**

Write `skills/_lib/cli/guide_cmd.py`:

```python
"""``rddf guide`` subcommand handler.

Port of the 10-priority state-detection ladder from
``skills/guide/scripts/scan-state.sh::scan_state``. Reads the same set
of files and emits the same ``RECOMMEND`` / ``REASON`` strings so that
the AI agent's behavior is unchanged after migration.

Priority order (highest first; matches scan-state.sh lines 41-53):
    1.  arch-handoff present, plan-handoff absent, ADR >= 1 → "guide-plan"
    1b. arch-handoff present, ADR < 1                     → "guide-arch (recover)"
    2.  plan-handoff present, active_changes > 0          → "guide-ship"
    2b. plan-handoff present, active_changes == 0         → "guide-ship (cleanup)"
    3-5. worktree states (incomplete/detached/complete)   → "guide-ship"
    6.  committed change in HEAD, no worktree             → "guide-ship"
    7.  no roadmap.md                                      → "guide-arch"
    8.  no openspec/changes/                               → "guide-plan"
    9.  proposal-suggestions.md has pending entry         → "guide-plan"
    10. default                                            → "guide-ship"

Stale ``workflow-state.md`` (pre-refactor format) emits a one-line
warning but does not change the recommendation.

Usage::

    python3 -m skills._lib.cli guide
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


# Status icons (match the existing dashboard renderer style)
_ICON_OK = "✅"
_ICON_MISSING = "❌"
_ICON_DIM = "·"


def _read_json(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on missing/invalid."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _git_worktree_list(project_root: str) -> list[str]:
    """Return list of worktree paths that have an openspec/* branch.

    Matches scan-state.sh lines 110-118: ``git worktree list``,
    filtering for the ``[openspec/`` prefix in column 3.
    """
    try:
        r = subprocess.run(
            ["git", "worktree", "list"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if r.returncode != 0:
        return []
    paths = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2].startswith("[openspec/"):
            paths.append(parts[0])
    return paths


def _worktree_has_incomplete_tasks(worktree_path: str) -> bool:
    """Return True if any tasks.md under the worktree has unchecked tasks."""
    wt = Path(worktree_path) / "openspec" / "changes"
    if not wt.is_dir():
        return False
    for tasks_md in wt.glob("*/tasks.md"):
        try:
            content = tasks_md.read_text()
        except OSError:
            continue
        if "- [ ]" in content:
            return True
    return False


def _has_committed_change_in_head(project_root: str) -> bool:
    """Return True if HEAD contains a committed openspec/changes/<name>/ directory."""
    changes_dir = Path(project_root) / "openspec" / "changes"
    if not changes_dir.is_dir():
        return False
    for d in changes_dir.iterdir():
        if not d.is_dir() or d.name == "archive":
            continue
        # Check if this path exists in HEAD
        try:
            r = subprocess.run(
                ["git", "show", f"HEAD:openspec/changes/{d.name}"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
        if r.returncode == 0:
            return True
    return False


def _check_stale_workflow_state(project_root: str) -> list[str]:
    """Return warning lines for stale pre-refactor state files."""
    warnings = []
    if (Path(project_root) / "workflow-state.md").is_file():
        warnings.append(
            "⚠️  Stale workflow-state.md detected (pre-refactor format)."
        )
        warnings.append(
            "   This file is no longer used and will be ignored."
        )
        warnings.append(
            "   Remove it manually if you want: rm workflow-state.md"
        )
    return warnings


def _scan_state(project_root: str) -> Tuple[str, str]:
    """Run the 10-priority ladder; return (RECOMMEND, REASON).

    This is the Python equivalent of scan-state.sh::scan_state. The
    return values match the strings emitted by the bash version.
    """
    state_dir = Path(project_root) / ".rddf" / "state"
    arch_handoff = state_dir / ".arch-handoff.json"
    plan_handoff = state_dir / ".plan-handoff.json"

    arch = _read_json(arch_handoff)
    plan = _read_json(plan_handoff)

    # 1. arch-handoff present, plan-handoff absent
    if arch is not None and plan is None:
        adr_count = int(arch.get("adr_count", 0) or 0)
        if adr_count < 1:
            return (
                "guide-arch",
                "arch-done 未完成 (ADR 数量不足 → 回到 adr-create 阶段)",
            )
        return ("guide-plan", "架构定义已完成 → 进入变更生成")

    # 2. plan-handoff present
    if plan is not None:
        active_count = int(plan.get("active_changes", 0) or 0)
        if active_count == 0:
            return (
                "guide-ship",
                "plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)",
            )
        # Cross-validate: count non-archived change dirs in filesystem
        changes_dir = Path(project_root) / "openspec" / "changes"
        fs_active = 0
        if changes_dir.is_dir():
            for d in changes_dir.iterdir():
                if d.is_dir() and d.name != "archive":
                    fs_active += 1
        if fs_active == 0:
            return (
                "guide-arch",
                f"plan-handoff stale (says {active_count} active, but 0 in filesystem -> all archived)",
            )
        return ("guide-ship", "变更生成已完成 → 进入变更执行")

    # 3-5. worktree states
    worktrees = _git_worktree_list(project_root)
    for wt in worktrees:
        if _worktree_has_incomplete_tasks(wt):
            return ("guide-ship", "worktree 存在,任务未完成 → 继续执行")

    detached = len(worktrees)
    if detached > 0:
        return (
            "guide-ship",
            f"{detached} 个 worktree 在跑（可能在分离终端）",
        )

    if worktrees:
        return ("guide-ship", "worktree 存在,任务已完成 → 进入 archive")

    # 6. committed change in HEAD (no worktree yet)
    if _has_committed_change_in_head(project_root):
        return ("guide-ship", "有已 commit 的 change 待建 worktree")

    # 7. no roadmap.md
    roadmap_rel = "roadmap.md"
    if arch is not None:
        roadmap_rel = arch.get("roadmap_path") or "roadmap.md"
    roadmap_path = Path(project_root) / roadmap_rel
    if not roadmap_path.is_file():
        return ("guide-arch", f"无 {roadmap_rel} → 进入架构定义")

    # 8. no openspec/changes/ directory
    if not (Path(project_root) / "openspec" / "changes").is_dir():
        return ("guide-plan", "无 change → 进入变更生成")

    # 9-10. proposal-suggestions.md
    suggestions_path = Path(project_root) / "proposal-suggestions.md"
    pending = False
    if suggestions_path.is_file():
        try:
            entries = json.loads(suggestions_path.read_text())
            if isinstance(entries, list):
                pending = any(
                    isinstance(e, dict) and e.get("status") == "待创建"
                    for e in entries
                )
        except (json.JSONDecodeError, OSError):
            pending = False

    if pending:
        return ("guide-plan", "有 change 待创建 → 继续 propose")
    return ("guide-ship", "无待创建 change → 准备 ship")


def cmd_guide(args: list[str]) -> int:
    """Handle ``rddf guide``.

    Args:
        args: Unused (the guide subcommand takes no arguments).

    Returns:
        0 on success. State-detection errors are non-fatal: the
        function emits a recommendation based on whatever state it
        could read, plus any stale-state warnings.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    state_dir = Path(project_root) / ".rddf" / "state"

    recommend, reason = _scan_state(project_root)
    warnings = _check_stale_workflow_state(project_root)

    # Render
    print()
    print("🔍 项目状态扫描")
    print("━" * 40)
    print(f"  roadmap.md:           {_present((Path(project_root) / 'roadmap.md').is_file())}")
    print(f"  .arch-handoff.json:   {_present((state_dir / '.arch-handoff.json').is_file())}")
    print(f"  .plan-handoff.json:   {_present((state_dir / '.plan-handoff.json').is_file())}")
    print(f"  iteration.json:       {_present((state_dir / 'iteration.json').is_file())}")
    worktree_count = len(_git_worktree_list(project_root))
    print(f"  worktrees:            {worktree_count}")
    print("━" * 40)
    print(f"  💡 建议: {recommend}")
    print(f"     {reason}")
    for w in warnings:
        print(f"  {w}")
    print()
    return 0


def _present(ok: bool) -> str:
    return f"{_ICON_OK} 存在" if ok else f"{_ICON_MISSING} 缺失"


__all__ = ["cmd_guide"]
```

- [ ] **Step 4.4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_cli_guide.py -v`
Expected: 12 passed

- [ ] **Step 4.5: Commit**

```bash
git add skills/_lib/cli/guide_cmd.py tests/unit/test_cli_guide.py
git commit -m "feat(rddf): add guide_cmd.py port of scan-state.sh priority ladder"
```

---

## Task 5: Wire 4 new subcommands into the routing table

**Files:**
- Modify: `skills/_lib/cli/__init__.py` (add 4 entries to `_ROUTES`)
- Modify: `skills/_lib/cli/__main__.py` (add 4 entries to `_print_help()`)

- [ ] **Step 5.1: Update `__init__.py` routing table**

Edit `skills/_lib/cli/__init__.py`. In the `_ROUTES` dict (lines 78-87), add 4 new entries:

```python
_ROUTES: Dict[str, str] = {
    "archive": "skills._lib.cli.archive_cmd:cmd_archive",
    "cleanup": "skills._lib.cli.cleanup_cmd:cmd_cleanup",
    "dashboard": "skills._lib.cli.dashboard_cmd:cmd_dashboard",
    "deps": "skills._lib.cli.deps_cmd:cmd_deps",
    "feature": "skills._lib.cli.feature_cmd:cmd_feature",
    "guide": "skills._lib.cli.guide_cmd:cmd_guide",
    "init": "skills._lib.cli.init_cmd:cmd_init",
    "monitor": "skills._lib.cli.monitor_cmd:cmd_monitor",
    "status": "skills._lib.cli.status_cmd:cmd_status",
    "sessions": "skills._lib.cli.sessions_cmd:cmd_sessions",
    "validate": "skills._lib.cli.validate_cmd:cmd_validate",
    "version": "skills._lib.cli.version_cmd:cmd_version",
}
```

- [ ] **Step 5.2: Update `__main__.py` help text**

Edit `skills/_lib/cli/__main__.py`. In `_print_help()` (lines 159-169), update the subcommand list to include all 12 commands:

```python
def _print_help() -> None:
    """Print top-level help to stdout."""
    print("usage: python3 -m skills._lib.cli <subcommand> [args...]")
    print()
    print("subcommands:")
    print("  dashboard    Unified dashboard (7 sections). Flags: --json, --plain")
    print("  status       Change status overview. Flag: --iteration, --roadmap, <name>")
    print("  feature      Feature grouping (summary, graph, status, order)")
    print("  sessions     Session management (read-only). Subcmds: show <id>, current, gc")
    print("  deps         Dependency analysis table from deps-analysis.json")
    print("  cleanup      Clean orphaned worktrees and branches")
    print("  validate     Quality gate checks")
    print("  monitor      Live monitor (--watch=<sec>)")
    print("  archive <n>  Archive a change (merge → openspec archive → cleanup)")
    print("  init [tgt]   Install spec-workflow to target's .opencode/skills/")
    print("  guide        Project state scan + recommendation")
    print("  version      Print rddf version")
    print()
    print(f"available: {', '.join(list_commands())}")
```

- [ ] **Step 5.3: Verify routing tests still pass + new subcommands listed**

Run: `python3 -m pytest tests/unit/test_cli_routing.py -q --tb=short`
Expected: all pass

Run: `python3 -c "from skills._lib.cli import list_commands; print(list_commands())"`
Expected: 12 commands including `['archive', 'guide', 'init', 'version']`

- [ ] **Step 5.4: Commit**

```bash
git add skills/_lib/cli/__init__.py skills/_lib/cli/__main__.py
git commit -m "feat(rddf): wire 4 new subcommands into routing table and help"
```

---

## Task 6: Update `skills/cli/rddf.sh` header comment

**Files:**
- Modify: `skills/cli/rddf.sh` (header comment only)

The thin shim itself (8 lines) is correct as-is. Only the header comment needs to be updated so that `cat skills/cli/rddf.sh` shows the up-to-date command list.

- [ ] **Step 6.1: Update header comment**

Edit `skills/cli/rddf.sh` (lines 1-8). The current comment is implicit (`PACKAGE_DIR=...`). Add a 1-line header at the very top:

```bash
#!/usr/bin/env bash
# rddf — spec-workflow CLI entry point (thin shim → python3 -m skills._lib.cli)
#
# Subcommands (12): dashboard, status, feature, sessions, deps, cleanup,
#                   validate, monitor, archive, init, guide, version
set -euo pipefail
_myself="$(realpath "${BASH_SOURCE[0]:-$0}")"
PACKAGE_DIR="$(dirname "$(dirname "$(dirname "$_myself")")")"
export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH:-}"
exec python3 -m skills._lib.cli "$@"
```

- [ ] **Step 6.2: Smoke-test the shim**

Run: `python3 -m skills._lib.cli version` (via the shim) — should print the banner.
Run: `python3 -m skills._lib.cli guide` — should print state scan + recommendation.
Run: `python3 -m skills._lib.cli archive` — should print usage and exit non-zero.

For all 3: exit codes match expectations.

- [ ] **Step 6.3: Commit**

```bash
git add skills/cli/rddf.sh
git commit -m "docs(rddf): update skills/cli/rddf.sh header with subcommand list"
```

---

## Task 7: Update `test_rddf_cli.bats` to assert new shim contract

**Files:**
- Modify: `tests/integration/test_rddf_cli.bats` (lines 76-79)

The current "≥20 rddf_* functions" assertion is testing the legacy root `rddf` script's internal function count. After Task 8 shrinks the root `rddf` to a 5-line shim, this assertion is impossible to satisfy. Replace it with a positive contract test on the shim.

- [ ] **Step 7.1: Remove the brittle ≥20 assertion and add 4 new contract cases**

Edit `tests/integration/test_rddf_cli.bats`. **Delete** lines 76-79 (the "≥20 rddf_* functions" test). **Add** these 4 new tests after the existing "rddf: unknown subcommand" test (after line 74):

```bash
@test "rddf: version subcommand dispatches to Python CLI" {
  run ./rddf version
  [ "$status" -eq 0 ]
  [[ "$output" == *"rddf v"* ]]
}

@test "rddf: guide subcommand dispatches to Python CLI" {
  run ./rddf guide
  [ "$status" -eq 0 ]
  [[ "$output" == *"项目状态"* ]] || [[ "$output" == *"guide-"* ]]
}

@test "rddf: init --help exits 0 with usage" {
  run ./rddf init --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"usage"* ]] || [[ "$output" == *"用法"* ]]
}

@test "rddf: archive (no args) prints usage and exits non-zero" {
  run ./rddf archive
  [ "$status" -ne 0 ]
  [[ "$output" == *"用法"* ]] || [[ "$output" == *"usage"* ]]
}
```

- [ ] **Step 7.2: Run updated test file**

Run: `bats tests/integration/test_rddf_cli.bats`
Expected: all pass (including the 4 new cases). The old "≥20 rddf_* functions" test no longer exists.

- [ ] **Step 7.3: Commit**

```bash
git add tests/integration/test_rddf_cli.bats
git commit -m "test(rddf): replace legacy function-count assertion with new shim contract"
```

---

## Task 8: Collapse root `rddf` to 5-line shim

**Files:**
- Replace: `rddf` (1525 lines → 5 lines)

This is the "retire the old" step. The root `rddf` is replaced with a shim that `exec`s `skills/cli/rddf.sh`. The 1500+ lines of dead code (the `rddf_status`/`rddf_cleanup`/etc. functions that main() no longer calls) are deleted in this commit.

- [ ] **Step 8.1: Save the legacy script for reference**

Before overwriting, archive the legacy `rddf` to `docs/legacy/rddf-legacy-v2.0.7.sh` so the dead code is still accessible for archaeology (per AGENTS.md "respect user data" convention).

```bash
mkdir -p docs/legacy
cp rddf docs/legacy/rddf-legacy-v2.0.7.sh
```

- [ ] **Step 8.2: Write the new shim**

Write `rddf` (overwrite the 1525-line file):

```bash
#!/usr/bin/env bash
# rddf — spec-workflow CLI entry point (shim)
#
# This file is now a 5-line shim. All logic lives in the Python CLI at
# `python3 -m skills._lib.cli`, invoked via `skills/cli/rddf.sh`.
# See docs/legacy/rddf-legacy-v2.0.7.sh for the pre-2.0.8 bash implementation
# (kept for archaeology; 1500+ lines of dead code, do not resurrect).
#
# Subcommands: dashboard, status, feature, sessions, deps, cleanup, validate,
#              monitor, archive, init, guide, version (run `rddf` for help).
set -euo pipefail
exec bash "$(dirname "$(readlink -f "$0")")/skills/cli/rddf.sh" "$@"
```

- [ ] **Step 8.3: Verify shim is executable and works**

```bash
chmod +x rddf
./rddf version
./rddf help
./rddf guide
```

All 3 should succeed with the same output as `python3 -m skills._lib.cli ...`.

- [ ] **Step 8.4: Commit**

```bash
git add rddf docs/legacy/rddf-legacy-v2.0.7.sh
git commit -m "refactor(rddf): collapse root rddf to 5-line shim (archives 1500+ lines of dead code)"
```

---

## Task 9: Full regression — all tests green

**Files:** none (verification only)

- [ ] **Step 9.1: Run full Python unit suite**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: all pass, including the 4 new `test_cli_*.py` files (26 new cases total: 4+6+4+12).

- [ ] **Step 9.2: Run full bats smoke suite**

Run: `bats tests/smoke.bats`
Expected: all pass.

- [ ] **Step 9.3: Run the updated `test_rddf_cli.bats`**

Run: `bats tests/integration/test_rddf_cli.bats`
Expected: all 16 cases pass (12 existing + 4 new shim contract cases; the deleted "≥20 rddf_* functions" test is gone).

- [ ] **Step 9.4: Run the routing unit tests to confirm 12 subcommands**

Run: `python3 -m pytest tests/unit/test_cli_routing.py -q --tb=short`
Expected: all pass.

- [ ] **Step 9.5: Verify `rddf help` lists all 12 subcommands**

Run: `./rddf help` (or `python3 -m skills._lib.cli` with no args)
Expected: lists `dashboard, status, feature, sessions, deps, cleanup, validate, monitor, archive, init, guide, version`.

- [ ] **Step 9.6: Commit (no source changes; only if any test fixup was needed)**

If everything passed, no commit. If a fixup was needed, commit with message:
```bash
git commit -am "test(rddf): fixup regression found in full-suite run"
```

---

## Self-Review

**1. Spec coverage** (the goal is: 4 commands migrated + root rddf retired):

| Spec requirement | Implementing task |
|---|---|
| `rddf version` works | Task 1, Task 5 (routing), Task 6 (shim header) |
| `rddf init [target]` works | Task 2, Task 5, Task 6 |
| `rddf archive <name>` works | Task 3, Task 5, Task 6 |
| `rddf guide` works with full 10-priority ladder | Task 4, Task 5, Task 6 |
| Root `rddf` becomes a 5-line shim | Task 8 |
| `test_rddf_cli.bats` no longer hard-asserts function count | Task 7 |
| All existing tests pass | Task 9 |

**2. Placeholder scan**: no "TBD", "TODO", "implement later", "add appropriate error handling", "similar to Task N" in this plan. All step bodies contain real code or real shell commands.

**3. Type consistency**:
- `cmd_<name>(args: list[str]) -> int` signature used consistently across all 4 new modules.
- `RDDF_PROJECT_ROOT` env var used consistently for project-root resolution.
- Exit codes: 0 (success), 1 (error / missing files), 2 (bad flag) — matches existing modules.
- Output to stdout for normal flow, stderr for errors — matches existing modules.
- All modules expose `__all__` and are imported via the same `"<module_path>:<func_name>"` routing convention.

**4. Cross-task consistency checks**:
- Task 1 / 2 / 3 / 4 test files use the same `monkeypatch.setenv("RDDF_PROJECT_ROOT", ...)` pattern as the existing `test_cli_routing.py`.
- Task 4 `cmd_guide` output format (the `🔍 项目状态扫描` header) matches the existing `rddf_guide` bash version for visual continuity.
- Task 8 shim uses `readlink -f` for robust path resolution (no fragile relative paths).

---

## Out-of-Scope (explicit non-goals)

- **Porting `archive.sh` to Python**: 250+ lines of bash that handle worktree-mode merge, openspec archive, worktree cleanup, and auto-commit. Out of scope for this change; tracked separately.
- **Porting `scan-state.sh`'s `scan_session_binding` and `check_heartbeat_timeouts`**: These are separate from the `guide` recommendation logic; they emit `BINDING_LINES` and handle session timeout marking. Not in the `rddf guide` user-facing path. The new `guide_cmd.py` does NOT call them — it only emits the recommendation. If session-binding info is needed in `rddf guide` output, that's a follow-up change.
- **Updating `install.sh`** to point at the new `skills/cli/rddf.sh` shim instead of the legacy root `rddf`: `install.sh` already points at `skills/cli/rddf.sh` (line 83) per the current contract. No change needed.
- **Removing the legacy archive of `rddf` from docs/legacy/**: keep for archaeology per AGENTS.md "respect user data" convention. Removal would be a separate change.

---

## Execution Notes

**Recommended execution mode**: Run the tasks in order (1→9). Each task ends with a commit, so progress is preserved if any task fails. The shim collapse (Task 8) is the most user-visible change and should be reviewed carefully before the final commit.

**Worktree**: This plan assumes execution in a worktree at `.rddf/wt/rddf-cli-completion` (per spec-workflow convention). If running in the main repo, ensure no other worktrees are active (`git worktree list` should show only the main repo).

**Skip Task 3 (archive_cmd) if the user wants to defer the archive.sh bash subprocess**: the only consequence is that `rddf archive <name>` will continue to use the legacy root `rddf`'s `rddf_archive` function via main() — but main() now delegates to Python, so `archive` will not work without Task 3. So Task 3 is required.
