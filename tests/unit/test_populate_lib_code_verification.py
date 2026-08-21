"""Unit tests for populate_lib code verification (v1.1+ feature: --code-verify flag).

Tests AdrCodeVerification dataclass, parse_symbols_from_adr_text,
verify_adr_by_code, verify_all_adrs, load/save_supplementary,
4 badge formatters, and _format_adr_block integration.
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "populate-roadmap-from-arch" / "scripts"))

from populate_lib import (  # noqa: E402
    AdrCodeVerification,
    AdrRecord,
    _format_badge_confirmed,
    _format_badge_placeholder_as_claimed,
    _format_badge_placeholder_but_exists,
    _format_badge_self_claim_only,
    _format_adr_block,
    load_supplementary_or_default,
    parse_symbols_from_adr_text,
    save_supplementary,
    verify_adr_by_code,
    verify_all_adrs,
)


# ---- Task 1: parse_symbols_from_adr_text ----

class TestParseSymbolsFromAdrText:
    def test_basic_backtick_patterns(self):
        text = """
        Use `parse_symbols()` helper and `AdrRecord` class.
        See `--code-verify` flag in CLI.
        """
        symbols = parse_symbols_from_adr_text(text)
        assert "parse_symbols()" in symbols
        assert "AdrRecord" in symbols
        assert "--code-verify" in symbols

    def test_filters_fenced_code_blocks(self):
        text = """
        Example:
        ```python
        def real_func(): pass
        ```
        But mention `helper_func()` outside the block.
        """
        symbols = parse_symbols_from_adr_text(text)
        assert "real_func" not in symbols
        assert "helper_func()" in symbols

    def test_extracts_python_def_and_class(self):
        text = """
        See def some_helper() and class SomeClass for details.
        Also `external_func()`.
        """
        symbols = parse_symbols_from_adr_text(text)
        assert "some_helper" in symbols
        assert "SomeClass" in symbols
        assert "external_func()" in symbols

    def test_dedupes_preserving_order(self):
        text = "`foo()` and `foo()` again, plus `bar`."
        symbols = parse_symbols_from_adr_text(text)
        assert symbols == ["foo()", "bar"]

    def test_empty_input(self):
        assert parse_symbols_from_adr_text("") == []


# ---- Task 1: AdrCodeVerification dataclass ----

class TestAdrCodeVerificationDataclass:
    def test_construct_with_all_fields(self):
        v = AdrCodeVerification(
            adr_id="ADR-0017",
            self_claim_version="v2.0.0+",
            code_symbols_found=["foo"],
            code_symbols_expected=["foo", "bar"],
            verification_status="confirmed",
            has_discrepancy=False,
            verified_at="2026-08-21T10:00:00Z",
            mcp_used=False,
        )
        assert v.adr_id == "ADR-0017"
        assert v.verification_status == "confirmed"
        assert v.has_discrepancy is False

    def test_self_claim_version_can_be_none(self):
        v = AdrCodeVerification(
            adr_id="ADR-0009",
            self_claim_version=None,
            code_symbols_found=[],
            code_symbols_expected=[],
            verification_status="placeholder-as-claimed",
            has_discrepancy=False,
            verified_at="2026-08-21T10:00:00Z",
            mcp_used=False,
        )
        assert v.self_claim_version is None


# ---- Task 2: verify_adr_by_code ----

class TestVerifyAdrByCode:
    def test_confirmed_when_all_symbols_found(self, tmp_path):
        (tmp_path / "foo.py").write_text("def helper_func(): pass\nclass MyClass: pass\n")
        adr = AdrRecord(
            id="ADR-0099", path=Path("docs/adr/ADR-0099-test.md"),
            title="Test ADR", status="已采纳", key_decision="Test",
            implementation_version="v2.0.0+",
        )
        result = verify_adr_by_code(adr, "Implements `helper_func()` and `MyClass`.", tmp_path)
        assert result.verification_status == "confirmed"
        assert result.has_discrepancy is False
        assert result.mcp_used is False

    def test_self_claim_only_when_below_threshold(self, tmp_path):
        (tmp_path / "real.py").write_text("def only_one(): pass\n")
        adr = AdrRecord(
            id="ADR-0098", path=Path("docs/adr/ADR-0098.md"),
            title="T", status="已采纳", key_decision="k",
            implementation_version="v2.0.0+",
        )
        adr_text = "See `only_one()`, `missing_two()`, and `missing_three()`."
        result = verify_adr_by_code(adr, adr_text, tmp_path)
        assert result.verification_status == "self-claim-only"
        assert result.has_discrepancy is True

    def test_placeholder_no_code(self, tmp_path):
        adr = AdrRecord(
            id="ADR-0097", path=Path("docs/adr/ADR-0097.md"),
            title="T", status="占位（v3.0 候选）", key_decision="k",
            implementation_version=None,
        )
        adr_text = "This is a placeholder. `nonexistent_symbol()` described."
        result = verify_adr_by_code(adr, adr_text, tmp_path)
        assert result.verification_status == "placeholder-as-claimed"
        assert result.has_discrepancy is False

    def test_placeholder_contradicts(self, tmp_path):
        (tmp_path / "real.py").write_text("def unexpected_symbol(): pass\n")
        adr = AdrRecord(
            id="ADR-0096", path=Path("docs/adr/ADR-0096.md"),
            title="T", status="占位（v3.0 候选）", key_decision="k",
            implementation_version=None,
        )
        adr_text = "This is a placeholder. `unexpected_symbol()` is mentioned."
        result = verify_adr_by_code(adr, adr_text, tmp_path)
        assert result.verification_status == "placeholder-but-exists"
        assert result.has_discrepancy is True


# ---- Task 3: verify_all_adrs parallel ----

class TestVerifyAllAdrsParallel:
    def test_parallel_returns_all_results(self, tmp_path):
        adrs = []
        for i in range(5):
            sym = f"func_{i}"
            (tmp_path / f"mod_{i}.py").write_text(f"def {sym}(): pass\n")
            adr = AdrRecord(
                id=f"ADR-{1000+i}", path=Path(f"docs/adr/ADR-{1000+i}.md"),
                title="T", status="已采纳", key_decision="k",
                implementation_version="v2.0.0+",
            )
            adrs.append((adr, f"See `{sym}()` in code.", tmp_path))

        start = time.time()
        results = verify_all_adrs(adrs, max_workers=4)
        elapsed = time.time() - start

        assert len(results) == 5
        assert elapsed < 5.0
        for r in results:
            assert r.verification_status == "confirmed"


# ---- Task 4: load_supplementary_or_default + save_supplementary ----

class TestLoadSupplementary:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = load_supplementary_or_default(tmp_path)
        assert result == {}

    def test_present_file_returns_parsed_records(self, tmp_path):
        state_dir = tmp_path / ".rddf" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / ".populate-supplementary.json").write_text(json.dumps({
            "version": 1,
            "generated_at": "2026-08-21T10:00:00Z",
            "records": [
                {"adr_id": "ADR-0017", "verification_status": "confirmed"}
            ]
        }))
        result = load_supplementary_or_default(tmp_path)
        assert "ADR-0017" in result
        assert result["ADR-0017"]["verification_status"] == "confirmed"

    def test_unsupported_version_returns_empty(self, tmp_path):
        state_dir = tmp_path / ".rddf" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / ".populate-supplementary.json").write_text(json.dumps({
            "version": 0,
            "generated_at": "2026-08-21T10:00:00Z",
            "records": []
        }))
        result = load_supplementary_or_default(tmp_path)
        assert result == {}


class TestSaveSupplementaryRoundtrip:
    def test_roundtrip_three_records(self, tmp_path):
        recs = [
            AdrCodeVerification(
                adr_id=f"ADR-{1000+i}", self_claim_version="v2.0.0+",
                code_symbols_found=[f"sym_{i}"], code_symbols_expected=[f"sym_{i}"],
                verification_status="confirmed", has_discrepancy=False,
                verified_at="2026-08-21T10:00:00Z", mcp_used=False,
            )
            for i in range(3)
        ]
        save_supplementary(recs, tmp_path)
        state_file = tmp_path / ".rddf" / "state" / ".populate-supplementary.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["version"] == 1
        assert len(data["records"]) == 3
        for orig, written in zip(recs, data["records"]):
            assert orig.adr_id == written["adr_id"]
            assert orig.verification_status == written["verification_status"]
            assert orig.code_symbols_found == written["code_symbols_found"]


# ---- Task 5: JSON Schema v1 ----

class TestSchemaValidation:
    def test_schema_file_exists(self):
        schema_path = (
            Path(__file__).resolve().parents[2]
            / "skills" / "_lib" / "schemas" / "populate_supplementary_schema.json"
        )
        assert schema_path.exists(), f"Schema not found at {schema_path}"

    def test_schema_validates_written_payload(self, tmp_path):
        import jsonschema

        schema_path = (
            Path(__file__).resolve().parents[2]
            / "skills" / "_lib" / "schemas" / "populate_supplementary_schema.json"
        )
        recs = [AdrCodeVerification(
            adr_id="ADR-0017", self_claim_version="v2.0.0+",
            code_symbols_found=["foo"], code_symbols_expected=["foo", "bar"],
            verification_status="confirmed", has_discrepancy=False,
            verified_at="2026-08-21T10:00:00Z", mcp_used=False,
        )]
        save_supplementary(recs, tmp_path)
        written = json.loads(
            (tmp_path / ".rddf/state/.populate-supplementary.json").read_text()
        )
        schema = json.loads(schema_path.read_text())
        jsonschema.validate(written, schema)


# ---- Task 6: 4 badge formatters ----

class TestBadgeFormatters:
    def test_confirmed(self):
        assert _format_badge_confirmed("v2.0.0+") == "*（已实施 v2.0.0+ + 代码验证）*"

    def test_self_claim_only(self):
        assert _format_badge_self_claim_only("v2.0.0+") == "*（已实施 v2.0.0+ 仅自报）*"

    def test_placeholder_but_exists(self):
        assert _format_badge_placeholder_but_exists() == "*（占位 + 代码已现 ⚠️）*"

    def test_placeholder_as_claimed(self):
        assert _format_badge_placeholder_as_claimed() == "*（占位 + 代码未现）*"


# ---- Task 7: _format_adr_block integration ----

class TestFormatAdrBlockIntegration:
    def test_with_verification_confirmed_renders_new_badge(self, tmp_path):
        adr = AdrRecord(
            id="ADR-0017", path=Path("docs/adr/ADR-0017.md"),
            title="Test", status="已采纳", key_decision="key",
            implementation_version="v2.0.0+",
        )
        v = AdrCodeVerification(
            adr_id="ADR-0017", self_claim_version="v2.0.0+",
            code_symbols_found=["foo"], code_symbols_expected=["foo"],
            verification_status="confirmed", has_discrepancy=False,
            verified_at="2026-08-21T10:00:00Z", mcp_used=False,
        )
        out = _format_adr_block(adr, tmp_path, "phase-1", verification=v)
        assert "*（已实施 v2.0.0+ + 代码验证）*" in out

    def test_no_verification_uses_v1_marker(self, tmp_path):
        adr = AdrRecord(
            id="ADR-0017", path=Path("docs/adr/ADR-0017.md"),
            title="Test", status="已采纳", key_decision="key",
            implementation_version="v2.0.0+",
        )
        out = _format_adr_block(adr, tmp_path, "phase-1", verification=None)
        assert "*（已实施 v2.0.0+ + 代码验证）*" not in out
        assert "*（已实施 v2.0.0+ 仅自报）*" not in out


# ---- Task 9: MCP unavailable falls back to grep ----

class TestMcpFallback:
    def test_no_codebase_memory_dir_falls_back_to_grep(self, tmp_path, monkeypatch):
        assert not (tmp_path / ".codebase-memory").exists()

        (tmp_path / "foo.py").write_text("def mentioned_func(): pass\n")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stderr", captured)

        adr = AdrRecord(
            id="ADR-0050", path=Path("docs/adr/ADR-0050.md"),
            title="T", status="已采纳", key_decision="k",
            implementation_version="v2.0.0+",
        )
        result = verify_adr_by_code(adr, "Uses `mentioned_func()`.", tmp_path)

        assert result.mcp_used is False
        assert "mentioned_func()" in result.code_symbols_found
        assert result.verification_status == "confirmed"