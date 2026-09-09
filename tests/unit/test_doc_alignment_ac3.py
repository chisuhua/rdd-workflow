"""AC-1, AC-2, AC-3, AC-4: spec §3.2 / §3.4 alignment after correction.

Per fix-v4-rdd-planner-scope-over-assignment Tasks 5, 6, 7, 8, 9, 10 (A1-A9).
"""
import re
from pathlib import Path

SPEC = Path("docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md")
PLANNER_SKILL = Path("skills/rdd-planner/SKILL.md")
BUILDER_SKILL = Path("skills/rdd-builder/SKILL.md")
ADR_0025 = Path("docs/adr/ADR-0025-design-proposal-creation.md")
ADR_0038 = Path("docs/adr/ADR-0038-rdd-planner-crosscutting.md")


def test_ac1_section_3_2_row_165_no_proposal_md_authoring():
    """AC-1: spec §3.2 row 165 MUST NOT contain 'proposal.md` (authoring only...'."""
    text = SPEC.read_text()
    matches = re.findall(r"\|\s*\*\*rdd-planner\*\*[^|]*\|[^|]*\|", text)
    assert matches, "couldn't find rdd-planner row in spec §3.2"
    row_text = matches[0]
    assert "(authoring only" not in row_text, \
        f"AC-1 violated: row 165 still has proposal.md authoring: {row_text}"
    assert "proposal.md" not in row_text, \
        f"AC-1 violated: row 165 still mentions proposal.md: {row_text}"


def test_ac2_section_3_2_row_166_builder_owns_proposal_md():
    """AC-2: spec §3.2 row 166 (rdd-builder) MUST add 'proposal.md (authoring via P0 approve, per ADR-0025)'."""
    text = SPEC.read_text()
    assert "proposal.md (authoring via P0 approve" in text, \
        "AC-2 violated: spec doesn't mention 'authoring via P0 approve'"


def test_ac3_section_3_4_phase_0_input():
    """AC-3: spec §3.4 Phase 0 input MUST mention 'authored at P0 approve'."""
    text = SPEC.read_text()
    assert "proposal.md (authored at P0 approve" in text, \
        "AC-3 violated: spec §3.4 doesn't mention authored at P0 approve"


def test_ac4_section_9_no_scaffold_contradiction():
    """AC-4: spec §9 demo MUST NOT contain 'rddf planner (new|brainstorm|accept) ... scaffold ... tasks'."""
    text = SPEC.read_text()
    pattern = re.compile(r"rddf planner (new|brainstorm|accept).*scaffold.*tasks", re.DOTALL)
    matches = pattern.findall(text)
    assert not matches, f"AC-4 violated: §9 demo still has 'planner accept scaffold tasks': {matches}"


def test_ac6_planner_skill_md_owns_excludes_proposal_md():
    """AC-6: rdd-planner SKILL.md role.owns MUST NOT include proposal.md; not_owns MUST."""
    text = PLANNER_SKILL.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert m, "no YAML frontmatter in rdd-planner SKILL.md"
    fm = m.group(1)
    owns_match = re.search(r"owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    not_owns_match = re.search(r"not_owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    assert owns_match, "no owns block found"
    assert not_owns_match, "no not_owns block found"
    owns_text = owns_match.group(1)
    not_owns_text = not_owns_match.group(1)
    assert "openspec/changes/<name>/proposal.md" not in owns_text, \
        f"AC-6 violated: proposal.md still in owns: {owns_text}"
    assert "openspec/changes/<name>/proposal.md" in not_owns_text, \
        f"AC-6 violated: proposal.md NOT in not_owns: {not_owns_text}"


def test_ac7_builder_skill_md_owns_includes_proposal_md():
    """AC-7: rdd-builder SKILL.md role.owns MUST include 'openspec/changes/<name>/proposal.md' (authoring via P0 approve, per ADR-0025)."""
    text = BUILDER_SKILL.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert m, "no YAML frontmatter in rdd-builder SKILL.md"
    fm = m.group(1)
    owns_match = re.search(r"owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    not_owns_match = re.search(r"not_owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    assert owns_match and not_owns_match, "couldn't find both blocks"
    owns_text = owns_match.group(1)
    not_owns_text = not_owns_match.group(1)
    assert any("proposal.md" in line and "P0 approve" in line for line in owns_text.split("\n")), \
        f"AC-7 violated: proposal.md (with P0 approve) NOT in owns: {owns_text}"
    assert "openspec/changes/<name>/proposal.md" not in not_owns_text, \
        f"AC-7 violated: proposal.md still in not_owns: {not_owns_text}"


def test_ac8_adr_0025_evolution_note():
    """AC-8: ADR-0025 MUST contain evolution note referencing v4/ADR-0043/rdd-builder P0."""
    pattern = re.compile(r"(v4|ADR-0043|rdd-builder P0)")
    matches = pattern.findall(ADR_0025.read_text())
    assert matches, "AC-8 violated: ADR-0025 lacks evolution note mentioning v4/ADR-0043/rdd-builder P0"


def test_ac9_adr_0038_amendment():
    """AC-9: ADR-0038 MUST contain amendment marker (superseded/amended/dual identity/ADR-0043)."""
    pattern = re.compile(r"(superseded|amended|双重身份|dual identity|ADR-0043)")
    matches = pattern.findall(ADR_0038.read_text())
    assert matches, "AC-9 violated: ADR-0038 lacks amendment marker"
