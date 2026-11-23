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

# ── 方案 B：git.openspec_tracked 只管「归档路径」维度（ADR-0036 修订 2026-11-17）
#     ⇒ 只排除 openspec/changes/ 也是合法形态（specs/ 可跟踪）。

@test "env-check: false mode + openspec/changes/ only → silent + PROTECTED=yes" {
    seed_project_yaml "false"
    echo "openspec/changes/" > .gitignore
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore; echo \"PROTECTED=\$_GITIGNORE_PROTECTED\""
    [ "$status" -eq 0 ]
    [[ "$output" != *"guard missing"* ]]
    [[ "$output" == *"PROTECTED=yes"* ]]
}

@test "env-check: false mode + openspec/changes (no trailing slash) → PROTECTED=yes" {
    seed_project_yaml "false"
    echo "openspec/changes" > .gitignore
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore; echo \"PROTECTED=\$_GITIGNORE_PROTECTED\""
    [ "$status" -eq 0 ]
    [[ "$output" == *"PROTECTED=yes"* ]]
}

# 方案 B 的失效模式：只挡归档路径，但 specs 从未 git add ⇒ 保护落空
# （fresh checkout 无 openspec/specs/ ⇒ CI 的 validate 门静默 skip）。
# 非阻塞 hint：结论仍是受保护，只提示补齐。
@test "env-check: archive-only exclusion + untracked specs/ → non-blocking hint" {
    seed_project_yaml "false"
    echo "openspec/changes/" > .gitignore
    mkdir -p openspec/specs/probe
    echo "# probe" > openspec/specs/probe/spec.md
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore; echo \"PROTECTED=\$_GITIGNORE_PROTECTED\""
    [ "$status" -eq 0 ]
    [[ "$output" == *"openspec/specs/ 存在但未入库"* ]]
    [[ "$output" == *"PROTECTED=yes"* ]]
}

@test "env-check: archive-only exclusion + no specs/ dir → no hint" {
    seed_project_yaml "false"
    echo "openspec/changes/" > .gitignore
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore; echo \"PROTECTED=\$_GITIGNORE_PROTECTED\""
    [ "$status" -eq 0 ]
    [[ "$output" != *"存在但未入库"* ]]
    [[ "$output" == *"PROTECTED=yes"* ]]
}

@test "env-check: whole-tree exclusion → no hint even when specs/ exists untracked" {
    seed_project_yaml "false"
    echo "openspec/" > .gitignore
    mkdir -p openspec/specs/probe
    echo "# probe" > openspec/specs/probe/spec.md
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    # 整树形态下 specs 本就不该跟踪 ⇒ 不提示
    [[ "$output" != *"存在但未入库"* ]]
}

@test "env-check: false mode + both forms absent → warn names both acceptable forms" {
    seed_project_yaml "false"
    echo "# nothing relevant" > .gitignore
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    [[ "$output" == *"neither 'openspec/' nor 'openspec/changes/'"* ]]
}

@test "env-check: tracked=true + openspec/changes/ only → reverse inconsistency warning" {
    seed_project_yaml "true"
    echo "openspec/changes/" > .gitignore
    run bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    [[ "$output" == *"反向不一致"* ]]
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
    grep -qxF 'openspec/changes/' .gitignore

    # second run: no duplicate
    run env RDDF_ENV_FIX_GITIGNORE=yes bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    ENTRY_COUNT=$(grep -c '^openspec/changes/$' .gitignore)
    [ "$ENTRY_COUNT" -eq 1 ]
}

@test "env-check: RDDF_ENV_FIX_GITIGNORE=yes does not touch an already-protected project" {
    seed_project_yaml "false"
    printf 'openspec/\n' > .gitignore
    run env RDDF_ENV_FIX_GITIGNORE=yes bash -c "source '$REPO_ROOT/_lib/env_checks.sh'; _check_gitignore"
    [ "$status" -eq 0 ]
    # 整树形态已保护 ⇒ 不得追加第二种形态（避免把 specs 意外挡掉）
    [ "$(cat .gitignore)" = "openspec/" ]
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

@test "doctor: false + openspec/changes/ only → no findings, exit 0" {
    seed_project_yaml "false"
    echo "openspec/changes/" > .gitignore
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category gitignore
    [ "$status" -eq 0 ]
    [[ "$output" == *"All 1 categories OK"* ]]
}

@test "doctor: tracked=true + openspec/changes/ only → reverse inconsistency WARNING" {
    seed_project_yaml "true"
    echo "openspec/changes/" > .gitignore
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category gitignore
    [ "$status" -ne 0 ]
    [[ "$output" == *"reverse inconsistency"* ]]
}

@test "doctor: archive-only exclusion + untracked specs/ → INFO finding (exit 1, no WARNING)" {
    seed_project_yaml "false"
    echo "openspec/changes/" > .gitignore
    mkdir -p openspec/specs/probe
    echo "# probe" > openspec/specs/probe/spec.md
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category gitignore
    # exit 1 = 有 finding 但非 CRITICAL（doctor 的既定语义：INFO/WARNING 都是 1）
    [ "$status" -eq 1 ]
    [[ "$output" == *"openspec/specs/ exists but is not tracked"* ]]
    [[ "$output" == *"0 WARNING"* ]]
    [[ "$output" == *"1 INFO"* ]]
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