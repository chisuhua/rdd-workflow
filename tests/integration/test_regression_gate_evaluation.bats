#!/usr/bin/env bats
# tests/integration/test_regression_gate_evaluation.bats
# 回归门「未评估可见化」的脚本级契约测试（per fix-bats-per-file-timeout）。
#
# 全部用 fake bats ⇒ 不真的等 30s，也不动仓库真实的基线文件。
# 被测对象：
#   tests/scripts/collect_bats_failures.sh  采集侧（两级超时 / rc 分类 / 归因）
#   tests/scripts/report_regression.sh      报告侧（未评估维度 / fail-open 防线）

load ../test_helper

COLLECT="$REPO_ROOT/tests/scripts/collect_bats_failures.sh"
REPORT="$REPO_ROOT/tests/scripts/report_regression.sh"

setup() {
  cd "$REPO_ROOT"
  BIN="$BATS_TEST_TMPDIR/bin"
  FIXTURES="$BATS_TEST_TMPDIR/fixtures"
  mkdir -p "$BIN" "$FIXTURES"
  OUT="$BATS_TEST_TMPDIR/out.txt"
  EMPTY_BASELINE="$BATS_TEST_TMPDIR/empty-baseline.txt"
  : > "$EMPTY_BASELINE"

  # fake bats：`--version` 必须答得上来（collect 用它判定 BATS_TEST_TIMEOUT
  # 可用性），其余行为由 FAKE_BATS_MODE 决定。
  cat > "$BIN/bats" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then echo "Bats 1.13.0"; exit 0; fi
echo "ARGS: $*" >> "${FAKE_BATS_LOG:-/dev/null}"
echo "TESTTIMEOUT: ${BATS_TEST_TIMEOUT:-none}" >> "${FAKE_BATS_LOG:-/dev/null}"
# 只让文件名匹配 FAKE_BATS_HANG_MATCH 的文件挂住 —— 报告脚本采集的是**真实的**
# tests/integration/（50+ 个文件），全挂会让测试跑上几十分钟。
if [ -n "${FAKE_BATS_HANG_MATCH:-}" ]; then
  case "$*" in
    *"$FAKE_BATS_HANG_MATCH"*) sleep 999 ;;
  esac
fi
case "${FAKE_BATS_MODE:-clean}" in
  clean)    echo "1..0"; exit 0 ;;
  fail)     echo "not ok 1 some failure"; exit 1 ;;
  fail_many) for i in $(seq 1 50); do echo "not ok $i failure $i"; done; exit 1 ;;
  infra125) exit 125 ;;
  hang)     sleep 999 ;;
  slow)     echo "ok 1 first"; echo "ok 2 second"; sleep 999 ;;
  per_test)
    if [ -n "${BATS_TEST_TIMEOUT:-}" ]; then
      echo "not ok 1 stuck test # timeout after ${BATS_TEST_TIMEOUT}s"
      echo "not ok 2 real failure"
      exit 1
    fi
    sleep 999 ;;
  first_fail_then_ok)
    if [ -n "${BATS_TEST_TIMEOUT:-}" ]; then
      echo "not ok 2 second-run failure"
      exit 1
    fi
    echo "not ok 1 first-run failure"
    sleep 999 ;;
  first_fail_then_timeout)
    echo "not ok 1 first-run failure"
    sleep 999 ;;
esac
EOF
  chmod +x "$BIN/bats"
  export FAKE_BATS_LOG="$BATS_TEST_TMPDIR/bats-args.log"
  : > "$FAKE_BATS_LOG"
  export PATH="$BIN:$PATH"
}

# collect（固定 1s 超时 ⇒ 测试不等 30s）
#
# The timeouts are FIXED, not inherited: `${BATS_TIMEOUT:-1}` would pick up an
# ambient BATS_TIMEOUT from whoever runs the suite (e.g. 180 while the machine
# is loaded) and turn this file into a 661s monster — the regression gate's
# own per-file budget then gave up and reported the file "unevaluated", i.e.
# the GATE turned red for a reason that had nothing to do with the code.
# Cases that need a specific value pass it explicitly on the `run env` line.
collect() {
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_MODE="${FAKE_BATS_MODE:-clean}" \
    BATS_TIMEOUT=1 BATS_TIMEOUT_RETRY=1 \
    bash "$COLLECT" "$FIXTURES/" "$OUT"
}

