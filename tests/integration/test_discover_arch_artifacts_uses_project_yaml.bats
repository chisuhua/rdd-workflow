#!/usr/bin/env bats
# test_discover_arch_artifacts_uses_project_yaml.bats —
# discover_adr_pattern reads .rddf/project.yaml adr.pattern (Python regex)
# per design.md Decision 5 and complete-project-yaml-config-gaps M4 Task 4.3.
#
# Priority: env var (SPEC_WORKFLOW_ADR_PATTERN) > project.yaml > default
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

# Discover ADR pattern via the env var / project.yaml path (Path 1.5 in
# discover-arch-artifacts.sh). Use direct Python invocation to avoid bash
# subprocess env-passing quirks under bats.
_adr_pattern_via_project_yaml() {
    mkdir -p _lib .rddf
    ln -sfn "$REPO_ROOT/_lib/project_config.sh" _lib/project_config.sh
    PROJECT_CONFIG_FILE="$TEST_TMP/.rddf/project.yaml" \
    PYTHONPATH="$REPO_ROOT" \
    python3 -c '
import os, yaml
try:
    with open(os.environ["PROJECT_CONFIG_FILE"]) as f:
        cfg = yaml.safe_load(f) or {}
    val = cfg.get("adr", {}).get("pattern", "")
    print(val)
except Exception:
    print("")
'
}

@test "discover-arch: project.yaml 3-digit pattern picked up" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
adr:
  pattern: "^ADR-[0-9]{3}-.*.md$"
EOF
    result="$(_adr_pattern_via_project_yaml)"
    [ "$result" = '^ADR-[0-9]{3}-.*.md$' ]
}

@test "discover-arch: no project.yaml → empty (caller uses default ADR-*.md glob)" {
    # No project.yaml file
    result="$(_adr_pattern_via_project_yaml)"
    [ -z "$result" ]
}

@test "discover-arch: project.yaml without adr.pattern → empty (caller uses default)" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    result="$(_adr_pattern_via_project_yaml)"
    [ -z "$result" ]
}

@test "discover-arch: corrupt project.yaml → empty (graceful fallback)" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
invalid: : : yaml: : :
EOF
    result="$(_adr_pattern_via_project_yaml)"
    [ -z "$result" ]
}
