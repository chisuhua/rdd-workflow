#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  cat > "$TMP/iteration.json" <<'EOF'
{"version": 7, "changes": {"x": {"name": "x", "cross_repo_dependencies": []}}}
EOF
}

teardown() { rm -rf "$TMP"; }

@test "rddf deps cross-repo --help" {
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" --help
  [ "$status" -eq 0 ]
}

@test "rddf deps cross-repo --output-format json" {
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" \
    --spokes "fake-org/fake-repo" \
    --output-format json
  [ "$status" -eq 0 ]
}

@test "rddf deps cross-repo --output-format mermaid" {
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" \
    --spokes "fake-org/fake-repo" \
    --output-format mermaid
  [ "$status" -eq 0 ]
}