# 最小「假仓」：真 report + 真 collect 脚本，但只面对 1 个 .bats 文件。
# 报告侧绝大多数用例不需要「真实仓里那 256 个文件」—— 用真仓会让每个用例都跑一遍
# 256 次 fake-bats 调用（本文件 20 个用例就变成分钟级，自己成了慢文件）。
make_fake_repo() {
  FAKE_REPO="$BATS_TEST_TMPDIR/fakerepo"
  mkdir -p "$FAKE_REPO/tests/scripts" "$FAKE_REPO/tests/integration" "$FAKE_REPO/.rddf/state"
  cp "$REPORT" "$FAKE_REPO/tests/scripts/report_regression.sh"
  cp "$COLLECT" "$FAKE_REPO/tests/scripts/collect_bats_failures.sh"
  : > "$FAKE_REPO/tests/KNOWN_FAILURES.txt"
  : > "$FAKE_REPO/tests/KNOWN_UNEVALUATED.txt"
  : > "$FAKE_REPO/tests/integration/a.bats"
  # 报告侧的 bypass 审计用 <repo>/_lib/bypass_audit.sh ⇒ 假仓里也放一份
  mkdir -p "$FAKE_REPO/_lib"
  cp "$REPO_ROOT/_lib/bypass_audit.sh" "$FAKE_REPO/_lib/" 2>/dev/null || true
}

# ── env 取值校验（AC-M）──────────────────────────────────────────────────────

@test "collect: BATS_TIMEOUT 非法取值 ⇒ exit 2（不得静默变成「不设限」）" {
  : > "$FIXTURES/a.bats"
  # 空值 = 未设置 ⇒ 走默认值（不是错误）；0 / 负数 / 非数字 ⇒ 错误
  for bad in 0 -5 abc; do
    run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 BATS_TIMEOUT="$bad" bash "$COLLECT" "$FIXTURES/" "$OUT"
    [ "$status" -eq 2 ]
  done
}

@test "collect: BATS_TIMEOUT_RETRY < BATS_TIMEOUT ⇒ exit 2" {
  : > "$FIXTURES/a.bats"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 BATS_TIMEOUT=60 BATS_TIMEOUT_RETRY=10 bash "$COLLECT" "$FIXTURES/" "$OUT"
  [ "$status" -eq 2 ]
}

@test "collect: BATS_RETRY_BUDGET 非法 ⇒ exit 2" {
  : > "$FIXTURES/a.bats"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 BATS_RETRY_BUDGET=0 bash "$COLLECT" "$FIXTURES/" "$OUT"
  [ "$status" -eq 2 ]
}

# ── rc 分类（AC-E）───────────────────────────────────────────────────────────

@test "collect: rc 0 ⇒ 无失败被采集" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=clean
  collect
  [ "$status" -eq 0 ]
  [ ! -s "$OUT" ]
}

@test "collect: rc 1（带 not ok）⇒ 失败被采集" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=fail
  collect
  [ "$status" -eq 0 ]
  grep -q "some failure" "$OUT"
}

@test "collect: rc 125 ⇒ infra error exit 2（不是「通过」）" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=infra125
  collect
  [ "$status" -eq 2 ]
}

# ── per-test 归因（AC-K）+ 重试语义（AC-O）+ env 穿透（AC-F）─────────────────

@test "collect: per-test 超时 ⇒ 按 test 名归因，同文件其余 test 仍被评估" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=per_test
  collect
  [ "$status" -eq 0 ]
  # 卡住的 test 进独立的 per-test 段
  grep -q "stuck test" "$OUT.per-test-timeouts"
  # 同文件的另一个 test 的失败仍被采集
  grep -q "real failure" "$OUT"
  # per-test 超时项不得进失败集合
  ! grep -q "stuck test" "$OUT"
}

