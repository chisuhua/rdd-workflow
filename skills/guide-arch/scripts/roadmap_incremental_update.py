#!/usr/bin/env python3
"""Main roadmap incremental updater (guide-arch Phase 6 Roadmap Sync).

Implements the four-mode algorithm (skip / adr_only / code_only / full) on top
of populate_lib's Task C API, backed by .rddf/state/.populate-state.json
(schema v2). All configuration arrives via env vars (Oracle C1); the codegraph
signal is injected as RDDF_CODEGRAPH_FINGERPRINT — Python NEVER calls MCP.

Env vars:
  RDDF_PROJECT_ROOT          required; project root directory
  RDDF_CODEBASE_COMMIT       optional; git commit recorded in state (default: git HEAD)
  RDDF_ROADMAP_UPDATE        on | off | force   (default on)
  RDDF_INCREMENTAL           on | off           (default on; off == force)
  RDDF_CODEGRAPH_FINGERPRINT optional; "stale" forces full mode

Exit codes: 0 success (including skipped), 1 runtime error, 2 invalid env.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path bootstrap (no hardcoded paths — derived from __file__).
#   parents[0] = guide-arch/scripts
#   parents[1] = guide-arch
#   parents[2] = skills          (enables `from _lib...` global-install layout)
#   parents[3] = project root    (enables `from skills._lib...` repo layout)
_HERE = Path(__file__).resolve()
for _p in (_HERE.parents[2], _HERE.parents[3]):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)


def _import_dependencies():
    """Import scan_adr_catalog + populate_lib API across repo / worktree /
    global-install layouts (mirrors populate_lib._import_scan_adr_catalog)."""
    try:
        from skills._lib.adr_catalog import scan_adr_catalog
        from skills.populate_roadmap_from_arch.scripts.populate_lib import (
            decide_update_mode,
            detect_adr_changes,
            detect_code_changes,
            load_populate_state_or_default,
            save_populate_state,
            select_adrs_for_incremental_verify,
            should_rewrite_phase_fragment,
        )
        return (
            scan_adr_catalog,
            load_populate_state_or_default,
            save_populate_state,
            detect_adr_changes,
            detect_code_changes,
            decide_update_mode,
            select_adrs_for_incremental_verify,
            should_rewrite_phase_fragment,
        )
    except ModuleNotFoundError:
        # Global-install layout: skills/_lib on sys.path via .pth.
        from _lib.adr_catalog import scan_adr_catalog  # type: ignore[no-redef]

        scripts_dir = str(_HERE.parents[2] / "populate-roadmap-from-arch" / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from populate_lib import (  # type: ignore[no-redef]
            decide_update_mode,
            detect_adr_changes,
            detect_code_changes,
            load_populate_state_or_default,
            save_populate_state,
            select_adrs_for_incremental_verify,
            should_rewrite_phase_fragment,
        )
        return (
            scan_adr_catalog,
            load_populate_state_or_default,
            save_populate_state,
            detect_adr_changes,
            detect_code_changes,
            decide_update_mode,
            select_adrs_for_incremental_verify,
            should_rewrite_phase_fragment,
        )


def _validate_env() -> int:
    """Run the sibling env validator (roadmap_incremental_update.env.py).

    The file name contains a dot (`.env.py`) so it cannot be imported as a
    normal module; load it by path via importlib. Exit code 2 on invalid env.
    """
    env_py = _HERE.with_name("roadmap_incremental_update.env.py")
    spec = importlib.util.spec_from_file_location(
        "roadmap_incremental_update_env", env_py
    )
    if spec is None or spec.loader is None:
        print(f"❌ env validator not loadable: {env_py}", file=sys.stderr)
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate()


def _maybe_save_supplementary(records, project_root: Path) -> None:
    """Crash-safe write order, step 1 (design.md Decision 6): supplementary
    verification records (schema v1) are written BEFORE the v2 state file.

    This entry point produces no AdrCodeVerification records, so the call is
    a no-op today; it is wired explicitly so a future verification-enabled
    caller can pass records without reordering writes. Skip silently if the
    v1.1 helper is not importable.
    """
    if not records:
        return
    try:
        from skills.populate_roadmap_from_arch.scripts.populate_lib import (
            save_supplementary,
        )
    except ImportError:
        return
    save_supplementary(records, project_root)


def _git_head(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        head = result.stdout.strip()
        if result.returncode == 0 and head:
            return head
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "0000000"


def main() -> int:
    start = time.monotonic()

    rc = _validate_env()
    if rc != 0:
        return rc

    project_root = Path(os.environ["RDDF_PROJECT_ROOT"])
    codebase_commit = os.environ.get("RDDF_CODEBASE_COMMIT", "") or _git_head(project_root)
    roadmap_update = os.environ.get("RDDF_ROADMAP_UPDATE", "on")
    incremental = os.environ.get("RDDF_INCREMENTAL", "on") == "on"

    if roadmap_update == "off":
        return 0

    (
        scan_adr_catalog,
        load_populate_state_or_default,
        save_populate_state,
        detect_adr_changes,
        detect_code_changes,
        decide_update_mode,
        select_adrs_for_incremental_verify,
        should_rewrite_phase_fragment,
    ) = _import_dependencies()

    try:
        state = load_populate_state_or_default(project_root)

        if state is None or roadmap_update == "force" or not incremental:
            mode = "full"
            if state is None:
                reason = "no baseline"
            elif roadmap_update == "force":
                reason = "force flag"
            else:
                reason = "incremental off"
            extra = None
        else:
            adr_changes = detect_adr_changes(state, project_root, scan_adr_catalog)
            code_changes = detect_code_changes(state, project_root)
            mode, reason, extra = decide_update_mode(adr_changes, code_changes)

        catalog = scan_adr_catalog(project_root)
        to_verify, to_reuse = select_adrs_for_incremental_verify(
            list(catalog.keys()), state or {}, mode, extra
        )
        # Phase fragments are rewritten only for full / adr_only modes
        # (populate_lib.should_rewrite_phase_fragment); this updater owns the
        # state file, fragment rendering stays with the populate skill.
        _ = should_rewrite_phase_fragment  # imported for the Phase 6 caller chain

        # Crash-safe write order (design.md Decision 6):
        #   1. save_supplementary (v1.1, optional — no records here, see helper)
        #   2. save_populate_state (v2, required)
        # A crash between the two leaves state lagging -> next run falls back
        # to a conservative full mode.
        if mode != "skip":
            _maybe_save_supplementary([], project_root)
            prev = state or {}
            new_state = {
                "adrs": {
                    adr_id: {
                        "file_path": str(meta.file_path),
                        "file_hash": meta.file_hash,
                        "title": meta.title,
                        "status": meta.status,
                        "phase": meta.phase,
                        "category": meta.category,
                    }
                    for adr_id, meta in catalog.items()
                },
                "reverse_index": dict(prev.get("reverse_index", {})),
                "phases": dict(prev.get("phases", {})),
                "codegraph_fingerprint": os.environ.get("RDDF_CODEGRAPH_FINGERPRINT") or None,
            }
            save_populate_state(new_state, project_root, codebase_commit)

        elapsed = time.monotonic() - start
        print(
            f"✓ Mode: {mode} | Reason: {reason} | "
            f"ADRs to verify: {len(to_verify)} | Elapsed: {elapsed:.1f}s",
            file=sys.stderr,
        )
        return 0
    except Exception as e:  # noqa: BLE001 — top-level guard, fail with exit 1
        print(f"❌ roadmap_incremental_update failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
