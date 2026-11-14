"""consolidate-verifier-state: verifier state namespace + one-shot migration.

Per openspec/changes/consolidate-verifier-state:
- `.rddf/state/verifier/` is the single namespace for verifier state
- the verdict cache path has exactly one definition point (`verdict_cache_path`)
- the archive gate keeps resolving its OWN root (main repo) — the path
  expression is shared, the root is not
- legacy files under `.rddf/state/` are moved once, explicitly (no dual-path
  read fallback: a dual path would let the bash archive gate and the python
  reader disagree about whether a cache exists)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.cache import (  # noqa: E402
    audit_log_path,
    blocked_audit_log_path,
    legacy_verdict_cache_path,
    migrate_legacy_state,
    read_verdict_cache,
    verdict_cache,
    verdict_cache_path,
    verify_context_path,
)
from _lib.verifier.archive_gate import _cache_path as archive_gate_cache_path  # noqa: E402


# ── Path shape ──────────────────────────────────────────────────────────────

def test_verdict_cache_path_is_under_verifier_namespace():
    p = verdict_cache_path(Path("/tmp/proj"), "ch-x")
    assert p == Path("/tmp/proj/.rddf/state/verifier/.ac-verdict-ch-x.json")


def test_audit_and_context_paths_are_under_verifier_namespace():
    root = Path("/tmp/proj")
    assert audit_log_path(root) == Path("/tmp/proj/.rddf/state/verifier/.ac-verification.jsonl")
    assert blocked_audit_log_path(root) == Path(
        "/tmp/proj/.rddf/state/verifier/.ac-verifier-blocked.jsonl")
    assert verify_context_path(root, "ch-x") == Path(
        "/tmp/proj/.rddf/state/verifier/rdd-verify-context-ch-x.json")


def test_legacy_path_is_still_reachable_for_migration():
    assert legacy_verdict_cache_path(Path("/tmp/proj"), "ch-x") == Path(
        "/tmp/proj/.rddf/state/.ac-verdict-ch-x.json")


def test_archive_gate_shares_path_expression_but_not_root():
    """Same path expression, DIFFERENT root — the worktree trap.

    The archive gate resolves the main repository root itself (worktree mode
    keeps the cache in the main repo). Unifying the roots would make the gate
    look in the worktree and always miss.
    """
    main_root = Path("/repo")
    worktree = Path("/repo/.rddf/wt/ch-x")
    assert archive_gate_cache_path(main_root, "ch-x") == verdict_cache_path(main_root, "ch-x")
    assert archive_gate_cache_path(main_root, "ch-x") != verdict_cache_path(worktree, "ch-x")


def test_single_path_principle_no_dual_read(tmp_path):
    """A cache at the legacy location is NOT read (single path, no fallback).

    The archive gate (bash) only ever looks at the new path; if the python
    reader silently accepted the legacy path too, the two sides could disagree
    about whether a verdict exists.
    """
    legacy = tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({
        "schema_version": 2, "change": "ch-x", "codebase_commit": "abc",
        "verdict": [{"ac_id": "AC-1", "status": "pass"}],
    }))
    assert read_verdict_cache(tmp_path, "ch-x") is None


# ── Migration ───────────────────────────────────────────────────────────────

def _legacy_file(root: Path, name: str) -> Path:
    p = root / ".rddf" / "state" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")
    return p


def test_migration_moves_all_four_kinds(tmp_path):
    names = [
        ".ac-verdict-ch-x.json",
        ".ac-verification.jsonl",
        ".ac-verifier-blocked.jsonl",
        "rdd-verify-context-ch-x.json",
    ]
    for n in names:
        _legacy_file(tmp_path, n)
    results = migrate_legacy_state(tmp_path)
    assert sorted(results) == sorted(("moved", n) for n in names)
    target = tmp_path / ".rddf" / "state" / "verifier"
    for n in names:
        assert (target / n).is_file()
        assert not (tmp_path / ".rddf" / "state" / n).exists()


def test_migration_never_overwrites_existing_destination(tmp_path):
    _legacy_file(tmp_path, ".ac-verdict-ch-x.json")
    dest = tmp_path / ".rddf" / "state" / "verifier" / ".ac-verdict-ch-x.json"
    dest.parent.mkdir(parents=True)
    dest.write_text('{"keep": true}')
    results = migrate_legacy_state(tmp_path)
    assert ("skipped", ".ac-verdict-ch-x.json") in results
    assert json.loads(dest.read_text()) == {"keep": True}


def test_migration_is_idempotent(tmp_path):
    _legacy_file(tmp_path, ".ac-verdict-ch-x.json")
    migrate_legacy_state(tmp_path)
    assert migrate_legacy_state(tmp_path) == []


def test_migration_on_missing_state_dir_is_noop(tmp_path):
    assert migrate_legacy_state(tmp_path) == []


def test_migration_failure_is_reported_not_raised(tmp_path):
    """Best effort: an unusable target directory must not raise, and the
    source files must survive (a lost cache would only cost a re-run, but a
    lost verdict must never look like a passed verification)."""
    names = [".ac-verdict-ch-x.json", ".ac-verification.jsonl"]
    for n in names:
        _legacy_file(tmp_path, n)
    # Make the target directory impossible to create (a file sits there).
    (tmp_path / ".rddf" / "state" / "verifier").write_text("not a directory")
    results = migrate_legacy_state(tmp_path)
    assert sorted(results) == sorted(("failed", n) for n in names)
    for n in names:
        assert (tmp_path / ".rddf" / "state" / n).is_file()


# ── Round trip: write → read through the new namespace ──────────────────────

def test_cache_round_trip_in_new_namespace(tmp_path):
    verdict_cache(tmp_path, "ch-x", "abc123",
                  [{"ac_id": "AC-1", "status": "pass"}], ran_by="rdd-verifier")
    cached = read_verdict_cache(tmp_path, "ch-x")
    assert cached is not None
    assert cached["codebase_commit"] == "abc123"
    assert verdict_cache_path(tmp_path, "ch-x").is_file()
