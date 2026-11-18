# fix-bats-per-file-timeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让回归门「新增失败 0」这个结论的前提可见 —— 哪些 bats 文件被评估了、哪些没有、为什么没有；并让「慢」不再等于「整文件弃」。

**Architecture:** 采集侧（`tests/scripts/collect_bats_failures.sh`）从「一级 per-file 超时 ⇒ 整文件弃」改成「一级 per-file 超时 ⇒ 二级 per-test 超时 ⇒ 按 test 名归因」，未评估的文件带原因落进 `$OUTPUT.hangs`；报告侧（`tests/scripts/report_regression.sh`）把「未评估」从**计数阈值**改成**命名基线**（`tests/KNOWN_UNEVALUATED.txt`，不在清单内 ⇒ 门失败），并补齐 fail-open 防线（collect summary 缺失 / rc 125-127 / M 分母不一致 ⇒ exit 2）。

**Tech Stack:** bash 4+、bats 1.13.0（`BATS_TEST_TIMEOUT` 自 1.5.0 起提供）、GNU coreutils `timeout`、GitHub Actions。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `tests/scripts/collect_bats_failures.sh` | 采集侧：env 校验 → 一级 per-file 超时 → 二级 per-test 重试 → rc 分类 → 三个产物文件（failures / hangs / per-test-timeouts）+ summary |
| `tests/scripts/report_regression.sh` | 报告侧：调 collect → 解析 summary（缺失 ⇒ exit 2）→ 自己 glob 独立算 M → 未评估 × 命名基线判定 → 失败集合 diff → 退出码 0/1/2 |
| `tests/KNOWN_UNEVALUATED.txt` | **新增**：未评估文件的命名基线（`path # reason`），CI shrink-only |
| `.github/workflows/test.yml` | 回归门 step 显式阈值 + KNOWN_UNEVALUATED shrink-only + `SKIP_UNEVALUATED_GATE` 未设置断言 |
| `tests/README.md` | 更新 collect/report 的直连用法（新增 env 变量与产物文件） |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_regression_gate_evaluation.bats` | **新增**：脚本级契约测试（fake bats 夹具）—— rc 分类 / env 校验 / per-test 归因 / 重试语义 / hang-vs-慢 / 并发与嵌套 / summary 分母 / 报告侧未评估门 / scope 声明 / fail-open 防线 |
| `tests/integration/test_known_failures_baseline.bats` | 适配：fake bats 补 `--version`；嵌套调用显式退出递归保护 |
| `tests/integration/test_execute_regression_gate.bats` | 同上 |

---

### Task 1: collect 的前置校验与 rc 分类

**Files:**
- Modify: `tests/scripts/collect_bats_failures.sh`
- Test: `tests/integration/test_regression_gate_evaluation.bats`

- [ ] **Step 1: Write the failing test**

在 `tests/integration/test_regression_gate_evaluation.bats` 写入夹具与首批用例：

```bash
#!/usr/bin/env bats
# tests/integration/test_regression_gate_evaluation.bats
# 回归门「未评估可见化」的脚本级契约测试（全部用 fake bats ⇒ 不真的等 30s）。

load ../test_helper

COLLECT="$REPO_ROOT/tests/scripts/collect_bats_failures.sh"
REPORT="$REPO_ROOT/tests/scripts/report_regression.sh"

setup() {
  cd "$REPO_ROOT"
  BIN="$BATS_TEST_TMPDIR/bin"
  FIXTURES="$BATS_TEST_TMPDIR/fixtures"
  mkdir -p "$BIN" "$FIXTURES"
  OUT="$BATS_TEST_TMPDIR/out.txt"

  # fake bats：--version 必须答得上来（collect 用它判定 BATS_TEST_TIMEOUT 可用性），
  # 其余行为由 FAKE_BATS_MODE 决定。
  cat > "$BIN/bats" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then echo "Bats 1.13.0"; exit 0; fi
echo "ARGS: $*" >> "${FAKE_BATS_LOG:-/dev/null}"
case "${FAKE_BATS_MODE:-clean}" in
  clean)   echo "1..0"; exit 0 ;;
  fail)    echo "not ok 1 some failure"; exit 1 ;;
  infra125) exit 125 ;;
  hang)    sleep 999 ;;
  slow)    echo "ok 1 first"; echo "ok 2 second"; sleep 999 ;;
  per_test)
    if [ -n "${BATS_TEST_TIMEOUT:-}" ]; then
      echo "not ok 1 stuck test # timeout after ${BATS_TEST_TIMEOUT}s"
      echo "not ok 2 real failure"
      exit 1
    fi
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

