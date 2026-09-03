#!/usr/bin/env bats
# test_ship_execution_mode_reads_project_yaml.bats — parse_execution_mode
# reads .rddf/project.yaml git.openspec_tracked field per design.md
# Decision 5 (project.yaml takes precedence over env var).
#
# Per complete-project-yaml-config-gaps M3 Tasks 3.2 + 3.5:
# Priority order: CLI flag > project.yaml > RDD_SHIP_PARALLEL env > default
load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    cd "$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

_run_parse() {
    # Setup: symlink _lib/project_config.sh from rdd-workflow repo into test project
    # (matches real installation pattern: either local _lib or globally installed).
    mkdir -p "$TEST_TMP/_lib"
    ln -sfn "$REPO_ROOT/_lib/project_config.sh" "$TEST_TMP/_lib/project_config.sh"
    PROJECT_ROOT="$TEST_TMP" bash "$REPO_ROOT/_lib/ship_execution_mode.sh" parse_execution_mode "$@"
}

@test "ship-execution-mode: openspec_tracked=false forces serial (no CLI flag)" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    result="$(_run_parse)"
    [ "$result" = "serial" ]
}

@test "ship-execution-mode: CLI flag --parallel wins over project.yaml" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    result="$(_run_parse --parallel)"
    [ "$result" = "parallel" ]
}

@test "ship-execution-mode: project.yaml openspec_tracked=false beats RDD_SHIP_PARALLEL env" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    RDD_SHIP_PARALLEL=yes result="$(RDD_SHIP_PARALLEL=yes _run_parse)"
    [ "$result" = "serial" ]
}

@test "ship-execution-mode: no project.yaml + RDD_SHIP_PARALLEL=yes → parallel" {
    RDD_SHIP_PARALLEL=yes result="$(RDD_SHIP_PARALLEL=yes PROJECT_ROOT="$TEST_TMP" bash "$REPO_ROOT/_lib/ship_execution_mode.sh" parse_execution_mode)"
    [ "$result" = "parallel" ]
}

@test "ship-execution-mode: no project.yaml + no env → serial (default)" {
    result="$(_run_parse)"
    [ "$result" = "serial" ]
}
