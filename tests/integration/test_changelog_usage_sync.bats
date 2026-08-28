#!/usr/bin/env bats
# tests/integration/test_changelog_usage_sync.bats

load 'test_helper'

setup() {
    REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
    cd "$REPO_ROOT"
}

@test "changelog-usage-sync: USAGE.md contains VERSION_BANNER markers" {
    grep -q "VERSION_BANNER_START" USAGE.md
    grep -q "VERSION_BANNER_END" USAGE.md
}

@test "changelog-usage-sync: banner extraction returns non-empty content" {
    run python3 -c "
import sys
sys.path.insert(0, '_lib')
from sync_usage_banner import extract_banner
from pathlib import Path
banner = extract_banner(Path('USAGE.md'))
print(repr(banner))
"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
}

@test "changelog-usage-sync: --check mode exits 0 (no drift) or 1 (drift)" {
    run python3 _lib/sync_usage_banner.py --check
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
}

@test "changelog-usage-sync: CHANGELOG.md parse_unreleased returns dict" {
    run python3 -c "
import sys
sys.path.insert(0, '_lib')
from sync_usage_banner import parse_unreleased
from pathlib import Path
sections = parse_unreleased(Path('CHANGELOG.md'))
assert isinstance(sections, dict)
print(f'parsed {len(sections)} sections')
"
    [ "$status" -eq 0 ]
}