#!/usr/bin/env bash
# tests/e2e/run_external_testbed.sh
#
# Auto-bootstrap + run chisuhua/rdd-workflow-e2e (external third-party test bed).
#
# Behavior:
#   1. If $RDD_E2E_DIR (= /workspace/project/rdd-workflow-e2e by default) does
#      not exist, git clone --depth 1 chisuhua/rdd-workflow-e2e into it.
#   2. If the directory already exists, reuse it (no re-clone).
#   3. Call testbed's ./install_testbed.sh --symlink to point the global install
#      ($HOME/.agents/skills/rdd-workflow) at this local rdd-workflow checkout.
#   4. Run `bats tests/` from inside the testbed. Any extra args are forwarded.
#
# Exit code: 0 = all green, 1 = bats failures, 2 = setup error, 127 = missing dep.
#
# Env vars (with defaults):
#   RDD_E2E_DIR         testbed directory (default: /workspace/project/rdd-workflow-e2e)
#   RDD_E2E_REPO        testbed GitHub repo (default: chisuhua/rdd-workflow-e2e)
#   RDD_WORKFLOW_REPO   path to rdd-workflow checkout to test against
#                       (default: /workspace/project/rdd-workflow)
#
# Usage:
#   tests/e2e/run_external_testbed.sh                 # run all bats
#   tests/e2e/run_external_testbed.sh tests/integration/   # subset
#
# Spec: docs/superpowers/specs/2026-09-08-rdd-workflow-e2e-coop-contract.md

set -euo pipefail

TESTBED_DIR="${RDD_E2E_DIR:-/workspace/project/rdd-workflow-e2e}"
TESTBED_REPO="${RDD_E2E_REPO:-chisuhua/rdd-workflow-e2e}"
RDD_REPO_DIR="${RDD_WORKFLOW_REPO:-/workspace/project/rdd-workflow}"

# ── Preflight ──────────────────────────────────────────────────────────
command -v git >/dev/null 2>&1 || { echo "❌ missing: git" >&2; exit 127; }
command -v bats >/dev/null 2>&1 || { echo "❌ missing: bats-core" >&2; exit 127; }

if [ ! -d "$RDD_REPO_DIR/_lib" ] || [ ! -d "$RDD_REPO_DIR/skills" ]; then
    echo "❌ rdd-workflow checkout not found at $RDD_REPO_DIR (missing _lib/ or skills/)" >&2
    exit 2
fi

# ── Auto-clone if missing ──────────────────────────────────────────────
if [ ! -d "$TESTBED_DIR/.git" ]; then
    if [ -e "$TESTBED_DIR" ] && [ ! -d "$TESTBED_DIR" ]; then
        echo "❌ $TESTBED_DIR exists but is not a directory" >&2
        exit 2
    fi
    echo "▶ Cloning $TESTBED_REPO → $TESTBED_DIR (depth=1)"
    mkdir -p "$(dirname "$TESTBED_DIR")"
    git clone --depth 1 "https://github.com/${TESTBED_REPO}.git" "$TESTBED_DIR"
else
    echo "▶ Reusing existing testbed at $TESTBED_DIR"
fi

# ── Verify testbed structure ───────────────────────────────────────────
if [ ! -f "$TESTBED_DIR/install_testbed.sh" ]; then
    echo "❌ install_testbed.sh missing in $TESTBED_DIR (corrupt clone?)" >&2
    exit 2
fi
# Ensure executable (depth=1 clones don't always preserve +x)
chmod +x "$TESTBED_DIR/install_testbed.sh" 2>/dev/null || true

# ── Symlink current rdd-workflow into the global install path ──────────
# install_testbed.sh --symlink resolves $REPO_ROOT/../rdd-workflow, which is
# the sibling directory convention we use. We override via RDD_WORKFLOW_REPO
# by exporting it for the symlink path the script computes internally.
echo "▶ Linking $RDD_REPO_DIR as global rdd-workflow install"
REPO_ROOT="$RDD_REPO_DIR" "$TESTBED_DIR/install_testbed.sh" --symlink

# ── Run testbed bats suite ─────────────────────────────────────────────
# Tests live under tests/integration/ + tests/_lib/ in the testbed repo;
# `bats tests/` (the README example) returns 0 tests because it only
# matches top-level *.bats. Use `--recursive` to cover all subdirs.
echo "▶ Running bats tests (recursive) in $TESTBED_DIR"
cd "$TESTBED_DIR"
exec bats --recursive tests/ "$@"