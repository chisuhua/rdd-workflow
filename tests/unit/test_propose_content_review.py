"""Tests for propose_content_review module."""
import json
import os
import pytest
from skills._lib.propose_content_review import (
    build_oracle_prompt,
    parse_oracle_response,
    write_review,
    should_skip,
    REVIEW_DIMENSIONS,
)


SAMPLE_PROPOSAL = """
## 架构依据
- ADR-022: Stream 管道操作符设计决策

## 范围
- **In Scope**:
  - 实现 m2sPipe/s2mPipe 操作符
  - 修改 stream_operators.h
- **Out Scope**:
  - 不修改 FIFO/Arbiter

## 验收标准
- 3 个操作符编译通过
- 4 个 Catch2 测试覆盖
"""


SAMPLE_ORACLE_RESPONSE = """{
  "scope_clarity": {"score": 4, "evidence": "In Scope and Out Scope are listed with specific items", "suggestion": ""},
  "adr_relevance": {"score": 3, "evidence": "ADR-022 is cited but no ADR number for scope boundary", "suggestion": "Add ADR reference for Stream base class architecture"},
  "acceptance_criteria_testability": {"score": 5, "evidence": "All criteria are concrete and measurable", "suggestion": ""},
  "scope_boundary_reasonableness": {"score": 4, "evidence": "Scope edges are clear with explicit Out Scope items", "suggestion": ""},
  "overall_rating": "pass",
  "summary": "Well-structured proposal with clear scope and testable criteria."
}"""


class TestBuildOraclePrompt:
    def test_includes_proposal_text(self):
        prompt = build_oracle_prompt(SAMPLE_PROPOSAL)
        assert "ADR-022" in prompt
        assert "m2sPipe" in prompt
        assert "scope_clarity" in prompt
        assert "adr_relevance" in prompt

    def test_mentions_all_4_dimensions(self):
        prompt = build_oracle_prompt(SAMPLE_PROPOSAL)
        for dim in REVIEW_DIMENSIONS:
            assert dim in prompt

    def test_requests_json_output(self):
        prompt = build_oracle_prompt(SAMPLE_PROPOSAL)
        assert "JSON" in prompt or "json" in prompt


class TestParseOracleResponse:
    def test_parses_valid_json(self):
        result = parse_oracle_response(SAMPLE_ORACLE_RESPONSE)
        assert result is not None
        assert result["overall_rating"] == "pass"
        assert result["scope_clarity"]["score"] == 4

    def test_handles_code_fence(self):
        wrapped = f"```json\n{SAMPLE_ORACLE_RESPONSE}\n```"
        result = parse_oracle_response(wrapped)
        assert result is not None
        assert result["overall_rating"] == "pass"

    def test_returns_none_on_bad_json(self):
        result = parse_oracle_response("this is not json")
        assert result is None


class TestWriteReview:
    def test_writes_json_file(self, tmp_path):
        output = str(tmp_path / "review.json")
        review = {
            "scope_clarity": {"score": 4, "evidence": "clear", "suggestion": ""},
            "overall_rating": "pass",
            "summary": "Good proposal.",
        }
        write_review(review, output_path=output, change_name="test-change")
        assert os.path.exists(output)
        with open(output) as f:
            data = json.load(f)
        assert data["change_name"] == "test-change"
        assert data["overall_rating"] == "pass"

    def test_creates_dirs(self, tmp_path):
        nested = str(tmp_path / "a" / "b" / "review.json")
        write_review({}, output_path=nested)
        assert os.path.exists(nested)


class TestShouldSkip:
    def test_skips_when_env_set(self, monkeypatch):
        monkeypatch.setenv("SKIP_CONTENT_REVIEW", "yes")
        assert should_skip() is True

    def test_does_not_skip_when_unset(self, monkeypatch):
        monkeypatch.delenv("SKIP_CONTENT_REVIEW", raising=False)
        assert should_skip() is False

    def test_skips_on_1_and_true(self, monkeypatch):
        for val in ("1", "true", "TRUE"):
            monkeypatch.setenv("SKIP_CONTENT_REVIEW", val)
            assert should_skip() is True