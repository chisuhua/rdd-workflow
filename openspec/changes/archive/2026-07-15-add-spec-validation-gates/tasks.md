---
SCOPE: shared
STATUS: PROPOSED
---

# Tasks: add-spec-validation-gates

> **Goal**: Add 2 validator utilities (`validate_baseline.py` + `validate_delta_targets.py`) and wire them into propose/guide-plan/guide-ship skills. Catches baseline fabrication and MODIFIED-on-empty-spec failures before commit/archive.
> **Risk**: low (additive, fail-fast, no API changes).
> **Estimated effort**: 1-1.5 d.

## 1. Pre-flight

- [ ] 1.1 Verify baseline tests pass before changes

```bash
cd /workspace/project/spec-workflow
pip install -r requirements.txt
python3 -m pytest tests/unit/ -q --tb=short
bats tests/smoke.bats
```

Expected: all existing tests pass.

- [ ] 1.2 Locate gate.py hooks for plan-done/ship-done checks

```bash
grep -n "plan_done\|ship_done\|arch_done" skills/_lib/gate.py | head -10
```

Expected: find `default_checks` dict where new checks will be added.

- [ ] 1.3 Identify existing baseline claim patterns (research)

```bash
# Look at all active changes to see baseline claim styles
for f in openspec/changes/*/.openspec.yaml; do
  echo "=== $f ==="
  awk '/^baseline:/,/^[a-z]/{print}' "$f" 2>/dev/null | head -20
done | head -80
```

Expected: observe that baseline values are mostly free-text descriptions; no current convention for structured prefixes.

## 2. Apply change

### Task 2.1: Create validate_baseline.py

**Files:**
- Create: `skills/_lib/validate_baseline.py`
- Test: `tests/unit/test_validate_baseline.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_validate_baseline.py`:

```python
"""Unit tests for validate_baseline.py."""
import pytest
import subprocess
import tempfile
import os
import yaml
from pathlib import Path


def run_validator(change_dir: Path, change_name: str) -> tuple[int, str]:
    """Run validate_baseline.py as subprocess. Return (exit_code, stdout+stderr)."""
    result = subprocess.run(
        ["python3", str(change_dir / "skills/_lib/validate_baseline.py"), change_name],
        capture_output=True, text=True, cwd=change_dir,
    )
    return result.returncode, result.stdout + result.stderr


def make_change_with_baseline(tmpdir: Path, baseline: dict) -> Path:
    """Create a fake change dir with .openspec.yaml containing baseline."""
    openspec_dir = tmpdir / "openspec/changes/test-change"
    openspec_dir.mkdir(parents=True)
    spec_dir = openspec_dir / "specs/test-cap"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# test-cap Specification\n## Purpose\nTBD\n")
    yaml_content = {
        "schema": "spec-driven",
        "name": "test-change",
        "baseline": baseline,
    }
    (openspec_dir / ".openspec.yaml").write_text(yaml.dump(yaml_content))
    return tmpdir


def test_file_exists_claim_passes_when_path_exists(tmp_path):
    fake_file = tmp_path / "src/exists.cpp"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("// exists")
    make_change_with_baseline(tmp_path, {
        "exists-file": f"file-exists:{fake_file.relative_to(tmp_path)}"
    })
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_file_exists_claim_fails_when_path_missing(tmp_path):
    make_change_with_baseline(tmp_path, {
        "missing-file": "file-exists:does/not/exist.cpp"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "does/not/exist.cpp" in out
    assert "file-exists" in out


def test_symbol_exists_claim_passes_when_match(tmp_path):
    src = tmp_path / "src/foo.cpp"
    src.parent.mkdir(parents=True)
    src.write_text("class FooBar {}")
    make_change_with_baseline(tmp_path, {
        "symbol": f"symbol-exists:{src.relative_to(tmp_path)}:FooBar"
    })
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_symbol_exists_claim_fails_when_no_match(tmp_path):
    src = tmp_path / "src/foo.cpp"
    src.parent.mkdir(parents=True)
    src.write_text("class Bar {}")
    make_change_with_baseline(tmp_path, {
        "symbol": f"symbol-exists:{src.relative_to(tmp_path)}:FooBar"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "FooBar" in out


def test_git_history_claim_passes_for_existing_symbol(tmp_path):
    # Set up minimal git repo with a commit
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("class RealSymbol {}")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add real symbol"], cwd=tmp_path, check=True)

    make_change_with_baseline(tmp_path, {
        "history": "git-history:RealSymbol"
    })
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_free_text_baseline_passes_with_warning(tmp_path):
    make_change_with_baseline(tmp_path, {
        "free-text": "this is just a description, no structured claim"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 0  # pass
    assert "unverifiable" in out.lower() or "skipped" in out.lower()


def test_v1_g_gpu_client_baseline_fails_regression(tmp_path):
    """Regression test: v1 spec claimed 'CudaStub g_cuda_stub; exists' but it didn't.
    This validator MUST catch it."""
    # src/test_fixture/cuda_stub.cpp exists but does NOT contain 'CudaStub g_cuda_stub;'
    stub = tmp_path / "src/test_fixture/cuda_stub.cpp"
    stub.parent.mkdir(parents=True)
    stub.write_text("// CudaStub class definition\nclass CudaStub {};\n")
    make_change_with_baseline(tmp_path, {
        "g_cuda_stub static instance": f"git-history:CudaStub g_cuda_stub"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "CudaStub g_cuda_stub" in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_validate_baseline.py -v --tb=short
```

