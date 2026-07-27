# tests/unit/test_reflect_engine.py
import os, json, tempfile, pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from skills._lib.reflect_engine import ReflectEngine, ReflectResult, IssueDraft


class TestReflectEngine:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.engine = ReflectEngine(
            phase="plan",
            project_root=self.tmpdir,
            dry_run=True,
        )

    def test_analyze_with_no_errors_returns_no_action(self):
        result = self.engine.analyze(failures=[])
        assert result.action == "none"
        assert result.fingerprint == ""

    def test_analyze_ship_unrecovered_failure(self):
        failures = [{"type": "unrecovered_failure",
                     "step": "execute",
                     "error": "worktree create timeout",
                     "max_retries": 3}]
        result = self.engine.analyze(failures=failures)
        assert result.action == "propose_issue"
        assert "ship" in result.fingerprint

    def test_analyze_plan_same_root_cause_twice(self):
        failures = [
            {"type": "gate_fail", "gate": "plan-done", "error": "quality-gate-fail", "retry": 1},
            {"type": "gate_fail", "gate": "plan-done", "error": "quality-gate-fail", "retry": 2},
        ]
        result = self.engine.analyze(failures=failures)
        assert result.action == "propose_issue"
        assert "plan" in result.fingerprint

    def test_analyze_plan_single_failure_no_action(self):
        failures = [{"type": "gate_fail", "gate": "plan-done", "error": "quality-gate-fail"}]
        result = self.engine.analyze(failures=failures)
        assert result.action == "none"

    def test_analyze_arch_always_log_only(self):
        engine = ReflectEngine(phase="arch", project_root=self.tmpdir, dry_run=True)
        failures = [{"type": "unrecovered_failure", "error": "any error"}]
        result = engine.analyze(failures=failures)
        assert result.action == "log_friction"
        assert result.fingerprint != ""

    def test_skip_workflow_reflection_env_var(self):
        os.environ["SKIP_WORKFLOW_REFLECTION"] = "1"
        engine = ReflectEngine(phase="ship", project_root=self.tmpdir)
        result = engine.analyze(failures=[{"type": "unrecovered_failure"}])
        assert result.action == "skipped"
        assert result.reason == "SKIP_WORKFLOW_REFLECTION=1"
        del os.environ["SKIP_WORKFLOW_REFLECTION"]

    def test_timeout_handling(self):
        """ReflectEngine should handle timeout exceptions gracefully."""
        engine = ReflectEngine(phase="ship", project_root=self.tmpdir, timeout=0.01)
        with patch.object(engine, '_do_analyze', side_effect=TimeoutError("simulated")):
            result = engine.analyze(failures=[{"type": "gate_fail"}])
            assert result.action == "error"
            assert "timeout" in result.reason.lower()

    def test_draft_issue_template(self):
        result = ReflectResult(
            action="propose_issue",
            fingerprint="ship:execute:worktree-timeout",
            session_id="rds_test123",
            errors=["worktree create timed out after 3 retries"],
        )
        draft = self.engine.draft_issue(result)
        assert isinstance(draft, IssueDraft)
        assert "worktree" in draft.title.lower()
        assert "rds_test123" in draft.body
        assert draft.target_repo is not None

    def test_route_issue_rdd_workflow_paths(self):
        """File paths under skills/_lib/ or docs/adr/ route to rdd-workflow repo."""
        paths = ["skills/_lib/gate.py", "docs/adr/ADR-0007.md"]
        repo = self.engine._route_issue(paths)
        assert repo == "chisuhua/rdd-workflow"

    def test_route_issue_user_project_paths(self):
        """Other file paths route to git remote origin."""
        os.makedirs(os.path.join(self.tmpdir, ".git"), exist_ok=True)
        with open(os.path.join(self.tmpdir, ".git", "config"), 'w') as f:
            f.write('[remote "origin"]\n\turl = https://github.com/user/project.git\n')
        paths = ["src/main.py", "tests/test_foo.py"]
        repo = self.engine._route_issue(paths)
        assert repo == "user/project"

    def test_fingerprint_format(self):
        """Fingerprint must follow {phase}:{gate_name}:{error_category} format."""
        fp = self.engine._make_fingerprint("ship", "archive-done", "worktree-timeout")
        assert fp == "ship:archive-done:worktree-timeout"

    def test_sanitize_fingerprint(self):
        """Fingerprint special chars should be stripped."""
        fp = self.engine._make_fingerprint("plan", "plan-done", "quality gate fail!!!")
        assert "!" not in fp
        assert " " not in fp
