#!/usr/bin/env bash
# tests/e2e/_lib/agent_runner.bash
# C-layer (agent simulation) helper: scenario JSON loader + mode dispatch.
# Per 2026-09-08-e2e-test-plan-design.md §3.1.
#
# Three modes:
#   validate — schema + golden field check (CI default, no agent)
#   mock     — use scenario.mock_output as recorded agent response
#   real     — actually invoke agent CLI (opencode / claude / codex)
#
# Mode priority (highest first):
#   $RDDF_AGENT_E2E=1  +  agent CLI detected  →  real
#   $AGENT_RUNNER_MODE=mock                     →  mock
#   default                                     →  validate (or mock if mock_output present)

# Required top-level fields in scenario JSON
_AGENT_RUNNER_REQUIRED_FIELDS=(
    "scenario_id"
    "skill"
    "input"
    "golden_output"
    "isolation"
)

# agent_runner::detect_mode
# Print one of: real | mock | validate
agent_runner::detect_mode() {
    # real mode: explicit opt-in + agent CLI on PATH
    if [ "${RDDF_AGENT_E2E:-no}" = "1" ]; then
        if command -v opencode >/dev/null 2>&1 \
            || command -v claude >/dev/null 2>&1 \
            || command -v codex >/dev/null 2>&1; then
            echo "real"
            return 0
        fi
    fi

    # explicit override
    if [ -n "${AGENT_RUNNER_MODE:-}" ]; then
        case "${AGENT_RUNNER_MODE}" in
            real|mock|validate) echo "${AGENT_RUNNER_MODE}"; return 0 ;;
        esac
    fi

    # default: validate (CI safe) unless scenario has mock_output → mock
    if [ -n "${_CURRENT_SCENARIO_PATH:-}" ] && [ -f "${_CURRENT_SCENARIO_PATH}" ]; then
        if grep -q '"mock_output"' "${_CURRENT_SCENARIO_PATH}" 2>/dev/null; then
            echo "mock"
            return 0
        fi
    fi

    echo "validate"
}

# agent_runner::should_skip
# Returns 0 if current mode would skip (no real agent + no mock_output).
# C-layer bats cases use this to skip cleanly when neither real nor mock applies.
agent_runner::should_skip() {
    local mode
    mode=$(agent_runner::detect_mode)
    [ "$mode" = "validate" ] && return 0  # validate mode always runs (just checks structure)
    return 1
}

# agent_runner::validate_scenario <scenario.json>
# Verify scenario JSON has all required top-level fields and golden_output has
# at least one of: files / fields / stdout_contains.
# Returns 0 on valid, 1 on missing field, 2 on malformed JSON.
agent_runner::validate_scenario() {
    local scenario="$1"
    if [ ! -f "$scenario" ]; then
        echo "ERROR: scenario not found: $scenario" >&2
        return 1
    fi

    # Parse JSON via python (avoid jq dependency for portability)
    _AGENT_RUNNER_SCENARIO="$scenario" python3 - <<'PYEOF' 2>&1
import json
import os
import sys

scenario_path = os.environ["_AGENT_RUNNER_SCENARIO"]
try:
    with open(scenario_path) as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    print(f"ERROR: malformed JSON: {e}", file=sys.stderr)
    sys.exit(2)

required = ["scenario_id", "skill", "input", "golden_output", "isolation"]
missing = [f for f in required if f not in data]
if missing:
    print(f"ERROR: missing required fields: {missing}", file=sys.stderr)
    sys.exit(1)

golden = data.get("golden_output", {})
if not any(k in golden for k in ("files", "fields", "stdout_contains", "history_jsonl")):
    print("ERROR: golden_output must have at least one of: files/fields/stdout_contains/history_jsonl", file=sys.stderr)
    sys.exit(1)

# isolation.locked_paths required (even if empty list)
if "locked_paths" not in data.get("isolation", {}):
    print("ERROR: isolation.locked_paths required", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# agent_runner::run <scenario.json> <output_dir>
# Dispatch by mode:
#   validate — just print "OK validate <scenario_id>"
#   mock     — copy mock_output files to output_dir, log mock stdout
#   real     — invoke agent CLI with constructed prompt
# Returns 0 on success.
agent_runner::run() {
    local scenario="$1"
    local output_dir="$2"
    _CURRENT_SCENARIO_PATH="$scenario"
    local mode
    mode=$(agent_runner::detect_mode)
    mkdir -p "$output_dir"

    case "$mode" in
        validate)
            echo "OK validate $(basename "$scenario" .json)"
            return 0
            ;;
        mock)
            _AGENT_RUNNER_SCENARIO="$scenario" _AGENT_RUNNER_OUTPUT_DIR="$output_dir" python3 - <<'PYEOF' 2>&1
import json
import os
import shutil
import sys

scenario_path = os.environ["_AGENT_RUNNER_SCENARIO"]
output_dir = os.environ["_AGENT_RUNNER_OUTPUT_DIR"]
with open(scenario_path) as f:
    data = json.load(f)

mock = data.get("mock_output", {})
if not mock:
    print("ERROR: mock_output missing for mock mode", file=sys.stderr)
    sys.exit(1)

# Materialize files
for relpath, content in mock.get("files", {}).items():
    dest = os.path.join(output_dir, relpath)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        f.write(content)

# Write stdout
stdout_path = os.path.join(output_dir, "stdout.txt")
with open(stdout_path, "w") as f:
    f.write(mock.get("stdout", ""))

# Write history_jsonl if specified
if "history_jsonl" in mock:
    h = os.path.join(output_dir, ".rddf/state/.quick-history.jsonl")
    os.makedirs(os.path.dirname(h), exist_ok=True)
    with open(h, "w") as f:
        entry = mock["history_jsonl"]
        if isinstance(entry, list):
            for e in entry:
                f.write(json.dumps(e) + "\n")
        else:
            f.write(json.dumps(entry) + "\n")

print(f"OK mock {data['scenario_id']}")
PYEOF
            return $?
            ;;
        real)
            _AGENT_RUNNER_SCENARIO="$scenario" _AGENT_RUNNER_OUTPUT_DIR="$output_dir" \
                _AGENT_RUNNER_CLI="" bash - <<'BASHEOF' 2>&1
