"""Test hook symmetry (attach/detach, entry/close)."""
import pytest


def test_hook_function_count():
    """Verify all hook functions are present and symmetric."""
    import subprocess
    
    # Count hook functions in rddf_session_hooks.sh
    result = subprocess.run(
        ["grep", "-c", "^rddf_session_hook_", "skills/rddf-session/scripts/rddf_session_hooks.sh"],
        capture_output=True, text=True, cwd="/workspace/project/rdd-workflow"
    )
    
    # Should have: entry, close, heartbeat, attach, detach (5 hooks)
    count = int(result.stdout.strip())
    assert count == 5, f"Expected 5 hooks, found {count}"


def test_attach_detach_symmetry():
    """Verify attach and detach have matching signatures."""
    from pathlib import Path
    
    hooks_file = Path("skills/rddf-session/scripts/rddf_session_hooks.sh")
    content = hooks_file.read_text()
    
    # Both should accept <kind> <change_name>
    assert "rddf_session_hook_attach() {" in content
    assert "rddf_session_hook_detach() {" in content
    
    # Both should have same parameter pattern
    attach_params = content.split("rddf_session_hook_attach() {")[1].split("}")[0]
    detach_params = content.split("rddf_session_hook_detach() {")[1].split("}")[0]
    
    # Both use local kind and local change_name
    assert 'local kind="$1"' in attach_params
    assert 'local kind="$1"' in detach_params
    assert 'local change_name="$2"' in attach_params
    assert 'local change_name="$2"' in detach_params


def test_entry_close_symmetry():
    """Verify entry and close are inverses."""
    from pathlib import Path
    
    hooks_file = Path("skills/rddf-session/scripts/rddf_session_hooks.sh")
    content = hooks_file.read_text()
    
    assert "rddf_session_hook_entry() {" in content
    assert "rddf_session_hook_close() {" in content
    
    # entry creates, close marks completed
    assert "create_session" in content
    assert "completed" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
