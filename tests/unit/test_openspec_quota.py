"""Unit tests for `_lib/openspec_quota.py` — the single quota implementation.

Covers, per `openspec/changes/add-openspec-kpi-quota/proposal.md`:
  - AC-4: the 12-row config matrix (absent / empty / missing key / 0 / 3 /
    string / float / bool (YAML `yes`/`on`) / negative / broken YAML /
    non-mapping top level / wrong nesting)
  - AC-5①: `count_active` **delegates** to
    `skills._lib.state_reader.list_change_dirs` (monkeypatch on the module
    attribute must be visible ⇒ no name-level `from … import func`)

Why the bool rows matter: PyYAML (YAML 1.1) parses `yes` / `on` / `true` as
`True`, and `isinstance(True, int)` is **True** in Python — without an explicit
bool rejection `proposed_limit: yes` would silently become a limit of 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import skills._lib.state_reader as state_reader  # noqa: E402

import _lib.openspec_quota as quota  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

def _write_yaml(project_root: Path, text: str) -> None:
    (project_root / ".rddf").mkdir(exist_ok=True)
    (project_root / ".rddf" / "project.yaml").write_text(text, encoding="utf-8")


def _make_changes(project_root: Path, names: list[str], *, archive: bool = False) -> None:
    changes = project_root / "openspec" / "changes"
    changes.mkdir(parents=True, exist_ok=True)
    if archive:
        (changes / "archive").mkdir(exist_ok=True)
    for name in names:
        (changes / name).mkdir()


# ---------------------------------------------------------------------------
# AC-4 — config matrix: "unlimited" rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "yaml_text",
    [
        None,                                # file absent
        "",                                  # empty file (safe_load → None)
        "other:\n  keep: 1\n",               # `openspec:` section absent
        "openspec:\n  other_key: 1\n",       # key absent
        "openspec:\n  proposed_limit: 0\n",  # explicit 0
    ],
    ids=["file-absent", "empty-file", "section-absent", "key-absent", "explicit-zero"],
)
def test_unlimited_rows(tmp_path: Path, yaml_text: str | None) -> None:
    if yaml_text is not None:
        _write_yaml(tmp_path, yaml_text)
    assert quota.read_limit(str(tmp_path)) == 0
    result = quota.evaluate(str(tmp_path))
    assert result.limit is None
    assert result.ok is True


def test_configured_limit_is_read(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "openspec:\n  proposed_limit: 3\n")
    assert quota.read_limit(str(tmp_path)) == 3


# ---------------------------------------------------------------------------
# AC-4 — config matrix: "error" rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "yaml_text",
    [
        'openspec:\n  proposed_limit: "3"\n',    # string
        "openspec:\n  proposed_limit: 3.0\n",    # float (integer-valued)
        "openspec:\n  proposed_limit: 3.5\n",    # float
        "openspec:\n  proposed_limit: true\n",   # YAML bool
        "openspec:\n  proposed_limit: false\n",  # YAML bool
        "openspec:\n  proposed_limit: yes\n",    # YAML 1.1 bool ← the trap
        "openspec:\n  proposed_limit: on\n",     # YAML 1.1 bool
        "openspec:\n  proposed_limit: -1\n",     # negative
        "openspec:\n  proposed_limit: [1]\n",    # list
    ],
    ids=["str", "float-int", "float", "bool-true", "bool-false", "yes", "on", "negative", "list"],
)
def test_broken_value_rows(tmp_path: Path, yaml_text: str) -> None:
    _write_yaml(tmp_path, yaml_text)
    with pytest.raises(quota.QuotaConfigError):
        quota.read_limit(str(tmp_path))


def test_broken_yaml_raises(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "openspec: [unclosed\n")
    with pytest.raises(quota.QuotaConfigError):
        quota.read_limit(str(tmp_path))


@pytest.mark.parametrize(
    "yaml_text",
    [
        "- just\n- a list\n",                    # top level list
        "42\n",                                  # top level scalar
        "openspec: just-a-string\n",             # section not a mapping
        "proposed_limit: 3\n",                   # wrong nesting (top level key)
    ],
    ids=["top-list", "top-scalar", "section-not-mapping", "wrong-nesting"],
)
def test_structurally_wrong_rows(tmp_path: Path, yaml_text: str) -> None:
    _write_yaml(tmp_path, yaml_text)
    with pytest.raises(quota.QuotaConfigError):
        quota.read_limit(str(tmp_path))


def test_error_message_names_the_key(tmp_path: Path) -> None:
    _write_yaml(tmp_path, 'openspec:\n  proposed_limit: "3"\n')
    with pytest.raises(quota.QuotaConfigError) as exc:
        quota.read_limit(str(tmp_path))
    assert "proposed_limit" in str(exc.value)


def test_wrong_nesting_message_explains_the_expected_place(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "proposed_limit: 3\n")
    with pytest.raises(quota.QuotaConfigError) as exc:
        quota.read_limit(str(tmp_path))
    assert "openspec" in str(exc.value)


# ---------------------------------------------------------------------------
# counting + AC-5① (delegation, not a second implementation)
# ---------------------------------------------------------------------------

def test_count_without_changes_dir(tmp_path: Path) -> None:
    assert quota.count_active(str(tmp_path)) == 0


def test_count_excludes_archive(tmp_path: Path) -> None:
    _make_changes(tmp_path, ["a", "b", "c"], archive=True)
    assert quota.count_active(str(tmp_path)) == 3


def test_count_many_dirs(tmp_path: Path) -> None:
    _make_changes(tmp_path, [f"change-{i}" for i in range(200)], archive=True)
    assert quota.count_active(str(tmp_path)) == 200


def test_count_ignores_non_directory_entries(tmp_path: Path) -> None:
    changes = tmp_path / "openspec" / "changes"
    changes.mkdir(parents=True)
    (changes / "a-file.md").write_text("x", encoding="utf-8")
    (changes / "real-change").mkdir()
    assert quota.count_active(str(tmp_path)) == 1


def test_count_delegates_to_state_reader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-5①: patching the *module attribute* must change the count.

    This fails if `count_active` binds the function at import time
    (`from … import list_change_dirs`) instead of looking it up on the module.
    """
    monkeypatch.setattr(state_reader, "list_change_dirs", lambda root: ["x", "y"])
    assert quota.count_active(str(tmp_path)) == 2


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------

