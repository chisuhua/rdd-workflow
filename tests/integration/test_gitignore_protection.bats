#!/usr/bin/env bats
# test_gitignore_protection.bats — .gitignore 硬防护一致性 (add-gitignore-hard-protection)
# 覆盖: _check_gitignore (env-check) 4 场景 + auto-fix 幂等 + doctor gitignore category

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    cd "$TEST_TMP"
    git init -q -b main
    git config user.email "t@t" && git config user.name "T"
    echo "x" > x.txt && git add x.txt && git commit -q -m "init"

    # _lib symlink for project_config.sh (pattern: test_archive_with_openspec_tracked_false.bats)
    mkdir -p _lib
    ln -sfn "$REPO_ROOT/_lib/project_config.sh" _lib/project_config.sh
    # project_yaml_get reads PROJECT_ROOT (env)
    export PROJECT_ROOT="$(pwd)"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# helper: seed project.yaml with openspec_tracked value
seed_project_yaml() {
    mkdir -p .rddf
    printf 'git:\n  openspec_tracked: %s\n' "$1" > .rddf/project.yaml
}

@test "env-check: false mode + missing entry → warn + PROTECTED=no + non-blocking" {
    seed_project_yaml "false"
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore; echo \"PROTECTED=\$_GITIGNORE_PROTECTED\""
    [ "$status" -eq 0 ]
    [[ "$output" == *"gitignore guard missing"* ]]
    [[ "$output" == *"PROTECTED=no"* ]]
}

@test "env-check: false mode + entry present → silent + PROTECTED=yes" {
    seed_project_yaml "false"
    echo "openspec/" > .gitignore
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore; echo \"PROTECTED=\$_GITIGNORE_PROTECTED\""
    [ "$status" -eq 0 ]
    [[ "$output" != *"guard missing"* ]]
    [[ "$output" == *"PROTECTED=yes"* ]]
}

@test "env-check: tracked=true + entry present → reverse inconsistency warning" {
    seed_project_yaml "true"
    echo "openspec/" > .gitignore
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    [[ "$output" == *"反向不一致"* ]]
}

@test "env-check: default (no tracked field) + missing entry → silent" {
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "env-check: RDDF_ENV_FIX_GITIGNORE=yes appends entry idempotently" {
    seed_project_yaml "false"
    run env RDDF_ENV_FIX_GITIGNORE=yes bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    [ -f .gitignore ]
    grep -qxF 'openspec/' .gitignore

    # second run: no duplicate
    run env RDDF_ENV_FIX_GITIGNORE=yes bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    ENTRY_COUNT=$(grep -c '^openspec/$' .gitignore)
    [ "$ENTRY_COUNT" -eq 1 ]
}

@test "doctor: gitignore category registered (--help lists it)" {
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"gitignore"* ]]
}

@test "doctor: false + missing entry → WARNING finding, exit non-zero" {
    seed_project_yaml "false"
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category gitignore
    [ "$status" -ne 0 ]
    [[ "$output" == *"WARNING"* ]]
    [[ "$output" == *"git.openspec_tracked=false but .gitignore lacks"* ]]
}

@test "doctor: false + entry present → no findings, exit 0" {
    seed_project_yaml "false"
    echo "openspec/" > .gitignore
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category gitignore
    [ "$status" -eq 0 ]
    [[ "$output" == *"All 1 categories OK"* ]]
}

@test "doctor: remains read-only (no file mutation)" {
    seed_project_yaml "false"
    BEFORE_GI=""
    BEFORE_YAML=$(cat .rddf/project.yaml)
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category gitignore
    # .gitignore must NOT have been created by doctor
    [ ! -f .gitignore ]
    [ "$(cat .rddf/project.yaml)" = "$BEFORE_YAML" ]
}