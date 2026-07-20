"""Unit tests for skills/propose/scripts/propose_quality_check.py.

Covers the 5 check functions plus run_all_checks aggregator and the
strict-mode behavior. Follows the pattern from test_deps_output.py:
- tmp_path fixtures for isolated filesystem
- Direct function imports
- No mocking of filesystem
"""
import os
import sys
from pathlib import Path

import pytest

from skills.propose.scripts import propose_quality_check as pqc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    """Isolated project root with openspec/changes/ scaffolded."""
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    return str(tmp_path)


def _write_proposal(project_root: str, name: str, content: str) -> str:
    """Write a proposal.md for the given change. Returns the path."""
    change_dir = Path(project_root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = change_dir / "proposal.md"
    proposal_path.write_text(content, encoding="utf-8")
    return str(proposal_path)


def _write_tasks(project_root: str, name: str, content: str) -> str:
    change_dir = Path(project_root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    tasks_path = change_dir / "tasks.md"
    tasks_path.write_text(content, encoding="utf-8")
    return str(tasks_path)


# ---------------------------------------------------------------------------
# check_proposal_length
# ---------------------------------------------------------------------------

class TestCheckProposalLength:
    def test_long_proposal_passes(self, project_root):
        proposal = "## Why\n\n" + ("x" * 600) + "\n"
        path = _write_proposal(project_root, "c1", proposal)
        assert pqc.check_proposal_length(path) == []

    def test_short_proposal_warns(self, project_root):
        proposal = "## Why\n\nshort\n"
        path = _write_proposal(project_root, "c1", proposal)
        warnings = pqc.check_proposal_length(path)
        assert len(warnings) == 1
        assert "too short" in warnings[0]
        assert "min 500" in warnings[0]

    def test_missing_file_returns_warning(self, project_root):
        path = os.path.join(project_root, "openspec", "changes", "ghost", "proposal.md")
        warnings = pqc.check_proposal_length(path)
        assert len(warnings) == 1
        assert "not found" in warnings[0]

    def test_skeleton_boilerplate_stripped_before_length_check(self, project_root):
        """The skeleton template written by create_skeleton_change has
        <skeleton motivation> and <file path> markers. Even if raw byte
        count exceeds 500, an unfilled skeleton must be detected as short."""
        # Build a skeleton that's >500 chars raw but <500 after stripping
        # the skeleton markers. We pad with the literal marker prefix
        # `<file path` (10 chars) repeated so stripping actually shrinks
        # the content meaningfully.
        skeleton = (
            "## Why\n\n"
            "<skeleton motivation - 1-2 sentences>\n\n"
            "## What Changes\n\n"
        )
        # Pad with `<file path` markers so stripping reduces length below 500.
        # Each marker is 10 chars; we add ~60 of them = 600 raw chars from markers.
        # After stripping, only the ~70-char skeleton frame remains (<500).
        skeleton += "<file path" * 60
        path = _write_proposal(project_root, "c1", skeleton)
        # Raw length > 500 but stripped < 500
        raw = Path(path).read_text()
        assert len(raw) > 500
        warnings = pqc.check_proposal_length(path)
        assert len(warnings) == 1
        assert "too short" in warnings[0]

    def test_exactly_500_chars_passes(self, project_root):
        """Boundary: exactly 500 chars (after stripping) should pass."""
        # "## Why\n\n" = 8 chars, "\n" = 1 char, so content needs 491 chars.
        proposal = "## Why\n\n" + ("a" * 491) + "\n"
        path = _write_proposal(project_root, "c1", proposal)
        assert len(Path(path).read_text()) == 500
        assert pqc.check_proposal_length(path) == []


# ---------------------------------------------------------------------------
# check_adr_references
# ---------------------------------------------------------------------------

class TestCheckAdrReferences:
    def test_proposal_with_adr_passes(self, project_root):
        proposal = "## Why\n\nImplements ADR-0019 change-arch-alignment.\n" + ("x" * 500)
        path = _write_proposal(project_root, "c1", proposal)
        assert pqc.check_adr_references(path) == []

    def test_proposal_with_multiple_adrs_passes(self, project_root):
        proposal = "## Why\n\nRefs ADR-0003 and ADR-0019.\n" + ("x" * 500)
        path = _write_proposal(project_root, "c1", proposal)
        assert pqc.check_adr_references(path) == []

    def test_proposal_without_adr_warns(self, project_root):
        proposal = "## Why\n\nNo architecture references here.\n" + ("x" * 500)
        path = _write_proposal(project_root, "c1", proposal)
        warnings = pqc.check_adr_references(path)
        assert len(warnings) == 1
        assert "ADR" in warnings[0]
        assert ">=1" in warnings[0] or "≥1" in warnings[0]

    def test_adr_with_two_digits_does_not_match(self, project_root):
        """ADR-NNNN requires 4 digits; ADR-19 should not match."""
        proposal = "## Why\n\nRefs ADR-19 only.\n" + ("x" * 500)
        path = _write_proposal(project_root, "c1", proposal)
        warnings = pqc.check_adr_references(path)
        assert len(warnings) == 1

    def test_missing_file_returns_no_warning(self, project_root):
        """Missing file is already reported by check_proposal_length;
        check_adr_references should not double-report."""
        path = os.path.join(project_root, "openspec", "changes", "ghost", "proposal.md")
        assert pqc.check_adr_references(path) == []


# ---------------------------------------------------------------------------
# check_scope_sections
# ---------------------------------------------------------------------------

class TestCheckScopeSections:
    def test_proposal_with_both_scope_sections_passes(self, project_root):
        proposal = (
            "## In Scope\n\ndo the thing\n\n"
            "## Out of Scope\n\nnot doing that\n"
            + ("x" * 500)
        )
        path = _write_proposal(project_root, "c1", proposal)
        assert pqc.check_scope_sections(path) == []

    def test_proposal_with_out_scope_shorthand_passes(self, project_root):
        """'Out Scope' (without 'of') is accepted as shorthand."""
        proposal = (
            "## In Scope\n\ndo the thing\n\n"
            "## Out Scope\n\nnot doing that\n"
            + ("x" * 500)
        )
        path = _write_proposal(project_root, "c1", proposal)
        assert pqc.check_scope_sections(path) == []

    def test_proposal_missing_in_scope_warns(self, project_root):
        proposal = "## Out of Scope\n\nnot doing that\n" + ("x" * 500)
        path = _write_proposal(project_root, "c1", proposal)
        warnings = pqc.check_scope_sections(path)
        assert any("In Scope" in w for w in warnings)

    def test_proposal_missing_out_scope_warns(self, project_root):
        proposal = "## In Scope\n\ndo the thing\n" + ("x" * 500)
        path = _write_proposal(project_root, "c1", proposal)
        warnings = pqc.check_scope_sections(path)
        assert any("Out of Scope" in w or "Out Scope" in w for w in warnings)

    def test_proposal_missing_both_scope_sections_warns_twice(self, project_root):
        proposal = "## Why\n\nJust a why.\n" + ("x" * 500)
        path = _write_proposal(project_root, "c1", proposal)
        warnings = pqc.check_scope_sections(path)
        assert len(warnings) == 2

    def test_missing_file_returns_no_warning(self, project_root):
        path = os.path.join(project_root, "openspec", "changes", "ghost", "proposal.md")
        assert pqc.check_scope_sections(path) == []


# ---------------------------------------------------------------------------
# check_roadmap_alignment
# ---------------------------------------------------------------------------

class TestCheckRoadmapAlignment:
    def _write_roadmap(self, project_root: str, content: str) -> None:
        Path(project_root, "roadmap.md").write_text(content, encoding="utf-8")

    def test_change_in_roadmap_passes(self, project_root):
        self._write_roadmap(project_root, "# Roadmap\n\n- add-propose-output-validation\n")
        assert pqc.check_roadmap_alignment("add-propose-output-validation", project_root) == []

    def test_change_not_in_roadmap_warns(self, project_root):
        self._write_roadmap(project_root, "# Roadmap\n\n- some-other-change\n")
        warnings = pqc.check_roadmap_alignment("add-propose-output-validation", project_root)
        assert len(warnings) == 1
        assert "not found in roadmap" in warnings[0]
        assert "add-propose-output-validation" in warnings[0]

    def test_missing_roadmap_warns(self, tmp_path):
        """No roadmap.md -> soft warning (compat mode is valid)."""
        root = str(tmp_path)
        # Ensure no roadmap.md exists
        assert not os.path.isfile(os.path.join(root, "roadmap.md"))
        warnings = pqc.check_roadmap_alignment("any-change", root)
        assert len(warnings) == 1
        assert "roadmap.md not found" in warnings[0]

    def test_change_name_as_substring_matches(self, project_root):
        """Change names may appear as ### headers or in tables; substring
        match is intentional."""
        self._write_roadmap(
            project_root,
            "# Roadmap\n\n### my-change-name is here\n",
        )
        assert pqc.check_roadmap_alignment("my-change-name", project_root) == []


# ---------------------------------------------------------------------------
# check_tasks_completeness
# ---------------------------------------------------------------------------

class TestCheckTasksCompleteness:
    def test_two_unchecked_tasks_passes(self, project_root):
        tasks = "## Tasks\n\n- [ ] task one\n- [ ] task two\n"
        path = _write_tasks(project_root, "c1", tasks)
        assert pqc.check_tasks_completeness(path) == []

    def test_one_task_warns(self, project_root):
        tasks = "## Tasks\n\n- [ ] only task\n"
        path = _write_tasks(project_root, "c1", tasks)
        warnings = pqc.check_tasks_completeness(path)
        assert len(warnings) == 1
        assert "min 2" in warnings[0]

    def test_zero_tasks_warns(self, project_root):
        tasks = "## Tasks\n\nNo tasks yet.\n"
        path = _write_tasks(project_root, "c1", tasks)
        warnings = pqc.check_tasks_completeness(path)
        assert len(warnings) == 1
        assert "0" in warnings[0]

    def test_checked_tasks_not_counted(self, project_root):
        """- [x] items represent done work; only - [ ] count toward the min."""
        tasks = "## Tasks\n\n- [x] done task\n- [ ] pending task\n"
        path = _write_tasks(project_root, "c1", tasks)
        warnings = pqc.check_tasks_completeness(path)
        assert len(warnings) == 1  # only 1 pending, below min 2

    def test_indented_tasks_counted(self, project_root):
        """Tasks may be indented under sub-headings."""
        tasks = (
            "## Tasks\n\n"
            "### Phase 1\n"
            "  - [ ] indented task one\n"
            "  - [ ] indented task two\n"
        )
        path = _write_tasks(project_root, "c1", tasks)
        assert pqc.check_tasks_completeness(path) == []

    def test_missing_file_returns_warning(self, project_root):
        path = os.path.join(project_root, "openspec", "changes", "ghost", "tasks.md")
        warnings = pqc.check_tasks_completeness(path)
        assert len(warnings) == 1
        assert "not found" in warnings[0]


# ---------------------------------------------------------------------------
# run_all_checks
# ---------------------------------------------------------------------------

class TestRunAllChecks:
    def _seed_good_change(self, project_root: str, name: str = "c1") -> None:
        """Seed a change that passes all 5 checks."""
        proposal = (
            "## Why\n\n"
            + ("x" * 500)
            + "\n\nRefs ADR-0019.\n\n"
            + "## In Scope\n\ndo thing\n\n"
            + "## Out of Scope\n\nnot doing\n"
        )
        _write_proposal(project_root, name, proposal)
        _write_tasks(project_root, name, "## Tasks\n\n- [ ] one\n- [ ] two\n")
        Path(project_root, "roadmap.md").write_text(
            f"# Roadmap\n\n- {name}\n", encoding="utf-8"
        )

    def test_all_pass_returns_empty_list(self, project_root):
        self._seed_good_change(project_root, "c1")
        assert pqc.run_all_checks("c1", project_root) == []

    def test_aggregates_warnings_from_all_checks(self, project_root):
        """A skeleton proposal (short, no ADR, no scope, no tasks) should
        produce multiple warnings."""
        # Just create the change dir with the skeleton proposal.md
        # (matches create_skeleton_change output exactly)
        _write_proposal(
            project_root,
            "c1",
            "## Why\n\n<skeleton motivation - 1-2 sentences>\n\n"
            "## What Changes\n\n- <file path or module affected>\n",
        )
        # No tasks.md, no roadmap.md
        warnings = pqc.run_all_checks("c1", project_root)
        # Expect: short proposal + no ADR + missing scope (x2) + missing roadmap + missing tasks
        assert len(warnings) >= 5
        all_text = " ".join(warnings)
        assert "too short" in all_text
        assert "ADR" in all_text
        assert "In Scope" in all_text
        assert "roadmap" in all_text
        assert "tasks.md not found" in all_text

    def test_missing_change_dir_aggregates_missing_file_warnings(self, project_root):
        """When the change dir doesn't exist, we should get missing-file
        warnings from proposal-length and tasks-completeness checks, plus
        roadmap warning if roadmap.md also missing."""
        warnings = pqc.run_all_checks("ghost", project_root)
        # proposal.md not found + tasks.md not found + roadmap not found
        # (adr_references and scope_sections defer to check #1's missing-file warning)
        assert any("proposal.md not found" in w for w in warnings)
        assert any("tasks.md not found" in w for w in warnings)


# ---------------------------------------------------------------------------
# CLI / main entry
# ---------------------------------------------------------------------------

class TestCliMain:
    def test_main_passes_exit_zero(self, project_root, capsys, monkeypatch):
        # Seed a good change
        proposal = (
            "## Why\n\n" + ("x" * 500) + "\n\nRefs ADR-0019.\n\n"
            "## In Scope\n\ndo thing\n\n## Out of Scope\n\nnot doing\n"
        )
        _write_proposal(project_root, "c1", proposal)
        _write_tasks(project_root, "c1", "## Tasks\n\n- [ ] one\n- [ ] two\n")
        Path(project_root, "roadmap.md").write_text("# Roadmap\n\n- c1\n")

        monkeypatch.setenv("PROJECT_ROOT", project_root)
        monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
        result = pqc.main(["--change", "c1"])
        # In default (non-strict) mode, main() returns the warnings list
        # (empty when all checks pass). It does NOT sys.exit in default mode.
        assert result == []
        captured = capsys.readouterr()
        assert "passes all quality checks" in captured.out

    def test_main_warnings_default_exit_zero(self, project_root, capsys, monkeypatch):
        """Default mode: warnings printed, exit 0."""
        _write_proposal(project_root, "c1", "## Why\n\nshort\n")
        monkeypatch.setenv("PROJECT_ROOT", project_root)
        monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)  # safety
        # main() returns warnings list (no sys.exit in default mode)
        warnings = pqc.main(["--change", "c1"])
        captured = capsys.readouterr()
        assert "Quality warnings" in captured.out
        # exit code 0 in default mode (no exception raised)
        assert isinstance(warnings, list)
        assert len(warnings) > 0

    def test_main_strict_flag_exits_nonzero(self, project_root, monkeypatch):
        """--strict flag: warnings become errors, exit 1."""
        _write_proposal(project_root, "c1", "## Why\n\nshort\n")
        monkeypatch.setenv("PROJECT_ROOT", project_root)
        monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            pqc.main(["--change", "c1", "--strict"])
        assert exc_info.value.code == 1

    def test_main_strict_env_var_exits_nonzero(self, project_root, monkeypatch):
        """STRICT_PROPOSE_GATE=yes: warnings become errors, exit 1."""
        _write_proposal(project_root, "c1", "## Why\n\nshort\n")
        monkeypatch.setenv("PROJECT_ROOT", project_root)
        monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
        with pytest.raises(SystemExit) as exc_info:
            pqc.main(["--change", "c1"])
        assert exc_info.value.code == 1

    def test_main_strict_flag_overrides_env_var_unset(
        self, project_root, monkeypatch
    ):
        """--strict flag works even when env var is not set."""
        _write_proposal(project_root, "c1", "## Why\n\nshort\n")
        monkeypatch.setenv("PROJECT_ROOT", project_root)
        monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            pqc.main(["--change", "c1", "--strict"])
        assert exc_info.value.code == 1

    def test_main_no_warnings_strict_exits_zero(self, project_root, monkeypatch):
        """Strict mode + no warnings = exit 0 (no SystemExit raised)."""
        proposal = (
            "## Why\n\n" + ("x" * 500) + "\n\nRefs ADR-0019.\n\n"
            "## In Scope\n\ndo thing\n\n## Out of Scope\n\nnot doing\n"
        )
        _write_proposal(project_root, "c1", proposal)
        _write_tasks(project_root, "c1", "## Tasks\n\n- [ ] one\n- [ ] two\n")
        Path(project_root, "roadmap.md").write_text("# Roadmap\n\n- c1\n")
        monkeypatch.setenv("PROJECT_ROOT", project_root)
        monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
        # Should not raise SystemExit; returns empty warnings list.
        result = pqc.main(["--change", "c1", "--strict"])
        assert result == []