Expected: all 7 tests fail with `ModuleNotFoundError` or `FileNotFoundError` (validator script doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/validate_baseline.py`:

```python
#!/usr/bin/env python3
"""validate_baseline.py - Verify .openspec.yaml baseline claims.

Catches fabricated baseline claims (e.g., claiming a static symbol exists
when it doesn't) before they propagate to implementation.

Exit codes:
  0 = pass (all verifiable claims hold; unverifiable skipped with warning)
  1 = hard fail (at least one verifiable claim is false)
  2 = soft warn (no failures, but unverifiable claims present)

Supported claim prefixes (baseline values starting with):
  file-exists:<path>     — file must exist at <path> (relative to change-root)
  symbol-exists:<path>:<regex> — file at <path> must match <regex>
  git-history:<symbol>   — `git log -S "<symbol>"` must return ≥1 commit
  (no prefix)            — free-text, treated as unverifiable, passed with warning
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml


def find_change_dir(change_name: str, search_root: Path) -> Path:
    """Find the change directory by name."""
    for cand in (search_root / "openspec/changes").iterdir():
        if cand.is_dir() and cand.name == change_name:
            return cand
    print(f"❌ Change '{change_name}' not found in {search_root}/openspec/changes/", file=sys.stderr)
    sys.exit(1)


def verify_file_exists(rel_path: str, change_root: Path) -> tuple[bool, str]:
    """Verify file exists. Return (pass, message)."""
    full = (change_root / rel_path).resolve()
    if full.exists() and full.is_file():
        return True, f"file-exists:{rel_path} OK ({full})"
    return False, f"file-exists:{rel_path} FAILED (not found: {full})"


def verify_symbol_exists(rel_path: str, pattern: str, change_root: Path) -> tuple[bool, str]:
    """Verify file contains symbol matching regex. Return (pass, message)."""
    full = (change_root / rel_path).resolve()
    if not full.exists():
        return False, f"symbol-exists:{rel_path}:{pattern} FAILED (file not found: {full})"
    try:
        content = full.read_text()
    except Exception as e:
        return False, f"symbol-exists:{rel_path}:{pattern} FAILED (read error: {e})"
    if re.search(pattern, content):
        return True, f"symbol-exists:{rel_path}:{pattern} OK"
    return False, f"symbol-exists:{rel_path}:{pattern} FAILED (pattern not found)"


def verify_git_history(symbol: str, change_root: Path, timeout: int = 10) -> tuple[bool, str]:
    """Verify symbol exists in git history. Return (pass, message)."""
    try:
        proc = subprocess.run(
            ["git", "log", "-S", symbol, "--all", "--oneline"],
            capture_output=True, text=True, timeout=timeout, cwd=change_root,
        )
    except subprocess.TimeoutExpired:
        return False, f"git-history:{symbol} FAILED (git log timeout after {timeout}s)"
    except FileNotFoundError:
        return False, f"git-history:{symbol} FAILED (git not installed)"
    if proc.returncode != 0:
        return False, f"git-history:{symbol} FAILED (git error: {proc.stderr.strip()})"
    commits = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(commits) >= 1:
        return True, f"git-history:{symbol} OK ({len(commits)} commits)"
    return False, f"git-history:{symbol} FAILED (no commits found)"


def validate_baseline(change_name: str, search_root: Path = None) -> int:
    """Validate .openspec.yaml baseline claims. Return exit code."""
    if search_root is None:
        search_root = Path.cwd()
    change_dir = find_change_dir(change_name, search_root)
    openspec_yaml = change_dir / ".openspec.yaml"
    if not openspec_yaml.exists():
        print(f"❌ {change_name}: .openspec.yaml not found at {openspec_yaml}", file=sys.stderr)
        return 1

    try:
        with openspec_yaml.open() as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"❌ {change_name}: .openspec.yaml parse error: {e}", file=sys.stderr)
        return 1

    baseline = data.get("baseline")
    if not baseline or not isinstance(baseline, dict):
        print(f"ℹ️  {change_name}: no baseline claims (pass)", file=sys.stderr)
        return 0

    failures = []
    warnings = []
    for claim_key, claim_value in baseline.items():
        if not isinstance(claim_value, str):
            warnings.append(f"  ⚠️  baseline.{claim_key}: non-string value (skipped)")
            continue
        if claim_value.startswith("file-exists:"):
            path = claim_value[len("file-exists:"):].strip()
            ok, msg = verify_file_exists(path, change_dir.parent.parent)
            if not ok:
                failures.append(f"  ❌ baseline.{claim_key}: {msg}\n     Fix: create the file or correct the path")
            else:
                print(f"  ✅ {msg}")
        elif claim_value.startswith("symbol-exists:"):
            rest = claim_value[len("symbol-exists:"):].strip()
            parts = rest.split(":", 1)
            if len(parts) != 2:
                failures.append(f"  ❌ baseline.{claim_key}: malformed symbol-exists (expected path:regex)")
                continue
            path, pattern = parts
            ok, msg = verify_symbol_exists(path, pattern, change_dir.parent.parent)
            if not ok:
                failures.append(f"  ❌ baseline.{claim_key}: {msg}\n     Fix: add symbol to file or correct pattern")
            else:
                print(f"  ✅ {msg}")
        elif claim_value.startswith("git-history:"):
            symbol = claim_value[len("git-history:"):].strip()
            ok, msg = verify_git_history(symbol, change_dir.parent.parent)
            if not ok:
                failures.append(f"  ❌ baseline.{claim_key}: {msg}\n     Fix: add the symbol or remove this claim")
            else:
                print(f"  ✅ {msg}")
        else:
            warnings.append(f"  ⚠️  baseline.{claim_key}: unverifiable free-text (skipped)")

    if failures:
        print(f"\n❌ {change_name}: {len(failures)} baseline claim(s) failed:", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        if warnings:
            print(f"\n⚠️  {len(warnings)} unverifiable claim(s) (not failures):", file=sys.stderr)
            for w in warnings:
                print(w, file=sys.stderr)
        return 1

    if warnings:
        print(f"\n⚠️  {change_name}: pass with {len(warnings)} unverifiable claim(s):", file=sys.stderr)
        for w in warnings:
            print(w, file=sys.stderr)
        return 2

    print(f"✅ {change_name}: all baseline claims verified")
    return 0


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_baseline.py <change-name>", file=sys.stderr)
        sys.exit(2)
    sys.exit(validate_baseline(sys.argv[1]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_validate_baseline.py -v --tb=short
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/validate_baseline.py tests/unit/test_validate_baseline.py
git commit -m "feat(_lib): add validate_baseline.py with TDD tests

- Validates .openspec.yaml baseline claims (file/symbol/git-history prefixes)
- Catches fabricated baselines (e.g., g-gpu-client-default-stub-init v1)
- Exit codes: 0=pass, 1=hard fail, 2=soft warn
- 7 unit tests covering all claim patterns + regression test for v1 incident"
```

### Task 2.2: Create validate_delta_targets.py

**Files:**
- Create: `skills/_lib/validate_delta_targets.py`
- Test: `tests/unit/test_validate_delta_targets.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_validate_delta_targets.py`:

```python
"""Unit tests for validate_delta_targets.py."""
import pytest
import subprocess
from pathlib import Path


def run_validator(change_dir: Path, change_name: str) -> tuple[int, str]:
    result = subprocess.run(
        ["python3", str(change_dir / "skills/_lib/validate_delta_targets.py"), change_name],
        capture_output=True, text=True, cwd=change_dir,
    )
    return result.returncode, result.stdout + result.stderr


def setup_change_with_spec(tmp_path: Path, cap_name: str, spec_content: str,
                            main_specs: dict = None) -> Path:
    """Create change dir + spec.md + optional main specs/."""
    change = tmp_path / f"openspec/changes/test-change/specs/{cap_name}"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(spec_content)
    if main_specs:
        for ms_name, ms_content in main_specs.items():
            ms = tmp_path / f"openspec/specs/{ms_name}"
            ms.mkdir(parents=True)
            (ms / "spec.md").write_text(ms_content)
    return tmp_path


def test_added_section_passes_when_no_main_spec(tmp_path):
    setup_change_with_spec(tmp_path, "new-cap", """\
# new-cap Specification
## ADDED Requirements
### Requirement: x
Body.
""")
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0  # ADDED is OK without main spec


def test_modified_section_fails_when_target_spec_missing(tmp_path):
    setup_change_with_spec(tmp_path, "new-cap", """\
# new-cap Specification
## MODIFIED Requirements
### Requirement: x
Body modifying nonexistent-target.
""")
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "nonexistent-target" in out or "MODIFIED" in out


def test_modified_section_passes_when_target_spec_exists(tmp_path):
    setup_change_with_spec(
        tmp_path, "new-cap",
        spec_content="""\
# new-cap Specification
## MODIFIED Requirements
### Requirement: x
Body modifying existing-target.
""",
        main_specs={"existing-target": "# existing-target Specification\n## Purpose\nTBD\n"},
    )
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_renamed_section_fails_when_source_spec_missing(tmp_path):
    setup_change_with_spec(tmp_path, "new-cap", """\
# new-cap Specification
## RENAMED Requirements
### Requirement: old-name -> new-name
Body.
""")
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "RENAMED" in out or "old-name" in out


def test_v2_g_gpu_client_meyers_fallback_regression(tmp_path):
    """Regression test: v2 spec had MODIFIED section for non-existent capability.
    This validator MUST catch it before archive abort."""
    setup_change_with_spec(tmp_path, "shim-default-init-fallback", """\
# shim-default-init-fallback Specification
## MODIFIED Requirements
### Requirement: shim functions return SUCCESS instead of NOT_INITIALIZED
Body.
""")
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "MODIFIED" in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/unit/test_validate_delta_targets.py -v --tb=short
```

Expected: all 5 tests fail (validator script doesn't exist).

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/validate_delta_targets.py`:

```python
#!/usr/bin/env python3
"""validate_delta_targets.py - Verify spec.md MODIFIED/RENAMED targets exist.

Catches archive aborts caused by MODIFIED or RENAMED sections targeting
capabilities that don't exist in main openspec/specs/.

Exit codes:
  0 = pass (no invalid MODIFIED/RENAMED targets)
  1 = hard fail (at least one target missing)

How it works:
  - Parses spec.md for ## MODIFIED Requirements and ## RENAMED Requirements sections
  - For MODIFIED: each requirement body should target an existing capability
    (v1 default: target = change's own capability name, unless body explicitly
    states "modifies: <other-cap>")
  - For RENAMED: the source capability must exist
"""
import re
import sys
from pathlib import Path

import yaml


def find_change_dir(change_name: str, search_root: Path) -> Path:
    for cand in (search_root / "openspec/changes").iterdir():
        if cand.is_dir() and cand.name == change_name:
            return cand
    print(f"❌ Change '{change_name}' not found", file=sys.stderr)
    sys.exit(1)


def find_change_capability(change_dir: Path) -> str:
    """Get the capability name from .openspec.yaml name field or dir name."""
    yaml_file = change_dir / ".openspec.yaml"
    if yaml_file.exists():
        try:
            with yaml_file.open() as f:
                data = yaml.safe_load(f) or {}
            name = data.get("name")
            if name:
                return name
        except yaml.YAMLError:
            pass
    return change_dir.name


def find_main_specs_dirs(search_root: Path) -> list:
    """Find all main spec directories under openspec/specs/."""
    specs_root = search_root / "openspec/specs"
    if not specs_root.exists():
        return []
    return [d for d in specs_root.iterdir() if d.is_dir() and (d / "spec.md").exists()]


def parse_delta_sections(spec_md: Path) -> dict:
    """Parse spec.md into sections. Return dict of section_name -> list of requirement bodies."""
    content = spec_md.read_text()
    sections = {}
    current_section = None
    for line in content.splitlines():
        m = re.match(r"^## (ADDED|MODIFIED|RENAMED|REMOVED) Requirements\s*$", line)
        if m:
            current_section = m.group(1)
            sections[current_section] = []
            continue
        m = re.match(r"^### Requirement:", line)
        if m and current_section in ("MODIFIED", "RENAMED"):
            sections[current_section].append(line)
    return sections


def extract_target_from_body(body_lines: list, change_cap: str) -> str:
    """Extract target capability from a MODIFIED requirement body.
    v1: look for 'modifies: <cap>' or 'target: <cap>' in first 5 lines, else change_cap.
    """
    for line in body_lines[:5]:
        m = re.match(r"\s*(?:modifies|target):\s*(\S+)", line)
        if m:
            return m.group(1)
    return change_cap


def extract_rename_source(body_lines: list) -> str:
    """Extract source capability from a RENAMED requirement header (e.g., 'old-name -> new-name')."""
    if not body_lines:
        return ""
    m = re.search(r"(\S+)\s*->\s*(\S+)", body_lines[0])
    if m:
        return m.group(1)
    return ""


def validate_delta_targets(change_name: str, search_root: Path = None) -> int:
    if search_root is None:
        search_root = Path.cwd()
    change_dir = find_change_dir(change_name, search_root)
    specs_dir = change_dir / "specs"
    if not specs_dir.exists():
        print(f"ℹ️  {change_name}: no specs/ directory (pass)", file=sys.stderr)
        return 0

    main_specs = {d.name for d in find_main_specs_dirs(search_root)}
    change_cap = find_change_capability(change_dir)

    failures = []
    for cap_spec_dir in specs_dir.iterdir():
        if not cap_spec_dir.is_dir():
            continue
        spec_md = cap_spec_dir / "spec.md"
        if not spec_md.exists():
            continue
        sections = parse_delta_sections(spec_md)

        for body_line in sections.get("MODIFIED", []):
            target = extract_target_from_body([body_line], change_cap)
            if target not in main_specs:
                failures.append(
                    f"  ❌ MODIFIED target '{target}' not in main openspec/specs/\n"
                    f"     Available: {sorted(main_specs) if main_specs else '(none)'}\n"
                    f"     Fix: either create openspec/specs/{target}/spec.md, "
                    f"or move this requirement to ## ADDED Requirements"
                )
        for body_line in sections.get("RENAMED", []):
            source = extract_rename_source([body_line])
            if source and source not in main_specs:
                failures.append(
                    f"  ❌ RENAMED source '{source}' not in main openspec/specs/\n"
                    f"     Available: {sorted(main_specs) if main_specs else '(none)'}\n"
                    f"     Fix: either create openspec/specs/{source}/spec.md, "
                    f"or remove this requirement"
                )

    if failures:
        print(f"\n❌ {change_name}: {len(failures)} delta target(s) invalid:", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        return 1

    print(f"✅ {change_name}: all MODIFIED/RENAMED targets valid")
    return 0


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_delta_targets.py <change-name>", file=sys.stderr)
        sys.exit(2)
    sys.exit(validate_delta_targets(sys.argv[1]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/unit/test_validate_delta_targets.py -v --tb=short
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/validate_delta_targets.py tests/unit/test_validate_delta_targets.py
git commit -m "feat(_lib): add validate_delta_targets.py with TDD tests

- Validates spec.md MODIFIED/RENAMED sections target existing capabilities
- Catches archive aborts (e.g., g-gpu-client-meyers-singleton-fallback v2)
- Exit codes: 0=pass, 1=hard fail
- 5 unit tests covering ADDED/MODIFIED/RENAMED + regression for v2 incident"
```

### Task 2.3: Wire validate_baseline.py into propose.md

**Files:**
- Modify: `skills/propose.md`

- [ ] **Step 1: Find insertion point in propose.md**

```bash
grep -n "openspec new change" skills/propose.md | head -5
```

Expected: find the section where `openspec new change <name>` is run, just before artifact writing starts.

- [ ] **Step 2: Insert validator call**

Find the line that writes the first artifact (usually proposal.md or .openspec.yaml). Insert just BEFORE this line:

```bash
# Add: validate baseline claims before writing artifacts
if ! python3 "$(dirname "${BASH_SOURCE[0]}")/_lib/validate_baseline.py" "$target_name" 2>/dev/null; then
    echo "❌ Baseline validation failed for $target_name"
    echo "   See errors above. Fix .openspec.yaml baseline claims before continuing."
    exit 1
fi
```

Note: Use `$(dirname "${BASH_SOURCE[0]}")/_lib/validate_baseline.py` for portable path resolution.

- [ ] **Step 3: Verify propose.md still parses**

```bash
# Smoke test: run propose on a fake change with valid baseline
mkdir -p /tmp/test-repo/openspec/changes
cd /tmp/test-repo
git init -q
git config user.email t@t.t && git config user.name t
echo "# TBD" > README.md && git add . && git commit -q -m init
mkdir -p openspec/changes/test/specs/test
cat > openspec/changes/test/.openspec.yaml <<EOF
schema: spec-driven
name: test
baseline:
  free-text: "any description"
EOF
cat > openspec/changes/test/specs/test/spec.md <<EOF
# test Specification
## ADDED Requirements
### Requirement: x
Body.
EOF
git add . && git commit -q -m "test"

# Now simulate propose flow (just call validate)
python3 /workspace/project/spec-workflow/skills/_lib/validate_baseline.py test
echo "exit=$?"
```

Expected: exit 0 (no failures).

- [ ] **Step 4: Test failure path**

```bash
# Create a change with false baseline claim
mkdir -p /tmp/test-repo/openspec/changes/bad/specs/bad
cat > /tmp/test-repo/openspec/changes/bad/.openspec.yaml <<EOF
schema: spec-driven
name: bad
baseline:
  fake-symbol: "file-exists:does/not/exist.cpp"
EOF
python3 /workspace/project/spec-workflow/skills/_lib/validate_baseline.py bad
echo "exit=$?"
```

Expected: exit 1 with "❌ file-exists:does/not/exist.cpp FAILED".

- [ ] **Step 5: Commit**

```bash
git add skills/propose.md
git commit -m "feat(propose): call validate_baseline.py before writing artifacts

- Blocks propose flow when .openspec.yaml baseline claim is fabricated
- Prevents g-gpu-client-default-stub-init v1 class incidents"
```

### Task 2.4: Wire validators into guide-plan.md Phase 4 plan-done gate

**Files:**
- Modify: `skills/guide-plan.md`

- [ ] **Step 1: Find plan-done gate section**

```bash
grep -n "plan-done\|门控 2\|all_artifacts_committed" skills/guide-plan.md | head -10
```

Expected: find the section that writes `.rddf/state/.plan-handoff.json`.

- [ ] **Step 2: Insert validator calls before handoff write**

Find the line just before `cat > "$HANDOFF_FILE" << EOF`. Insert:

```bash
# Pre-handoff: validate all active changes' baseline + delta targets
VALIDATION_FAILED=0
for d in "$PROJECT_ROOT"/openspec/changes/*/; do
    [ -d "$d" ] || continue
    case "$d" in */archive/) continue ;; esac
    name=$(basename "$d")
    if ! python3 "$PROJECT_ROOT/skills/_lib/validate_baseline.py" "$name" >/dev/null 2>&1; then
        echo "❌ plan-done gate: $name failed baseline validation"
        python3 "$PROJECT_ROOT/skills/_lib/validate_baseline.py" "$name" || true
        VALIDATION_FAILED=1
    fi
    if ! python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$name" >/dev/null 2>&1; then
        echo "❌ plan-done gate: $name failed delta target validation"
        python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$name" || true
        VALIDATION_FAILED=1
    fi
done
if [ "$VALIDATION_FAILED" -ne 0 ]; then
    echo "❌ plan-done gate blocked: fix validation errors above"
    exit 1
fi
```

- [ ] **Step 3: Test on a valid change**

Run `guide-plan` through to plan-done on a change that passes validation. Expect: handoff file written, exit 0.

- [ ] **Step 4: Test on an invalid change**

Create a change with bad baseline, run `guide-plan`. Expect: gate blocks, exit 1.

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan.md
git commit -m "feat(guide-plan): validate all active changes before plan-done handoff

- Calls validate_baseline.py + validate_delta_targets.py on each change
- Blocks plan-done handoff write when any change fails validation
- Prevents v1/v2 class incidents from reaching ship phase"
```

### Task 2.5: Wire validate_delta_targets.py into guide-ship.md Phase 3 archive pre-flight

**Files:**
- Modify: `skills/guide-ship.md`

- [ ] **Step 1: Find archive section**

```bash
grep -n "openspec archive" skills/guide-ship.md | head -5
```

Expected: find where `openspec archive "$CHANGE_NAME" --yes` is called.

- [ ] **Step 2: Insert validator call before archive**

Find the line just before `openspec archive`. Insert:

```bash
# Pre-archive: validate delta targets to avoid archive abort
if ! python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$CHANGE_NAME" 2>/dev/null; then
    echo "❌ Archive pre-flight failed for $CHANGE_NAME"
    echo "   Delta targets invalid. Run validate_delta_targets.py for details."
    python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$CHANGE_NAME"
    exit 1
fi
```

- [ ] **Step 3: Test archive flow on valid change**

Run `guide-ship` Phase 3 archive on a clean change. Expect: archive succeeds.

- [ ] **Step 4: Test archive flow on change with invalid MODIFIED target**

Create a change with `## MODIFIED Requirements` targeting non-existent capability. Run `guide-ship` Phase 3. Expect: pre-flight catches it, exit 1, archive NOT called.

- [ ] **Step 5: Commit**

```bash
git add skills/guide-ship.md
git commit -m "feat(guide-ship): validate delta targets before archive

- Calls validate_delta_targets.py before openspec archive
- Avoids 6-step recovery chain (commit spec fix + push + bump + push + retry)"
```

### Task 2.6: Update CI workflow to run validators

**Files:**
- Modify: `.github/workflows/test.yml`

- [ ] **Step 1: Find existing CI steps**

```bash
cat .github/workflows/test.yml | head -40
```

Expected: find steps like `pytest tests/unit/`, `bats tests/smoke.bats`.

- [ ] **Step 2: Add validator step (after pytest, before bats)**

Insert a new step after pytest that runs the validators on all active changes:

```yaml
      - name: Validate spec baseline + delta targets
        run: |
          for d in openspec/changes/*/; do
            [ -d "$d" ] || continue
            case "$d" in */archive/) continue ;; esac
            name=$(basename "$d")
            echo "=== Validating $name ==="
            python3 skills/_lib/validate_baseline.py "$name" || VALIDATION_FAILED=1
            python3 skills/_lib/validate_delta_targets.py "$name" || VALIDATION_FAILED=1
          done
          if [ "${VALIDATION_FAILED:-0}" -ne 0 ]; then
            echo "❌ Spec validation failed"
            exit 1
          fi
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/test.yml
git commit -m "ci: run validate_baseline.py + validate_delta_targets.py on all changes

- Adds spec validation step to CI workflow
- Catches fabricated baselines and invalid MODIFIED targets before merge"
```

## 3. Verification

- [ ] 3.1 Run full test suite

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/ -q --tb=short
```

Expected: all 28+2 existing test files + 2 new files pass (12 new tests).

- [ ] 3.2 Run bats smoke tests

```bash
bats tests/smoke.bats
```

Expected: all smoke tests pass (no regression).

- [ ] 3.3 Run full bats suite

```bash
npm test  # runs bats tests/
```

Expected: all bats tests pass.

- [ ] 3.4 End-to-end regression test: v1 incident

```bash
# Simulate v1 incident: create a change with false baseline claim
# Run propose → expect block at validate_baseline step
```

- [ ] 3.5 End-to-end regression test: v2 incident

```bash
# Simulate v2 incident: create a change with invalid MODIFIED target
# Run guide-ship Phase 3 → expect block at validate_delta_targets step
```

## 4. Commit + push

- [ ] 4.1 Final commit (if any uncommitted changes)

```bash
git status
git add -A
git diff --cached --stat
git commit -m "chore: final cleanup for add-spec-validation-gates"
```

- [ ] 4.2 Push branch to origin

```bash
git push origin <branch-name>
```

## Acceptance Criteria

- [ ] validate_baseline.py correctly identifies false baseline claims (regression-tested against g-gpu-client-default-stub-init v1)
- [ ] validate_delta_targets.py correctly identifies invalid MODIFIED targets
- [ ] propose.md blocks commit on validation failure
- [ ] guide-plan.md blocks plan-done on validation failure
- [ ] guide-ship.md blocks archive on validation failure
- [ ] All existing tests pass (pytest + bats)
- [ ] CI workflow runs validators on all changes
- [ ] Documentation: AGENTS.md updated to mention validators