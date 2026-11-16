"""Round-trip tests for generate_full_proposal.py.

5-段 improvement (.rddf/improvements/<name>.md) → full proposal.md
(openspec/changes/<name>/proposal.md) converter per ADR-0025 D1/D2.
"""
import re
import sys
from pathlib import Path

import pytest

# Add to sys.path so we can import from skills/rdd-builder/scripts
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-builder" / "scripts"))

from generate_full_proposal import generate_full_proposal, generate_spec_delta  # noqa: E402


SAMPLE_IMPROVEMENT = """# fix-sample

**优先级**: P1 | **来源**: 测试

## Why

The user wants to fix X.

## 范围

In Scope: A, B, C.

## Capabilities

- capability-sample

## Impact

Users benefit.

## Acceptance

- AC-1: foo works
- AC-2: bar works
- AC-3: baz works

## Reference

- ADR-0001
"""


def test_generate_full_proposal_populates_why():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Why" in out
    assert "The user wants to fix X" in out


def test_generate_full_proposal_populates_what_changes():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## What Changes" in out
    assert "- A" in out
    assert "- B" in out
    assert "- C" in out


def test_generate_full_proposal_populates_capabilities():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Capabilities" in out
    assert "- capability-sample" in out


def test_generate_full_proposal_populates_impact():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Impact" in out
    assert "Users benefit" in out


def test_generate_full_proposal_populates_acceptance():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Acceptance" in out
    assert "AC-1" in out
    assert "AC-2" in out
    assert "AC-3" in out


def test_generate_full_proposal_includes_change_name_in_title():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert out.startswith("# fix-sample")


def test_generate_full_proposal_no_placeholders():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "<skeleton motivation>" not in out
    assert "TBD" not in out
    assert "fill in details" not in out


def test_generate_full_proposal_handles_missing_acceptance():
    """If improvement lacks ## Acceptance, generate from ## Capabilities as fallback AC."""
    minimal = """# fix-min

## Why

Need to fix.

## 范围

Just one thing.

## Capabilities

- capability-x

## Impact

None.

## Reference
"""
    out = generate_full_proposal("fix-min", minimal)
    assert "## Acceptance" in out  # Fallback synthesized


def test_generate_full_proposal_handles_empty_improvement():
    """If improvement has only H1, generate a placeholder-but-valid proposal."""
    empty = "# fix-empty\n"
    out = generate_full_proposal("fix-empty", empty)
    assert out.startswith("# fix-empty")
    assert "## Why" in out
    assert "## What Changes" in out


def test_generate_full_proposal_preserves_references():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "ADR-0001" in out


def test_generate_full_proposal_preserves_priority_metadata():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "P1" in out


def test_generate_full_proposal_generates_skeleton_for_invalid_input():
    """Passing non-string raises TypeError (defensive)."""
    with pytest.raises(TypeError):
        generate_full_proposal("fix-x", None)


# ---------------------------------------------------------------------------
# fix-proposal-generator-section-merge / table-mapping
# ---------------------------------------------------------------------------

TABLE_IMPROVEMENT = """# fix-table

**优先级**: P1 | **来源**: 测试

## 架构依据

Evidence table.

## Why

Motivation paragraph.

## 范围

**In Scope**:

- 新增 `_lib/core/rddf_layout.py`：单一清单。每条字段 + 取值域：

  | 字段 | 取值 | 说明 |
  |---|---|---|
  | `path` | 字符串 | 相对 `.rddf/` 的顶层条目名 |

- 第二个条目

**Out of Scope**:

- 不做反向断言

## Capabilities

- MUST: 清单是唯一声明点
- SHOULD: 文档页措辞与 ADR 一致

## Impact

- **新增**：`_lib/core/rddf_layout.py`

## Acceptance

- [ ] 清单导出 RDFF_LAYOUT
"""


def test_scope_keeps_markdown_table_under_bullet():
    """A table under an In-Scope bullet is part of that item, not dropped."""
    out = generate_full_proposal("fix-table", TABLE_IMPROVEMENT)
    assert "| 字段 | 取值 | 说明 |" in out
    assert "| `path` | 字符串 | 相对 `.rddf/` 的顶层条目名 |" in out


