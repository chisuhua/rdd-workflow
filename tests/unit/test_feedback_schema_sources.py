"""feedback source 的 schema enum 必须与运行时 VALID_SOURCES 完全一致。"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_feedback_schema_sources_match_runtime():
    from skills._lib.feedback_appender import VALID_SOURCES

    schema = json.loads(
        (REPO_ROOT / "_lib/schemas/feedback_entry_schema.json").read_text(encoding="utf-8")
    )
    enum = set(schema["properties"]["source"]["enum"])
    assert enum == VALID_SOURCES, f"schema={sorted(enum)} runtime={sorted(VALID_SOURCES)}"


def test_schema_sources_include_all_v4_stages():
    """v4 阶段名必须可写入（否则按 schema 校验的外部消费者会拒）。"""
    schema = json.loads(
        (REPO_ROOT / "_lib/schemas/feedback_entry_schema.json").read_text(encoding="utf-8")
    )
    enum = set(schema["properties"]["source"]["enum"])
    assert {"rdd-arch", "rdd-planner", "rdd-builder", "rdd-verifier"} <= enum