scenario_path="${_AGENT_RUNNER_SCENARIO}"
output_dir="${_AGENT_RUNNER_OUTPUT_DIR}"

# Pick agent CLI
if command -v opencode >/dev/null 2>&1; then
    cli="opencode"
elif command -v claude >/dev/null 2>&1; then
    cli="claude"
elif command -v codex >/dev/null 2>&1; then
    cli="codex"
else
    echo "ERROR: no agent CLI found (opencode/claude/codex)" >&2
    exit 1
fi

# Build prompt from scenario input
prompt=$(python3 -c "
import json, os
with open(os.environ['_AGENT_RUNNER_SCENARIO']) as f:
    data = json.load(f)
inp = data.get('input', {})
prompt_text = inp.get('prompt', '')
if not prompt_text:
    cmd = inp.get('command', '')
    args = inp.get('args', [])
    prompt_text = f\"{cmd} {' '.join(args)}\"
print(prompt_text)
")

# Run with 60s timeout
mkdir -p "$output_dir"
timeout 60 "$cli" --prompt "$prompt" > "$output_dir/stdout.txt" 2>&1 || true
echo "OK real $(basename "$scenario" .json)"
BASHEOF
            return $?
            ;;
    esac
}

# agent_runner::verify <output_dir> <scenario.json>
# Check golden_output against actual output_dir.
# Returns 0 if all assertions pass, 1 if any fail.
agent_runner::verify() {
    local output_dir="$1"
    local scenario="$2"
    _AGENT_RUNNER_SCENARIO="$scenario" _AGENT_RUNNER_OUTPUT_DIR="$output_dir" python3 - <<'PYEOF' 2>&1
import json
import os
import sys

scenario_path = os.environ["_AGENT_RUNNER_SCENARIO"]
output_dir = os.environ["_AGENT_RUNNER_OUTPUT_DIR"]
with open(scenario_path) as f:
    data = json.load(f)
golden = data["golden_output"]
failures = []

# Check files exist
for f in golden.get("files", []):
    relpath = f["path"]
    must_exist = f.get("must_exist", True)
    full = os.path.join(output_dir, relpath)
    if must_exist and not os.path.exists(full):
        failures.append(f"file missing: {relpath}")
    elif not must_exist and os.path.exists(full):
        failures.append(f"file should NOT exist: {relpath}")

# Check stdout_contains
stdout_path = os.path.join(output_dir, "stdout.txt")
stdout = ""
if os.path.exists(stdout_path):
    with open(stdout_path) as f:
        stdout = f.read()
for needle in golden.get("stdout_contains", []):
    if needle not in stdout:
        failures.append(f"stdout missing: {needle[:60]}...")

# Check history_jsonl assertions
for h_assert in golden.get("history_jsonl", []):
    h_path = os.path.join(output_dir, ".rddf/state/.quick-history.jsonl")
    if not os.path.exists(h_path):
        failures.append("history_jsonl missing")
        continue
    with open(h_path) as f:
        lines = [json.loads(l) for l in f if l.strip()]
    # Find matching entry by name (any-matching semantics):
    # Each assertion must match at least one line in the jsonl on ALL its fields.
    name = h_assert.get("name")
    if name:
        candidates = [e for e in lines if e.get("name") == name]
    else:
        candidates = lines
    if not candidates:
        failures.append(f"history_jsonl: no entry with name={name}")
        continue
    # Find any candidate that matches all assertion fields
    matched = False
    for candidate in candidates:
        if all(candidate.get(k) == v for k, v in h_assert.items() if k != "name"):
            matched = True
            break
    if not matched:
        # Build a summary of what we saw
        seen = [(e.get("name"), e.get("outcome"), e.get("retry_count")) for e in candidates]
        failures.append(f"history_jsonl: no entry matches {h_assert} (saw: {seen})")

if failures:
    print("FAIL: golden_output mismatches:", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)
print("OK verify")
PYEOF
}