def test_evaluate_exceeded(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "openspec:\n  proposed_limit: 3\n")
    _make_changes(tmp_path, ["a", "b", "c", "d"], archive=True)
    result = quota.evaluate(str(tmp_path))
    assert (result.active, result.limit, result.ok) == (4, 3, False)


def test_evaluate_within_limit(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "openspec:\n  proposed_limit: 3\n")
    _make_changes(tmp_path, ["a", "b"], archive=True)
    result = quota.evaluate(str(tmp_path))
    assert (result.active, result.limit, result.ok) == (2, 3, True)


def test_evaluate_override_wins_over_config(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "openspec:\n  proposed_limit: 1\n")
    _make_changes(tmp_path, ["a", "b", "c"], archive=True)
    result = quota.evaluate(str(tmp_path), override=5)
    assert (result.active, result.limit, result.ok) == (3, 5, True)


def test_evaluate_override_zero_means_unlimited(tmp_path: Path) -> None:
    _make_changes(tmp_path, ["a"])
    result = quota.evaluate(str(tmp_path), override=0)
    assert result.limit is None
    assert result.ok is True


@pytest.mark.parametrize("bad", [-1, 2.0, True, "3", [3]])
def test_evaluate_override_rejects_bad_values(tmp_path: Path, bad: object) -> None:
    with pytest.raises(quota.QuotaConfigError):
        quota.evaluate(str(tmp_path), override=bad)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# find_limit_line — display-layer locator owned by this module (design D4)
# ---------------------------------------------------------------------------

def test_find_limit_line(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "a: 1\nopenspec:\n  proposed_limit: 3\n")
    assert quota.find_limit_line(str(tmp_path)) == 3


def test_find_limit_line_absent(tmp_path: Path) -> None:
    assert quota.find_limit_line(str(tmp_path)) is None
    _write_yaml(tmp_path, "openspec:\n  other: 1\n")
    assert quota.find_limit_line(str(tmp_path)) is None
