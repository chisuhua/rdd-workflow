#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  cat > "$TMP/auth-v2.yaml" <<'EOF'
openapi: 3.0.0
info: {title: Auth V2, version: 2.0.0}
paths:
  /v2/login:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email: {type: string}
                password: {type: string}
EOF
  cat > "$TMP/auth_impl_ok.py" <<'EOF'
def login(payload):
    email = payload.get('email')
    password = payload.get('password')
    return email and password
EOF
  cat > "$TMP/auth_impl_broken.py" <<'EOF'
def login(payload):
    return payload.get('password')
EOF
}

teardown() { rm -rf "$TMP"; }

@test "contract-check ok exit 0" {
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "$TMP/auth-v2.yaml" --local "$TMP/auth_impl_ok.py"
  [ "$status" -eq 0 ]
}

@test "contract-check breaking exit 1" {
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "$TMP/auth-v2.yaml" --local "$TMP/auth_impl_broken.py"
  [ "$status" -eq 1 ]
}

@test "contract-check --dry-run prints plan only" {
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "$TMP/auth-v2.yaml" --local "$TMP/auth_impl_broken.py" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY-RUN" ]]
}
