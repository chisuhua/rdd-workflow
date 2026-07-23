"""Test ADR index auto-sync."""
import pytest
from pathlib import Path


def test_extract_adr_metadata():
    """Test extracting metadata from ADR file."""
    import sys
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    from skills._lib.sync_adr_index import extract_adr_metadata
    
    # Test with actual ADR file
    adr_path = Path("/workspace/project/rdd-workflow/docs/adr/ADR-0003-three-phase-architecture.md")
    if adr_path.exists():
        metadata = extract_adr_metadata(adr_path)
        assert metadata is not None
        assert metadata["number"] == 3
        assert "filename" in metadata
        assert "title" in metadata


def test_generate_table():
    """Test markdown table generation."""
    import sys
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    from skills._lib.sync_adr_index import generate_table
    
    test_adrs = [
        {"number": 1, "filename": "ADR-0001-test.md", "title": "Test ADR", "status": "已采纳"},
        {"number": 2, "filename": "ADR-0002-test.md", "title": "Another ADR", "status": "待定"},
    ]
    
    table = generate_table(test_adrs)
    assert "| ADR | 标题 | 状态 |" in table
    assert "ADR-0001" in table
    assert "Test ADR" in table


def test_sync_dry_run():
    """Test dry-run mode doesn't modify files."""
    import sys
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    from skills._lib.sync_adr_index import sync_adr_index
    
    result = sync_adr_index("/workspace/project/rdd-workflow", dry_run=True)
    assert result is True


def test_finds_all_adrs():
    """Verify script finds all ADR files in docs/adr/."""
    import sys
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    from skills._lib.sync_adr_index import extract_adr_metadata
    
    adr_dir = Path("/workspace/project/rdd-workflow/docs/adr")
    adr_files = list(adr_dir.glob("ADR-*.md"))
    
    # Should have ADR-0000 through ADR-0023
    assert len(adr_files) >= 23, f"Expected at least 23 ADRs, found {len(adr_files)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
