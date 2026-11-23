"""Unit tests for the `.rddf/` layout manifest (RDFF_LAYOUT).

The manifest is the single source of truth for the `.rddf/` layout
(per ADR-0026). These tests pin its shape and its agreement with reality:
assertion A (path constants are covered) and assertion B (the storage class
matches the .gitignore reality).
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "_lib" / "core"))

from rddf_layout import (  # noqa: E402
    CLASSES,
    REQUIRED_WHEN,
    ROLES,
    SEVERITIES,
    as_dicts,
)


def covers(entry_path: str, target: str) -> bool:
    """True when `entry_path` (relative to `.rddf/`) covers `target`.

    Assertion A's helper: exact equality, or `target` starts with
    `entry_path + "/"`. The trailing slash matters — without it `roadmap`
    would swallow `roadmap.md`.
    """
    rel = target[len(".rddf/"):] if target.startswith(".rddf/") else target
    return rel == entry_path or rel.startswith(entry_path + "/")

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
    """`reviews/` is written by the agent only — read_by/write_by are facts."""
    entry = next(d for d in as_dicts() if d["path"] == "reviews")
    assert entry["write_by"] == ["agent"]
    assert "rdd" not in entry["read_by"]


def test_non_rdd_entries_name_their_actual_writer():
    """Every entry the rdd does not write must name its real owner.

    `read_by` / `write_by` are meant to be observable facts, not guesses —
    so this pins **all** of them, not one sample.  The single-entry test above
    (`reviews`) would still pass if e.g. `config` started claiming `rdd` as a
    writer, which would make the manifest a guess instead of a record.
    """
    expected = {
        "actions": ["user"],
        "config": ["external-tool"],
        "detectors": ["user"],
        "project.yaml": ["user"],
        "reviews": ["agent"],
        "roadmap": ["agent"],
        "roadmap.md": ["agent"],
        "skill-profiles": ["user"],
        "wt": ["git"],
    }
    got = {d["path"]: d["write_by"] for d in as_dicts() if "rdd" not in d["write_by"]}
    assert got == expected, got


def test_covers_does_not_confuse_sibling_names():
    """`roadmap` must not swallow `roadmap.md`."""
    assert covers("roadmap", ".rddf/roadmap.md") is False
    assert covers("roadmap", ".rddf/roadmap/phases/phase-4.md") is True
    assert covers("roadmap.md", ".rddf/roadmap.md") is True


def test_state_dir_is_written_by_rdd_and_agent():
    """`.rddf/state/` holds both rdd-written state and agent-written governance state.

    `.rddf/state/role.json` (the opencode build-agent role state, role-v2) and
    `.rddf/state/pair.json` (the dispatch registry) are written by the agent
    layer, not by rdd — the manifest must say so, otherwise it is not a
    "read_by / write_by are observable facts" record.
    """
    entry = next(d for d in as_dicts() if d["path"] == "state")
    assert "rdd" in entry["write_by"]
    assert "agent" in entry["write_by"]


def test_state_entry_keeps_agent_out_of_read_by():
    """The agent writes governance state; it does not read rdd's state internals."""
    entry = next(d for d in as_dicts() if d["path"] == "state")
    assert "agent" not in entry["read_by"]


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
        assert any(covers(p, t) for p in entries), t


def test_assertion_b_class_matches_gitignore_reality():
    """每条 entry 的 class 必须与 git check-ignore 实况一致。"""
    import fnmatch

    def ignored(probe: str) -> bool:
        res = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", probe],
            cwd=PROJECT_ROOT, capture_output=True,
        )
        assert res.returncode in (0, 1), res.returncode
        return res.returncode == 0

    rddf = PROJECT_ROOT / ".rddf"
    for d in as_dicts():
        if any(c in d["path"] for c in "*?["):
            # Glob entry: the probe path would contain a literal "*", which
            # git never matches against a multi-segment pattern. Verify via
            # the concrete directories that actually exist.
            matches = [
                p for p in rddf.iterdir()
                if fnmatch.fnmatchcase(p.name, d["path"])
            ]
            for m in matches:
                probe = f".rddf/{m.name}/.probe"
                if d["class"] == "runtime-only":
                    assert ignored(probe), f"{m.name} 应被 gitignore"
                else:
                    assert not ignored(probe), f"{m.name} 不应被 gitignore"
            continue
        probe = f".rddf/{d['path']}/.probe" if d["kind"] == "dir" else f".rddf/{d['path']}"
        if d["class"] == "runtime-only":
            assert ignored(probe), f"{d['path']} 应被 gitignore"
        else:
            assert not ignored(probe), f"{d['path']} 不应被 gitignore"
