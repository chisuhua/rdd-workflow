"""Tests for plan quality validation module.

Per improvements/plan-quality-and-validation.md:
- Plan quality checklist (BASH_SOURCE guards, fixture paths, expected counts)
- Auto-guard generation for script templates
- Dry-run validation
"""
import pytest

from skills._lib.plan_quality import (
    ChecklistItem,
    CheckResult,
    CheckStatus,
    evaluate_plan,
    auto_generate_bash_source_guard,
    PLAN_QUALITY_CHECKLIST,
)


class TestPlanQualityChecklist:
    def test_checklist_has_required_items(self):
        """Plan checklist has all expected items per proposal."""
        ids = [item.id for item in PLAN_QUALITY_CHECKLIST]
        assert "bash_source_guard" in ids
        assert "expected_count_real" in ids
        assert "fixture_path_safe" in ids
        assert "cross_stage_env_var" in ids

    def test_evaluate_plan_with_all_pass(self):
        """Evaluate plan passing all checks returns no failures."""
        plan = {
            "step_5_scripts": [
                'if [ "${BASH_SOURCE[0]:-$0}" = "${0}" ]; then\nfoo() { echo; }\nfi'
            ],
            "expected_counts": {"test_count": 17},
            "fixture_paths": ["$BATS_TEST_TMPDIR"],
            "uses_cross_stage": True,
            "env_vars": {"RDDF_ALLOW_CROSS_STAGE_PARALLEL": "yes"},
        }
        result = evaluate_plan(plan)
        assert len(result.failures) == 0
        assert len(result.warnings) == 0

    def test_evaluate_plan_missing_bash_source_guard(self):
        """Plan with script step lacking BASH_SOURCE guard fails."""
        plan = {
            "step_5_scripts": ["foo() { echo; }"],  # no guard
            "expected_counts": {"test_count": 17},
            "fixture_paths": ["$BATS_TEST_TMPDIR"],
            "uses_cross_stage": False,
        }
        result = evaluate_plan(plan)
        assert any(f.check_id == "bash_source_guard" for f in result.failures)

    def test_evaluate_plan_estimated_count_warning(self):
        """Plan with estimated count raises warning."""
        plan = {
            "step_5_scripts": ["# BASH_SOURCE[0] guard\nfoo() { echo; }"],
            "expected_counts": {"test_count": "approximately 17"},  # string = estimate
            "fixture_paths": ["$BATS_TEST_TMPDIR"],
            "uses_cross_stage": False,
        }
        result = evaluate_plan(plan)
        assert any(w.check_id == "expected_count_real" for w in result.warnings)

    def test_evaluate_plan_unsafe_fixture_path(self):
        """Plan with unsafe fixture path fails."""
        plan = {
            "step_5_scripts": ["# BASH_SOURCE[0] guard\nfoo() { echo; }"],
            "expected_counts": {"test_count": 17},
            "fixture_paths": ["/tmp/some-path"],  # not $BATS_TEST_TMPDIR
            "uses_cross_stage": False,
        }
        result = evaluate_plan(plan)
        assert any(f.check_id == "fixture_path_safe" for f in result.failures)

    def test_evaluate_plan_missing_cross_stage_env_var(self):
        """Plan using cross-stage tests without env var fails."""
        plan = {
            "step_5_scripts": ["# BASH_SOURCE[0] guard\nfoo() { echo; }"],
            "expected_counts": {"test_count": 17},
            "fixture_paths": ["$BATS_TEST_TMPDIR"],
            "uses_cross_stage": True,
            "env_vars": {},  # missing RDDF_ALLOW_CROSS_STAGE_PARALLEL
        }
        result = evaluate_plan(plan)
        assert any(f.check_id == "cross_stage_env_var" for f in result.failures)

    def test_check_result_status_enum(self):
        """CheckResult has PASS/WARN/FAIL statuses."""
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.WARN.value == "warn"
        assert CheckStatus.FAIL.value == "fail"


class TestBashSourceGuard:
    def test_auto_generate_guard_for_function_def(self):
        """Auto-generate BASH_SOURCE guard for script with function def."""
        script = """foo() {
    echo "hello"
}
"""
        result = auto_generate_bash_source_guard(script)
        assert "BASH_SOURCE[0]" in result
        assert 'if [ "${BASH_SOURCE[0]:-$0}" = "${0}" ]; then' in result
        assert "foo" in result

    def test_auto_generate_guard_idempotent(self):
        """Running on already-guarded script is idempotent."""
        script = """if [ "${BASH_SOURCE[0]:-$0}" = "${0}" ]; then
foo() { echo; }
fi
"""
        result = auto_generate_bash_source_guard(script)
        # Should not double-guard
        assert result.count("BASH_SOURCE[0]") == 1

    def test_no_guard_for_script_without_functions(self):
        """Script without function definitions doesn't need guard."""
        script = "# Simple script\nls -la\necho done\n"
        result = auto_generate_bash_source_guard(script)
        # Should not add guard
        assert "BASH_SOURCE[0]" not in result
