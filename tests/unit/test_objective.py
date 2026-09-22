"""Unit tests for _lib/objective.py schema constants and validation.

Per design D7: 9 required frontmatter fields, status enum (4 values),
priority enum (3 values), kind enum (5 values), N/A format constraint.

These tests verify the *constants* and *validation logic*, not the schema
file itself (the JSON Schema file is parsed by external tools; here we
focus on Python-side guarantees).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from _lib.objective import (
    KIND_ENUM,
    NA_PATTERN,
    OPTIONAL_SECTIONS,
    PRIORITY_ENUM,
    REQUIRED_FRONTMATTER,
    REQUIRED_SECTIONS,
    STATUS_ENUM,
    derive_associations,
    grace_period_exceeded,
    is_na_format,
    parse_objective,
    validate_objective,
)

# ---------------------------------------------------------------------------
# Constants — schema invariants
# ---------------------------------------------------------------------------


def test_status_enum_has_exactly_4_values():
    assert STATUS_ENUM == frozenset({"active", "deferred", "completed", "archived"})


def test_priority_enum_has_exactly_3_values():
    assert PRIORITY_ENUM == frozenset({"P0", "P1", "P2"})


def test_kind_enum_has_exactly_5_values():
    assert KIND_ENUM == frozenset(
        {"deferral-rationale", "go-decision", "sprint-review", "scope-change", "adr-amendment"}
    )


def test_required_frontmatter_has_9_fields():
    assert len(REQUIRED_FRONTMATTER) == 9
    assert "id" in REQUIRED_FRONTMATTER
    assert "supersedes" not in REQUIRED_FRONTMATTER  # optional


def test_required_sections_count():
    """6 hand-written sections (per design D8): §1 §2 §3 §9 §10 §11."""
    assert len(REQUIRED_SECTIONS) == 6
    assert "## 1." in REQUIRED_SECTIONS
    assert "## 11." in REQUIRED_SECTIONS


def test_optional_sections_includes_only_5():
    assert "## 5." in OPTIONAL_SECTIONS
    assert len(OPTIONAL_SECTIONS) == 1


# ---------------------------------------------------------------------------
# N/A format regex
# ---------------------------------------------------------------------------


def test_na_pattern_accepts_well_formed():
    text = "## 10. next_sprint_candidates\nN/A — objective 维持 v3.2 deferred\n"
    assert NA_PATTERN.search(text) is not None


def test_na_pattern_rejects_plain_na():
    text = "## 10. next_sprint_candidates\nN/A\n"
    assert NA_PATTERN.search(text) is None


def test_na_pattern_requires_text_after_em_dash():
    text = "## 10. next_sprint_candidates\nN/A —\n"
    assert NA_PATTERN.search(text) is None


def test_na_pattern_accepts_multiple_na_lines():
    text = "N/A — reason one\nN/A — reason two\n"
    matches = NA_PATTERN.findall(text)
    assert len(matches) == 2


def test_is_na_format_helper():
    assert is_na_format("N/A — valid reason here") is True
    assert is_na_format("N/A") is False
    assert is_na_format("") is False
    assert is_na_format("regular content") is False


# ---------------------------------------------------------------------------
# parse_objective — happy path + error paths
# ---------------------------------------------------------------------------


def _write_objective(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "objective-test.md"
    p.write_text(content, encoding="utf-8")
    return p


VALID_OBJECTIVE = """---
id: objective-test
status: active
created: 2026-09-22
last_revised: 2026-09-22
review_by: 2026-12-21
owner: rdd-planner
priority: P1
manual_deps: []
supersedes: null
theme: Test objective for unit tests
---

# Objective: objective-test

## 1. 驱动诊断（Why now）
Test content for section 1.

## 2. 目标愿景 + 完成判据
- Done when criterion 1
- Done when criterion 2

## 3. 架构依据
ADR-0000

## 5. 反例
Test anti-pattern.

## 9. 目标依赖与 Decision Gate
### 9.1 前置 objective 依赖
None

### 9.2 Go / No-Go Decision Gate
Test criterion

## 10. next_sprint_candidates
- TODO candidate 1

