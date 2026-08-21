r"""Scenario tests for populate_lib.py incremental-update functions (Task C / Task I.1).

Covers the decision matrix T1-T9 + T13-T16 from tasks.md plus edge cases:
- T1  no changes                    -> skip
- T2  only ADR changed              -> adr_only
- T3  only code changed             -> code_only
- T4  both changed                  -> full
- T5  new ADR detected              -> adr_only (new id in extra)
- T6  ADR deleted                   -> adr_only (deleted id in extra)
- T7  state missing                 -> load returns None (caller picks full)
- T8  RDDF_CODEGRAPH_FINGERPRINT=stale -> full
- T9  state version=1               -> load returns None + stderr (caller picks full)
- T13 codebase_commit not in git    -> full + stderr warning
- T14 valid last..HEAD range        -> no crash, files detected
- T15 state rewrite roundtrip       -> save/load preserves new codebase_commit
- T16 merge commit                  -> code_only (conservative)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "populate-roadmap-from-arch" / "scripts"))

from populate_lib import (  # noqa: E402
    decide_update_mode,
    detect_adr_changes,
    detect_code_changes,
    load_populate_state_or_default,
    save_populate_state,
    select_adrs_for_incremental_verify,
    should_rewrite_phase_fragment,
)
from skills._lib.adr_catalog import scan_adr_catalog  # noqa: E402


# ---- Helpers / fixtures ----

def _make_state(commit: str = "9536da9", adrs=None, reverse_index=None, phases=None) -> dict:
    return {
        "version": 2,
        "generated_at": "2026-08-21T00:00:00Z",
        "codebase_commit": commit,
        "codegraph_fingerprint": None,
        "adrs": adrs or {},
        "reverse_index": reverse_index or {},
        "phases": phases or {},
    }


def _adr_entry(adr_id: str, file_hash: str, title: str = "T", status: str = "已采纳") -> dict:
    return {
        "file_path": f"docs/adr/{adr_id}-x.md",
        "file_hash": file_hash,
        "title": title,
        "status": status,
        "phase": None,
        "category": None,
    }


def _write_adr(adr_dir: Path, adr_id: str, slug: str, body: str = "# body\n") -> Path:
    f = adr_dir / f"{adr_id}-{slug}.md"
    f.write_text(
        f"---\nstatus: 已采纳\ntitle: {slug}\n---\n# {slug}\n\n{body}",
        encoding="utf-8",
    )
    return f


def _state_adrs_from_catalog(catalog: dict) -> dict:
    return {
        aid: {
            "file_path": str(meta.file_path),
            "file_hash": meta.file_hash,
            "title": meta.title,
            "status": meta.status,
            "phase": meta.phase,
            "category": meta.category,
        }
        for aid, meta in catalog.items()
    }


@pytest.fixture
def adr_project(tmp_path):
    """Project with docs/adr/ADR-0001 + ADR-0002 and a matching v2 state."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, "ADR-0001", "foo")
    _write_adr(adr_dir, "ADR-0002", "bar")
    state = _make_state(adrs=_state_adrs_from_catalog(scan_adr_catalog(tmp_path)))
    return tmp_path, adr_dir, state


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, capture_output=True, text=True,
    )


