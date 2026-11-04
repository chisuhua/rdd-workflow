"""populate 的 schema 路径必须解析到仓库内的真实文件，且校验**真的执行**。

背景：`populate_lib.py` 曾用 `Path(__file__).resolve().parents[2]` 拼 schema 路径，
解析到**仓库的父目录** → `exists() == False` → jsonschema 校验被静默跳过
（只走 stdlib 手工兜底）。本文件锁住两件事：路径存在、校验走的是 jsonschema 分支。
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _minimal_payload() -> dict:
    """满足 stdlib 手工兜底（required keys + version const）的最小 payload。"""
    return {
        "version": 2,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "codebase_commit": "0" * 40,
        "adrs": {},
        "reverse_index": {},
        "phases": {},
    }


def test_state_schema_path_resolves_to_real_file():
    from _lib.populate_lib import _populate_state_schema_path

    path = _populate_state_schema_path()
    assert path.is_file(), f"schema 路径未解析到真实文件：{path}"
    assert path.name == "populate_state_schema.json"
    assert REPO_ROOT in path.parents


def test_supplementary_schema_path_resolves_to_real_file():
    """`populate_supplementary` 的 schema 同样必须解析到仓库内。"""
    source = (REPO_ROOT / "_lib" / "populate_lib.py").read_text(encoding="utf-8")
    assert "populate_supplementary_schema.json" in source

    candidate = REPO_ROOT / "_lib" / "schemas" / "populate_supplementary_schema.json"
    assert candidate.is_file(), candidate
    json.loads(candidate.read_text(encoding="utf-8"))


def test_jsonschema_branch_actually_runs():
    """构造一个「过手工兜底、但违 jsonschema」的 payload → 必须返回错误。

    手工兜底只查 required keys + version const；jsonschema 还会查类型。
    `adrs` 在 schema 里是 object-of-object（每项 additionalProperties=false），
    所以 `{"adrs": {"ADR-0001": {"bogus": 1}}}` 过得了手工兜底、过不了 jsonschema。
    若返回 None → 说明校验仍在被静默跳过。
    """
    from _lib.populate_lib import _validate_populate_state_payload

    payload = _minimal_payload()
    assert _validate_populate_state_payload(payload) is None, "最小合规 payload 应通过"

    bad = dict(payload)
    bad["adrs"] = {"ADR-0001": {"not_a_real_field": 1}}
    error = _validate_populate_state_payload(bad)
    assert error is not None, "违 schema 的 payload 必须被 jsonschema 拦下（否则说明校验被跳过）"
    assert isinstance(error, str)


def test_minimal_payload_is_schema_valid():
    """最小合规 payload 必须真的过 jsonschema（不是只过手工兜底）。"""
    import jsonschema

    schema = json.loads(
        (REPO_ROOT / "_lib" / "schemas" / "populate_state_schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(_minimal_payload(), schema)
