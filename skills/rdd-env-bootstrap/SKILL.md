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
  Boundary: owns orchestration only; delegates fixes to rddf setup/init/doctor via subprocess.
license: MIT
compatibility: requires Python 3.11+, bash 4+. No external skill deps.
metadata:
  author: rdd-workflow
  version: "1.0"
  evolved-from: "fix-skill-post-install-discoverability (Layer 0→3 architecture, ADR-0052)"
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

# rdd-env-bootstrap Skill

> Per [ADR-0053](../adr/ADR-0053-rdd-env-bootstrap-orchestrator.md) — 4-phase environment orchestrator that fills the orchestration gap left after Layer 0→3 progressive context architecture (ADR-0052).

## Entry / Exit Contract

**Entry**: `rddf env-bootstrap [flags]` (5 flags: `--check-only` / `--auto-fix` / `--yes` / `--target` / `--report`)

**Exit**:
- Report: `<target>/.rddf/state/.env-bootstrap-report.json` (schema v1)
- Exit code per AC-8:
  - `0` = all healthy / all warnings auto-fixed
  - `1` = WARNING auto-fixed (some findings required action)
  - `2` = CRITICAL or manual-only remaining
  - `3` = environment error (rddf not installed / target not a rdd-workflow project)

## Phase 1 — Project Env Detection (read-only)

**File-based checks. No subprocess. <200ms target.**

| Check | Detection |
|---|---|
| Git repo | `(project_root / ".git").exists()` |
| `.rddf/` initialized | `(project_root / ".rddf").exists()` |
| Language hints | scan for `pyproject.toml`/`setup.py`/`package.json`/`go.mod`/`Cargo.toml` |
| `rddf` CLI install | `shutil.which("rddf")` + `rddf --version` |
| AI config files | scan `AGENTS.md` / `.cursorrules` / `CLAUDE.md` / `.clinerules` / `.continue/rules/*.md` / `.github/copilot-instructions.md` |

Pure functions: `detect_git_repo()` / `detect_rddf_dir()` / `detect_language()` / `detect_rddf_install()` / `detect_ai_config_files()`. See `references/fix-decisions.md` for whitelist rationale.

## Phase 2 — Health Diagnosis (read-only, delegates to doctor)

**`subprocess.run(["rddf", "doctor", "--json"], timeout=5)`** then classify each finding:

| Class | Examples | Behavior |
|---|---|---|
| `auto-fixable` | `ai-context-bootstrap: 未部署` / `块已陈旧` | Phase 4 may execute automatically |
| `user-decision` | `ai-context-bootstrap` (other) / `gitignore` / `docs-consistency` | Phase 4 outputs suggestion only |
| `manual-only` | `bypass-audit` / `orphan-gates` / `migration-residue` | Phase 4 reports + skips |

**Caching**: `rddf doctor` has its own 3600s TTL cache. Re-running env-bootstrap within the cache window is essentially free.

## Phase 3 — Init Suggestion (read+report)

Based on Phase 1 detection, emit suggestions:

- No `.rddf/project.yaml` → suggest `rddf init`
- No AI config files → suggest `rddf setup ai-context`
- Layer 2 docs missing → suggest `bash install.sh --with-docs`
- `manual_only > 0` findings → suggest `rddf doctor --category <cat>` review

Pure computation. <50ms target. Suggestions are written into the report's `phase_3_init_suggestion[]` array.

## Phase 4 — Guided Fix (write)

For each `[auto-fixable]` finding:

| Mode | Behavior |
|---|---|
| Default (no `--auto-fix`) | `input("运行 \`rddf setup ai-context --yes\`? [Y/n] ")` per fix |
| `--auto-fix` | Skip all prompts (auto-runs all `[auto-fixable]`) |
| `--yes` | Same as `--auto-fix` but explicit |

**Safety principle** (per `references/fix-decisions.md`):
- Only `ai-context-bootstrap: 未部署` + `块已陈旧` are auto-fixable
- No modifications to `.gitignore` / tracked files / `.rddf/state/*.json` (other than `.env-bootstrap-report.json`)
- Each fix wrapped in `try/except` → failures recorded, never crash the phase
- `--check-only` skips Phase 4 entirely

## Session Binding

Per [ADR-0017](../adr/ADR-0017-rddf-session-binding.md), skill entry SHOULD bind to a rddf-session via `owner_opencode_session_id`. Binding failure friendly-degrades (proceeds without binding). See `skills/rddf-session/SKILL.md` for the binding contract.

## Environment Variables

| Var | Default | Purpose |
|---|---|---|
| `RDDF_PROJECT_ROOT` | cwd | Target root for project detection (overridden by `--target`) |
| `RDDF_REPORT_ENABLED` | false | Opt-in to L2 reporting (inherited from Hub-Spoke spec) |

## See also

- `references/fix-decisions.md` — auto-fix whitelist + risk levels
- `skills/rdd-env-check/` — phase-internal quick check (different scope, ≤200ms)
- `skills/rdd-doctor/` — read-only diagnostic (delegated target)
- [`../adr/ADR-0053-rdd-env-bootstrap-orchestrator.md`](../adr/ADR-0053-rdd-env-bootstrap-orchestrator.md) — decision record
- [`../adr/ADR-0052-layer-0-progressive-context.md`](../adr/ADR-0052-layer-0-progressive-context.md) — predecessor architecture
- `skills/rddf-session/SKILL.md` — session binding contract
- `.rddf/improvements/add-env-bootstrap-skill.md` — design rationale