def _git_commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "-c", "commit.gpgsign=false", "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def git_repo(tmp_path):
    """A git repo with one .py file committed; returns (root, base_commit)."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "foo.py").write_text("def alpha():\n    pass\n", encoding="utf-8")
    base = _git_commit(tmp_path, "init")
    return tmp_path, base


# ---- T1-T4: decide_update_mode matrix ----

def test_t1_decide_skip_when_nothing_changed():
    mode, reason, extra = decide_update_mode(([], [], []), (set(), [], "ok"))
    assert mode == "skip"
    assert reason == "no changes"
    assert extra is None


def test_t2_decide_adr_only_when_only_adr_changed():
    mode, reason, extra = decide_update_mode((["ADR-0001"], [], []), (set(), [], "ok"))
    assert mode == "adr_only"
    assert "ADR-0001" in extra


def test_t3_decide_code_only_when_only_code_changed():
    mode, reason, extra = decide_update_mode(([], [], []), ({"ADR-0001"}, ["foo.py"], "ok"))
    assert mode == "code_only"
    assert extra == {"ADR-0001"}


def test_t4_decide_full_when_both_changed():
    mode, reason, extra = decide_update_mode((["ADR-0001"], [], []), ({"ADR-0002"}, ["foo.py"], "ok"))
    assert mode == "full"
    assert extra is None


# ---- T5/T6: detect_adr_changes new / deleted ----

def test_t5_new_adr_detected_as_adr_only_with_id_in_extra(adr_project):
    project_root, adr_dir, state = adr_project
    _write_adr(adr_dir, "ADR-0099", "new-adr")

    changed, new, deleted = detect_adr_changes(state, project_root, scan_adr_catalog)
    assert changed == [] and deleted == []
    assert new == ["ADR-0099"]

    mode, _, extra = decide_update_mode((changed, new, deleted), (set(), [], "ok"))
    assert mode == "adr_only"
    assert "ADR-0099" in extra


def test_t6_deleted_adr_detected_as_adr_only_with_id_in_extra(adr_project):
    project_root, adr_dir, state = adr_project
    (adr_dir / "ADR-0001-foo.md").unlink()

    changed, new, deleted = detect_adr_changes(state, project_root, scan_adr_catalog)
    assert changed == [] and new == []
    assert deleted == ["ADR-0001"]

    mode, _, extra = decide_update_mode((changed, new, deleted), (set(), [], "ok"))
    assert mode == "adr_only"
    assert "ADR-0001" in extra


def test_t2b_modified_adr_detected_via_file_hash(adr_project):
    project_root, adr_dir, state = adr_project
    _write_adr(adr_dir, "ADR-0001", "foo", body="# body changed\n")

    changed, new, deleted = detect_adr_changes(state, project_root, scan_adr_catalog)
    assert changed == ["ADR-0001"]
    assert new == [] and deleted == []


# ---- T7/T9: load_populate_state_or_default failure modes ----

def test_t7_missing_state_file_returns_none_caller_picks_full(tmp_path):
    state = load_populate_state_or_default(tmp_path)
    assert state is None
    # caller contract (roadmap_incremental_update.py): no baseline -> full
    mode = "full" if state is None else decide_update_mode(([], [], []), (set(), [], "ok"))[0]
    assert mode == "full"


def test_t9_version1_state_returns_none_with_stderr(tmp_path, capsys):
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    bad = _make_state()
    bad["version"] = 1
    (state_dir / ".populate-state.json").write_text(json.dumps(bad), encoding="utf-8")

    state = load_populate_state_or_default(tmp_path)
    assert state is None
    err = capsys.readouterr().err
    assert "schema version 1 unsupported, expected 2" in err
    # caller contract: schema mismatch -> full rebuild
    mode = "full" if state is None else "skip"
    assert mode == "full"


# ---- T8: codegraph stale env var ----

def test_t8_codegraph_stale_env_forces_full(git_repo, monkeypatch):
    project_root, base = git_repo
    monkeypatch.setenv("RDDF_CODEGRAPH_FINGERPRINT", "stale")
    state = _make_state(commit=base)

    _, _, status = detect_code_changes(state, project_root)
    assert status == "stale"

    mode, reason, extra = decide_update_mode(([], [], []), (set(), [], status))
    assert mode == "full"
    assert reason == "codegraph stale"


# ---- T13: force-push / missing baseline commit ----

def test_t13_missing_codebase_commit_forces_full_with_stderr(git_repo, capsys, monkeypatch):
    monkeypatch.delenv("RDDF_CODEGRAPH_FINGERPRINT", raising=False)
    project_root, _ = git_repo
    state = _make_state(commit="0" * 40)  # not in repo history

    changed, files, status = detect_code_changes(state, project_root)
    assert status != "ok"
    err = capsys.readouterr().err
    assert "not found" in err or "missing" in err.lower()

    mode, _, _ = decide_update_mode(([], [], []), (changed, files, status))
    assert mode == "full"


# ---- T14: valid range after new commit (rebase-safe path) ----

def test_t14_valid_range_detects_changed_py_file_no_crash(git_repo, monkeypatch):
    monkeypatch.delenv("RDDF_CODEGRAPH_FINGERPRINT", raising=False)
    project_root, base = git_repo
    (project_root / "foo.py").write_text(
        "def alpha():\n    pass\n\ndef gamma():\n    pass\n", encoding="utf-8"
    )
    _git_commit(project_root, "add gamma")

    state = _make_state(commit=base, reverse_index={"gamma": ["ADR-0001"]})
    changed_adrs, files, status = detect_code_changes(state, project_root)

    assert status == "ok"
    assert "foo.py" in files
    assert changed_adrs == {"ADR-0001"}

    mode, _, extra = decide_update_mode(([], [], []), (changed_adrs, files, status))
    assert mode == "code_only"
    assert extra == {"ADR-0001"}


# ---- T15: state rewrite roundtrip (cherry-pick => new HEAD persisted) ----

def test_t15_state_rewrite_roundtrip_preserves_new_commit(git_repo):
    project_root, base = git_repo
    (project_root / "bar.py").write_text("def beta():\n    pass\n", encoding="utf-8")
    new_head = _git_commit(project_root, "cherry-picked change")

    state = _make_state(adrs={"ADR-0001": _adr_entry("ADR-0001", "a" * 64)})
    save_populate_state(state, project_root, new_head)

    loaded = load_populate_state_or_default(project_root)
    assert loaded is not None
    assert loaded["codebase_commit"] == new_head
    assert loaded["version"] == 2
    assert set(loaded["adrs"].keys()) == {"ADR-0001"}


# ---- T16: merge commit -> code_only (conservative) ----

def test_t16_merge_commit_yields_code_only(git_repo, monkeypatch):
    monkeypatch.delenv("RDDF_CODEGRAPH_FINGERPRINT", raising=False)
    project_root, base = git_repo

    _git(project_root, "checkout", "-b", "side")
    (project_root / "side.py").write_text("def side_fn():\n    pass\n", encoding="utf-8")
    _git_commit(project_root, "side work")

    _git(project_root, "checkout", "master")
    (project_root / "main.py").write_text("def main_fn():\n    pass\n", encoding="utf-8")
    _git_commit(project_root, "main work")

    _git(project_root, "-c", "commit.gpgsign=false", "merge", "--no-ff", "side", "-m", "merge side")

    state = _make_state(commit=base)
    changed_adrs, files, status = detect_code_changes(state, project_root)
    assert status == "ok"
    assert set(files) >= {"side.py", "main.py"}

    mode, _, _ = decide_update_mode(([], [], []), (changed_adrs, files, status))
    assert mode == "code_only"  # conservative over-trigger is correct


# ---- C6: select_adrs_for_incremental_verify ----

def test_select_adrs_skip_verifies_nothing_reuses_all():
    prev = {"ADR-0001": _adr_entry("ADR-0001", "a" * 64)}
    state = _make_state(adrs=prev)
    to_verify, to_reuse = select_adrs_for_incremental_verify(["ADR-0001"], state, "skip", None)
    assert to_verify == []
    assert set(to_reuse.keys()) == {"ADR-0001"}


def test_select_adrs_full_verifies_all_reuses_nothing():
    prev = {"ADR-0001": _adr_entry("ADR-0001", "a" * 64)}
    state = _make_state(adrs=prev)
    to_verify, to_reuse = select_adrs_for_incremental_verify(["ADR-0001", "ADR-0002"], state, "full", None)
    assert set(to_verify) == {"ADR-0001", "ADR-0002"}
    assert to_reuse == {}


def test_select_adrs_adr_only_splits_verify_and_reuse():
    prev = {
        "ADR-0001": _adr_entry("ADR-0001", "a" * 64),
        "ADR-0002": _adr_entry("ADR-0002", "b" * 64),
    }
    state = _make_state(adrs=prev)
    to_verify, to_reuse = select_adrs_for_incremental_verify(
        ["ADR-0001", "ADR-0002"], state, "adr_only", ["ADR-0001"]
    )
    assert to_verify == ["ADR-0001"]
    assert set(to_reuse.keys()) == {"ADR-0002"}


def test_select_adrs_code_only_maps_symbols_via_reverse_index():
    prev = {
        "ADR-0001": _adr_entry("ADR-0001", "a" * 64),
        "ADR-0002": _adr_entry("ADR-0002", "b" * 64),
    }
    state = _make_state(adrs=prev, reverse_index={"gamma": ["ADR-0002"]})
    to_verify, to_reuse = select_adrs_for_incremental_verify(
        ["ADR-0001", "ADR-0002"], state, "code_only", {"gamma"}
    )
    assert to_verify == ["ADR-0002"]
    assert set(to_reuse.keys()) == {"ADR-0001"}


# ---- C7: should_rewrite_phase_fragment ----

def test_should_rewrite_phase_fragment_matrix():
    prev = _make_state(phases={"phase-1": {"fragment_path": ".rddf/roadmap/phases/phase-1.md",
                                            "last_generated_at": "2026-08-21T00:00:00Z"}})
    new = _make_state()
    assert should_rewrite_phase_fragment("phase-1", prev, new, "full") is True
    assert should_rewrite_phase_fragment("phase-1", prev, new, "adr_only") is True
    assert should_rewrite_phase_fragment("phase-1", prev, new, "skip") is False
    assert should_rewrite_phase_fragment("phase-1", prev, new, "code_only") is False


# ---- Edge cases ----

def test_edge_code_only_with_empty_reverse_index_still_triggers(git_repo, monkeypatch):
    """Non-.py change (or unindexed symbols): files changed but no ADR mapped."""
    monkeypatch.delenv("RDDF_CODEGRAPH_FINGERPRINT", raising=False)
    project_root, base = git_repo
    (project_root / "README.md").write_text("# docs changed\n", encoding="utf-8")
    _git_commit(project_root, "docs")

    state = _make_state(commit=base)  # empty reverse_index
    changed_adrs, files, status = detect_code_changes(state, project_root)
    assert changed_adrs == set()
    assert files == ["README.md"]

    mode, _, extra = decide_update_mode(([], [], []), (changed_adrs, files, status))
    assert mode == "code_only"
    assert extra == set()


def test_edge_duplicate_symbols_across_files_dedup_to_same_adr(git_repo, monkeypatch):
    """Same symbol defined/referenced in two changed files maps to one ADR id."""
    monkeypatch.delenv("RDDF_CODEGRAPH_FINGERPRINT", raising=False)
    project_root, base = git_repo
    (project_root / "foo.py").write_text("def shared():\n    pass\n", encoding="utf-8")
    (project_root / "bar.py").write_text("def shared():\n    pass\n", encoding="utf-8")
    _git_commit(project_root, "two files same symbol")

    state = _make_state(commit=base, reverse_index={"shared": ["ADR-0007"]})
    changed_adrs, files, status = detect_code_changes(state, project_root)
    assert status == "ok"
    assert set(files) == {"foo.py", "bar.py"}
    assert changed_adrs == {"ADR-0007"}  # set semantics: no duplicates


def test_edge_detect_adr_changes_no_modifications_all_empty(adr_project):
    project_root, _, state = adr_project
    changed, new, deleted = detect_adr_changes(state, project_root, scan_adr_catalog)
    assert changed == [] and new == [] and deleted == []


def test_edge_save_populate_state_atomic_write_and_schema_fields(tmp_path):
    state = _make_state(adrs={"ADR-0001": _adr_entry("ADR-0001", "c" * 64)})
    save_populate_state(state, tmp_path, "abc1234")

    target = tmp_path / ".rddf" / "state" / ".populate-state.json"
    assert target.exists()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["codebase_commit"] == "abc1234"
    assert payload["version"] == 2
    assert "generated_at" in payload
    # no torn-write leftovers
    leftovers = list((tmp_path / ".rddf" / "state").glob("*.tmp"))
    assert leftovers == []