collect() { run env PATH="$PATH" FAKE_BATS_MODE="${FAKE_BATS_MODE:-clean}" \
  bash "$COLLECT" "$FIXTURES" "$OUT"; }

@test "collect: env 取值非法 ⇒ exit 2（不得静默变成「不设限」）" {
  : > "$FIXTURES/empty.bats"
  run env PATH="$PATH" BATS_TIMEOUT=0 bash "$COLLECT" "$FIXTURES" "$OUT"
  [ "$status" -eq 2 ]
  run env PATH="$PATH" BATS_TIMEOUT=-5 bash "$COLLECT" "$FIXTURES" "$OUT"
  [ "$status" -eq 2 ]
  run env PATH="$PATH" BATS_TIMEOUT=abc bash "$COLLECT" "$FIXTURES" "$OUT"
  [ "$status" -eq 2 ]
}

@test "collect: BATS_TIMEOUT_RETRY < BATS_TIMEOUT ⇒ exit 2" {
  : > "$FIXTURES/empty.bats"
  run env PATH="$PATH" BATS_TIMEOUT=60 BATS_TIMEOUT_RETRY=10 bash "$COLLECT" "$FIXTURES" "$OUT"
  [ "$status" -eq 2 ]
}

@test "collect: rc 125（timeout 自身失败）⇒ infra error exit 2，不是「通过」" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=infra125
  collect
  [ "$status" -eq 2 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_regression_gate_evaluation.bats`
Expected: FAIL —— `BATS_TIMEOUT=0` 现在被 `timeout` 当成「不设限」，脚本不会 exit 2。

- [ ] **Step 3: Write minimal implementation**

在 `tests/scripts/collect_bats_failures.sh` 顶部加校验块（默认值只在这里出现一次）：

```bash
PER_FILE_TIMEOUT="${BATS_TIMEOUT:-30}"
RETRY_TIMEOUT="${BATS_TIMEOUT_RETRY:-120}"
RETRY_BUDGET="${BATS_RETRY_BUDGET:-600}"

die_infra() { printf '❌ %s\n' "$*" >&2; exit 2; }

case "$PER_FILE_TIMEOUT" in ''|*[!0-9]*) die_infra "BATS_TIMEOUT must be a positive integer, got '$PER_FILE_TIMEOUT'" ;; esac
[ "$PER_FILE_TIMEOUT" -ge 1 ] || die_infra "BATS_TIMEOUT must be >= 1 (0 = no limit ⇒ a real hang blocks forever), got '$PER_FILE_TIMEOUT'"
case "$RETRY_TIMEOUT" in ''|*[!0-9]*) die_infra "BATS_TIMEOUT_RETRY must be a positive integer, got '$RETRY_TIMEOUT'" ;; esac
[ "$RETRY_TIMEOUT" -ge 1 ] || die_infra "BATS_TIMEOUT_RETRY must be >= 1, got '$RETRY_TIMEOUT'"
[ "$RETRY_TIMEOUT" -ge "$PER_FILE_TIMEOUT" ] || die_infra "BATS_TIMEOUT_RETRY ($RETRY_TIMEOUT) must be >= BATS_TIMEOUT ($PER_FILE_TIMEOUT)"
case "$RETRY_BUDGET" in ''|*[!0-9]*) die_infra "BATS_RETRY_BUDGET must be a positive integer, got '$RETRY_BUDGET'" ;; esac
```

并把 `set +e` / `set -e` 开关换成不会中止脚本的写法，且把 125/126/127 判成 infra error：

```bash
    if OUTPUT_LINE=$(timeout -k 5 "$PER_FILE_TIMEOUT" bats --tap "$f" 2>&1); then
        rc=0
    else
        rc=$?
    fi
    case "$rc" in
        125|126|127) die_infra "bats/timeout infra failure on $f (rc=$rc)" ;;
    esac
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_regression_gate_evaluation.bats`
Expected: PASS（3 个用例）

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 2: 两级重试 + per-test 归因 + 重试预算

**Files:**
- Modify: `tests/scripts/collect_bats_failures.sh`
- Test: `tests/integration/test_regression_gate_evaluation.bats`

- [ ] **Step 1: Write the failing test**

```bash
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

