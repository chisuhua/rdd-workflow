#!/usr/bin/env bats
# test_commit_gate_bootstrap.bats
#
# `rddf commit-gate init`（per change add-commit-gate-declaration-bootstrap）：
# - **不猜**验证命令（只从仓内既有入口推导；找不到 ⇒ 不写文件 + 手工模板）；
# - 生成物**非平凡** + **不代** `git add` / commit；
# - 已存在声明 ⇒ 不覆盖（`--force` 才覆盖）；`--dry-run` ⇒ 只打印。

load ../test_helper

setup() {
  TEST_REPO=$(mktemp -d "$BATS_TMPDIR/cg-bootstrap-XXXXXX")
  cd "$TEST_REPO"
  git init -q
  git config user.email "t@t"
  git config user.name "T"
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

_run_init() {
  RDDF_PROJECT_ROOT="$TEST_REPO" bash "$REPO_ROOT/rddf" commit-gate init "$@"
}

@test "commit-gate init: 工具链类入口 ⇒ 生成 且不代 add" {
  # ⚠ 脚本类入口（test.sh 等）**不再自动推导**（见 test_commit_gate_bootstrap_noop.bats）；
  # 本用例改用工具链类入口，保住「生成成功」这一侧的契约。
  printf '[project]\nname="x"\n' > pyproject.toml
  mkdir -p tests && : > tests/test_x.py
  run _run_init
  [ "$status" -eq 0 ]
  [ -f .rddf/commit-gate.json ]
  run python3 -c "import json;print(json.load(open('.rddf/commit-gate.json'))['verify_commands'])"
  [[ "$output" == *"pytest"* ]]
  # 不代 add：暂存区必须为空
  run git diff --cached --name-only
  [ -z "$output" ]
}

@test "commit-gate init: 找不到入口 ⇒ 不生成 + 给手工模板" {
  echo "nothing" > README.md
  run _run_init
  [ "$status" -eq 1 ]
  [ ! -f .rddf/commit-gate.json ]
  [[ "$output" == *"找不到可推导的验证入口"* ]]
  [[ "$output" == *"手工模板"* ]]
}

@test "commit-gate init: --dry-run 只打印不写盘" {
  printf '[project]\nname="x"\n' > pyproject.toml
  mkdir -p tests && : > tests/test_x.py
  run _run_init --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"[dry-run]"* ]]
  [ ! -f .rddf/commit-gate.json ]
}

@test "commit-gate init: 已有声明 ⇒ 不覆盖；--force + shell 声明 ⇒ 按工具链重生成" {
  # ⚠ `--force` 语义已改：既有合法声明 = **显式来源** ⇒ 沿用不改文件（见 noop.bats）；
  # 只有既有声明是 **shell**（不作数）时才重新推导。
  mkdir -p .rddf
  echo '{"verify_commands":[["echo"]]}' > .rddf/commit-gate.json
  printf '[project]\nname="x"\n' > pyproject.toml
  mkdir -p tests && : > tests/test_x.py
  run _run_init
  [ "$status" -eq 0 ]
  [[ "$output" == *"声明已存在，未覆盖"* ]]
  run cat .rddf/commit-gate.json
  [[ "$output" == *'"echo"'* ]]
  run _run_init --force
  [ "$status" -eq 0 ]
  run python3 -c "import json;print(json.load(open('.rddf/commit-gate.json'))['verify_commands'])"
  [[ "$output" == *"pytest"* ]]
}

@test "commit-gate init: 命名的入口文件必须真实存在（package.json 无 scripts.test ⇒ 不算命中）" {
  echo '{"scripts":{"build":"x"}}' > package.json
  run _run_init
  [ "$status" -eq 1 ]
  [ ! -f .rddf/commit-gate.json ]
}
