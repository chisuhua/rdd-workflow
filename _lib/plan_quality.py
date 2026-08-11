"""Plan quality validation module.

Per .rddf/improvements/plan-quality-and-validation.md:
- Pre-publish checklist (BASH_SOURCE guards, expected counts, fixture paths)
- Auto-generate BASH_SOURCE guards for script templates
- Dry-run validation

Out of scope: rewriting rdd-workflow-writing-plans, modifying execute skill.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class CheckStatus(Enum):
    """Severity of a plan quality check."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ChecklistItem:
    """Single item in the plan quality checklist."""
    id: str
    description: str
    severity: CheckStatus


@dataclass
class CheckResult:
    """Result of a single check."""
    check_id: str
    status: CheckStatus
    message: str


@dataclass
class PlanEvaluation:
    """Result of evaluating a plan."""
    failures: List[CheckResult] = field(default_factory=list)
    warnings: List[CheckResult] = field(default_factory=list)
    passes: List[CheckResult] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.failures) == 0


PLAN_QUALITY_CHECKLIST: List[ChecklistItem] = [
    ChecklistItem(
        id="bash_source_guard",
        description="Script step 5 含 BASH_SOURCE[0] guard(如适用,允许独立 bash 执行)",
        severity=CheckStatus.FAIL,
    ),
    ChecklistItem(
        id="expected_count_real",
        description="expected 数字基于实际测试运行(非估算)",
        severity=CheckStatus.WARN,
    ),
    ChecklistItem(
        id="fixture_path_safe",
        description="不假设未验证的 fixture 路径(优先使用 $BATS_TEST_TMPDIR)",
        severity=CheckStatus.FAIL,
    ),
    ChecklistItem(
        id="cross_stage_env_var",
        description="涉及跨 stage 测试的 plan 加入 RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes env var",
        severity=CheckStatus.FAIL,
    ),
]


_BASH_SOURCE_GUARD_PATTERN = re.compile(r'if\s+\[\s*"\$\{BASH_SOURCE\[0\][^}]*\}".*=\s*"\$\{0\}".*then', re.DOTALL)
_FUNCTION_DEF_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*\(\s*\)\s*\{", re.MULTILINE)
_UNSAFE_FIXTURE_PATHS = re.compile(r"^/(tmp|var|home)/[^$]")


def evaluate_plan(plan: dict) -> PlanEvaluation:
    """Evaluate a plan against the quality checklist.

    Args:
        plan: dict with keys:
            - step_5_scripts: list of script strings (or empty)
            - expected_counts: dict of metric name -> count (int) or estimate (str)
            - fixture_paths: list of fixture paths used
            - uses_cross_stage: bool
            - env_vars: dict of env var name -> value (optional)

    Returns:
        PlanEvaluation with failures/warnings/passes lists.
    """
    result = PlanEvaluation()

    # Check 1: BASH_SOURCE guards for script steps
    scripts = plan.get("step_5_scripts", [])
    for script in scripts:
        if not _has_function_def(script):
            continue
        if not _has_bash_source_guard(script):
            result.failures.append(CheckResult(
                check_id="bash_source_guard",
                status=CheckStatus.FAIL,
                message=f"Script with function definitions missing BASH_SOURCE[0] guard",
            ))
        else:
            result.passes.append(CheckResult(
                check_id="bash_source_guard",
                status=CheckStatus.PASS,
                message="BASH_SOURCE guard present",
            ))

    # Check 2: expected counts are real numbers (not estimates)
    counts = plan.get("expected_counts", {})
    for name, count in counts.items():
        if isinstance(count, str):
            result.warnings.append(CheckResult(
                check_id="expected_count_real",
                status=CheckStatus.WARN,
                message=f"Expected count '{name}' is a string estimate ('{count}'), not a real number",
            ))
        elif isinstance(count, int):
            result.passes.append(CheckResult(
                check_id="expected_count_real",
                status=CheckStatus.PASS,
                message=f"Expected count '{name}' is real number ({count})",
            ))

    # Check 3: fixture paths are safe
    paths = plan.get("fixture_paths", [])
    for path in paths:
        if _UNSAFE_FIXTURE_PATHS.match(path):
            result.failures.append(CheckResult(
                check_id="fixture_path_safe",
                status=CheckStatus.FAIL,
                message=f"Unsafe fixture path '{path}' — use $BATS_TEST_TMPDIR",
            ))
        else:
            result.passes.append(CheckResult(
                check_id="fixture_path_safe",
                status=CheckStatus.PASS,
                message=f"Safe fixture path '{path}'",
            ))

    # Check 4: cross-stage env var
    if plan.get("uses_cross_stage"):
        env_vars = plan.get("env_vars", {})
        if env_vars.get("RDDF_ALLOW_CROSS_STAGE_PARALLEL") != "yes":
            result.failures.append(CheckResult(
                check_id="cross_stage_env_var",
                status=CheckStatus.FAIL,
                message="Plan uses cross-stage tests but env var RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes not set",
            ))
        else:
            result.passes.append(CheckResult(
                check_id="cross_stage_env_var",
                status=CheckStatus.PASS,
                message="Cross-stage env var set",
            ))

    return result


def _has_function_def(script: str) -> bool:
    """Check if script contains any top-level function definition."""
    return bool(_FUNCTION_DEF_PATTERN.search(script))


def _has_bash_source_guard(script: str) -> bool:
    """Check if script already has BASH_SOURCE[0] direct-execution guard."""
    return bool(_BASH_SOURCE_GUARD_PATTERN.search(script))


def auto_generate_bash_source_guard(script: str) -> str:
    """Auto-append BASH_SOURCE[0] guard to script if it has function definitions.

    Returns the script with guard prepended, or original if already-guarded
    or no function definitions found.
    """
    if not _has_function_def(script):
        return script

    if _has_bash_source_guard(script):
        return script

    # Find function definitions and wrap them in guard
    # Use a simple approach: indent existing content and add guard
    lines = script.split("\n")
    indented = "\n".join("    " + line if line.strip() else line for line in lines)
    guard = (
        '# Auto-generated BASH_SOURCE[0] guard for direct execution\n'
        'if [ "${BASH_SOURCE[0]:-$0}" = "${0}" ]; then\n'
        f'{indented}\n'
        'fi\n'
    )
    return guard