@test "collect: 一级的部分输出被丢弃（重试的输出是权威结果）" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=first_fail_then_timeout
  collect
  [ "$status" -eq 0 ]
  ! grep -q "first-run failure" "$OUT"
}

@test "collect: BATS_TIMEOUT_RETRY 真的被用上（env 穿透到二级）" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=per_test
  run env PATH="$PATH" FAKE_BATS_MODE=per_test BATS_TIMEOUT=1 BATS_TIMEOUT_RETRY=3 \
    bash "$COLLECT" "$FIXTURES" "$OUT"
  [ "$status" -eq 0 ]
  grep -q "timeout after 3s" "$OUT.per-test-timeouts"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_regression_gate_evaluation.bats -f "per-test"`
Expected: FAIL —— 现在一级 124 直接 `continue`，`$OUT.per-test-timeouts` 不存在。

- [ ] **Step 3: Write minimal implementation**

在 collect 的循环里，rc==124 时进二级；并把 TAP 拆成「失败」与「per-test 超时」两段：

```bash
PER_TEST_LOG="$WORK/per-test-timeouts"
FILE_TIMEOUT=$((RETRY_TIMEOUT + PER_FILE_TIMEOUT))

# ... 一级超时后：
if [ "$rc" -eq 124 ] && [ "$budget_left" -ge "$FILE_TIMEOUT" ]; then
    budget_left=$((budget_left - FILE_TIMEOUT))
    if RETRY_LINE=$(timeout -k 5 "$FILE_TIMEOUT" env BATS_TEST_TIMEOUT="$RETRY_TIMEOUT" \
            bats --tap "$f" 2>&1); then
        rc=0
    else
        rc=$?
    fi
    case "$rc" in
        125|126|127) die_infra "bats/timeout infra failure on $f during retry (rc=$rc)" ;;
    esac
    OUTPUT_LINE="$RETRY_LINE"      # 一级的部分输出就此丢弃，绝不合并
fi

# TAP 拆分：per-test 超时的 not ok 不进失败集合
PER_TEST=$(printf '%s\n' "$OUTPUT_LINE" | grep -E "^not ok .*# timeout after [0-9]+s$" || true)
NOT_OK=$(printf '%s\n' "$OUTPUT_LINE" | grep -E "^not ok" | grep -vE "# timeout after [0-9]+s$" || true)
```

per-test 项落盘形状：`<path> # <test name>`。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_regression_gate_evaluation.bats`
Expected: PASS（新增 3 例）

- [ ] **Step 5: Defer commit**

---

### Task 3: 原子落盘 + 嵌套守卫

