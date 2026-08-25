#!/usr/bin/env bash
# tests/integration/test_helper.bash — bats auto-load shim for integration tests.
#
# bats auto-loads `test_helper.bash` from the same directory as each .bats
# file. Integration tests live at tests/integration/test_*.bats, so without
# this shim bats reports "Could not find tests/integration/test_helper.bash"
# and aborts with a single synthetic "bats-gather-tests" failure (which
# report_regression.sh flags as a NEW failure since KNOWN_FAILURES.txt
# doesn't list it).
#
# This file was missing on master before the P0+P1 debt cleanup commit
# (verified: same failure on fc13de7 baseline). Restoring it lets bats
# discover and run the integration suite, surfacing the real baseline of
# 62 known failures.
#
# Just re-export the parent helper; everything is REPO_ROOT-relative.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../test_helper.bash"
