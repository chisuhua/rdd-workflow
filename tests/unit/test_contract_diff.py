"""Unit tests for contract_diff.DiffEngine."""
import json
import tempfile
from pathlib import Path
import pytest

from skills._lib.contract_diff import DiffEngine, DiffResult, format_output, SEVERITY_LEVELS


@pytest.fixture
def hub_contract(tmp_path):
    """Hub OpenAPI contract defining /login requires email+password."""
    p = tmp_path / "auth-v2.yaml"
    p.write_text("""\
openapi: 3.0.0
info:
  title: Auth V2
  version: 2.0.0
paths:
  /v2/login:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email: {type: string}
                password: {type: string}
""")
    return p


@pytest.fixture
def local_impl_ok(tmp_path):
    p = tmp_path / "auth_impl.py"
    p.write_text("""\
def login(payload):
    email = payload.get('email')
    password = payload.get('password')
    if not email or not password:
        raise ValueError('missing field')
    return True
""")
    return p


@pytest.fixture
def local_impl_broken(tmp_path):
    p = tmp_path / "auth_impl.py"
    p.write_text("""\
def login(payload):
    password = payload.get('password')
    return True
""")
    return p


def test_breaking_change_detected(hub_contract, local_impl_broken):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_broken)
    assert isinstance(result, DiffResult)
    assert result.severity in ("Breaking-Change", "High")
    assert len(result.diffs) >= 1


def test_no_diff_when_compliant(hub_contract, local_impl_ok):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_ok)
    assert result.severity in ("No-Diff", "Low")


def test_format_output_json(hub_contract, local_impl_broken):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_broken)
    output = format_output(result, format="json")
    parsed = json.loads(output)
    assert "severity" in parsed
    assert "diffs" in parsed


def test_format_output_markdown(hub_contract, local_impl_broken):
    engine = DiffEngine()
    result = engine.run(hub_contract, local_impl_broken)
    output = format_output(result, format="markdown")
    assert "# Contract Diff Report" in output


def test_severity_levels():
    """Severity classifier returns expected enum values."""
    assert "Breaking-Change" in SEVERITY_LEVELS
    assert "No-Diff" in SEVERITY_LEVELS