**Files:**
- Modify: `tests/scripts/collect_bats_failures.sh`
- Test: `tests/integration/test_regression_gate_evaluation.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "collect: RDDF_BATS_COLLECT_ACTIVE=1 ⇒ exit 2（不递归采集）" {
  : > "$FIXTURES/a.bats"
  run env PATH="$PATH" RDDF_BATS_COLLECT_ACTIVE=1 bash "$COLLECT" "$FIXTURES" "$OUT"
  [ "$status" -eq 2 ]
}

@test "collect: 并发两次 collect ⇒ 失败集合不互相截断" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=fail
  ( env PATH="$PATH" FAKE_BATS_MODE=fail bash "$COLLECT" "$FIXTURES" "$OUT" >/dev/null 2>&1 ) &
  ( env PATH="$PATH" FAKE_BATS_MODE=fail bash "$COLLECT" "$FIXTURES" "$OUT" >/dev/null 2>&1 ) &
  wait
  # 结果必须是**完整**的一份（要么 A 的内容，要么 B 的内容），不是两者的混合/半截
  run cat "$OUT"
  [[ "$output" == *"some failure"* ]]
  [ "$(grep -c '^not ok' "$OUT")" -eq 1 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_regression_gate_evaluation.bats -f "RDDF_BATS_COLLECT_ACTIVE"`
Expected: FAIL —— 现在没有任何递归保护，脚本照常跑完。

- [ ] **Step 3: Write minimal implementation**

```bash
# 递归守卫：collect 导出该标记给子进程；嵌套采集读到 1 ⇒ 拒绝
if [ "${RDDF_BATS_COLLECT_ACTIVE:-0}" = "1" ]; then
  die_infra "collect_bats_failures.sh: refusing to start (RDDF_BATS_COLLECT_ACTIVE=1 ⇒ recursive collection)"
fi
export RDDF_BATS_COLLECT_ACTIVE=1

# 原子落盘：先写临时文件，结束时 mv（同一 fs 的 rename 是原子的）
WORK="$(mktemp -d -t rdd-bats-collect-XXXXXX)"
trap 'rm -rf "$WORK"' EXIT
OUT_TMP="$WORK/failures"; HANG_TMP="$WORK/hangs"; PT_TMP="$WORK/per-test-timeouts"
# ... 全部写进 $OUT_TMP / $HANG_TMP / $PT_TMP ...
sort -u "$OUT_TMP" -o "$OUT_TMP"
mkdir -p "$(dirname "$OUTPUT")"
mv -f "$OUT_TMP" "$OUTPUT"
mv -f "$HANG_TMP" "${OUTPUT}.hangs"
mv -f "$PT_TMP" "${OUTPUT}.per-test-timeouts"
```

（原实现开头的 `: > "$OUTPUT"` 与 `: > "$HANG_LOG"` 必须删掉 —— 那正是互相截断的根因。）

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_regression_gate_evaluation.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 4: summary 契约 + hang vs 慢 可分辨

**Files:**
- Modify: `tests/scripts/collect_bats_failures.sh`
- Test: `tests/integration/test_regression_gate_evaluation.bats`

- [ ] **Step 1: Write the failing test**

```bash
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

  : > "$FIXTURES/s.bats"
  export FAKE_BATS_MODE=slow
  collect
  grep -q "kind=slow" "$OUT.hangs"
  grep -q "last_tap=2" "$OUT.hangs"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_regression_gate_evaluation.bats -f "summary"`
Expected: FAIL —— 现在没有 `evaluated:` 行，也没有 `.hangs` 的 kind 字段。

- [ ] **Step 3: Write minimal implementation**

```bash
M="${#files[@]}"            # 分母在循环前算好
evaluated=0
# ... 循环内每成功评估一个文件 evaluated=$((evaluated+1)) ...
# 未评估落盘：
printf '%s rc=124 elapsed=%ss last_tap=%s kind=%s\n' \
  "$f" "$elapsed" "$tap_progress" "$kind" >> "$HANG_TMP"
# kind: tap_progress == 0 ⇒ hang；> 0 ⇒ slow

printf '📋 Collected from %d .bats files under %s\n' "$M" "$DIR"
printf '   files with failures: %d\n' "$files_with_failures"
printf '   total unique failures: %d (sorted to %s)\n' "$unique" "$OUTPUT"
printf '   evaluated: %d/%d files\n' "$evaluated" "$M"
printf '   unevaluated: %d file(s) (see %s)\n' "$unevaluated" "${OUTPUT}.hangs"
printf '   per-test timeouts: %d (see %s)\n' "$per_test_count" "${OUTPUT}.per-test-timeouts"
```

