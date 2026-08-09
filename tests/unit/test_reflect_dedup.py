# tests/unit/test_reflect_dedup.py
import os, tempfile, json, pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from skills._lib.reflect_dedup import DedupMatcher


class TestDedupMatcher:
    def setup_method(self, tmp_path):
        self.tmpdir = str(tmp_path)
        self.improvements_dir = os.path.join(self.tmpdir, "improvements")
        os.makedirs(self.improvements_dir, exist_ok=True)
        self.suggestions_file = os.path.join(self.tmpdir, "proposal-suggestions.md")
        self.approved_file = os.path.join(self.tmpdir, "proposal-approved.md")
        self.matcher = DedupMatcher(
            improvements_dir=self.improvements_dir,
            suggestions_file=self.suggestions_file,
            approved_file=self.approved_file,
            project_root=self.tmpdir,
        )

    def _create_improvement(self, name, content):
        path = os.path.join(self.improvements_dir, f"{name}.md")
        with open(path, 'w') as f:
            f.write(content)

    def _create_suggestions_json(self, entries):
        with open(self.suggestions_file, 'w') as f:
            json.dump(entries, f, indent=2)

    def _create_approved_md(self, table_rows):
        lines = ["# 已批准提案（Plan 阶段输入）", "",
                 "| 提案 | 优先级 | 批准时间 | 批准人 |",
                 "|------|--------|----------|--------|"]
        for row in table_rows:
            lines.append(f"| [{row['name']}](improvements/{row['name']}.md) | {row.get('priority','P1')} | {row.get('date','2026-01-01')} | {row.get('approver','guide-arch')} |")
        with open(self.approved_file, 'w') as f:
            f.write("\n".join(lines))

    def test_no_match_returns_none(self):
        result = self.matcher.check_all("some:unknown:error")
        assert result is None

    def test_match_in_improvements(self):
        self._create_improvement("propose-quality-autohook",
            "# propose-quality-autohook\n\nquality gate failure detection")
        result = self.matcher.check_all("plan:plan-done:quality-gate-fail")
        assert result is not None
        assert result["source"] == "improvements"
        assert "quality" in result["matched_name"]

    def test_match_in_suggestions(self):
        self._create_suggestions_json([
            {"name": "fix-gate-timeout", "priority": "P1", "source": "Oracle",
             "description": "Handle gate timeout edge cases"}
        ])
        result = self.matcher.check_all("plan:plan-done:gate-timeout")
        assert result is not None
        assert result["source"] == "suggestions"

    def test_match_in_approved(self):
        self._create_approved_md([
            {"name": "add-heartbeat-config", "priority": "P1", "date": "2026-01-01", "approver": "guide-arch"}
        ])
        result = self.matcher.check_all("ship:archive:heartbeat-timeout")
        assert result is not None
        assert result["source"] == "approved"

    def test_return_first_match_only(self):
        self._create_improvement("test-qa", "quality assurance")
        self._create_suggestions_json([
            {"name": "test-qa-v2", "priority": "P1", "source": "Oracle",
             "description": "QA improvements"}
        ])
        result = self.matcher.check_all("plan:plan-done:qa-fail")
        assert result is not None
        assert result["source"] in ("improvements", "suggestions")

    def test_signature_with_keywords_in_proposal_text(self):
        self._create_improvement("archive-cleanup",
            "archive process improvement for worktree cleanup")
        result = self.matcher.check_all("ship:archive-done:cleanup-failed")
        assert result is not None

    def test_empty_inputs_all_succeed_gracefully(self):
        # No improvements dir, no files
        matcher_empty = DedupMatcher(
            improvements_dir=os.path.join(self.tmpdir, "nonexistent"),
            suggestions_file=os.path.join(self.tmpdir, "nonexistent.md"),
            approved_file=os.path.join(self.tmpdir, "nonexistent.md"),
            project_root=self.tmpdir,
        )
        result = matcher_empty.check_all("any:fingerprint:here")
        assert result is None
