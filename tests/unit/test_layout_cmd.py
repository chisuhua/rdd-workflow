"""Unit tests for the `rddf layout --json` manifest view.

The payload is the *declared* layout (the product's definition), not a scan
of the current tree — that is the doctor's job. Two runs must be
byte-identical so consumers can diff them.
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(cwd: Path) -> str:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(cwd),
        "RDDF_PROJECT_ROOT": str(cwd),
        "PYTHONPATH": str(PROJECT_ROOT),
    }
    res = subprocess.run(
        [sys.executable, "-m", "_lib.cli", "layout", "--json"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, env=env, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return res.stdout


def test_layout_json_payload_shape(tmp_path):
    payload = json.loads(_run(tmp_path))
    assert payload["schema_version"] == 1
    assert payload["tool_version"]
    assert isinstance(payload["entries"], list)
    assert payload["entries"], "清单不应为空"
    assert payload["entries"] == sorted(payload["entries"], key=lambda e: e["path"])


def test_layout_json_has_no_timestamp(tmp_path):
    """输出确定性：两次运行字节一致，且不含时间戳字段。"""
    a = _run(tmp_path)
    b = _run(tmp_path)
    assert a == b
    assert "timestamp" not in a


def test_layout_json_runs_outside_a_project(tmp_path):
    """`.rddf/` 不存在时也能跑 —— 清单是产品定义，与项目状态无关。"""
    payload = json.loads(_run(tmp_path))
    assert payload["entries"], "清单是声明的默认布局，不随项目状态变化"


def test_layout_json_entries_carry_the_contract_fields(tmp_path):
    payload = json.loads(_run(tmp_path))
    for e in payload["entries"]:
        assert set(e) == {
            "path", "kind", "read_by", "write_by",
            "required_when", "transient", "class", "severity",
        }
        assert e["class"] in ("runtime-only", "committed")
