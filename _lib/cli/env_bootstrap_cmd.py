"""rddf env-bootstrap orchestrator (4 phases: detect → diagnose → suggest → guided-fix).

CLI entry point for `rddf env-bootstrap [flags]`.

Flags (per AC-2):
    --check-only    Run Phases 1-2 only (read-only, CI-friendly).
    --auto-fix      Phase 4 skips prompts (requires --yes for explicit double confirm).
    --yes           Skip all confirmation prompts.
    --target <path> Target project root (default: $RDDF_PROJECT_ROOT or cwd).
    --report <path> Report output path (default: <target>/.rddf/state/.env-bootstrap-report.json).

Exit codes (per AC-8):
    0 = healthy / all warnings auto-fixed
    1 = WARNING auto-fixed (some findings required action)
    2 = CRITICAL or manual-only remaining
    3 = environment error (rddf not installed / target not a rdd-workflow project)

Boundary (per ADR-0028):
    owns: .rddf/state/.env-bootstrap-report.json
    not_owns: _lib/cli/{setup,init,doctor}_cmd.py, skills/rdd-doctor/, skills/rdd-env-check/
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from skills._lib.cli import resolve_project_root  # noqa: E402  (per fix-33-handlers)


def _resolve_target_root(args_target: str | None) -> Path:
    """Resolve target project root from --target, env var, or cwd."""
    return Path(
        args_target
        or os.environ.get("RDDF_PROJECT_ROOT")
        or resolve_project_root()
    ).resolve()


def _is_rdd_workflow_project(target_root: Path) -> bool:
    """Heuristic: project has _lib/ or .rddf/state/."""
    return (target_root / "_lib").is_dir() or (target_root / ".rddf" / "state").is_dir()


def _build_fix_command(finding: dict[str, Any]) -> list[str]:
    """Per AC-6: only ai-context-bootstrap with 未部署/块已陈旧/stale/outdated is auto-fixable."""
    msg = finding.get("message", "")
    msg_lower = msg.lower()
    if (
        "未部署" in msg
        or "块已陈旧" in msg
        or "stale" in msg_lower
        or "outdated" in msg_lower
    ):
        return ["rddf", "setup", "ai-context", "--yes"]
    # Fallback: no-op (should not happen because classify_finding already gates this)
    return ["echo", "no-auto-fix-available"]


def _confirm(prompt: str) -> bool:
    """Interactive Y/n prompt. Returns True on empty / y / yes."""
    try:
        reply = input(prompt).strip().lower()
    except EOFError:
        return False
    return reply in ("", "y", "yes")


def _compute_exit_code(phase_2: dict[str, Any], phase_4: dict[str, Any]) -> int:
    """Compute exit code per AC-8."""
    has_critical = any(
        f.get("severity") == "critical" for f in phase_2.get("findings", [])
    )
    manual_only = phase_2.get("manual_only", 0)
    warnings_auto_fixed = sum(
        1 for e in phase_4.get("executed", []) if e.get("status") == "success"
    )

    if has_critical or manual_only > 0:
        return 2
    if warnings_auto_fixed > 0:
        return 1
    return 0


def cmd_env_bootstrap(args: list[str]) -> int:
    """Handle ``rddf env-bootstrap [flags]``."""
    parser = argparse.ArgumentParser(
        prog="rddf env-bootstrap",
        description=(
            "4-phase environment orchestrator "
            "(detect → diagnose → suggest → guided-fix). "
            "Boundary: owns orchestration only; delegates fixes to rddf setup/init/doctor via subprocess."
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run Phases 1-2 only. No writes. Exits 0 if doctor ran.",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Phase 4 skips prompts (use with --yes for double confirmation).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip all confirmation prompts.",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Target project root (default: $RDDF_PROJECT_ROOT or cwd).",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Report output path (default: <target>/.rddf/state/.env-bootstrap-report.json).",
    )

    parsed = parser.parse_args(args)

    target_root = _resolve_target_root(parsed.target)
    if not _is_rdd_workflow_project(target_root):
        print(
            f"ℹ️  not a rdd-workflow project (target={target_root})",
            file=sys.stderr,
        )
        print(
            "   Run: bash ~/.agents/skills/rdd-workflow/install.sh --global",
            file=sys.stderr,
        )
        return 3

    # Phase 1: import scripts
    _SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "rdd-env-bootstrap"
    scripts_path = str(_SKILL_ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)

    # Import canonical data layer (no skills._lib shim, per P1-1b canonical layer)
    try:
        from _lib.env_bootstrap_report import build_report, write_report, load_report
        from detect_environment import (
            detect_git_repo, detect_rddf_dir, detect_language,
            detect_rddf_install, detect_ai_config_files,
        )
        from diagnose import diagnose
        from guided_fix import run_guided_fix
    except ImportError as e:
        print(f"❌ env-bootstrap: import failure: {e}", file=sys.stderr)
        return 1

    # Phase 1 detection
    phase_1 = {
        "is_git_repo": detect_git_repo(target_root),
        "has_rddf_dir": detect_rddf_dir(target_root),
        "language_hints": detect_language(target_root),
        "rddf_installed": detect_rddf_install(),
        "ai_config_files_detected": detect_ai_config_files(target_root),
    }

    # Idempotency: if report exists with version=1, reuse phase_1 (per AC-7)
    report_path = Path(
        parsed.report
        or (target_root / ".rddf" / "state" / ".env-bootstrap-report.json")
    )
    existing = load_report(report_path) if report_path.is_file() else None
    if existing and existing.get("version") == 1 and not parsed.check_only:
        # Reuse phase_1 from previous run, but re-run doctor (Phase 2 may have new findings)
        phase_1_reused = existing.get("phase_1_detection", {})
        # Only reuse if target_root matches
        if existing.get("project_root") == str(target_root):
            phase_1 = phase_1_reused

    if parsed.check_only:
        # Phases 1-2 only, no write
        phase_2 = diagnose(target_root)
        print(
            json.dumps(
                {"phase_1": phase_1, "phase_2": phase_2},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    # Phase 2 diagnosis
    phase_2 = diagnose(target_root)

    # Phase 3 suggestion
    phase_3: list[str] = []
    if not phase_1.get("has_rddf_dir"):
        phase_3.append("rddf init (生成 .rddf/project.yaml)")
    if not phase_1.get("ai_config_files_detected"):
        phase_3.append("rddf setup ai-context (部署 Layer 0)")
    if phase_2.get("manual_only", 0) > 0:
        phase_3.append(
            f"review {phase_2['manual_only']} manual-only findings via rddf doctor"
        )

    # Phase 4 guided fix
    auto_fixable = [
        f for f in phase_2.get("findings", []) if f.get("class") == "auto-fixable"
    ]
    confirm_fn: Any = None
    if not (parsed.yes or parsed.auto_fix):
        confirm_fn = _confirm
    phase_4 = run_guided_fix(
        auto_fixable_findings=auto_fixable,
        target_root=str(target_root),
        fix_command_for=_build_fix_command,
        auto_fix=bool(parsed.auto_fix or parsed.yes),
        confirm=confirm_fn,
    )

    exit_code = _compute_exit_code(phase_2, phase_4)

    report = build_report(
        phase_1_detection=phase_1,
        phase_2_diagnosis=phase_2,
        phase_3_init_suggestion=phase_3,
        phase_4_guided_fix=phase_4,
        exit_code=exit_code,
        project_root=str(target_root),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        write_report(report, report_path)
    except Exception as e:
        print(f"⚠️  write_report failed: {e}", file=sys.stderr)

    print(f"✅ Report: {report_path} (exit={exit_code})")
    if phase_3:
        print("\n💡 Suggested actions:")
        for s in phase_3:
            print(f"  - {s}")
    if phase_4["executed"]:
        success = sum(1 for e in phase_4["executed"] if e["status"] == "success")
        print(f"\n🔧 Phase 4 executed: {success}/{len(phase_4['executed'])} successful")
    return exit_code


__all__ = ["cmd_env_bootstrap"]
