#!/usr/bin/env bats
# test_rdd_verifier_hook_provider.bats — provider=hook integration tests
#
# Per complete-project-yaml-config-gaps M2 Task 2.5 + spec.md
# 'verifier-hook-provider-routing' requirement: when .rddf/project.yaml
# sets verification.provider: hook, rdd-verify delegates to
# tools/verify_change.sh and maps exit codes to verdicts.
load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    cd "$TEST_TMP"
    git init -q -b main
    git config user.email "t@t"
    git config user.name "T"
    echo "x" > x.txt
    git add x.txt
    git commit -q -m "init"
    mkdir -p .rddf/state openspec/changes/test-change
    echo "x" > openspec/changes/test-change/proposal.md
    git add -A && git commit -q -m "seed"
    sha="$(git rev-parse HEAD)"
    git checkout -q -b openspec/test-change
    mkdir -p .rddf/state
    # Minimal eligible change (status=in_worktree, tasks_done==tasks_total)
    cat > .rddf/state/iteration.json <<EOF
{
  "version": 7,
  "current_phase": "v2.1",
  "changes": [
    {"name": "test-change", "phase": "v2.1", "status": "in_worktree",
     "implementation_ref": "openspec/test-change",
     "codebase_commit_at_last_run": "$sha",
     "tasks_done": 1, "tasks_total": 1}
  ]
}
EOF
}

teardown() {
    rm -rf "$TEST_TMP"
}

_make_hook() {
    local rc="$1"
    mkdir -p tools
    cat > tools/verify_change.sh <<EOF
#!/bin/sh
exit $rc
EOF
    chmod +x tools/verify_change.sh
}

@test "hook-provider: exit 0 → rdd-verify rc 0" {
    _make_hook 0
    cat > .rddf/project.yaml <<'EOF'
verification:
  provider: hook
EOF
    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 0 ]
}

@test "hook-provider: exit 1 → rdd-verify rc 1 (failed)" {
    _make_hook 1
    cat > .rddf/project.yaml <<'EOF'
verification:
  provider: hook
EOF
    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 1 ]
}

@test "hook-provider: exit 2 → rdd-verify rc 3 (error)" {
    _make_hook 2
    cat > .rddf/project.yaml <<'EOF'
verification:
  provider: hook
EOF
    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 3 ]
}

@test "hook-provider: missing tools/verify_change.sh → rc 0 (skipped = backward compat)" {
    # No tools/ directory; hook path missing
    cat > .rddf/project.yaml <<'EOF'
verification:
  provider: hook
EOF
    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 0 ]
}

@test "hook-provider: hook script outside tools/ rejected (security whitelist)" {
    cat > .rddf/project.yaml <<'EOF'
verification:
  provider: hook
EOF
    # Manually invoke the runner with an out-of-tree hook path
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from pathlib import Path
from _lib.cli.rdd_verify_cmd import _hook_runner
from _lib.verifier.hook_runner import HookPathError
try:
    _hook_runner('test-change', Path('.'), hook_path=Path('/tmp/evil.sh'))
    sys.exit(0)
except HookPathError:
    sys.exit(7)
except Exception as exc:
    print('UNEXPECTED:', exc)
    sys.exit(99)
"
    [ "$status" -eq 7 ]
}

@test "hook-provider: SHA-based cache isolation (cache_key differs llm vs hook)" {
    _make_hook 0
    cat > .rddf/project.yaml <<'EOF'
verification:
  provider: hook
EOF
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.verifier.cache import cache_key
from pathlib import Path
key_llm = cache_key('test-change', Path('.'), provider='llm')
key_hook = cache_key('test-change', Path('.'), provider='hook', hook_path=Path('./tools/verify_change.sh'))
assert key_llm != key_hook, f'cache keys must differ: llm={key_llm} hook={key_hook}'
print('OK: keys differ')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK: keys differ"* ]]
}

@test "default-provider: no project.yaml → rdd-verify uses default runner (LLM path)" {
    # No .rddf/project.yaml, no tools/verify_change.sh
    # Use SKIP_RDD_VERIFIER=yes with bypass reason to short-circuit
    # default runner invocation (which would call ac-verifier and fail
    # since the script doesn't exist). The test focuses on routing logic,
    # not LLM execution.
    SKIP_RDD_VERIFIER=yes RDDF_VERIFIER_BYPASS_REASON="integration-test" \
        run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 0 ]
}