def test_scope_table_stays_attached_to_its_bullet():
    """The table must follow its bullet, not float into another item."""
    out = generate_full_proposal("fix-table", TABLE_IMPROVEMENT)
    lines = out.splitlines()
    bullet_idx = next(i for i, l in enumerate(lines) if "单一清单。每条字段" in l)
    table_idx = next(i for i, l in enumerate(lines) if l.strip().startswith("| 字段 |"))
    assert table_idx > bullet_idx
    # A table needs a blank line before it, otherwise it is paragraph text.
    assert lines[table_idx - 1].strip() == ""


def test_why_merges_why_and_architecture_basis():
    """When both "## Why" and "## 架构依据" exist, neither is dropped."""
    out = generate_full_proposal("fix-table", TABLE_IMPROVEMENT)
    assert "Motivation paragraph." in out
    assert "Evidence table." in out
    assert out.index("Motivation paragraph.") < out.index("Evidence table.")


def test_impact_section_has_no_double_dash():
    """The Impact section is emitted as-is — no "- - " prefix."""
    out = generate_full_proposal("fix-table", TABLE_IMPROVEMENT)
    assert "- - " not in out
    assert "- **新增**：`_lib/core/rddf_layout.py`" in out


def test_spec_delta_captures_plain_must_format():
    """`- MUST: x` (5-段 convention) must become a capability Requirement."""
    src = TABLE_IMPROVEMENT
    delta = generate_spec_delta(src, "fix-table")
    assert re.search(r"^### Requirement: capability-\d+$", delta, re.MULTILINE)
    assert "The system MUST 清单是唯一声明点." in delta


def test_spec_delta_captures_bold_must_format():
    """`- **MUST**: x` (bold variant) keeps working."""
    src = "## Capabilities\n\n- **MUST**: 清单是唯一声明点\n- **MUST NOT**: 不得修改既有路径\n"
    delta = generate_spec_delta(src, "fix-table")
    assert "The system MUST 清单是唯一声明点." in delta
    assert "The system MUST NOT 不得修改既有路径." in delta


def test_spec_delta_captures_should():
    """SHOULD entries are normative too — they become Requirements."""
    delta = generate_spec_delta(TABLE_IMPROVEMENT, "fix-table")
    assert "The system SHOULD 文档页措辞与 ADR 一致." in delta


def test_spec_delta_keeps_acceptance_requirements():
    delta = generate_spec_delta(TABLE_IMPROVEMENT, "fix-table")
    assert "### Requirement: acceptance-1" in delta
    assert "The system SHALL 清单导出 RDFF_LAYOUT." in delta


def test_cli_output_mode_spec_delta(tmp_path):
    """OUTPUT_MODE=spec-delta makes the script emit the D3 delta, not a proposal."""
    import os
    import subprocess

    script = PROJECT_ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
    imp = tmp_path / "improvement.md"
    imp.write_text(TABLE_IMPROVEMENT, encoding="utf-8")
    env = dict(os.environ)
    env.update({
        "IMPROVEMENTS_PATH": str(imp),
        "CHANGE_NAME": "fix-table",
        "OUTPUT_MODE": "spec-delta",
    })
    res = subprocess.run(
        ["python3", str(script)], capture_output=True, text=True, env=env, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.startswith("## ADDED Requirements")
    assert "### Requirement: acceptance-1" in res.stdout
    assert "## What Changes" not in res.stdout


def test_cli_default_output_is_proposal(tmp_path):
    """Without OUTPUT_MODE the script emits the proposal draft."""
    import os
    import subprocess

    script = PROJECT_ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
    imp = tmp_path / "improvement.md"
    imp.write_text(TABLE_IMPROVEMENT, encoding="utf-8")
    env = dict(os.environ)
    env.update({"IMPROVEMENTS_PATH": str(imp), "CHANGE_NAME": "fix-table"})
    res = subprocess.run(
        ["python3", str(script)], capture_output=True, text=True, env=env, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    assert "## What Changes" in res.stdout
    assert "## ADDED Requirements" not in res.stdout
