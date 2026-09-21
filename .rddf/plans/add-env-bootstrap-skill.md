# add-env-bootstrap-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `rdd-env-bootstrap` skill — a NEW orchestration skill that wires together `rddf init`, `rddf setup ai-context`, `rddf doctor`, and guided-fix into a single 4-phase user-facing workflow, filling the orchestration gap left after the Layer 0→3 progressive context architecture (per fix-skill-post-install-discoverability + ADR-0052).

**Architecture:** Four-phase orchestration:
1. **Phase 1 (detect, read-only)** — file-based detection: git repo? .rddf/? language (Python/Node/Go/Rust)? rddf CLI installed/version? AI config files?
2. **Phase 2 (diagnose, read-only)** — fork `rddf doctor --json`, classify findings into `auto-fixable` / `user-decision` / `manual-only`
3. **Phase 3 (suggest, read+report)** — emit suggested `rddf init` / `rddf setup ai-context` / `install.sh --with-docs` commands; write report
4. **Phase 4 (guided-fix, write)** — fork subprocesses for `[auto-fixable]` items, with `--auto-fix --yes` mode for CI

**Tech Stack:** Python 3.11+ stdlib only (argparse, json, subprocess, shutil, pathlib). No new dependencies. Schema v1 in `_lib/schemas/env_bootstrap_report_schema.json`. New CLI subcommand `env_bootstrap` (per `_lib/cli/env_bootstrap_cmd.py`).

**Boundary contract (per ADR-0028 + skill description convention ADR-0051):**
- `rdd-env-bootstrap` owns `.rddf/state/.env-bootstrap-report.json`
- Does NOT modify `rdd-doctor` (kept read-only), `rddf setup ai-context` (delegated via subprocess), `rddf init` (delegated), `install.sh`

**Fix whitelist (per Improvement AC-6):** Only `ai-context-bootstrap: 未部署` + `ai-context-bootstrap: 块已陈旧` are auto-fixable. All other findings require explicit user decision.

**Plan verification:**
- TDD: red→green for each task (write failing test → run → implement → verify green)
- After all tasks: `./test.sh --full --regression` (no new failures vs. baseline)
- AC-10 must keep 2 pre-existing failures (brainstorm-hardgate + v3-rename-guard) in `KNOWN_FAILURES.txt` only

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-env-bootstrap/SKILL.md` | Skill frontmatter (name/description/license/compatibility/metadata/role). 4-phase prose state machine (P0 entry → P1 detect → P2 diagnose → P3 suggest → P4 fix). Boundary per ADR-0028. Description per ADR-0051. |
| `skills/rdd-env-bootstrap/references/fix-decisions.md` | Auto-fix whitelist table (per Improvement AC-6) + risk levels + alternative actions |
| `skills/rdd-env-bootstrap/scripts/detect_environment.py` | Phase 1 pure functions: `detect_git_repo()`, `detect_rddf_dir()`, `detect_language()`, `detect_rddf_install()`, `detect_ai_config_files()`. All return `dict[str, Any]` for JSON-friendliness. <200ms total. |
| `skills/rdd-env-bootstrap/scripts/diagnose.py` | Phase 2 logic: fork `rddf doctor --json`, parse findings, classify into `auto-fixable` / `user-decision` / `manual-only` per whitelist. <1s. |
| `skills/rdd-env-bootstrap/scripts/guided_fix.py` | Phase 4 fork subprocess wrapper with try/except + report aggregation. Each fix: command + status + stderr. |
| `_lib/env_bootstrap_report.py` | Report schema data layer: `validate_report(report) -> bool`, `build_report(...) -> dict`, `write_report(report, path)` (atomic temp + rename), `load_report(path)`. Pure functions for testability. |
| `_lib/cli/env_bootstrap_cmd.py` | `cmd_env_bootstrap(args: list[str]) -> int`. argparse for `--check-only` / `--auto-fix` / `--yes` / `--target` / `--report` / `--help`. Routes to scripts. |
| `_lib/schemas/env_bootstrap_report_schema.json` | JSON Schema v1. `version: 1`, required fields: `phase_1_detection` / `phase_2_diagnosis` / `phase_3_init_suggestion` / `phase_4_guided_fix` / `exit_code`. |
| `_lib/cli/__init__.py` | Add `"env-bootstrap": "skills._lib.cli.env_bootstrap_cmd:cmd_env_bootstrap"` to `_ROUTES` |
| `_lib/cli/__main__.py` | Extend `_NO_STATE_CHECK = {"setup", "doctor", "env-bootstrap"}` and add help line |

### Documentation

| File | Responsibility |
|---|---|
| `docs/adr/ADR-0053-rdd-env-bootstrap-orchestrator.md` | Decision record. Status: 已采纳 (2026-09-22). Background (3-paragraph), Decision D1-D5, Boundary vs `rdd-env-check` + `rdd-doctor`, Consequences: positive/negative/risks (with mitigations). |
| `AGENTS.md` | Add new "## rdd-env-bootstrap" section after "## rdd-doctor" section. 4 phases + env-var table. |
| `README.md` | Add `rdd-env-bootstrap/SKILL.md` row to skill list (27 → 28). Mention `_NO_STATE_CHECK` extension. |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_env_bootstrap_report.py` | ≥5 tests: schema v1 validates, build_report produces all 5 required fields, write_report creates file atomically, load_report round-trips, validate_report rejects missing required field. |
| `tests/integration/test_env_bootstrap.bats` | ≥8 cases: (a) `rddf env-bootstrap --help` shows 4 flags + 1 example; (b) `--check-only` runs Phases 1-2 only, no file written; (c) default mode prompt acceptance via stdin; (d) `--auto-fix --yes` skips prompts; (e) `--target /tmp/random` exits 3 (non-rdd project); (f) auto-fixable detection triggers setup ai-context subprocess; (g) report schema lands with version=1; (h) exit code 0/1/2/3 semantics. |

