"""tests/unit/test_report_regression_strip.py — strip 逻辑单测。

修复后的 strip 策略:仅白名单 strip ` # pre-existing:` 和 ` # historical:` 两类已知注释,
保留 description 内合法的 `##` / `# ADR-NNNN:` 内容。
"""
import re

def strip_comment(line: str) -> str:
    return re.sub(r'\s+# (pre-existing|historical)[^a-zA-Z0-9_].*$', '', line)

def test_strip_removes_pre_existing_comment():
    assert strip_comment("ok 1 description # pre-existing: x") == "ok 1 description"

def test_strip_removes_historical_comment():
    assert strip_comment("ok 2 description # historical: y") == "ok 2 description"

def test_strip_keeps_inline_double_hash_description():
    assert strip_comment("ok 3 description ## 决策 or ## Decision section") == "ok 3 description ## 决策 or ## Decision section"

def test_strip_keeps_adr_hash_description():
    assert strip_comment("ok 4 every ADR has # ADR-NNNN: header") == "ok 4 every ADR has # ADR-NNNN: header"

def test_strip_keeps_description_with_no_comment():
    assert strip_comment("ok 5 plain description") == "ok 5 plain description"
