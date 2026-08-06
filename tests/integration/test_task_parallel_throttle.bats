load ../test_helper

@test "parallel-throttle: script exists" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run test -f "$PROJECT_ROOT/_lib/parallel_throttle.sh"
    [ "$status" -eq 0 ]
}

@test "parallel-throttle: has throttle_acquire function" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run grep -c "throttle_acquire" "$PROJECT_ROOT/_lib/parallel_throttle.sh"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "parallel-throttle: has default max concurrent of 3" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run grep -c "DEFAULT_MAX_CONCURRENT=3" "$PROJECT_ROOT/_lib/ship_parallel.sh"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "parallel-throttle: has --max-concurrent arg parsing" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run grep -c "max-concurrent" "$PROJECT_ROOT/_lib/ship_parallel.sh"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}