TAP 进展计数：`printf '%s\n' "$OUTPUT_LINE" | grep -cE '^(ok|not ok) '`（`|| true` 防空输出触发 `set -e`）。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_regression_gate_evaluation.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 5: 报告侧 —— 未评估维度 + 命名基线 + fail-open 防线

**Files:**
- Modify: `tests/scripts/report_regression.sh`
- Test: `tests/integration/test_regression_gate_evaluation.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "report: 未评估文件不在 KNOWN_UNEVALUATED.txt 内 ⇒ 门失败且不打印 ✅" {
  : > "$FIXTURES/a.bats"
  export FAKE_BATS_MODE=hang
  run env PATH="$PATH" FAKE_BATS_MODE=hang RDDF_KNOWN_FAILURES_FILE="$BATS_TEST_TMPDIR/empty-baseline.txt" \
    RDDF_UNEVALUATED_FILE="$BATS_TEST_TMPDIR/empty-unevaluated.txt" bash "$REPORT"
  [ "$status" -ne 0 ]
  [[ "$output" != *"✅ 0 新增失败"* ]]
  [[ "$output" == *"未评估"* ]]
}

@test "report: 未评估文件在 KNOWN_UNEVALUATED.txt 内 ⇒ 打印但不失败" {
  : > "$FIXTURES/a.bats"
  printf '%s\n' "$FIXTURES/a.bats # known slow file" > "$BATS_TEST_TMPDIR/unevaluated.txt"
  run env PATH="$PATH" FAKE_BATS_MODE=hang RDDF_KNOWN_FAILURES_FILE="$BATS_TEST_TMPDIR/empty-baseline.txt" \
    RDDF_UNEVALUATED_FILE="$BATS_TEST_TMPDIR/unevaluated.txt" bash "$REPORT"
  [ "$status" -eq 0 ]
}

@test "report: scope 声明（采集范围 + 仓内其它 .bats 不在本门范围）" {
  run env PATH="$PATH" bash "$REPORT"
  [[ "$output" == *"tests/integration/"* ]]
  [[ "$output" == *"不在本门范围"* ]]
}

@test "report: collect summary 缺失 ⇒ exit 2（fail-open 防线）" {
  # 用一个只打印垃圾、不给 summary 的假 collect
  cat > "$BATS_TEST_TMPDIR/bin/collect_bats_failures.sh" <<'EOF'
#!/usr/bin/env bash
echo "garbage without summary"
exit 0
EOF
  chmod +x "$BATS_TEST_TMPDIR/bin/collect_bats_failures.sh"
  run env PATH="$PATH" bash "$REPORT"
  [ "$status" -eq 2 ]
  [[ "$output" != *"✅ 0 新增失败"* ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_regression_gate_evaluation.bats -f "report:"`
Expected: FAIL —— 现在未评估只是一行警告，门仍然通过。

- [ ] **Step 3: Write minimal implementation**

在 `tests/scripts/report_regression.sh` 里：

```bash
# 默认值只由 collect 拥有 —— 这里只透传
if ! bash "$SCRIPT_DIR/collect_bats_failures.sh" tests/integration/ "$ACTUAL" >"$TMP_DIR/collect.log" 2>&1; then
  printf '❌ collect_bats_failures.sh failed; inspect collect.log:\n' >&2
  cat "$TMP_DIR/collect.log" >&2
  exit 2
fi

# summary 缺失 ⇒ infra error（不得当作「未评估 0」）
SUMMARY=$(grep -E '^[[:space:]]*evaluated: [0-9]+/[0-9]+ files' "$TMP_DIR/collect.log" | head -1 || true)
[ -n "$SUMMARY" ] || { printf '❌ collect summary missing (infra error)\n' >&2; exit 2; }

# M 由报告侧自己 glob（不信 collect 的 stdout）
M=$(ls "$REPO_ROOT"/tests/integration/*.bats 2>/dev/null | wc -l | tr -d ' ')
COLLECT_M=$(printf '%s' "$SUMMARY" | sed -E 's#.*evaluated: [0-9]+/([0-9]+) files.*#\1#')
[ "$M" = "$COLLECT_M" ] || { printf '❌ collect/报告侧分母不一致 (%s vs %s)\n' "$COLLECT_M" "$M" >&2; exit 2; }

# 未评估 × 命名基线
UNEVAL_FILE="${RDDF_UNEVALUATED_FILE:-$REPO_ROOT/tests/KNOWN_UNEVALUATED.txt}"
UNLISTED=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if ! grep -qF "$f" "$UNEVAL_FILE" 2>/dev/null; then
    printf '  + %s\n' "$f"; UNLISTED=1
  fi
done < "${ACTUAL}.hangs"
```

