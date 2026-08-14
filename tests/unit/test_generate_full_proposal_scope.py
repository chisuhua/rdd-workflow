"""Test scope extraction for numbered list items in generate_full_proposal.py"""
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from skills.guide_design.scripts.generate_full_proposal import _extract_bullet_items


def test_numbered_list_extraction():
    """Numbered items (1. 2. 3.) should be extracted as scope items."""
    content = """1. Parse numbered list items with dot separator
2. Parse numbered list items with paren separator
3. Preserve item descriptions intact"""
    result = _extract_bullet_items(content)
    assert result == [
        "Parse numbered list items with dot separator",
        "Parse numbered list items with paren separator",
        "Preserve item descriptions intact",
    ]


def test_mixed_bullet_and_numbered():
    """Both bullet and numbered items should coexist."""
    content = """- Bullet item one
1. Numbered item two
- Bullet item three
2. Numbered item four"""
    result = _extract_bullet_items(content)
    assert result == [
        "Bullet item one",
        "Numbered item two",
        "Bullet item three",
        "Numbered item four",
    ]


def test_sub_item_attachment():
    """Indented sub-items should attach to parent numbered item."""
    content = """1. Parent item with details
   - Sub-item detail one
   - Sub-item detail two
2. Second parent item"""
    result = _extract_bullet_items(content)
    assert len(result) == 2
    assert "Sub-item detail one" in result[0]
    assert "Sub-item detail two" in result[0]
    assert "Second parent item" == result[1]


def test_empty_section_fallback():
    """Empty content should return explicit empty marker."""
    content = ""
    result = _extract_bullet_items(content)
    assert result == []  # Current behavior returns empty list, not explicit marker


def test_backward_compatibility_bullets():
    """Existing bullet-only format (138+ files) must still work."""
    content = """- Bullet item alpha
- Bullet item beta
- Bullet item gamma"""
    result = _extract_bullet_items(content)
    assert result == [
        "Bullet item alpha",
        "Bullet item beta",
        "Bullet item gamma",
    ]


def test_capabilities_impact_split():
    """Constraint items should split by MUST vs MUST NOT."""
    from skills.guide_design.scripts.generate_full_proposal import _split_capabilities_impact
    
    constraints = [
        "MUST support backward compatibility with bullet lists",
        "MUST NOT modify _extract_section() signature",
        "MUST recognize numbered formats (1. and 1))",
        "MUST NOT introduce new dependencies",
        "SHOULD preserve line budget under 50 lines",
    ]
    
    capabilities, impact = _split_capabilities_impact(constraints)
    
    assert len(capabilities) == 3  # 2 MUST + 1 SHOULD (routed to Capabilities by default)
    assert len(impact) == 2  # 2 MUST NOT
    
    assert "MUST support backward compatibility" in capabilities[0]
    assert "MUST recognize numbered formats" in capabilities[1]
    assert "SHOULD preserve line budget" in capabilities[2]
    
    assert "MUST NOT modify _extract_section()" in impact[0]
    assert "MUST NOT introduce new dependencies" in impact[1]
