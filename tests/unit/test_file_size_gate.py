"""Test file size quality gate."""
import pytest


def test_check_file_size_passes_small_files():
    """Files under limit should pass."""
    import sys
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    from skills._lib.arch_quality_gate import _check_file_size
    
    # Use a small project directory
    result = _check_file_size({"project_root": "/tmp"})
    assert result[0] is True  # Passes when no skills/_lib


def test_check_file_size_warns_large_files():
    """Files over 300 lines should trigger warning."""
    import sys
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    from skills._lib.arch_quality_gate import _check_file_size
    
    # This repo has large files in skills/_lib
    result = _check_file_size({"project_root": "/workspace/project/rdd-workflow"})
    # Should fail (with warning severity)
    assert result[0] is False
    assert result[1] == "warning"


def test_file_size_in_arch_quality_report():
    """File size check should be part of ArchQualityReport."""
    import sys
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    from skills._lib.arch_quality_gate import ArchQualityReport
    
    report = ArchQualityReport.verify("/workspace/project/rdd-workflow")
    assert "file_size_limit" in report.detail
    assert "adr_no_placeholders" in report.warnings or "file_size_limit" in report.warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
