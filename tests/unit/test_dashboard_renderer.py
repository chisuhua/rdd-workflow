"""Unit tests for ``_lib/dashboard/renderer.py``.

Covers all 3 render modes (``terminal``, ``json``, ``plain``), the
auto-degrade behavior when stdout is not a TTY, the ``output_file``
parameter, the invalid-mode error path, and several content-shape
scenarios (empty data, divergence warnings, sessions, changes,
features, arch/plan phase status).

Sister file ``test_state_reader.py`` covers the 8 read-only state_reader
functions; this file deliberately does NOT touch state_reader - it only
constructs ``DashboardData`` instances in memory and feeds them to
``render()``.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from skills._lib.dashboard import (
    ApprovedProposalEntry,
    ArchInfo,
    ChangeEntry,
    DashboardData,
    FeatureSummary,
    PlanInfo,
    SessionEntry,
    SuggestionEntry,
)
from skills._lib.dashboard import collect
from skills._lib.dashboard.renderer import render
import skills._lib.dashboard as dashboard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_empty_data():
    """Return a ``DashboardData`` with all fields set to empty defaults.

    The only required field is ``project_root``; every other field has a
    dataclass default (empty list / empty dict / None / 0). We construct
    the instance explicitly so the test intent is self-documenting and
    so future schema additions that remove a default will surface here
    rather than silently passing tests.
    """

    def _build(project_root: str = "/test/project") -> DashboardData:
        return DashboardData(
            project_root=project_root,
            arch=ArchInfo(),
            plan=PlanInfo(),
            changes=[],
            sessions=[],
            worktrees=[],
            features=[],
            roadmap_phase=None,
            roadmap_counts={},
            pending_suggestions=0,
            suggestions=[],
            divergence_warnings=[],
        )

    return _build


# ---------------------------------------------------------------------------
# Mode: terminal
# ---------------------------------------------------------------------------


class TestTerminalMode:
    def test_terminal_returns_nonempty_string(self, make_empty_data):
        """render(mode='terminal') with output_file returns non-empty output."""
        out = render(make_empty_data(), mode="terminal", output_file="/dev/null")
        assert isinstance(out, str)
        assert len(out) > 0

    def test_terminal_contains_box_drawing_chars(self, make_empty_data, tmp_path):
        """Terminal mode (forced via output_file so no auto-degrade) uses box chars."""
        out = render(make_empty_data(), mode="terminal", output_file=str(tmp_path / "o.txt"))
        # Box-drawing chars used by _render_terminal
        box_chars = {"╔", "╗", "╚", "╝", "═", "║", "╟", "╢", "─"}
        found = {c for c in box_chars if c in out}
        assert found, f"expected box-drawing chars in terminal mode, found none in: {out[:200]!r}"

    def test_terminal_forced_via_output_file_avoids_auto_degrade(
        self, make_empty_data, tmp_path
    ):
        """When output_file is given, terminal mode stays terminal even if not a TTY."""
        # Patch _stdout_is_tty to return False to simulate piped stdout.
        with patch("skills._lib.dashboard.renderer._stdout_is_tty", return_value=False):
            out = render(
                make_empty_data(),
                mode="terminal",
                output_file=str(tmp_path / "force.txt"),
            )
        assert "╔" in out, "output_file should force terminal mode despite non-TTY"


# ---------------------------------------------------------------------------
# Mode: json
# ---------------------------------------------------------------------------


class TestJsonMode:
    def test_json_returns_valid_json_dict(self, make_empty_data):
        out = render(make_empty_data(), mode="json")
        parsed = json.loads(out)
        assert isinstance(parsed, dict)

    def test_json_has_expected_top_level_keys(self, make_empty_data):
        out = render(make_empty_data(), mode="json")
        parsed = json.loads(out)
        expected = {
            "project_root",
            "arch",
            "plan",
            "changes",
            "sessions",
            "worktrees",
            "features",
            "roadmap_phase",
            "roadmap_counts",
            "pending_suggestions",
            "suggestions",
            "approved_proposals",
            "divergence_warnings",
        }
        assert expected.issubset(parsed.keys()), (
            f"missing keys: {expected - set(parsed.keys())}"
        )

    def test_json_round_trips_via_json_loads(self, make_empty_data):
        """JSON output must round-trip cleanly through json.loads()."""
        out = render(make_empty_data(), mode="json")
        # Must not raise
        parsed = json.loads(out)
        # Re-serialize and parse again for true round-trip
        re_parsed = json.loads(json.dumps(parsed))
        assert re_parsed == parsed

    def test_json_empty_data_has_all_keys_with_null_or_empty(self, make_empty_data):
        out = render(make_empty_data(), mode="json")
        parsed = json.loads(out)
        assert parsed["arch"]["arch_complete_at"] is None
        assert parsed["plan"]["plan_complete_at"] is None
        assert parsed["changes"] == []
        assert parsed["sessions"] == []
        assert parsed["worktrees"] == []
        assert parsed["features"] == []
        assert parsed["roadmap_phase"] is None
        assert parsed["roadmap_counts"] == {}
        assert parsed["pending_suggestions"] == 0
        assert parsed["approved_proposals"] == []
        assert parsed["divergence_warnings"] == []


# ---------------------------------------------------------------------------
# Mode: plain
# ---------------------------------------------------------------------------


class TestPlainMode:
    def test_plain_is_ascii_only(self, make_empty_data):
        """Plain mode output must contain only ASCII characters (codepoints < 128)."""
        out = render(make_empty_data(), mode="plain")
        non_ascii = [c for c in out if ord(c) >= 128]
        assert not non_ascii, (
            f"plain mode must be ASCII-only; found non-ASCII chars: "
            f"{[repr(c) for c in non_ascii[:10]]}"
        )

    def test_plain_has_no_box_drawing_chars(self, make_empty_data):
        """Plain mode must not contain any box-drawing characters."""
        out = render(make_empty_data(), mode="plain")
        box_chars = {"╔", "╗", "╚", "╝", "═", "║", "╟", "╢", "─"}
        found = {c for c in box_chars if c in out}
        assert not found, f"plain mode should not contain box-drawing chars: {found}"

    def test_plain_has_no_emoji(self, make_empty_data):
        """Plain mode must not contain any emoji codepoints."""
        out = render(make_empty_data(), mode="plain")
        # Emoji typically live in the supplementary plane (>= U+1F000) plus
        # a handful of pictographs in the U+2600..U+27BF range. We reject
        # any non-ASCII char (which is a superset check; plain mode is
        # ASCII-only by spec).
        non_ascii = [c for c in out if ord(c) >= 128]
        assert not non_ascii, f"plain mode should not contain emoji/non-ASCII: {non_ascii[:5]}"


# ---------------------------------------------------------------------------
# Empty data: all 7 sections present
# ---------------------------------------------------------------------------


class TestEmptyDataSections:
    def test_plain_all_sections_present_when_empty(self, make_empty_data):
        """All 7 section headers should appear even when data is empty."""
        out = render(make_empty_data(), mode="plain")
        for section in [
            "1. Workflow Phase",
            "2. Session",
            "3. Changes",
            "4. Worktrees",
            "5. Features",
            "6. Roadmap",
            "7. Pending",
        ]:
            assert section in out, f"section header {section!r} missing from plain output"

    def test_terminal_all_sections_present_when_empty(self, make_empty_data, tmp_path):
        out = render(make_empty_data(), mode="terminal", output_file=str(tmp_path / "x.txt"))
        for section in [
            "1. Workflow Phase",
            "2. Session",
            "3. Changes",
            "4. Worktrees",
            "5. Features",
            "6. Roadmap",
            "7. Pending",
        ]:
            assert section in out, f"section header {section!r} missing from terminal output"

    def test_empty_data_shows_na_or_placeholder(self, make_empty_data):
        """Empty data should render placeholders (e.g. 'not started', 'no sessions')."""
        out = render(make_empty_data(), mode="plain")
        # Spot-check several "empty" indicators
        assert "not started" in out or "[ ]" in out, "arch not-started hint missing"
        assert "(no sessions)" in out
        assert "(no changes tracked)" in out
        assert "(no worktrees)" in out
        assert "(no features)" in out
        assert "(no pending suggestions)" in out
        assert "(no approved proposals)" in out


# ---------------------------------------------------------------------------
# Content: divergence warnings
# ---------------------------------------------------------------------------


class TestDivergenceWarnings:
    def test_terminal_shows_warning_emoji_in_changes_section(
        self, make_empty_data, tmp_path
    ):
        data = make_empty_data()
        data.divergence_warnings = [
            "iteration.json lists 'ghost-change' as 'proposed' but its directory is missing"
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "w.txt"))
        # Warning emoji ⚠️ is U+26A0 U+FE0F
        assert "⚠️" in out, "divergence warning emoji missing from terminal output"
        assert "divergence warnings" in out
        # Warning should be within the changes section (after "3. Changes" header)
        changes_idx = out.index("3. Changes")
        warning_idx = out.index("divergence warnings")
        assert warning_idx > changes_idx, "warning should appear inside changes section"
        assert "ghost-change" in out

    def test_plain_shows_warning_marker_in_changes_section(self, make_empty_data):
        data = make_empty_data()
        data.divergence_warnings = ["disk has 'extra-change' but iteration has no record"]
        out = render(data, mode="plain")
        # Plain mode uses [!] marker for divergence
        assert "[!]" in out
        assert "divergence warnings" in out
        assert "extra-change" in out
        # Must remain ASCII-only
        assert all(ord(c) < 128 for c in out)


# ---------------------------------------------------------------------------
# Content: pending suggestions
# ---------------------------------------------------------------------------


class TestPendingSuggestions:
    def test_terminal_shows_suggestion_table(self, make_empty_data, tmp_path):
        """Terminal mode shows suggestion table with name/priority/status/phase."""
        data = make_empty_data()
        data.pending_suggestions = 2
        data.suggestions = [
            SuggestionEntry(name="fix-bug", priority="P0", status="skeleton", phase="v2.0"),
            SuggestionEntry(name="add-feature", priority="P1", status="待创建", phase="v2.1"),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "p.txt"))
        assert "2 pending proposal suggestion(s)" in out
        assert "fix-bug" in out
        assert "add-feature" in out
        assert "P0" in out
        assert "P1" in out
        # Header row
        assert "NAME" in out and "PRI" in out and "STATUS" in out and "PHASE" in out

    def test_plain_shows_suggestion_table(self, make_empty_data):
        """Plain mode shows suggestion table via ASCII markers."""
        data = make_empty_data()
        data.pending_suggestions = 1
        data.suggestions = [
            SuggestionEntry(name="fix-bug", priority="P0", status="skeleton", phase="v2.0"),
        ]
        out = render(data, mode="plain")
        assert "1 pending proposal suggestion(s)" in out
        assert "fix-bug" in out
        assert "P0" in out
        # Must remain ASCII-only (emoji replaced with plain marker)
        assert all(ord(c) < 128 for c in out)

    def test_json_includes_suggestions(self, make_empty_data):
        """JSON mode includes suggestions array."""
        data = make_empty_data()
        data.pending_suggestions = 1
        data.suggestions = [
            SuggestionEntry(name="fix-bug", priority="P0", status="skeleton", phase="v2.0"),
        ]
        out = render(data, mode="json")
        parsed = json.loads(out)
        assert parsed["pending_suggestions"] == 1
        assert len(parsed["suggestions"]) == 1
        assert parsed["suggestions"][0]["name"] == "fix-bug"

    def test_no_suggestions_shows_placeholder(self, make_empty_data):
        """When no suggestions, show placeholder not table."""
        data = make_empty_data()
        data.pending_suggestions = 0
        out = render(data, mode="plain")
        assert "(no pending suggestions)" in out
        assert "(no approved proposals)" in out
        assert "NAME" not in out  # no table header


# ---------------------------------------------------------------------------
# Content: sessions
# ---------------------------------------------------------------------------


class TestSessionsRendering:
    def test_terminal_shows_current_session_binding(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.sessions = [
            SessionEntry(
                session_id="ses_abc123",
                kind="plan",
                state="active",
                goal="implement dashboard",
                attached_changes=["dashboard-renderer"],
                is_current=True,
            ),
            SessionEntry(
                session_id="ses_old",
                kind="ship",
                state="completed",
                is_current=False,
            ),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "s.txt"))
        # Current session line uses 📍 emoji (U+1F4CD)
        assert "📍" in out
        assert "ses_abc123" in out
        assert "implement dashboard" in out
        # Other (non-current) sessions get listed too
        assert "ses_old" in out

    def test_plain_shows_current_session_without_emoji(self, make_empty_data):
        data = make_empty_data()
        data.sessions = [
            SessionEntry(
                session_id="ses_xyz",
                kind="arch",
                state="active",
                is_current=True,
            ),
        ]
        out = render(data, mode="plain")
        assert "ses_xyz" in out
        assert "current" in out
        # Plain mode uses "*" for active sessions instead of 📍
        assert "📍" not in out
        # ASCII-only invariant
        assert all(ord(c) < 128 for c in out)


# ---------------------------------------------------------------------------
# Content: changes
# ---------------------------------------------------------------------------


class TestChangesRendering:
    def test_terminal_renders_change_table_with_name(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.changes = [
            ChangeEntry(
                name="add-dashboard-renderer",
                status="proposed",
                phase="v2.1",
                category="dashboard",
                priority="high",
                tasks_done=2,
                tasks_total=5,
                plan_path=".rddf/plans/add-dashboard-renderer.md",
            ),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "c.txt"))
        assert "add-dashboard-renderer" in out
        # Proposed status uses 📋 emoji
        assert "📋" in out
        # Tasks count should appear
        assert "2/5" in out
        # Plan column should show ✅ when plan_path is set
        assert "✅" in out

    def test_plain_renders_change_table_ascii(self, make_empty_data):
        data = make_empty_data()
        data.changes = [
            ChangeEntry(name="c1", status="completed", tasks_done=3, tasks_total=3),
            ChangeEntry(name="c2", status="in_worktree", tasks_total=0),
        ]
        out = render(data, mode="plain")
        assert "c1" in out
        assert "c2" in out
        # Completed uses 'v' icon in plain mode, in_worktree uses '*'
        assert "v" in out
        assert "*" in out
        # ASCII-only invariant
        assert all(ord(c) < 128 for c in out)


# ---------------------------------------------------------------------------
# Content: features
# ---------------------------------------------------------------------------


class TestFeaturesRendering:
    def test_terminal_shows_feature_counts(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.features = [
            FeatureSummary(
                name="feature-dashboard",
                status="in_progress",
                change_count=4,
                archived_count=2,
                parallel_group=1,
            ),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "f.txt"))
        assert "feature-dashboard" in out
        # archived_count/change_count appears as "2/4"
        assert "2/4" in out
        # in_progress status uses 🔧 emoji
        assert "🔧" in out

    def test_plain_shows_feature_counts_ascii(self, make_empty_data):
        data = make_empty_data()
        data.features = [
            FeatureSummary(
                name="f-x", status="done", change_count=3, archived_count=3
            ),
        ]
        out = render(data, mode="plain")
        assert "f-x" in out
        assert "3/3" in out
        # Plain mode 'done' uses 'v' icon
        assert "v" in out
        assert all(ord(c) < 128 for c in out)


# ---------------------------------------------------------------------------
# Content: arch + plan phase status
# ---------------------------------------------------------------------------


class TestArchPlanPhaseRendering:
    def test_terminal_shows_arch_and_plan_status_icons(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.arch = ArchInfo(
            arch_complete_at="2026-07-15T10:00:00Z",
            adr_count=22,
            current_phase="v2.1",
        )
        data.plan = PlanInfo(
            plan_complete_at="2026-07-18T14:30:00Z",
            committed_changes=["c1", "c2"],
            active_changes=2,
        )
        out = render(data, mode="terminal", output_file=str(tmp_path / "ap.txt"))
        # Arch complete -> ✅
        assert "✅" in out
        # Plan done -> 💼
        assert "💼" in out
        assert "2026-07-15T10:00:00Z" in out
        assert "22" in out
        assert "v2.1" in out
        assert "2026-07-18T14:30:00Z" in out
        assert "c1" in out and "c2" in out

    def test_plain_shows_arch_and_plan_status_markers(self, make_empty_data):
        data = make_empty_data()
        data.arch = ArchInfo(
            arch_complete_at="2026-07-15",
            adr_count=5,
            current_phase="v2.0",
        )
        data.plan = PlanInfo(plan_complete_at="2026-07-18", active_changes=1)
        out = render(data, mode="plain")
        # Plain mode uses [v] for complete, [$] for plan-done
        assert "[v]" in out
        assert "[$]" in out
        assert "2026-07-15" in out
        assert "5" in out
        assert "v2.0" in out
        # ASCII-only invariant
        assert all(ord(c) < 128 for c in out)

    def test_terminal_ships_in_progress_when_ship_started(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.arch = ArchInfo(arch_complete_at="2026-07-01")
        data.plan = PlanInfo(
            plan_complete_at="2026-07-05",
            ship_started_at="2026-07-10",
        )
        out = render(data, mode="terminal", output_file=str(tmp_path / "sp.txt"))
        # Ship in progress -> 🔧
        assert "🔧" in out
        assert "Ship in progress" in out


# ---------------------------------------------------------------------------
# Content: arch completed_adr_ids + pending_adr_ids (v2.1+ arch-handoff fields)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Content: approved proposals (Section 7b)
# ---------------------------------------------------------------------------


class TestApprovedProposalsRendering:
    def test_terminal_shows_approved_subsubsection(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.approved_proposals = [
            ApprovedProposalEntry(
                name="fix-bug", priority="P0", date="2026-08-15", section="approved"
            ),
            ApprovedProposalEntry(
                name="add-feature", priority="P1", date="2026-08-14", section="implemented"
            ),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "ap.txt"))
        assert "7b. Approved proposals" in out
        assert "2 total" in out
        assert "(1 not yet implemented)" in out
        assert "(1 implemented)" in out
        assert "fix-bug" in out and "add-feature" in out

    def test_plain_shows_approved_table_ascii(self, make_empty_data):
        data = make_empty_data()
        data.approved_proposals = [
            ApprovedProposalEntry(name="c1", priority="P1", date="2026-08-15", section="implemented"),
        ]
        out = render(data, mode="plain")
        assert "7b. Approved proposals" in out
        assert "1 total" in out
        assert "(1 implemented)" in out
        assert "c1" in out
        assert all(ord(c) < 128 for c in out)

    def test_terminal_implemented_limit_is_five(self, make_empty_data, tmp_path):
        """Implemented proposals are limited to the 5 most recent by date desc."""
        data = make_empty_data()
        data.approved_proposals = [
            ApprovedProposalEntry(
                name=f"p{i}", section="implemented",
                date=f"2026-08-{i + 1:02d}",
            )
            for i in range(15)
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "lim.txt"))
        assert "15 total" in out
        # 10 hidden (15 - 5)
        assert "+10 implemented hidden" in out
        assert "most recent 5" in out
        # Most recent first: p14 (2026-08-15) should appear, p0 should not
        assert "p14" in out
        assert "p0" not in out

    def test_terminal_shows_all_not_yet_implemented(self, make_empty_data, tmp_path):
        """Section=='approved' rows are shown in full (no limit)."""
        data = make_empty_data()
        data.approved_proposals = [
            ApprovedProposalEntry(name=f"a{i}", section="approved", date="2026-08-01")
            for i in range(8)
        ] + [
            ApprovedProposalEntry(name="z", section="implemented", date="2026-08-15"),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "all.txt"))
        for i in range(8):
            assert f"a{i}" in out, f"a{i} should appear (not yet implemented)"
        assert "z" in out

    def test_json_includes_approved_proposals(self, make_empty_data):
        data = make_empty_data()
        data.approved_proposals = [
            ApprovedProposalEntry(name="x", priority="P0", date="2026-08-01", section="approved"),
        ]
        out = render(data, mode="json")
        parsed = json.loads(out)
        assert len(parsed["approved_proposals"]) == 1
        assert parsed["approved_proposals"][0]["name"] == "x"
        assert parsed["approved_proposals"][0]["section"] == "approved"


# ---------------------------------------------------------------------------
# Content: archived changes limit (Section 3)
# ---------------------------------------------------------------------------


class TestArchivedChangesLimit:
    def test_terminal_archived_shown_count_is_at_most_five(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.changes = [
            ChangeEntry(
                name=f"old-{i:02d}", status="archived",
                archived_at=f"2026-08-{i + 1:02d}T00:00:00Z",
            )
            for i in range(12)
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "al.txt"))
        # 7 archived hidden (12 - 5)
        assert "+7 archived change(s) hidden" in out
        assert "most recent 5" in out

    def test_terminal_sorts_archived_by_archived_at_desc(self, make_empty_data, tmp_path):
        data = make_empty_data()
        data.changes = [
            ChangeEntry(name="oldest", status="archived", archived_at="2026-01-01"),
            ChangeEntry(name="middle", status="archived", archived_at="2026-06-01"),
            ChangeEntry(name="newest", status="archived", archived_at="2026-12-01"),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "ord.txt"))
        newest_pos = out.index("newest")
        middle_pos = out.index("middle")
        oldest_pos = out.index("oldest")
        assert newest_pos < middle_pos < oldest_pos

    def test_terminal_active_changes_unaffected_by_archive_limit(self, make_empty_data, tmp_path):
        """Non-archived changes should always be shown, regardless of count."""
        data = make_empty_data()
        data.changes = [
            ChangeEntry(name=f"active-{i:02d}", status="in_worktree")
            for i in range(8)
        ] + [
            ChangeEntry(name="archived-1", status="archived", archived_at="2026-08-01"),
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "act.txt"))
        for i in range(8):
            assert f"active-{i:02d}" in out
        # No hide line since only 1 archived
        assert "archived change(s) hidden" not in out

    def test_plain_archived_limit_is_five(self, make_empty_data):
        data = make_empty_data()
        data.changes = [
            ChangeEntry(
                name=f"old-{i:02d}", status="archived",
                archived_at=f"2026-08-{i + 1:02d}",
            )
            for i in range(8)
        ]
        out = render(data, mode="plain")
        assert "+3 archived change(s) hidden" in out
        assert "most recent 5" in out


# ---------------------------------------------------------------------------
# parse_approved_proposals_detailed — unit tests for the new helper
# ---------------------------------------------------------------------------


class TestParseApprovedDetailed:
    def test_returns_one_row_per_table_line(self, tmp_path):
        from _lib.parse_approved import parse_approved_proposals_detailed

        md = tmp_path / "p.md"
        md.write_text(
            "# title\n\n"
            "## 已批准提案\n\n"
            "| 提案 | 优先级 | 批准时间 | 批准者 |\n"
            "|------|--------|----------|--------|\n"
            "| [a](.rddf/improvements/a.md) | P0 | 2026-08-01 | alice |\n"
            "| [b](.rddf/improvements/b.md) | P1 | 2026-08-02 | bob |\n"
            "\n"
            "## 已实施\n\n"
            "| [c](.rddf/improvements/c.md) | P2 | 2026-08-03 |\n",
            encoding="utf-8",
        )
        rows = parse_approved_proposals_detailed(str(md))
        assert len(rows) == 3
        assert rows[0].name == "a"
        assert rows[0].priority == "P0"
        assert rows[0].date == "2026-08-01"
        assert rows[0].section == "approved"
        assert rows[2].section == "implemented"

    def test_skips_rows_in_non_canonical_sections(self, tmp_path):
        from _lib.parse_approved import parse_approved_proposals_detailed

        md = tmp_path / "p.md"
        md.write_text(
            "## supersedes (2026-08-02)\n\n"
            "| [should-skip](.rddf/improvements/skip.md) | P0 | x |\n"
            "\n"
            "## 已批准提案\n\n"
            "| [kept](.rddf/improvements/kept.md) | P1 | 2026-08-01 |\n",
            encoding="utf-8",
        )
        rows = parse_approved_proposals_detailed(str(md))
        names = [r.name for r in rows]
        assert "kept" in names
        assert "should-skip" not in names

    def test_dedup_keeps_first_occurrence(self, tmp_path):
        from _lib.parse_approved import parse_approved_proposals_detailed

        md = tmp_path / "p.md"
        md.write_text(
            "## 已批准提案\n\n"
            "| [dup](.rddf/improvements/dup.md) | P0 | 2026-08-01 |\n"
            "\n"
            "## 已实施\n\n"
            "| [dup](.rddf/improvements/dup.md) | P2 | 2026-08-09 |\n",
            encoding="utf-8",
        )
        rows = parse_approved_proposals_detailed(str(md))
        assert len(rows) == 1
        assert rows[0].section == "approved"  # first occurrence wins

    def test_missing_file_returns_empty_list(self, tmp_path):
        from _lib.parse_approved import parse_approved_proposals_detailed

        rows = parse_approved_proposals_detailed(str(tmp_path / "nope.md"))
        assert rows == []


# ---------------------------------------------------------------------------
# Auto-degrade (isatty detection)
# ---------------------------------------------------------------------------


class TestAutoDegrade:
    def test_terminal_auto_degrades_to_plain_when_not_tty(self, make_empty_data):
        """When stdout is not a TTY and no output_file given, terminal -> plain."""
        with patch(
            "skills._lib.dashboard.renderer._stdout_is_tty", return_value=False
        ):
            out = render(make_empty_data(), mode="terminal")
        # Should have plain-mode markers ([v], [ ], etc.) and no box chars
        assert "╔" not in out
        assert "║" not in out
        assert "+" in out  # plain mode top border uses +

    def test_terminal_keeps_box_when_tty(self, make_empty_data):
        """When stdout IS a TTY, terminal mode retains box-drawing chars."""
        with patch(
            "skills._lib.dashboard.renderer._stdout_is_tty", return_value=True
        ):
            out = render(make_empty_data(), mode="terminal")
        assert "╔" in out
        assert "║" in out


# ---------------------------------------------------------------------------
# output_file parameter
# ---------------------------------------------------------------------------


class TestOutputFile:
    def test_output_file_is_written_correctly(self, make_empty_data, tmp_path):
        target = tmp_path / "dash.txt"
        out = render(make_empty_data(), mode="plain", output_file=str(target))
        assert target.exists(), "output_file was not created"
        written = target.read_text(encoding="utf-8")
        assert written == out, (
            "file content must match the returned string exactly"
        )

    def test_output_file_terminal_mode_written(self, make_empty_data, tmp_path):
        target = tmp_path / "dash_term.txt"
        out = render(make_empty_data(), mode="terminal", output_file=str(target))
        assert target.exists()
        assert target.read_text(encoding="utf-8") == out
        # Should contain box-drawing chars (output_file forces terminal mode)
        assert "╔" in out


# ---------------------------------------------------------------------------
# Error path: invalid mode
# ---------------------------------------------------------------------------


class TestInvalidMode:
    def test_invalid_mode_raises_valueerror(self, make_empty_data):
        with pytest.raises(ValueError) as exc_info:
            render(make_empty_data(), mode="html")
        assert "html" in str(exc_info.value)
        assert "terminal" in str(exc_info.value)
        assert "json" in str(exc_info.value)
        assert "plain" in str(exc_info.value)

    def test_invalid_mode_empty_string_raises(self, make_empty_data):
        with pytest.raises(ValueError):
            render(make_empty_data(), mode="")

    def test_invalid_mode_case_sensitive(self, make_empty_data):
        """Mode matching is case-sensitive: 'TERMINAL' is not 'terminal'."""
        with pytest.raises(ValueError):
            render(make_empty_data(), mode="TERMINAL")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_terminal_output_ends_with_newline(self, make_empty_data, tmp_path):
        """Non-empty output should always end with a newline (per render() docstring)."""
        out = render(make_empty_data(), mode="terminal", output_file=str(tmp_path / "nl.txt"))
        assert out.endswith("\n")

    def test_plain_output_ends_with_newline(self, make_empty_data):
        out = render(make_empty_data(), mode="plain")
        assert out.endswith("\n")

    def test_json_output_ends_with_newline(self, make_empty_data):
        out = render(make_empty_data(), mode="json")
        assert out.endswith("\n")

    def test_project_root_appears_in_output(self, make_empty_data):
        """The project_root string should appear in every render mode."""
        data = make_empty_data(project_root="/some/unique/root/xyz")
        for mode in ("plain", "json"):
            out = render(data, mode=mode)
            assert "/some/unique/root/xyz" in out

    def test_many_changes_render_without_error(self, make_empty_data, tmp_path):
        """Stress test: many change entries should render without error."""
        data = make_empty_data()
        data.changes = [
            ChangeEntry(name=f"change-{i:03d}", status="proposed", tasks_total=i + 1)
            for i in range(50)
        ]
        out = render(data, mode="terminal", output_file=str(tmp_path / "many.txt"))
        assert "change-000" in out
        assert "change-049" in out

    def test_unicode_in_change_name_renders_in_json(self, make_empty_data):
        """Non-ASCII change names must round-trip through JSON mode."""
        data = make_empty_data()
        data.changes = [ChangeEntry(name="变更-测试", status="proposed")]
        out = render(data, mode="json")
        parsed = json.loads(out)
        assert parsed["changes"][0]["name"] == "变更-测试"


class TestCollectCurrentSession:
    def _patch_readers(self, monkeypatch, sessions):
        monkeypatch.setattr(dashboard, "read_arch_handoff", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_plan_handoff", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_iteration", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_roadmap_state", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_improvement_entries", lambda _p: [])
        monkeypatch.setattr(dashboard, "list_worktrees", lambda: [])
        monkeypatch.setattr(dashboard, "list_change_dirs", lambda _p: [])
        monkeypatch.setattr(dashboard, "read_sessions", lambda _p: sessions)

    def test_collect_marks_owner_session_as_current(self, monkeypatch, tmp_path):
        sessions = [
            {
                "session_id": "s1",
                "kind": "plan",
                "state": "active",
                "owner_opencode_session_id": "owner_a",
                "started_at": "2026-07-21T10:00:00+00:00",
            },
            {
                "session_id": "s2",
                "kind": "ship",
                "state": "active",
                "owner_opencode_session_id": "owner_b",
                "started_at": "2026-07-21T11:00:00+00:00",
            },
        ]
        self._patch_readers(monkeypatch, sessions)
        monkeypatch.setenv("OPENCODE_SESSION_ID", "owner_a")
        data = collect(str(tmp_path))
        by_id = {s.session_id: s for s in data.sessions}
        assert by_id["s1"].is_current is True
        assert by_id["s2"].is_current is False

    def test_collect_falls_back_to_most_recent_active(self, monkeypatch, tmp_path):
        sessions = [
            {
                "session_id": "s1",
                "kind": "plan",
                "state": "active",
                "owner_opencode_session_id": "owner_a",
                "started_at": "2026-07-21T10:00:00+00:00",
            },
            {
                "session_id": "s2",
                "kind": "ship",
                "state": "active",
                "owner_opencode_session_id": "owner_b",
                "started_at": "2026-07-21T11:00:00+00:00",
            },
        ]
        self._patch_readers(monkeypatch, sessions)
        monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
        data = collect(str(tmp_path))
        by_id = {s.session_id: s for s in data.sessions}
        assert by_id["s2"].is_current is True
        assert by_id["s1"].is_current is False
