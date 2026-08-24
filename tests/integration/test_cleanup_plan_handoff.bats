#!/usr/bin/env bats

load ../test_helper

setup() {
    TEST_TMPDIR="${BATS_TMPDIR}/cleanup-plan-handoff-$$"
    mkdir -p "$TEST_TMPDIR/.rddf/state"
    HANDOFF="$TEST_TMPDIR/.rddf/state/.plan-handoff.json"
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

write_handoff() {
    cat > "$HANDOFF" <<EOF
{
    "plan_complete_at": "2026-08-22T12:00:00+00:00",
    "active_changes": $1,
    "all_artifacts_committed": true,
    "ship_started_at": "2026-08-22T13:00:00+00:00",
    "current_change": "$2",
    "execution_mode_decisions": {"$3": "worktree"},
    "archived_changes": []
}
EOF
}

read_field() {
    python3 -c "
import json
d = json.load(open('$HANDOFF'))
print(d.get('$1'))
"
}

@test "scenario 1: single archive clears current_change + active_changes" {
    write_handoff 1 "fix-foo" "fix-foo"

    PROJECT_ROOT="$REPO_ROOT" \
    HANDOFF_FILE="$HANDOFF" \
    CHANGE_NAME="fix-foo" \
    python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from pathlib import Path
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
cleanup_plan_handoff(Path(os.environ["HANDOFF_FILE"]), os.environ["CHANGE_NAME"])
PYEOF

    [ "$(read_field active_changes)" = "0" ]
    [ "$(read_field current_change)" = "None" ]
    [ "$(read_field ship_started_at)" = "None" ]
}

@test "scenario 2: multi-change archive clears current_change only on match" {
    write_handoff 2 "fix-foo" "fix-foo"

    PROJECT_ROOT="$REPO_ROOT" \
    HANDOFF_FILE="$HANDOFF" \
    CHANGE_NAME="fix-bar" \
    python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from pathlib import Path
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
cleanup_plan_handoff(Path(os.environ["HANDOFF_FILE"]), os.environ["CHANGE_NAME"])
PYEOF

    [ "$(read_field active_changes)" = "1" ]
    [ "$(read_field current_change)" = "fix-foo" ]

    PROJECT_ROOT="$REPO_ROOT" \
    HANDOFF_FILE="$HANDOFF" \
    CHANGE_NAME="fix-foo" \
    python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from pathlib import Path
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
cleanup_plan_handoff(Path(os.environ["HANDOFF_FILE"]), os.environ["CHANGE_NAME"])
PYEOF

    [ "$(read_field active_changes)" = "0" ]
    [ "$(read_field current_change)" = "None" ]
}

@test "scenario 3: ship-done marker clears ship_started_at" {
    write_handoff 0 "None" "fix-prior"
    # Set pre-existing archived_changes
    python3 -c "import json; d=json.load(open('$HANDOFF')); d['archived_changes']=['fix-prior']; open('$HANDOFF','w').write(json.dumps(d,indent=2))"

    PROJECT_ROOT="$REPO_ROOT" \
    HANDOFF_FILE="$HANDOFF" \
    CHANGE_NAME="fix-prior" \
    python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from pathlib import Path
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
cleanup_plan_handoff(Path(os.environ["HANDOFF_FILE"]), os.environ["CHANGE_NAME"])
PYEOF

    [ "$(read_field ship_started_at)" = "None" ]
}

@test "scenario 4: current_change mismatch is preserved" {
    write_handoff 1 "fix-foo" "fix-foo"

    PROJECT_ROOT="$REPO_ROOT" \
    HANDOFF_FILE="$HANDOFF" \
    CHANGE_NAME="fix-bar" \
    python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from pathlib import Path
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
cleanup_plan_handoff(Path(os.environ["HANDOFF_FILE"]), os.environ["CHANGE_NAME"])
PYEOF

    [ "$(read_field current_change)" = "fix-foo" ]
}

@test "scenario 5: missing handoff file is idempotent skip" {
    rm -f "$HANDOFF"

    cat > "$TEST_TMPDIR/run_cleanup.py" <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from pathlib import Path
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
cleanup_plan_handoff(Path(os.environ["HANDOFF_FILE"]), os.environ["CHANGE_NAME"])
PYEOF

    run env PROJECT_ROOT="$REPO_ROOT" HANDOFF_FILE="$HANDOFF" CHANGE_NAME="fix-foo" \
        python3 "$TEST_TMPDIR/run_cleanup.py"

    [ "$status" -eq 0 ]
}