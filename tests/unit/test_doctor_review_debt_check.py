"""Unit tests for the doctor `review-debt` checker's scope (2026-11-18).

The repo-wide marker scan used to be 52-for-52 noise in this repository:
every hit was either a test fixture (the detector tests NEED unticketed
markers to be meaningful), the vocabulary's own definition files, or a
document-template placeholder. A diagnostic nobody can act on is worse than
no diagnostic, so the checker excludes those three classes — and this file
pins the exclusions, because silently widening them again (or narrowing the
real signal away) is exactly the failure mode being fixed.

Signal that MUST survive: a bare marker in production code.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-doctor" / "scripts"))

import checks.review_debt_check as review_debt_check  # noqa: E402
from doctor_render import Severity  # noqa: E402


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_production_marker_is_reported(tmp_path):
    _write(tmp_path, "_lib/feature.py", "def f():\n    # TODO: wire this up\n    pass\n")

    findings = review_debt_check.run(tmp_path)

    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert findings[0].category == "review-debt.unticketed-marker"
    assert findings[0].file == "_lib/feature.py"
    assert findings[0].line == 2


def test_ticketed_marker_is_silent(tmp_path):
    _write(tmp_path, "_lib/feature.py", "# TODO(RDDF-123): tracked\n")

    assert review_debt_check.run(tmp_path) == []


def test_test_fixtures_are_not_reported(tmp_path):
    # The detector tests must be able to contain a bare marker.
    _write(tmp_path, "tests/unit/test_detector.py", 'FIXTURE = "// TODO: stuff"\n')
    _write(tmp_path, "tests/integration/test_x.bats", '# TODO marker assertion\n')

    assert review_debt_check.run(tmp_path) == []


def test_vocabulary_files_are_not_reported(tmp_path):
    # Files that define or emit the vocabulary by design.
    for rel in review_debt_check._VOCABULARY_FILES:
        _write(tmp_path, rel, "# TODO: this file owns the vocabulary\n")

    assert review_debt_check.run(tmp_path) == []


def test_placeholder_syntax_is_not_reported(tmp_path):
    # `<TODO>` is document-template placeholder syntax, not leftover work.
    _write(tmp_path, "_lib/gate_rules.py", 'PLACEHOLDERS = [r"<TODO>"]\n')

    assert review_debt_check.run(tmp_path) == []


def test_runtime_state_dirs_are_skipped(tmp_path):
    _write(tmp_path, ".rddf/plans/x.md", "# TODO: plan scratch\n")
    _write(tmp_path, ".rddf/notes.py", "# TODO: scratch\n")

    assert review_debt_check.run(tmp_path) == []


def test_every_vocabulary_entry_carries_a_reason():
    """The allowlist is an accountability ledger — no bare paths."""
    for rel, reason in review_debt_check._VOCABULARY_FILES.items():
        assert rel.strip() == rel and rel, f"bad path: {rel!r}"
        assert reason.strip(), f"missing reason for {rel}"