---

## Tasks

### Task 1: Schema + Python data layer (TDD red→green)

**Problem:** The report file `.rddf/state/.env-bootstrap-report.json` needs a versioned schema and atomic write primitive. Foundation for all downstream phases.

**Files:**
- Create: `_lib/schemas/env_bootstrap_report_schema.json`
- Create: `_lib/env_bootstrap_report.py`
- Create: `tests/unit/test_env_bootstrap_report.py`

- [ ] **Step 1: Write failing unit tests**

  Create `tests/unit/test_env_bootstrap_report.py` with 5 tests:
  - `test_schema_v1_exists_and_loads` — schema file exists, parses as JSON, declares `version: 1`
  - `test_build_report_produces_all_required_fields` — `build_report(phase_1, phase_2, phase_3, phase_4, exit_code)` returns dict containing all 5 required top-level keys
  - `test_write_report_creates_file_atomically` — fresh path → file exists, valid JSON, atomic via temp+rename
  - `test_load_report_round_trips` — write then load → deep-equal
  - `test_validate_report_rejects_missing_field` — drop `exit_code`, expect validation failure

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 5 FAILED (module does not exist)

- [ ] **Step 2: Implement schema v1**

  Create `_lib/schemas/env_bootstrap_report_schema.json` per Improvement §4 (4 阶段 + 报告 schema). Top-level: `$schema`, `title: "env-bootstrap-report"`, `version: 1`, `type: object`, `required: ["version", "generated_at", "project_root", "phase_1_detection", "phase_2_diagnosis", "phase_3_init_suggestion", "phase_4_guided_fix", "exit_code"]`. Each `phase_*` is `type: object` with specific subfields.

  Verify: `python3 -c "import json; print(json.load(open('_lib/schemas/env_bootstrap_report_schema.json'))['version'])"`
  Expected: `1`

- [ ] **Step 3: Implement `_lib/env_bootstrap_report.py`**

  Four public functions:
  - `build_report(phase_1_detection: dict, phase_2_diagnosis: dict, phase_3_init_suggestion: list, phase_4_guided_fix: dict, exit_code: int, project_root: str, generated_at: str) -> dict` — returns dict with all 7 top-level keys (including `version: 1`)
  - `write_report(report: dict, path: Path) -> None` — validate via jsonschema, atomic write via temp file + `os.replace`
  - `load_report(path: Path) -> dict | None` — read JSON, return None if file missing
  - `validate_report(report: dict) -> bool` — uses `jsonschema.Draft7Validator(schema).is_valid(report)`

  Stdlib + jsonschema only (already in `requirements.txt`). Module docstring noting: NO imports from `skills._lib.*`.