未评估门失败 ⇒ `SUPPRESS_SUCCESS_BANNER=1` 传给 diff 段（不打印 `✅ 0 新增失败`）且退出码 1。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_regression_gate_evaluation.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 6: 命名基线文件 + CI + README

**Files:**
- Create: `tests/KNOWN_UNEVALUATED.txt`
- Modify: `.github/workflows/test.yml`
- Modify: `tests/README.md`
- Test: `tests/integration/test_regression_gate_evaluation.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "CI: 断言 KNOWN_UNEVALUATED.txt 不增长 + SKIP_UNEVALUATED_GATE 未设置" {
  run grep -n "KNOWN_UNEVALUATED" "$REPO_ROOT/.github/workflows/test.yml"
  [ "$status" -eq 0 ]
  run grep -n "SKIP_UNEVALUATED_GATE" "$REPO_ROOT/.github/workflows/test.yml"
  [ "$status" -eq 0 ]
  [ -f "$REPO_ROOT/tests/KNOWN_UNEVALUATED.txt" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_regression_gate_evaluation.bats -f "CI:"`
Expected: FAIL —— 文件与 workflow 步骤都还没有。

- [ ] **Step 3: Write minimal implementation**

`tests/KNOWN_UNEVALUATED.txt`（初始只有说明；实测仍会未评估的文件按 `path # reason` 追加）：

```
# 未评估文件基线 —— 格式：<path> # <reason>
#
# 语义：回归门采集时若有文件未被评估（重试后仍超时），
#   - 该文件不在本清单内 ⇒ 门失败（exit 1）
#   - 该文件在本清单内   ⇒ 打印但不失败
# 本清单只减不增（CI shrink-only 断言，见 .github/workflows/test.yml）。
```

`.github/workflows/test.yml` 追加两个 step（照抄 `KNOWN_FAILURES.txt` shrink-only 的形态）：

```yaml
      - name: Incremental Bats regression gate
        env:
          BATS_TIMEOUT: '30'
          BATS_TIMEOUT_RETRY: '120'
          BATS_RETRY_BUDGET: '600'
        run: bash tests/scripts/report_regression.sh

      - name: KNOWN_UNEVALUATED.txt shrink-only enforcement
        run: |
          set -e
          BASE=$(git show origin/master:tests/KNOWN_UNEVALUATED.txt 2>/dev/null || git show HEAD~1:tests/KNOWN_UNEVALUATED.txt || true)
          CUR=$(cat tests/KNOWN_UNEVALUATED.txt)
          NEW=$(comm -13 <(printf '%s\n' "$BASE" | sed '/^[[:space:]]*$/d' | sort -u) \
                          <(printf '%s\n' "$CUR"  | sed '/^[[:space:]]*$/d' | sort -u) || true)
          if [ -n "$NEW" ]; then
            echo "❌ KNOWN_UNEVALUATED.txt grew (CI forbidden):"; echo "$NEW"; exit 1
          fi
          echo "✅ KNOWN_UNEVALUATED.txt did not grow"

      - name: SKIP_UNEVALUATED_GATE must not be set in CI
        run: |
          if [ -n "${SKIP_UNEVALUATED_GATE:-}" ]; then
            echo "::error title=regression-gate::SKIP_UNEVALUATED_GATE is set in CI"; exit 1
          fi
          echo "✅ no regression-gate bypass"
```