@test "collect: 一级的部分输出被丢弃（重试的输出才是权威结果）" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=first_fail_then_ok
  collect
  [ "$status" -eq 0 ]
  grep -q "second-run failure" "$OUT"
  ! grep -q "first-run failure" "$OUT"
}

@test "collect: BATS_TIMEOUT_RETRY 真的被用上（env 穿透到二级）" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=per_test
  : > "$FAKE_BATS_LOG"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_MODE=per_test BATS_TIMEOUT=1 BATS_TIMEOUT_RETRY=3 \
    bash "$COLLECT" "$FIXTURES/" "$OUT"
  [ "$status" -eq 0 ]
  # 二级重试把 BATS_TIMEOUT_RETRY 作为 per-test 超时传给了 bats
  grep -q "TESTTIMEOUT: 3" "$FAKE_BATS_LOG"
  # per-test 段记的是**测试名**（不带 bats 的超时元数据）
  grep -q "stuck test" "$OUT.per-test-timeouts"
  ! grep -q "timeout after" "$OUT.per-test-timeouts"
}

# ── 并发与嵌套（AC-N）────────────────────────────────────────────────────────

@test "collect: RDDF_BATS_COLLECT_ACTIVE=1 ⇒ exit 2（不递归采集）" {
  : > "$FIXTURES/a.bats"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=1 bash "$COLLECT" "$FIXTURES/" "$OUT"
  [ "$status" -eq 2 ]
}

@test "collect: 并发两次 collect ⇒ 失败集合不互相截断" {
  : > "$FIXTURES/a.bats"
  ( env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_MODE=fail_many bash "$COLLECT" "$FIXTURES/" "$OUT" >/dev/null 2>&1 ) &
  ( env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_MODE=fail_many bash "$COLLECT" "$FIXTURES/" "$OUT" >/dev/null 2>&1 ) &
  wait
  # 必须是**完整**的一份（50 条失败），不是被对方截断后的半截
  [ "$(wc -l < "$OUT" | tr -d ' ')" -eq 50 ]
}

# ── summary 契约（AC-C）+ hang vs 慢（AC-L）─────────────────────────────────

@test "collect: summary 的分母 M 在循环前算好（与文件数一致）" {
  : > "$FIXTURES/a.bats"; : > "$FIXTURES/b.bats"; : > "$FIXTURES/c.bats"
  export FAKE_BATS_MODE=clean
  collect
  [ "$status" -eq 0 ]
  [[ "$output" == *"evaluated: 3/3 files"* ]]
}

@test "collect: 零 TAP 进展 ⇒ kind=hang；有进展 ⇒ kind=slow" {
  : > "$FIXTURES/h.bats"
  export FAKE_BATS_MODE=hang
  collect
  grep -q "kind=hang" "$OUT.hangs"
  grep -q "last_tap=0" "$OUT.hangs"

  rm -f "$FIXTURES/h.bats"
  : > "$FIXTURES/s.bats"
  export FAKE_BATS_MODE=slow
  collect
  grep -q "kind=slow" "$OUT.hangs"
  grep -q "last_tap=2" "$OUT.hangs"
}

# ── 报告侧：未评估维度（命名基线）+ scope 声明 + fail-open 防线 ──────────────

@test "report: 未评估文件不在 KNOWN_UNEVALUATED.txt 内 ⇒ 门失败且不打印 ✅" {
  make_fake_repo
  # 假仓里的 a.bats 挂住（FAKE_BATS_HANG_MATCH），KNOWN_UNEVALUATED.txt 是空的
  # ⇒ 未评估文件不在命名基线内 ⇒ 门失败。
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_HANG_MATCH="a.bats" \
    BATS_TIMEOUT=1 BATS_TIMEOUT_RETRY=1 \
    bash "$FAKE_REPO/tests/scripts/report_regression.sh"
  [ "$status" -ne 0 ]
  [[ "$output" != *"✅ 0 新增失败"* ]]
  [[ "$output" == *"未评估"* ]]
}