- [ ] **Step 4: Run tests green**

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q`
  Expected: 5 passed

- [ ] **Step 5: Defer commit**

### Task 2: Phase 1 detection module (TDD red→green)

**Problem:** Phase 1 must detect git repo, .rddf/ existence, project language, rddf CLI install/version, and AI config files — all in <200ms. Each detector is a pure function for testability.

**Files:**
- Create: `skills/rdd-env-bootstrap/scripts/detect_environment.py`
- Create: `tests/unit/test_detect_environment.py` (≥3 cases; may be added to env_bootstrap_report.py if simpler)

- [ ] **Step 1: Write failing unit tests**

  Add 3 tests to `tests/unit/test_env_bootstrap_report.py` (or new file):
  - `test_detect_git_repo_true_for_repo_with_git_dir` — `tmp_path / ".git"` exists → `detect_git_repo(tmp_path) == True`
  - `test_detect_language_python_for_pyproject_toml` — `tmp_path / "pyproject.toml"` exists → `detect_language(tmp_path) == ["python"]`
  - `test_detect_ai_config_files_finds_agents_md` — write `tmp_path / "AGENTS.md"`, expect `detect_ai_config_files(tmp_path)` to include it

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 3 FAILED (module does not exist)

- [ ] **Step 2: Implement detect_environment.py**

  Five pure functions, all `def detect_*(project_root: Path) -> <return>`. Use `pathlib.Path.is_file()`, `subprocess.run(["git", "rev-parse", ...], capture_output=True, timeout=2)`, `shutil.which("rddf")`, `subprocess.run(["rddf", "--version"], capture_output=True, timeout=2)`. Return types:

  - `detect_git_repo(project_root) -> bool` — check `project_root / ".git"` exists (fast path, no subprocess needed)
  - `detect_rddf_dir(project_root) -> bool` — check `project_root / ".rddf"` exists
  - `detect_language(project_root) -> list[str]` — check for `pyproject.toml`/`setup.py` → "python", `package.json` → "node", `go.mod` → "go", `Cargo.toml` → "rust"
  - `detect_rddf_install() -> dict` — return `{"installed": bool, "version": str | None}` using `shutil.which("rddf")` + `rddf --version` parse
  - `detect_ai_config_files(project_root) -> list[str]` — check files in priority order: `AGENTS.md`, `.cursorrules`, `CLAUDE.md`, `.clinerules`, `.continue/rules/*.md`, `.github/copilot-instructions.md`

  Add CLI entry: `if __name__ == "__main__": json.dump({k: v(project_root) for k, v in {...}.items()}, sys.stdout)`. <100ms target.

- [ ] **Step 3: Run tests green**

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 8 passed (5 from Task 1 + 3 from Task 2)

- [ ] **Step 4: Defer commit**

### Task 3: Phase 2 diagnose + classify module (TDD red→green)

**Problem:** Phase 2 must invoke `rddf doctor --json`, parse findings, and classify each finding into `auto-fixable` / `user-decision` / `manual-only` per the whitelist.

**Files:**
- Create: `skills/rdd-env-bootstrap/scripts/diagnose.py`
- Create: `tests/unit/test_diagnose.py` (≥2 cases)

- [ ] **Step 1: Write failing unit tests**

  Add 2 tests:
  - `test_classify_finding_auto_fixable_ai_context_undeployed` — finding `{"category": "ai-context-bootstrap", "severity": "warning", "message": "未部署 Layer 0"}` → `classify_finding(finding) == "auto-fixable"`
  - `test_classify_finding_user_decision_gitignore_missing` — finding `{"category": "gitignore", ...}` → `classify_finding(finding) == "user-decision"`

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 2 FAILED (no classify_finding function)

- [ ] **Step 2: Implement diagnose.py**

  ```python
  # skills/rdd-env-bootstrap/scripts/diagnose.py
  """Phase 2: invoke rddf doctor --json + classify findings.

  Pure functions:
    classify_finding(finding: dict) -> "auto-fixable" | "user-decision" | "manual-only"
    diagnose(target_root: Path, doctor_json: dict | None = None) -> dict
  """
  from __future__ import annotations
  import json, subprocess
  from pathlib import Path

  _AUTO_FIXABLE_CATEGORIES = {"ai-context-bootstrap"}  # Per AC-6 whitelist
  _USER_DECISION_CATEGORIES = {"gitignore", "docs-consistency"}
  # Anything else is manual-only (bypass-audit, orphan-gates, migration-residue, etc.)

  def classify_finding(finding: dict) -> str:
      cat = finding.get("category", "")
      if cat in _AUTO_FIXABLE_CATEGORIES:
          # Even within ai-context-bootstrap, only "未部署" or "块已陈旧" are auto-fixable
          msg = finding.get("message", "")
          if any(kw in msg for kw in ("未部署", "块已陈旧", "stale", "outdated")):
              return "auto-fixable"
          return "user-decision"
      if cat in _USER_DECISION_CATEGORIES:
          return "user-decision"
      return "manual-only"

  def diagnose(target_root: Path, doctor_json: dict | None = None) -> dict:
      """Phase 2 entry. Returns dict with doctor_invoked, total_findings, breakdown."""
      if doctor_json is None:
          r = subprocess.run(
              ["rddf", "doctor", "--json"],
              capture_output=True, text=True, timeout=5, cwd=str(target_root),
          )
          if r.returncode != 0 and not r.stdout.strip():
              return {
                  "doctor_invoked": False,
                  "total_findings": 0,
                  "auto_fixable": 0,
                  "user_decision": 0,
                  "manual_only": 0,
                  "findings": [],
              }
          try:
              doctor_json = json.loads(r.stdout)
          except json.JSONDecodeError:
              doctor_json = {"findings": []}

      findings = doctor_json.get("findings", [])
      breakdown = {"auto_fixable": 0, "user_decision": 0, "manual_only": 0}
      classified = []
      for f in findings:
          kind = classify_finding(f)
          breakdown[f"{kind.replace('-', '_')}"] += 1
          classified.append({**f, "class": kind})
      return {
          "doctor_invoked": True,
          "total_findings": len(findings),
          **breakdown,
          "findings": classified,
      }
  ```

- [ ] **Step 3: Run tests green**

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 10 passed (8 from Task 1+2 + 2 from Task 3)

- [ ] **Step 4: Defer commit**

### Task 4: Phase 4 guided_fix module (TDD red→green)

**Problem:** Phase 4 must fork subprocesses for `[auto-fixable]` findings with try/except + report aggregation. Each fix must be wrapped to never crash the whole phase.

**Files:**
- Create: `skills/rdd-env-bootstrap/scripts/guided_fix.py`
- Create: `tests/unit/test_guided_fix.py` (≥3 cases)

- [ ] **Step 1: Write failing unit tests**

  Add 3 tests:
  - `test_run_fix_success_returns_executed` — mock subprocess, run with command `["true"]`, expect status `"success"`
  - `test_run_fix_failure_returns_failed` — run with command `["false"]`, expect status `"failed"`
  - `test_run_fix_aggregates_into_executed_list` — 2 fixes, first success + second fail → executed list has 2 entries with mixed status

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 3 FAILED

- [ ] **Step 2: Implement guided_fix.py**

  ```python
  # skills/rdd-env-bootstrap/scripts/guided_fix.py
  """Phase 4: fork subprocesses for [auto-fixable] findings with try/except."""
  from __future__ import annotations
  import subprocess
  from typing import Callable

  def run_fix(finding: dict, command: list[str], target_root: str, timeout: int = 5) -> dict:
      """Run a single fix subprocess. Returns dict with finding/command/status/stderr."""
      try:
          r = subprocess.run(
              command, capture_output=True, text=True, timeout=timeout, cwd=target_root,
          )
          return {
              "finding": finding.get("message", ""),
              "command": " ".join(command),
              "status": "success" if r.returncode == 0 else "failed",
              "returncode": r.returncode,
              "stderr": r.stderr[:200] if r.stderr else "",
          }
      except (subprocess.TimeoutExpired, OSError) as e:
          return {
              "finding": finding.get("message", ""),
              "command": " ".join(command),
              "status": "failed",
              "returncode": -1,
              "stderr": str(e)[:200],
          }

  def run_guided_fix(
      auto_fixable_findings: list[dict],
      target_root: str,
      fix_command_for: Callable[[dict], list[str]],
      auto_fix: bool = False,
      confirm: Callable[[str], bool] | None = None,
  ) -> dict:
      """Phase 4 entry. Returns {executed: [...], skipped: [...], manual_required: [...]}."""
      executed = []
      skipped = []
      manual_required = []

      for finding in auto_fixable_findings:
          cmd = fix_command_for(finding)
          should_run = auto_fix
          if not auto_fix and confirm is not None:
              should_run = confirm(f"运行 `{cmd[0]} {' '.join(cmd[1:])}`? [Y/n] ")

          if not should_run:
              skipped.append({"finding": finding.get("message", ""), "command": " ".join(cmd)})
              continue

          executed.append(run_fix(finding, cmd, target_root))

      return {"executed": executed, "skipped": skipped, "manual_required": manual_required}
  ```

- [ ] **Step 3: Run tests green**

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 13 passed (10 + 3)

- [ ] **Step 4: Defer commit**

### Task 5: CLI subcommand `rddf env-bootstrap` (TDD red→green)

**Problem:** New CLI subcommand must be registered, accept 5 flags (`--check-only` / `--auto-fix` / `--yes` / `--target` / `--report` / `--help`), and orchestrate all 4 phases. Must handle non-rdd-workflow projects (exit 3) and bad usage (exit 2).

**Files:**
- Create: `_lib/cli/env_bootstrap_cmd.py`
- Modify: `_lib/cli/__init__.py` (add route)
- Modify: `_lib/cli/__main__.py` (extend `_NO_STATE_CHECK`, add help line)
- Create: `tests/integration/test_env_bootstrap.bats` (≥8 cases)

- [ ] **Step 1: Write failing integration tests**

  Create `tests/integration/test_env_bootstrap.bats` with 8 tests:

  - `env-bootstrap: rddf env-bootstrap --help shows 5 flags` — run `rddf env-bootstrap --help`, grep for `--check-only`, `--auto-fix`, `--yes`, `--target`, `--report`
  - `env-bootstrap: --check-only runs phases 1-2 only, no file written` — run in `tests/_lib/scratch/empty-project/`, assert no `.rddf/state/.env-bootstrap-report.json` written
  - `env-bootstrap: default mode prompts via stdin` — feed `n\nn\n...` to stdin, assert exit code 0 and `skipped` array populated in report
  - `env-bootstrap: --auto-fix --yes skips prompts` — same setup, assert all `[auto-fixable]` items in `executed[]` array
  - `env-bootstrap: --target /tmp/random exits 3` — run with `--target /tmp/non-rdd-project-$$`, assert exit code 3
  - `env-bootstrap: ai-context-bootstrap triggers setup ai-context subprocess` — pre-condition: target project lacks Layer 0, expect `executed[]` contains `"rddf setup ai-context"`
  - `env-bootstrap: report schema lands with version=1` — after successful run, jq -r `.version` returns `1`
  - `env-bootstrap: exit code semantics` — three sub-tests:
    - clean project → exit 0
    - WARNING + auto-fixed → exit 1
    - manual-only remaining → exit 2

  Run: `bats tests/integration/test_env_bootstrap.bats`
  Expected: 8 FAILED (env-bootstrap command not registered)

- [ ] **Step 2: Implement env_bootstrap_cmd.py**

  ```python
  # _lib/cli/env_bootstrap_cmd.py
  """rddf env-bootstrap orchestrator (4 phases: detect → diagnose → suggest → guided-fix)."""
  from __future__ import annotations
  import argparse, json, os, sys
  from datetime import datetime, timezone
  from pathlib import Path

  # scripts/ lives under skills/rdd-env-bootstrap/scripts/
  _SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "rdd-env-bootstrap"
  sys.path.insert(0, str(_SKILL_ROOT / "scripts"))

  from detect_environment import detect_git_repo, detect_rddf_dir, detect_language, \
      detect_rddf_install, detect_ai_config_files
  from diagnose import diagnose
  from guided_fix import run_guided_fix
  from _lib.env_bootstrap_report import build_report, write_report, load_report

  def _resolve_target_root(args_target: str | None) -> Path:
      return Path(args_target or os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()).resolve()

  def _is_rdd_workflow_project(target_root: Path) -> bool:
      # Heuristic: project has _lib/ or is current rdd-workflow repo itself
      return (target_root / "_lib").is_dir() or (target_root / ".rddf" / "state").is_dir()

  def _build_fix_command(finding: dict) -> list[str]:
      """Per AC-6: only ai-context-bootstrap with 未部署/块已陈旧 is auto-fixable."""
      msg = finding.get("message", "")
      if "未部署" in msg or "stale" in msg.lower() or "outdated" in msg.lower() or "块已陈旧" in msg:
          return ["rddf", "setup", "ai-context", "--yes"]
      return ["echo", "no-auto-fix-available"]

  def _confirm(prompt: str) -> bool:
      try:
          reply = input(prompt).strip().lower()
      except EOFError:
          return False
      return reply in ("", "y", "yes")

  def cmd_env_bootstrap(args: list[str]) -> int:
      parser = argparse.ArgumentParser(
          prog="rddf env-bootstrap",
          description="4-phase environment orchestrator (detect → diagnose → suggest → guided-fix).",
      )
      parser.add_argument("--check-only", action="store_true", help="Run Phases 1-2 only, no writes.")
      parser.add_argument("--auto-fix", action="store_true", help="Skip Phase 4 prompts (requires --yes).")
      parser.add_argument("--yes", action="store_true", help="Skip all confirmation prompts.")
      parser.add_argument("--target", default=None, help="Target project root (default: cwd).")
      parser.add_argument("--report", default=None, help="Report output path (default: <target>/.rddf/state/.env-bootstrap-report.json).")
      parsed = parser.parse_args(args)

      target_root = _resolve_target_root(parsed.target)
      if not _is_rdd_workflow_project(target_root):
          print(f"ℹ️  not a rdd-workflow project (target={target_root})", file=sys.stderr)
          print(f"   Run: bash ~/.agents/skills/rdd-workflow/install.sh --global", file=sys.stderr)
          return 3

      # Phase 1
      phase_1 = {
          "is_git_repo": detect_git_repo(target_root),
          "has_rddf_dir": detect_rddf_dir(target_root),
          "language_hints": detect_language(target_root),
          "rddf_installed": detect_rddf_install(),
          "ai_config_files_detected": detect_ai_config_files(target_root),
      }
      # If previously written report exists, reuse phase_1 if env says so (idempotent)
      report_path = Path(parsed.report or target_root / ".rddf" / "state" / ".env-bootstrap-report.json")
      if parsed.check_only:
          # Phase 1+2 only, no report write
          phase_2 = diagnose(target_root)
          print(json.dumps({"phase_1": phase_1, "phase_2": phase_2}, ensure_ascii=False, indent=2))
          return 0

      # Phase 2
      phase_2 = diagnose(target_root)

      # Phase 3: init suggestion (simple, derived from phase_1)
      phase_3 = []
      if not phase_1["has_rddf_dir"]:
          phase_3.append("rddf init (生成 .rddf/project.yaml)")
      if not phase_1["ai_config_files_detected"]:
          phase_3.append("rddf setup ai-context (部署 Layer 0)")

      # Phase 4
      auto_fixable = [f for f in phase_2.get("findings", []) if f.get("class") == "auto-fixable"]
      confirm_fn = None if parsed.yes or parsed.auto_fix else _confirm
      phase_4 = run_guided_fix(
          auto_fixable_findings=auto_fixable,
          target_root=str(target_root),
          fix_command_for=_build_fix_command,
          auto_fix=parsed.auto_fix or parsed.yes,
          confirm=confirm_fn,
      )

      # Exit code semantics per AC-8
      manual_only = phase_2.get("manual_only", 0)
      warnings_auto_fixed = len([e for e in phase_4["executed"] if e["status"] == "success"])
      has_critical = any(f.get("severity") == "critical" for f in phase_2.get("findings", []))
      if has_critical or manual_only > 0:
          exit_code = 2
      elif warnings_auto_fixed > 0:
          exit_code = 1
      else:
          exit_code = 0

      report = build_report(
          phase_1_detection=phase_1,
          phase_2_diagnosis=phase_2,
          phase_3_init_suggestion=phase_3,
          phase_4_guided_fix=phase_4,
          exit_code=exit_code,
          project_root=str(target_root),
          generated_at=datetime.now(timezone.utc).isoformat(),
      )
      write_report(report, report_path)
      print(f"✅ Report: {report_path} (exit={exit_code})")
      return exit_code
  ```

- [ ] **Step 3: Register route in `_lib/cli/__init__.py`**

  Add to `_ROUTES` dict (alphabetical position between `discover-ship-changes` and `doctor`):
  ```python
  "env-bootstrap": "skills._lib.cli.env_bootstrap_cmd:cmd_env_bootstrap",
  ```

- [ ] **Step 4: Extend `_NO_STATE_CHECK` in `_lib/cli/__main__.py`**

  Change line 195 from:
  ```python
  _NO_STATE_CHECK = {"setup", "doctor"}
  ```
  to:
  ```python
  _NO_STATE_CHECK = {"setup", "doctor", "env-bootstrap"}
  ```

  Also add to `_print_help` output:
  ```
  print("  env-bootstrap  4-phase env orchestrator (detect→diagnose→suggest→guided-fix)")
  ```

- [ ] **Step 5: Run integration tests green**

  Run: `bats tests/integration/test_env_bootstrap.bats`
  Expected: 8 passed

- [ ] **Step 6: Defer commit**

### Task 6: SKILL.md + references/fix-decisions.md (TDD red→green)

**Problem:** The skill file must declare `role.boundaries` per ADR-0028, document the 4-phase state machine, and reference the fix-decisions doc.

**Files:**
- Create: `skills/rdd-env-bootstrap/SKILL.md`
- Create: `skills/rdd-env-bootstrap/references/fix-decisions.md`
- Modify: `tests/integration/test_env_bootstrap.bats` (add 2 structural tests)

- [ ] **Step 1: Add 2 structural tests**

  Append to `tests/integration/test_env_bootstrap.bats`:
  - `env-bootstrap: SKILL.md frontmatter declares role.boundaries` — file exists, parse YAML frontmatter, assert `role.boundaries.owns` and `not_owns` present
  - `env-bootstrap: SKILL.md body documents 4 phases` — body text contains all 4: `Phase 1`, `Phase 2`, `Phase 3`, `Phase 4`

  Run: `bats tests/integration/test_env_bootstrap.bats`
  Expected: 2 FAILED (SKILL.md missing)

- [ ] **Step 2: Write SKILL.md frontmatter (per ADR-0051 + ADR-0028)**

  ```yaml
  ---
  name: rdd-env-bootstrap
  description: |
    Environment bootstrap orchestrator for new/existing rdd-workflow projects.
    Invoke when:
      1. User just installed rdd-workflow in a new project (刚 bash install.sh --global 完, 进入新项目目录)
      2. User wants guided remediation of doctor findings (rddf doctor 报 N 个 WARNING, 想批量修)
      3. User says "set up rdd-workflow" / "bootstrap environment" / "fix my env"
    Default: 4-phase flow (detect → diagnose → suggest → guided-fix).
    With --check-only: phases 1-2 only (read-only, CI-friendly).
    With --auto-fix: phase 4 executes all safe fixes without prompts.
    Boundary: owns orchestration; delegates fixes to setup/init/doctor via subprocess.
  license: MIT
  compatibility: requires Python 3.11+, bash 4+. No external skill deps.
  metadata:
    author: rdd-workflow
    version: "1.0"
    evolved-from: "fix-skill-post-install-discoverability (Layer 0→3 architecture)"
    user-invocable: true
  role:
    title: "Environment Bootstrap Orchestrator (环境编排者)"
    perspective: "填补 Layer 0→3 部署后的'一键编排 + 引导式修复'层, 把 init / setup / doctor / 修复串联成 4 阶段工作流。"
    boundaries:
      owns:
        - ".rddf/state/.env-bootstrap-report.json"
      not_owns:
        - "_lib/cli/setup_cmd.py"
        - "_lib/cli/init_cmd.py"
        - "_lib/cli/doctor_cmd.py"
        - "skills/rdd-doctor/"
        - "skills/rdd-env-check/"
      human_involvement: "medium"
  ---
  ```

- [ ] **Step 3: Write SKILL.md body**

  Sections:
  - `# rdd-env-bootstrap Skill`
  - `## Entry / Exit Contract`
    - Entry: `rddf env-bootstrap [flags]` (5 flags: --check-only / --auto-fix / --yes / --target / --report)
    - Exit: report at `<target>/.rddf/state/.env-bootstrap-report.json`, exit code 0/1/2/3
  - `## Phase 1 — Project Env Detection (read-only)`
    - File-based checks. No subprocess. <200ms target.
    - Detect: git repo, .rddf/ existence, language (Python/Node/Go/Rust), rddf CLI install/version, AI config files
  - `## Phase 2 — Health Diagnosis (read-only, delegates to doctor)`
    - `subprocess.run(["rddf", "doctor", "--json"], timeout=5)`
    - Classify each finding into `auto-fixable` / `user-decision` / `manual-only` per `references/fix-decisions.md`
    - <1s target (doctor caches TTL 3600s)
  - `## Phase 3 — Init Suggestion (read+report)`
    - Based on Phase 1 detection, suggest:
      - No `.rddf/project.yaml` → `rddf init`
      - No AI config files → `rddf setup ai-context`
      - Layer 2 missing → `install.sh --with-docs`
    - Pure computation. <50ms.
  - `## Phase 4 — Guided Fix (write)`
    - For each `[auto-fixable]` finding:
      - Default mode: `input("运行 `rddf setup ai-context --yes`? [Y/n] ")`, run on confirm
      - `--auto-fix --yes`: skip prompts, run all
    - Each fix wrapped in try/except → failures recorded in report, never crash phase
    - `--check-only` skips Phase 4 entirely
  - `## Session Binding`
    - Skill entry SHOULD bind to rddf-session via `owner_opencode_session_id` (per ADR-0017); failure friendly-degrades (proceeds without binding)
  - `## Environment Variables`
    - `RDDF_PROJECT_ROOT` (default: cwd) — target root for project detection
    - `RDDF_REPORT_ENABLED` (default: false) — opt-in to L2 reporting (inherited)
  - `## See also`
    - `references/fix-decisions.md` — auto-fix whitelist + risk levels
    - `skills/rdd-env-check/` — phase-internal quick check (different scope)
    - `skills/rdd-doctor/` — read-only diagnostic (delegated target)
    - `docs/adr/ADR-0053-rdd-env-bootstrap-orchestrator.md` — decision record
    - `docs/adr/ADR-0052-layer-0-progressive-context.md` — predecessor architecture

- [ ] **Step 4: Write references/fix-decisions.md**

  ```markdown
  # Auto-Fix Decision Table (Phase 4)

  Per AC-6: only `[auto-fixable]` items in this table can be executed automatically.

  | Finding category | Auto-fixable? | Command | Risk |
  |---|---|---|---|
  | `ai-context-bootstrap: 未部署` | ✅ | `rddf setup ai-context --yes` | Low (idempotent sentinel) |
  | `ai-context-bootstrap: 块已陈旧` | ✅ | `rddf setup ai-context --yes` | Low (force overwrite sentinel) |
  | `gitignore: openspec/ 缺失` | ❌ | output suggestion | Medium (affects git behavior) |
  | `docs-consistency: ADR drift` | ❌ | output suggestion + rebuild hint | Medium (affects doc sync) |
  | `bypass-audit: bypass > 阈值` | ❌ | output audit report | High (needs human review) |
  | `orphan-gates: gate 失效` | ❌ | output diagnosis | High (affects phase safety) |
  | `migration-residue` | ❌ | output checklist | Medium (affects schema consistency) |

  ## Safety principle

  Any fix that would modify `.gitignore`, tracked files, or `.rddf/state/*.json`
  (other than `.env-bootstrap-report.json`) is **NOT** auto-fixable. User must
  explicitly confirm via Phase 4 prompt OR run with `--auto-fix --yes` after
  reviewing the report.

  ## Idempotency

  `rddf setup ai-context --yes` is idempotent per AC-6 reviewer note:
  - First run: creates `AGENTS.md` with Layer 0 sentinel block
  - Repeat run: detects sentinel, skips (no-op)
  - Stale detection: regenerates the block if drift detected
  ```

- [ ] **Step 5: Run all tests green**

  Run: `bats tests/integration/test_env_bootstrap.bats`
  Expected: 10 passed (8 from Task 5 + 2 structural)

  Run: `pytest tests/unit/test_env_bootstrap_report.py -q --tb=short`
  Expected: 13 passed (all unit)

- [ ] **Step 6: Defer commit**

### Task 7: ADR-0053 + README + AGENTS + docs sync (TDD red→green)

**Problem:** Per AC-11, ADR-0053 must be authored, README skill list updated, AGENTS.md key conventions updated.

**Files:**
- Create: `docs/adr/ADR-0053-rdd-env-bootstrap-orchestrator.md`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write ADR-0053**

  ```markdown
  # ADR-0053: rdd-env-bootstrap 编排层

  **状态**: 已采纳 (2026-09-22)
  **作者**: rdd-workflow

  ## Background

  `fix-skill-post-install-discoverability` (ADR-0052, 2026-09-21) 实现了 Layer 0→3 渐进式
  上下文注入架构, 第三方项目用户从此可以在安装后立刻使用 rdd-workflow。但部署完成后,
  用户仍需手动串联 4 个独立命令 (`rddf init` / `rddf setup ai-context` / `rddf doctor` /
  修复) 才能完成"新项目启用 rdd-workflow"的标准流程。

  ## Decision

  D1. 新增独立 skill `rdd-env-bootstrap` + CLI 子命令 `rddf env-bootstrap`, 不修改
      `rdd-doctor` (保持只读) / `rddf setup ai-context` (作为底层原语) / `rddf init` /
      `install.sh`。

  D2. 4 阶段工作流: detect → diagnose → suggest → guided-fix。每阶段明确职责边界。
      Phase 1-3 只读, Phase 4 在用户确认或 `--auto-fix --yes` 模式下写。

  D3. 修复白名单固定: 仅 `ai-context-bootstrap: 未部署` + `ai-context-bootstrap: 块已陈旧`
      两类可自动修复。任何涉及 `.gitignore` / tracked files / `.rddf/state/*.json` 的
      修复**禁止自动执行**, 必须用户显式确认。

  D4. 报告 schema version=1 锁定, 写在 `<target>/.rddf/state/.env-bootstrap-report.json`。
      版本不兼容时 bump version 强制迁移。

  D5. 退出码对齐 openspec validate: 0 健康/1 警告已自动修/2 关键失败/3 环境错误
      (rddf 未装 / cwd 非 rdd-workflow 项目)。

  ## Boundary vs 既有 skill

  - **vs `rdd-env-check`**: 后者是 phase 内嵌快速检查 (≤200ms 缓存), 前者是用户主动全流程编排
    (≤10s 含 1-3 个 fix)
  - **vs `rdd-doctor`**: 后者只读 + 多 category 诊断, 前者只读 doctor 结果 + 引导式修复
    (doctor 不动, env-bootstrap 加修复路径)
  - **vs `rdd-hub-bootstrap`**: 后者是 Hub repo (rdd-hub) 的引导式初始化 (Projects V2 board + CI),
    前者是任意第三方项目的环境引导

  ## Consequences

  ### 正面
  - 第三方项目用户从 "5 步手动串联" → "1 个命令完成", 大幅降低使用门槛
  - doctor 保持只读语义边界 (user insight 采纳)
  - 复用现有 `rddf setup / init / doctor` (不重新实现)

  ### 负面
  - 新增 skill 需维护; CLI 增加一个 subcommand 需保证不破坏现有命令
  - env-bootstrap 自身复杂度 (4 阶段 + 决策表 + 报告 schema) 需后续维护
  - 增加一个报告文件路径需 `.gitignore` 管理 (per-project local file)

  ### 风险

  | 风险 | 等级 | 缓解 |
  |---|---|---|
  | 自动修复越界 (修改 tracked files) | 中 | 修复白名单固定, 仅 ai-context-bootstrap 两类 |
  | 退出码语义混乱 | 低 | 严格对齐 openspec validate (0/1/2/3) |
  | 子进程 fork 失败容错 | 中 | try/except 包裹 + 报告记录失败 |
  | 报告 schema 版本不兼容 | 低 | version 字段 const=1, bump version 强制迁移 |
  | 与 `rdd-env-check` 职责重叠 | 中 | 文档明确分工 (本 ADR §Boundary) |
  ```

- [ ] **Step 2: Update README.md**

  Find the existing skill list table (around line ~110 in README.md) and add one row:
  ```
  | `rdd-env-bootstrap` | Environment orchestrator (4 phases: detect→diagnose→suggest→guided-fix). Flags: `--check-only`, `--auto-fix`, `--yes`, `--target`, `--report`. |
  ```

  Also add to the directory structure tree under `skills/`:
  ```
  rdd-env-bootstrap/
  ```

- [ ] **Step 3: Update AGENTS.md**

  Find `## rdd-doctor` section and add a new `## rdd-env-bootstrap` section immediately after:

  ```markdown
  ## rdd-env-bootstrap (per ADR-0053)

  4-phase environment orchestrator (detect → diagnose → suggest → guided-fix) that fills
  the orchestration gap left after Layer 0→3 progressive context architecture (ADR-0052).

  ### 关键约定

  - **新增 skill 边界**: owns `.rddf/state/.env-bootstrap-report.json` only
  - **禁止修改**: `rdd-doctor` (保持只读) / `rddf setup ai-context` (底层原语) / `rddf init` / `install.sh`
  - **CLI 子命令注册**: `_lib/cli/__init__.py::_ROUTES` 添加 `"env-bootstrap"`
  - **`_NO_STATE_CHECK` 白名单**: `_lib/cli/__main__.py` 把 `env-bootstrap` 加入 `{"setup", "doctor", "env-bootstrap"}`
  - **修复白名单**: 仅 `ai-context-bootstrap: 未部署` + `ai-context-bootstrap: 块已陈旧` 可自动修复
  - **退出码语义**: 0 健康 / 1 警告已自动修 / 2 关键失败 / 3 环境错误 (对齐 openspec validate)
  - **报告 schema**: `_lib/schemas/env_bootstrap_report_schema.json` version=1
  - **ADR 索引**: 见 `docs/adr/ADR-0053-rdd-env-bootstrap-orchestrator.md`
  ```

- [ ] **Step 4: Run full regression gate**

  Run: `./test.sh --full --regression`
  Expected: ALL GREEN except the 2 pre-existing failures in `KNOWN_FAILURES.txt`
  (`brainstorm-hardgate-enforcement` + `v3-rename-spec-workflow-to-rdd-workflow`).

  If new failures appear: fix or escalate per AGENTS.md "全量回归门" section.

- [ ] **Step 5: Defer commit (worktree-internal)**

  Per AGENTS.md "Worktree Commit Flow", do NOT commit per-task. One aggregate commit at end.

### Task 8: Single aggregate commit + archive (no per-task commit)

**Problem:** Per Worktree Commit Flow, all changes are committed as a single commit on the worktree branch, then archive.

- [ ] **Step 1: Stage all changes**

  ```bash
  cd /workspace/project/rdd-workflow/.rddf/wt/add-env-bootstrap-skill
  git add skills/rdd-env-bootstrap/ _lib/env_bootstrap_report.py _lib/cli/env_bootstrap_cmd.py _lib/cli/__init__.py _lib/cli/__main__.py _lib/schemas/env_bootstrap_report_schema.json tests/unit/test_env_bootstrap_report.py tests/integration/test_env_bootstrap.bats docs/adr/ADR-0053-rdd-env-bootstrap-orchestrator.md README.md AGENTS.md
  git status --short | head -20
  ```

  Note: `openspec/changes/add-env-bootstrap-skill/` is **gitignored** (per `.rddf/project.yaml::git.openspec_tracked: false`) and will NOT appear in `git status`. This is expected.

- [ ] **Step 2: Single commit with conventional message**

  ```bash
  git -c user.name="rdd-builder" -c user.email="builder@rdd-workflow" commit -m "$(cat <<'EOF'
  feat(rdd-env-bootstrap): add 4-phase environment orchestrator

  New skill rdd-env-bootstrap + rddf env-bootstrap CLI subcommand that
  fills the orchestration gap left after Layer 0→3 progressive context
  architecture (per ADR-0052). 4-phase flow: detect → diagnose →
  suggest → guided-fix. Doctor stays read-only (per user insight).

  Includes:
  - skills/rdd-env-bootstrap/{SKILL.md, references/fix-decisions.md, scripts/}
  - _lib/env_bootstrap_report.py (data layer, stdlib + jsonschema)
  - _lib/cli/env_bootstrap_cmd.py (argparse, 4-phase orchestrator)
  - _lib/schemas/env_bootstrap_report_schema.json (v1, 7 required top-level fields)
  - _lib/cli/__init__.py + __main__.py route registration + _NO_STATE_CHECK extension
  - 13 unit tests (5 schema + 3 detect + 2 classify + 3 guided_fix)
  - 10 integration tests (8 CLI + 2 structural)
  - docs/adr/ADR-0053-rdd-env-bootstrap-orchestrator.md (decision record)
  - AGENTS.md / README.md sync

  Auto-fix whitelist restricted to ai-context-bootstrap deploy/staleness
  only (per AC-6). Exit code semantics align with openspec validate.

  Closes add-env-bootstrap-skill.
  EOF
  )"
  ```

- [ ] **Step 3: Verify commit landed on worktree branch**

  ```bash
  git log --oneline -3
  git rev-parse --abbrev-ref HEAD
  ```

  Expected: branch `openspec/add-env-bootstrap-skill`, latest commit shows above message.

- [ ] **Step 4: Run rdd-builder P2.5 review**

  Per `skills/rdd-builder/scripts/phase2_5_review.sh::handle_review_action`:
  - 4-option dispatch: approve / revise / defer / reject
  - Default: review build output, test results, commit message
  - If approve → continue to P3 archive

- [ ] **Step 5: Archive change (P3)**

  Per `skills/rdd-builder/scripts/phase3_archive.sh::archive_change_for_mode`:
  - Worktree mode detected (since we used `.rddf/wt/add-env-bootstrap-skill/`)
  - Run `openspec archive add-env-bootstrap-skill --yes`
  - This triggers `archive_change` in `_lib/archive.sh`:
    1. Find worktree path + default branch (master)
    2. Check worktree has commits (we did)
    3. Switch to default branch (master)
    4. Merge `openspec/add-env-bootstrap-skill` → master
    5. `openspec archive add-env-bootstrap-skill --yes`
    6. Cleanup worktree + branch
    7.5. (Skipped — `git.openspec_tracked: false` → no auto-commit per project.yaml)

  Run: `cd /workspace/project/rdd-workflow && bash skills/rdd-builder/scripts/phase3_archive.sh add-env-bootstrap-skill 2>&1 | head -30`

  Expected: archive completes, master branch contains the merge commit, worktree directory cleaned up.

- [ ] **Step 6: Final regression gate**

  Run from main repo: `./test.sh --full --regression`
  Expected: ALL GREEN except the 2 pre-existing `KNOWN_FAILURES.txt` failures.

- [ ] **Step 7: Done**

  Task complete. The rdd-builder P3 archive gate verifies AC-10 and clears the change from
  `openspec/changes/`.
