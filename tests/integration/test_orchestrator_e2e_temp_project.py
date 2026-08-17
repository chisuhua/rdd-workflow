"""End-to-end orchestrator tests with temporary project setup.

Creates a minimal git repo + openspec structure to exercise orchestrator
in realistic phase scenarios.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest


@pytest.fixture
def temp_project(tmp_path):
    """Create a minimal git repo with openspec structure."""
    proj = tmp_path / "test-project"
    proj.mkdir()
    
    # Git init
    subprocess.run(["git", "init"], cwd=proj, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=proj,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=proj,
        check=True,
        capture_output=True,
    )
    
    # Minimal openspec structure
    (proj / "openspec").mkdir()
    (proj / "openspec" / "changes").mkdir()
    (proj / "openspec" / "changes" / "archive").mkdir()
    (proj / "openspec" / "specs").mkdir()
    
    # Minimal docs
    (proj / "docs").mkdir()
    (proj / "docs" / "adr").mkdir()
    (proj / "roadmap.md").write_text("# Roadmap\n\nPlaceholder\n")
    
    # .rddf state
    (proj / ".rddf").mkdir()
    (proj / ".rddf" / "state").mkdir()
    trace_dir = proj / ".rddf" / "state" / "trace"
    trace_dir.mkdir()
    
    # Initial commit
    subprocess.run(["git", "add", "."], cwd=proj, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=proj,
        check=True,
        capture_output=True,
    )
    
    return proj


def test_orchestrator_subprocess_in_temp_project(temp_project):
    """Run orchestrate subprocess in a temp project context."""
    trace_dir = temp_project / ".rddf" / "state" / "trace"
    
    env = os.environ.copy()
    env.update({
        "RDDF_USE_ORCHESTRATOR": "yes",
        "RDDF_PHASE": "test-phase",
        "RDDF_TRACE_DIR": str(trace_dir),
        "RDDF_PROJECT_ROOT": str(temp_project),
        # Lock to legacy capture mode (ADR-0027 §1.0.1) so the trace contains
        # exactly one `subprocess` event. Default `tee` mode emits `reader_chunk`
        # events first (commit d089ca0), which would change events[0] from
        # `subprocess` to `reader_chunk`. This test's intent — "verify trace
        # has a subprocess event with returncode=0" — is independent of mode.
        "RDDF_ORCHESTRATOR_CAPTURE": "capture",
    })
    
    result = subprocess.run(
        [sys.executable, "-m", "skills._lib.cli", "orchestrate", "subprocess", "echo", "test"],
        cwd=temp_project,
        env=env,
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0
    traces = list(trace_dir.glob("*.jsonl"))
    assert len(traces) == 1
    
    events = [json.loads(line) for line in traces[0].read_text().splitlines() if line]
    assert events[0]["type"] == "subprocess"
    assert events[0]["returncode"] == 0


def test_stale_trace_sweep_in_temp_project(temp_project):
    """Verify sweep detects and reports stale trace in temp project."""
    trace_dir = temp_project / ".rddf" / "state" / "trace"
    issues_dir = temp_project / ".rddf" / "issues"
    issues_dir.mkdir()
    
    env = os.environ.copy()
    env.update({
        "RDDF_USE_ORCHESTRATOR": "yes",
        "RDDF_PHASE": "test-phase",
        "RDDF_TRACE_DIR": str(trace_dir),
        "RDDF_PROJECT_ROOT": str(temp_project),
        "RDDF_TRACE_STALE_MINUTES": "0",
    })
    
    # Step 1: create trace with subprocess
    subprocess.run(
        [sys.executable, "-m", "skills._lib.cli", "orchestrate", "subprocess", "echo", "step1"],
        cwd=temp_project,
        env=env,
        capture_output=True,
    )
    
    # Step 2: make trace look old
    trace_file = list(trace_dir.glob("*.jsonl"))[0]
    os.utime(trace_file, (1000000, 1000000))
    
    # Step 3: trigger sweep via new subprocess
    subprocess.run(
        [sys.executable, "-m", "skills._lib.cli", "orchestrate", "subprocess", "echo", "step2"],
        cwd=temp_project,
        env=env,
        capture_output=True,
    )
    
    # Verify: old trace deleted, new trace exists, issue created
    traces = list(trace_dir.glob("*.jsonl"))
    assert len(traces) == 1
    
    # Check last event is from step2
    events = [json.loads(line) for line in traces[0].read_text().splitlines() if line]
    assert events[-1]["type"] == "subprocess"
    assert "step2" in str(events[-1]["cmd"])
    
    # Check issue file created
    issues = list(issues_dir.glob("phase-crash-*.md"))
    assert len(issues) == 1
    content = issues[0].read_text()
    assert "INTERRUPTED" in content or "phase-crash" in content


def test_finalize_closes_trace_in_temp_project(temp_project):
    """Verify finalize appends finalize event and enables graceful shutdown."""
    trace_dir = temp_project / ".rddf" / "state" / "trace"
    
    env = os.environ.copy()
    env.update({
        "RDDF_USE_ORCHESTRATOR": "yes",
        "RDDF_PHASE": "test-phase",
        "RDDF_TRACE_DIR": str(trace_dir),
        "RDDF_PROJECT_ROOT": str(temp_project),
    })
    
    # Step 1: subprocess
    subprocess.run(
        [sys.executable, "-m", "skills._lib.cli", "orchestrate", "subprocess", "echo", "work"],
        cwd=temp_project,
        env=env,
        capture_output=True,
    )
    
    # Step 2: finalize
    subprocess.run(
        [sys.executable, "-m", "skills._lib.cli", "orchestrate", "finalize"],
        cwd=temp_project,
        env=env,
        capture_output=True,
    )
    
    # Verify finalize event
    traces = list(trace_dir.glob("*.jsonl"))
    assert len(traces) == 1
    events = [json.loads(line) for line in traces[0].read_text().splitlines() if line]
    assert events[-1]["type"] == "finalize"
    assert events[-1]["subprocess_failures"] == 0
    
    # Step 3: sweep should NOT delete finalized trace (unless > 7 days old for GC)
    # Our trace is set to epoch 1000000 (1970), which triggers GC cleanup
    env["RDDF_TRACE_STALE_MINUTES"] = "0"
    os.utime(traces[0], (1000000, 1000000))
    
    subprocess.run(
        [sys.executable, "-m", "skills._lib.cli", "orchestrate", "subprocess", "echo", "new"],
        cwd=temp_project,
        env=env,
        capture_output=True,
    )
    
    # Old trace gets GC'd (> 7 days old), only new trace remains
    traces_after = list(trace_dir.glob("*.jsonl"))
    assert len(traces_after) == 1  # GC deleted old finalized trace, new unfinalized remains
