"""Tests for StateVector — unified workflow state with file lock + schema validation."""
import json
import os
import time
import subprocess
import pytest
from skills._lib.state_vector import StateVector, StateVectorError


@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / "state-vector.json")


def test_create_default_returns_valid_state():
    """`create_default()` returns a fully-populated state matching the schema."""
    sv = StateVector.create_default()
    jsonschema = __import__("jsonschema")
    schema_path = os.path.join(os.path.dirname(__file__), "../../skills/_lib/schemas/state_vector_schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    jsonschema.validate(sv.to_dict(), schema)
    assert sv.to_dict()["version"] == "2.0"
    assert sv.to_dict()["metadata"]["spec_workflow_version"]


def test_roundtrip_via_save_and_load(state_path):
    """Save → load must preserve all fields."""
    sv = StateVector.create_default()
    sv.update_field("goal", "implement state vector")
    sv.save(state_path)
    loaded = StateVector.load(state_path)
    assert loaded.get_field("goal") == "implement state vector"


def test_load_nonexistent_returns_default(state_path):
    """Loading from a missing file returns a default state."""
    assert not os.path.exists(state_path)
    sv = StateVector.load(state_path)
    assert sv.to_dict()["version"] == "2.0"


def test_update_field_supports_nested_keys(state_path):
    """update_field with dotted path updates nested fields."""
    sv = StateVector.create_default()
    sv.update_field("loop_state.iteration", 5)
    sv.update_field("metadata.git_commit", "abc123")
    sv.save(state_path)
    loaded = StateVector.load(state_path)
    assert loaded.get_field("loop_state.iteration") == 5
    assert loaded.get_field("metadata.git_commit") == "abc123"


def test_invalid_schema_rejected_on_save(state_path):
    """Saving an invalid state (missing required field) must raise."""
    sv = StateVector.create_default()
    # Corrupt by removing a required field via direct mutation of internal dict
    sv._data["version"] = "1.0"  # violates `const: "2.0"`
    with pytest.raises(StateVectorError, match="schema"):
        sv.save(state_path)


def test_corruption_detected_via_checksum(state_path):
    """Manually corrupted file (bad checksum) is detected on load."""
    sv = StateVector.create_default()
    sv.save(state_path)
    # Manually corrupt the file
    with open(state_path, "r") as f:
        data = f.read()
    corrupted = data.replace('"2.0"', '"2.1"')
    with open(state_path, "w") as f:
        f.write(corrupted)
    # load() should raise or fall back — depending on policy; here we require it raise
    with pytest.raises(StateVectorError, match="checksum"):
        StateVector.load(state_path, verify_checksum=True)


def test_file_size_under_50kb(state_path):
    """A fresh state vector must be well under 50KB."""
    sv = StateVector.create_default()
    sv.save(state_path)
    size = os.path.getsize(state_path)
    assert size < 50_000, f"State vector too large: {size} bytes"


def test_read_write_latency_under_10ms(state_path):
    """Save + load roundtrip on local FS must take < 10ms (after first warmup)."""
    sv = StateVector.create_default()
    # Warmup
    sv.save(state_path)
    StateVector.load(state_path)
    # Measure
    start = time.perf_counter()
    for _ in range(100):
        sv.save(state_path)
        StateVector.load(state_path)
    elapsed = time.perf_counter() - start
    per_op = elapsed / 100
    assert per_op < 0.010, f"Roundtrip too slow: {per_op*1000:.2f}ms (must be < 10ms)"


def test_concurrent_writes_are_serialized(state_path):
    """Two processes writing simultaneously must not corrupt the file."""
    code = f"""
import sys
sys.path.insert(0, '.')
from skills._lib.state_vector import StateVector
sv = StateVector.create_default()
for i in range(50):
    sv.update_field('loop_state.iteration', i)
    sv.save('{state_path}')
"""
    p1 = subprocess.Popen(["python3", "-c", code], cwd=".")
    p2 = subprocess.Popen(["python3", "-c", code], cwd=".")
    p1.wait(timeout=30)
    p2.wait(timeout=30)
    # File must still load successfully
    loaded = StateVector.load(state_path)
    assert loaded.get_field("loop_state.iteration") >= 0
