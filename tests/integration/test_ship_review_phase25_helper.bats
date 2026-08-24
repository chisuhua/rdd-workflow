@test "ship_review.sh Phase 2.5 invokes review_debt_checker before commit" {
    # Mock: create a project with TODO + no debt file
    export TEST_TMPDIR="${BATS_TMPDIR}/phase25-test"
    mkdir -p "$TEST_TMPDIR"
    cd "$TEST_TMPDIR"
    git init -q
    mkdir -p .rddf/improvements
    echo '// TODO: stuff' > main.go

    # Run helper directly (avoid full ship_review orchestration)
    run python3 -c "
import sys, os, datetime
sys.path.insert(0, '$BATS_TEST_DIRNAME/../../_lib')
from review_debt_checker import check_review_debt_recorded
v = check_review_debt_recorded(
    project_root='$TEST_TMPDIR',
    change_name='test-change',
    execute_finished_at=datetime.datetime.now(datetime.timezone.utc),
)
print(f'persisted={v.persisted} count={v.found_count}')
assert v.found_count >= 1, f'expected TODO detection; got count={v.found_count}'
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"count=1"* ]]
}