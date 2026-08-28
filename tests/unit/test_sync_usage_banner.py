"""Unit tests for _lib/sync_usage_banner.py"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))

from sync_usage_banner import parse_unreleased, extract_banner, check_drift


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestParseUnreleased:
    def test_parse_unreleased_returns_dict(self):
        """parse_unreleased 返回 dict。"""
        sections = parse_unreleased(REPO_ROOT / "CHANGELOG.md")
        assert isinstance(sections, dict)

    def test_parse_unreleased_section_keys(self):
        """如果 [Unreleased] 段存在,section keys 是 Added/Changed/Fixed。"""
        sections = parse_unreleased(REPO_ROOT / "CHANGELOG.md")
        for key in sections:
            assert key in ("Added", "Changed", "Fixed", "Removed", "Deprecated")


class TestExtractBanner:
    def test_extract_banner_returns_string(self):
        """extract_banner 返回字符串(可能为空)。"""
        banner = extract_banner(REPO_ROOT / "USAGE.md")
        assert isinstance(banner, str)


class TestCheckDrift:
    def test_check_drift_returns_list(self):
        """check_drift 返回 list of warnings。"""
        warnings = check_drift(REPO_ROOT / "CHANGELOG.md", REPO_ROOT / "USAGE.md")
        assert isinstance(warnings, list)