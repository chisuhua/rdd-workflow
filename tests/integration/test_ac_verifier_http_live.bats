#!/usr/bin/env bats
#
# Integration test: real requests.post hits a local Python HTTP mock server.
# Validates full invoke_ai_agent() dispatch path through the bash wrapper
# (which sets PROJECT_ROOT=tmp, no PYTHONPATH, no conftest.py — exercises
# the dash-bridge in ac_verifier.py).
#

load test_helper

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
export REPO_ROOT

# Python preamble that registers the dash-bridge for skills.ac_verifier.*
# (the directory has a hyphen, not a valid Python identifier). Normally
# conftest.py does this for pytest, but bats runs outside pytest.
DASH_BRIDGE_PY='
import sys, types
from pathlib import Path
sys.path.insert(0, "'"$REPO_ROOT"'")
_scripts = Path("'"$REPO_ROOT"'/skills/ac-verifier/scripts").resolve()
_av = _scripts.parent
if "skills.ac_verifier" not in sys.modules:
    s = types.ModuleType("skills.ac_verifier"); s.__path__ = [str(_av)]
    sys.modules["skills.ac_verifier"] = s
if "skills.ac_verifier.scripts" not in sys.modules:
    s = types.ModuleType("skills.ac_verifier.scripts"); s.__path__ = [str(_scripts)]
    sys.modules["skills.ac_verifier.scripts"] = s
'

start_mock_server() {
    local port="$1"
    local mode="${2:-ok}"
    MOCK_PORT_FILE="$BATS_TEST_TMPDIR/mock_port_${mode}"
    MOCK_PID_FILE="$BATS_TEST_TMPDIR/mock_pid_${mode}"
    MOCK_LOG="$BATS_TEST_TMPDIR/mock_log_${mode}"

    python3 "$REPO_ROOT/tests/_lib/mock_llm_server.py" "$port" "$mode" \
        >"$MOCK_LOG" 2>&1 &
    echo $! > "$MOCK_PID_FILE"

    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if curl -s "http://127.0.0.1:${port}/" >/dev/null 2>&1; then
            return 0
        fi
        sleep 0.2
    done
    return 1
}

stop_mock_server() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid
        pid="$(cat "$pid_file")"
        kill -9 "$pid" 2>/dev/null || true
        rm -f "$pid_file"
    fi
}

teardown() {
    stop_mock_server "$BATS_TEST_TMPDIR/mock_pid_ok"
    stop_mock_server "$BATS_TEST_TMPDIR/mock_pid_401"
}

@test "live: openai provider hits mock server and parses 200 response" {
    port=18730
    start_mock_server "$port" "ok"

    run python3 -c "${DASH_BRIDGE_PY}
import os
os.environ['AC_LLM_PROVIDER'] = 'openai'
os.environ['AC_LLM_API_KEY'] = 'sk-test'
os.environ['AC_LLM_BASE_URL'] = 'http://127.0.0.1:${port}'
from skills.ac_verifier.scripts.llm_providers import get_provider
result = get_provider('openai').invoke('sys', 'usr')
assert 'ok' in result, f'unexpected: {result}'
print('PASS')
"
    [ "$status" -eq 0 ]
    [ "$output" = "PASS" ]
}

@test "live: 401 from server surfaces as AuthError without retry" {
    port=18731
    start_mock_server "$port" "401"

    run python3 -c "${DASH_BRIDGE_PY}
import os
os.environ['AC_LLM_PROVIDER'] = 'openai'
os.environ['AC_LLM_API_KEY'] = 'sk-test'
os.environ['AC_LLM_BASE_URL'] = 'http://127.0.0.1:${port}'
os.environ['AC_LLM_MAX_RETRIES'] = '0'
from skills.ac_verifier.scripts.llm_providers import get_provider
from skills.ac_verifier.scripts.llm_providers.base import AuthError
try:
    get_provider('openai').invoke('s', 'u')
    print('FAIL: no exception')
except AuthError as e:
    assert '401' in str(e), f'expected 401, got: {e}'
    print('PASS')
"
    [ "$status" -eq 0 ]
    [ "$output" = "PASS" ]
}

@test "live: provider module imports cleanly in subprocess (dash-bridge works)" {
    TMP="$(mktemp -d)"
    mkdir -p "$TMP/openspec/changes/test-change"
    printf '%s\n' "## 验收标准" "- AC one" > "$TMP/openspec/changes/test-change/proposal.md"
    echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"

    port=18732
    start_mock_server "$port" "ok"

    run env \
        PROJECT_ROOT="$TMP" \
        AC_LLM_PROVIDER=openai \
        AC_LLM_API_KEY=sk-test \
        AC_LLM_BASE_URL="http://127.0.0.1:${port}" \
        bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change

    # We don't care about exit code (depends on parse_verdict of canned response).
    # We DO care that the dash-bridge worked — no ModuleNotFoundError.
    [[ ! "$output" == *"ModuleNotFoundError"* ]]
    [[ ! "$output" == *"ImportError"* ]]
    rm -rf "$TMP"
}