`tests/README.md`：补 collect 的新 env 变量与三个产物文件。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_regression_gate_evaluation.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 7: 两处 fake-bats 夹具适配新契约

**Files:**
- Modify: `tests/integration/test_known_failures_baseline.bats`
- Modify: `tests/integration/test_execute_regression_gate.bats`

- [ ] **Step 1: Write the failing test**

不需要新用例 —— 既有夹具在新契约下会红，直接跑它们即可：

Run: `bats tests/integration/test_known_failures_baseline.bats tests/integration/test_execute_regression_gate.bats`
Expected: FAIL —— fake bats 不认 `--version` ⇒ collect exit 2；嵌套采集撞递归守卫。

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_known_failures_baseline.bats`
Expected: FAIL（status 2 而非 0）

- [ ] **Step 3: Write minimal implementation**

两处夹具的 fake bats 补 `--version` 分支：

```bash
  cat > "$TEST_BIN/bats" <<EOF
#!/usr/bin/env bash
if [ "\${1:-}" = "--version" ]; then echo "Bats 1.13.0"; exit 0; fi
printf '%s\\n' "$output"
exit $exit_status
EOF
```

两处夹具的嵌套调用显式退出递归保护（这是**有意的**嵌套采集 —— fake bats，不碰真 bats）：

```bash
  run env PATH="$TEST_BIN:$PATH" RDDF_BATS_COLLECT_ACTIVE=0 \
      RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REPORT"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_known_failures_baseline.bats tests/integration/test_execute_regression_gate.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 8: 端到端实测（AC-A / AC-G / AC-H）

**Files:**
- Modify: `tests/integration/test_known_failures_baseline.bats`（临时插入合成失败，验证后撤掉）

- [ ] **Step 1: Write the failing test**（AC-A 的可判定形态）

在 `tests/integration/test_known_failures_baseline.bats` 临时追加：

```bash
@test "zz-synthetic-red" { false; }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash tests/scripts/report_regression.sh`
Expected: 报告出现 `新增失败: 1`，明细含 `zz-synthetic-red`（**改动前**：该文件撞 30s 被跳过 ⇒ 报告里看不到它）

- [ ] **Step 3: Write minimal implementation**

无需新代码 —— 本步验证的是「改动生效」。**验证后必须撤掉合成失败**（否则门会一直红）。

- [ ] **Step 4: Run test to verify it passes**

Run: `bash tests/scripts/report_regression.sh` → 撤掉合成失败后重跑 ⇒ 回到 `新增失败: 0`；
AC-H：`pgrep -f "bats .*\.bats"` 为空（无残留进程）；
AC-G：记录改动前后的 bats 阶段 wall clock，写进 improvement 的实施记录。

- [ ] **Step 5: Defer commit**

---

## Self-Review

**Spec 覆盖**：AC-A（Task 8）、AC-B/AC-D（Task 5）、AC-C/AC-L（Task 4）、AC-E/AC-M（Task 1）、
AC-F（Task 2）、AC-H/AC-G（Task 8）、AC-I/AC-J（Task 6）、AC-K/AC-O（Task 2）、AC-N（Task 3）。
AC-B 的「collect 中途 exit 1 ⇒ report 必须失败」由 Task 5 的 summary 缺失用例覆盖（同一 fail-open 防线）。

**类型一致性**：产物文件名在三个脚本里一致 —— `$OUTPUT` / `$OUTPUT.hangs` / `$OUTPUT.per-test-timeouts`；
env 变量名一致 —— `BATS_TIMEOUT` / `BATS_TIMEOUT_RETRY` / `BATS_RETRY_BUDGET` / `RDDF_BATS_COLLECT_ACTIVE` /
`RDDF_UNEVALUATED_FILE` / `SKIP_UNEVALUATED_GATE`。

**占位符扫描**：无 TBD / TODO / “类似 Task N”。
