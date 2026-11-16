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


def test_layout_payload_is_not_shadowed_by_a_consumer_lib(tmp_path):
    """A consumer project with its own `_lib/` package must not shadow the manifest.

    `rddf.sh` puts the package root on PYTHONPATH, but `python3 -m` also puts
    the cwd first — a consumer that ships a top-level `_lib/` package could
    otherwise shadow the tool's own modules, and `rddf layout --json` would
    report the consumer's code instead of the product's declared layout.
    """
    consumer = tmp_path / "_lib" / "core"
    consumer.mkdir(parents=True)
    (tmp_path / "_lib" / "__init__.py").write_text("")
    (consumer / "__init__.py").write_text("")
    (consumer / "rddf_layout.py").write_text(
        "def as_dicts():\n    return [{'path': 'HIJACKED'}]\n"
    )
    code = (
        "from _lib.cli.layout_cmd import cmd_layout;"
        f"import sys; sys.path.insert(0, {str(tmp_path)!r});"
        "cmd_layout([])"
    )
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(tmp_path),
           "PYTHONPATH": str(PROJECT_ROOT)}
    res = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT,
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert len(payload["entries"]) == 14
    assert "HIJACKED" not in res.stdout
