"""Unit tests for execute skill regression gate coverage."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = REPO_ROOT / "skills" / "execute" / "SKILL.md"


def test_step5_full_regression_in_skill() -> None:
    content = SKILL_PATH.read_text()
    assert "Step 5: Full Regression Gate" in content
    after_step5 = content.split("Step 5: Full Regression Gate")[1]
    assert "ctest" in after_step5
    assert "SKIP_REGRESSION" in after_step5
