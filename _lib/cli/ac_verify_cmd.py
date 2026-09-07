"""``rddf ac-verify`` subcommand handler — DEPRECATED shim (ADR-0045).

⚠️ DEPRECATED 2026-09-07 per ADR-0045 (inline-ac-verifier-into-rdd-verifier).
`rdd-verifier` v2.0 self-contains LLM verification; this CLI is retained as a
backward-compatibility shim for one release cycle. New code MUST use
``rddf rdd-verify``.

Shim semantics (maps old ac-verify behavior onto the v2.0 agent protocol):
    rddf ac-verify <change> [--dry-run] [--strict] [--skip]

Exit codes:
    0 = all cached ACs pass, no AC section, staged for agent verification,
        or --dry-run
    1 = cached verdict has a failed AC under --strict
    2 = skipped (--skip, no proposal.md)
    3 = staging error

Env vars still honored (gate level only):
    STRICT_AC_GATE, SKIP_AC_VERIFICATION, RDDF_PROJECT_ROOT
(AC_LLM_* variables are no longer consumed — the executing AI agent IS the
LLM; see skills/rdd-verifier/SKILL.md § "LLM Verification Protocol".)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _lib.verifier.cache import read_verdict_cache, is_cache_fresh
from _lib.verifier.protocol import stage_verification_context


def _print_deprecation_notice() -> None:
    print("⚠️  DEPRECATED: 'rddf ac-verify' is deprecated per ADR-0045; "
          "use 'rddf rdd-verify' instead.", file=sys.stderr)


def cmd_ac_verify(args: list[str]) -> int:
    """Handle ``rddf ac-verify`` (deprecated shim → v2.0 agent protocol)."""
    parser = argparse.ArgumentParser(
        prog="rddf ac-verify",
        description="Verify OpenSpec change acceptance criteria (deprecated shim "
                    "per ADR-0045; prefer 'rddf rdd-verify')",
    )
    parser.add_argument("change_name", help="OpenSpec change name")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be staged without writing files")
    parser.add_argument("--strict", action="store_true",
                        help="Block (exit 1) on any cached AC fail")
    parser.add_argument("--skip", action="store_true",
                        help="Skip verification entirely")
    parser.add_argument("--project-root", type=Path, default=None,
                        help="Project root (default: $RDDF_PROJECT_ROOT or cwd)")
    parsed = parser.parse_args(args)

    _print_deprecation_notice()

    project_root = parsed.project_root or Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )

    if parsed.skip or os.environ.get("SKIP_AC_VERIFICATION", "").lower() == "yes":
        print("⏭️  AC verification skipped", file=sys.stderr)
        return 2

    proposal = project_root / "openspec" / "changes" / parsed.change_name / "proposal.md"
    if not proposal.is_file():
        print(f"⚠️  proposal.md not found at {proposal}; skipping", file=sys.stderr)
        return 2

    # Fresh cache → evaluate cached verdict directly (no agent round-trip).
    current_sha = None
    try:
        import subprocess as _sp
        current_sha = _sp.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except Exception:
        current_sha = None

    if current_sha and is_cache_fresh(project_root, parsed.change_name, current_sha):
        cached = read_verdict_cache(project_root, parsed.change_name) or {}
        verdict = cached.get("verdict", [])
        failed = [v for v in verdict if v.get("status") == "fail"]
        if not failed:
            print("♻️  Reusing verdict cache: all ACs pass")
            return 0
        strict = parsed.strict or os.environ.get("STRICT_AC_GATE", "").lower() == "yes"
        for v in failed:
            print(f"  ❌ {v.get('ac_id', '?')}: {v.get('reasoning', 'no reasoning')}")
        if strict:
            print("❌ AC verification failed under --strict/STRICT_AC_GATE (cached)")
            return 1
        print("⚠️  AC verification failed (cached); warning only "
              "(use --strict/STRICT_AC_GATE=yes to block)")
        return 0

    # Cache miss/stale → stage agent context (v2.0 protocol).
    if parsed.dry_run:
        print(f"[dry-run] Would stage verification context for "
              f"{parsed.change_name} at "
              f".rddf/state/rdd-verify-context-{parsed.change_name}.json")
        return 0

    ctx_path = stage_verification_context(parsed.change_name, project_root)
    if ctx_path is None:
        print("❌ failed to stage verification context", file=sys.stderr)
        return 3

    # Zero-AC proposal → pass-through (v2.0 SKILL.md Step 6 + legacy contract)
    import json as _json
    ctx = _json.loads(Path(ctx_path).read_text(encoding="utf-8"))
    if ctx.get("ac_count", 0) == 0:
        print("✅ No acceptance criteria section; pass-through (exit 0)")
        return 0

    print(f"📌 Staged verification context: {ctx_path}")
    print("   Agent: verify per skills/rdd-verifier/SKILL.md § LLM Verification "
          "Protocol, write the verdict cache, then re-run to evaluate.")
    return 0


if __name__ == "__main__":
    sys.exit(cmd_ac_verify(sys.argv[1:]))
