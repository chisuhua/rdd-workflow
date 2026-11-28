#!/usr/bin/env bats
# test_commit_gate_bootstrap_noop.bats
#
# `rddf commit-gate init` 的**拒绝契约**（change fix-commit-gate-generator-fake-green）：
# - 脚本类入口（test.sh / npm test / make test）**不再自动推导** ⇒ 拒绝（rc=3）+ 显式 argv 模板；
# - 既有**合法**声明即显式来源 ⇒ `--force` 逐字沿用 + 提示「未重新推导」；
# - 拒绝**不改动**既有声明（字节相等）；`--dry-run` 同判。

load ../test_helper

setup() {
  TEST_REPO=$(mktemp -d "$BATS_TMPDIR/cg-noop-XXXXXX")
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

@test "commit-gate init: 空转脚本入口 ⇒ rc=3 + 不写文件 + 给显式 argv 模板（AC1）" {
  printf '#!/bin/sh\nif [ -z "$1" ]; then echo "usage"; exit 0; fi\n' > test.sh
  chmod +x test.sh
  run _run_init
  [ "$status" -eq 3 ]
  [ ! -f .rddf/commit-gate.json ]
  [[ "$output" == *"需要显式 argv"* ]]
  [[ "$output" == *'"verify_commands"'* ]]
}

@test "commit-gate init: 拒绝码与「无可推导入口」不同（3 vs 1）" {
  echo "nothing" > README.md
  run _run_init
  [ "$status" -eq 1 ]
  [[ "$output" == *"找不到可推导的验证入口"* ]]
}

@test "commit-gate init: --dry-run 同样拒绝（不写盘，AC 同判）" {
  printf '#!/bin/sh\nexit 0\n' > test.sh && chmod +x test.sh
  run _run_init --dry-run
  [ "$status" -eq 3 ]
  [ ! -f .rddf/commit-gate.json ]
}

@test "commit-gate init --force: 既有合法声明即显式来源 ⇒ 逐字沿用 + 提示未重新推导（AC2）" {
  mkdir -p .rddf
  printf '{"verify_commands":[["./test.sh","--verify"]]}\n' > .rddf/commit-gate.json
  printf '#!/bin/sh\n[ "$1" = "--verify" ] || exit 9\ntouch RAN\n' > test.sh && chmod +x test.sh
  run _run_init --force
  [ "$status" -eq 0 ]
  [[ "$output" == *"未重新推导"* ]]
  run python3 -c "import json;print(json.load(open('.rddf/commit-gate.json'))['verify_commands'])"
  [[ "$output" == *"'--verify'"* ]]
  # 该 argv 真的不是 help 分支
  run ./test.sh --verify
  [ "$status" -eq 0 ]
  [ -f RAN ]
}

@test "commit-gate init --force: 既有声明是 shell ⇒ 不算显式来源 ⇒ 拒绝且字节不变（AC4）" {
  mkdir -p .rddf
  printf '{"verify_commands":[["echo"]]}\n' > .rddf/commit-gate.json
  cp .rddf/commit-gate.json before.json
  printf '#!/bin/sh\nexit 0\n' > test.sh && chmod +x test.sh
  run _run_init --force
  [ "$status" -eq 3 ]
  run cmp -s .rddf/commit-gate.json before.json
  [ "$status" -eq 0 ]
}

@test "commit-gate init: 工具链类有测试件仍可生成（非回归）" {
  printf '[project]\nname="x"\n' > pyproject.toml
  mkdir -p tests && : > tests/test_x.py
  run _run_init
  [ "$status" -eq 0 ]
  run python3 -c "import json;print(json.load(open('.rddf/commit-gate.json'))['verify_commands'])"
  [[ "$output" == *"pytest"* ]]
}