@test "report: 未评估文件在 KNOWN_UNEVALUATED.txt 内 ⇒ 打印但不失败" {
  make_fake_repo
  printf '%s\n' "tests/integration/a.bats # known slow file" \
    > "$FAKE_REPO/tests/KNOWN_UNEVALUATED.txt"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_HANG_MATCH="a.bats" \
    BATS_TIMEOUT=1 BATS_TIMEOUT_RETRY=1 \
    bash "$FAKE_REPO/tests/scripts/report_regression.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"未评估"* ]]
}

@test "report: SKIP_UNEVALUATED_GATE=yes ⇒ 放行但留下 bypass 审计记录" {
  make_fake_repo
  AUDIT_ROOT="$BATS_TEST_TMPDIR/audit-root"
  mkdir -p "$AUDIT_ROOT/.rddf/state"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_HANG_MATCH="a.bats" \
    BATS_TIMEOUT=1 BATS_TIMEOUT_RETRY=1 \
    RDDF_PROJECT_ROOT="$AUDIT_ROOT" \
    SKIP_UNEVALUATED_GATE=yes RDDF_UNEVALUATED_BYPASS_REASON="test bypass" \
    bash "$FAKE_REPO/tests/scripts/report_regression.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"SKIP_UNEVALUATED_GATE"* ]]
  grep -q "SKIP_UNEVALUATED_GATE" "$AUDIT_ROOT/.rddf/state/.bypass-audit.jsonl"
}

@test "report: scope 声明（采集范围 + 仓内其它 .bats 不在本门范围）" {
  make_fake_repo
  # 假仓另放一个不在 tests/integration/ 下的 .bats ⇒ 「不在本门范围」应当是 1
  mkdir -p "$FAKE_REPO/tests/unit"
  : > "$FAKE_REPO/tests/unit/smoke.bats"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 bash "$FAKE_REPO/tests/scripts/report_regression.sh"
  [[ "$output" == *"tests/integration/"* ]]
  [[ "$output" == *"不在本门范围"* ]]
  [[ "$output" == *"另 1 个"* ]]
}

@test "report: collect summary 缺失 ⇒ exit 2（fail-open 防线）" {
  # 用一份「假仓」跑报告脚本：collect 是假的（不打印 summary），
  # 报告侧必须自己发现 summary 缺失 ⇒ exit 2，而不是「未评估 0 ⇒ 通过」。
  FAKE_REPO="$BATS_TEST_TMPDIR/fakerepo"
  mkdir -p "$FAKE_REPO/tests/scripts" "$FAKE_REPO/tests/integration"
  cp "$REPORT" "$FAKE_REPO/tests/scripts/report_regression.sh"
  cat > "$FAKE_REPO/tests/scripts/collect_bats_failures.sh" <<'EOF'
#!/usr/bin/env bash
echo "garbage without a summary line"
exit 0
EOF
  : > "$FAKE_REPO/tests/KNOWN_FAILURES.txt"
  : > "$FAKE_REPO/tests/KNOWN_UNEVALUATED.txt"
  : > "$FAKE_REPO/tests/integration/a.bats"

  run env RDDF_BATS_COLLECT_ACTIVE=0 bash "$FAKE_REPO/tests/scripts/report_regression.sh"
  [ "$status" -eq 2 ]
  [[ "$output" != *"✅ 0 新增失败"* ]]
}

@test "report: collect 自身失败（infra error）⇒ exit 2" {
  make_fake_repo
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=0 FAKE_BATS_MODE=infra125 \
    bash "$FAKE_REPO/tests/scripts/report_regression.sh"
  [ "$status" -eq 2 ]
  [[ "$output" != *"✅ 0 新增失败"* ]]
}

# ── CI 侧口径（AC-I / AC-J）──────────────────────────────────────────────────

@test "CI: 断言 KNOWN_UNEVALUATED.txt 不增长 + SKIP_UNEVALUATED_GATE 未设置" {
  [ -f "$REPO_ROOT/tests/KNOWN_UNEVALUATED.txt" ]
  run grep -n "KNOWN_UNEVALUATED" "$REPO_ROOT/.github/workflows/test.yml"
  [ "$status" -eq 0 ]
  run grep -n "SKIP_UNEVALUATED_GATE" "$REPO_ROOT/.github/workflows/test.yml"
  [ "$status" -eq 0 ]
}