## 11. 跟踪台账（append-only）
| Sprint | kind | 内容 | Decision/调整 | 原因 |
|--------|------|------|---------------|------|
| sprint-2026-09 | sprint-review | objective created | — | initial |
| sprint-2026-09 | scope-change | Added criterion 2 | accept | feedback |
"""


def test_parse_happy_path(tmp_path):
    p = _write_objective(tmp_path, VALID_OBJECTIVE)
    data = parse_objective(p)
    assert data["frontmatter"]["id"] == "objective-test"
    assert data["frontmatter"]["status"] == "active"
    assert data["frontmatter"]["priority"] == "P1"
    assert data["frontmatter"]["owner"] == "rdd-planner"
    assert data["sections"]["## 1."].startswith("Test content")
    assert data["sections"]["## 5."].startswith("Test anti-pattern")
    assert len(data["ledger_rows"]) == 2
    assert data["ledger_rows"][0]["kind"] == "sprint-review"
    assert data["ledger_rows"][1]["kind"] == "scope-change"


def test_parse_missing_frontmatter(tmp_path):
    p = _write_objective(tmp_path, "# Objective without frontmatter\n\n## 1. ...\n")
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_objective(p)


def test_parse_malformed_frontmatter(tmp_path):
    bad = "---\nid: objective-test\n[unclosed bracket\n---\n## 1. ...\n"
    p = _write_objective(tmp_path, bad)
    with pytest.raises(ValueError, match="invalid YAML"):
        parse_objective(p)


def test_parse_optional_section_5_missing(tmp_path):
    """Per design D8, §5 is optional. Missing should not raise."""
    no_section_5 = VALID_OBJECTIVE.replace("## 5. 反例\nTest anti-pattern.\n\n", "")
    p = _write_objective(tmp_path, no_section_5)
    data = parse_objective(p)
    assert data["sections"]["## 5."] == ""
    # Should validate cleanly
    errors = validate_objective(data)
    assert not any("## 5." in e for e in errors)


def test_parse_required_section_1_missing(tmp_path):
    no_section_1 = VALID_OBJECTIVE.replace("## 1. 驱动诊断（Why now）\nTest content for section 1.\n\n", "")
    p = _write_objective(tmp_path, no_section_1)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("## 1." in e for e in errors)


# ---------------------------------------------------------------------------
# validate_objective
# ---------------------------------------------------------------------------


def test_validate_accepts_valid_objective(tmp_path):
    p = _write_objective(tmp_path, VALID_OBJECTIVE)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert errors == []


def test_validate_rejects_invalid_status(tmp_path):
    bad = VALID_OBJECTIVE.replace("status: active", "status: bogus-state")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("invalid status" in e for e in errors)


def test_validate_rejects_invalid_priority(tmp_path):
    bad = VALID_OBJECTIVE.replace("priority: P1", "priority: P9")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("invalid priority" in e for e in errors)


def test_validate_rejects_wrong_owner(tmp_path):
    bad = VALID_OBJECTIVE.replace("owner: rdd-planner", "owner: rdd-builder")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("owner" in e for e in errors)


def test_validate_rejects_non_list_manual_deps(tmp_path):
    bad = VALID_OBJECTIVE.replace("manual_deps: []", "manual_deps: \"some-string\"")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("manual_deps" in e for e in errors)


def test_validate_rejects_non_iso_date(tmp_path):
    bad = VALID_OBJECTIVE.replace("created: 2026-09-22", "created: 09/22/2026")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("created" in e and "ISO" in e for e in errors)


def test_validate_rejects_invalid_kind_in_ledger(tmp_path):
    bad = VALID_OBJECTIVE.replace("| sprint-2026-09 | sprint-review |", "| sprint-2026-09 | unknown-kind |")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("kind" in e for e in errors)


def test_validate_rejects_plain_na_in_section_10(tmp_path):
    """Per design D9, plain 'N/A' without em-dash reason fails."""
    bad = VALID_OBJECTIVE.replace("- TODO candidate 1", "N/A")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert any("N/A" in e for e in errors)


def test_validate_accepts_na_with_reason_in_section_10(tmp_path):
    """Per design D9, 'N/A — <reason>' format is accepted."""
    bad = VALID_OBJECTIVE.replace("- TODO candidate 1", "N/A — objective 维持 v3.2 deferred 决策")
    p = _write_objective(tmp_path, bad)
    data = parse_objective(p)
    errors = validate_objective(data)
    assert not any("N/A" in e for e in errors)


# ---------------------------------------------------------------------------
# grace_period_exceeded
# ---------------------------------------------------------------------------


def test_grace_exceeded_active_with_past_review_by(tmp_path):
    p = _write_objective(tmp_path, VALID_OBJECTIVE)
    data = parse_objective(p)
    # Make review_by in the past
    data["frontmatter"]["review_by"] = "2020-01-01"
    data["frontmatter"]["status"] = "active"
    assert grace_period_exceeded(data, today=date(2026, 9, 22)) is True


def test_grace_not_exceeded_active_with_future_review_by(tmp_path):
    p = _write_objective(tmp_path, VALID_OBJECTIVE)
    data = parse_objective(p)
    data["frontmatter"]["review_by"] = "2099-12-31"
    assert grace_period_exceeded(data, today=date(2026, 9, 22)) is False


def test_grace_not_exceeded_for_completed(tmp_path):
    """Completed objectives should not trigger grace warning."""
    p = _write_objective(tmp_path, VALID_OBJECTIVE)
    data = parse_objective(p)
    data["frontmatter"]["review_by"] = "2020-01-01"
    data["frontmatter"]["status"] = "completed"
    assert grace_period_exceeded(data, today=date(2026, 9, 22)) is False


def test_grace_not_exceeded_for_archived(tmp_path):
    """Archived objectives should not trigger grace warning."""
    p = _write_objective(tmp_path, VALID_OBJECTIVE)
    data = parse_objective(p)
    data["frontmatter"]["review_by"] = "2020-01-01"
    data["frontmatter"]["status"] = "archived"
    assert grace_period_exceeded(data, today=date(2026, 9, 22)) is False


# ---------------------------------------------------------------------------
# derive_associations (Phase 1 stub)
# ---------------------------------------------------------------------------


def test_derive_associations_returns_empty_for_new_objective(tmp_path):
    p = _write_objective(tmp_path, VALID_OBJECTIVE)
    data = parse_objective(p)
    assoc = derive_associations(data)
    assert assoc["features"] == []
    assert assoc["changes"] == []
    assert assoc["objectives"] == []


def test_derive_associations_returns_manual_deps(tmp_path):
    content = VALID_OBJECTIVE.replace("manual_deps: []", 'manual_deps: ["objective-other"]')
    p = _write_objective(tmp_path, content)
    data = parse_objective(p)
    assoc = derive_associations(data)
    assert assoc["objectives"] == ["objective-other"]
