#!/usr/bin/env bats
# tests/integration/test_phase_root_anchoring.bats
#
# phase 脚本的项目根锚定 + 「未锚定路径」静态门禁
# （fix-script-project-root-anchoring）
#
# 全部用例都在假仓 / 假扫描根里跑：真仓只被**读取**（断言「真仓零写入」）。
# 门禁用单 check 模式（RDDF_ISOLATION_ONLY）：本仓的其它隔离检查有历史违规，
# 不隔离就断言不了新 check 自己的退出码。

load ../test_helper

GATE="$REPO_ROOT/tests/scripts/check_test_isolation.sh"
ONLY="RDDF_ISOLATION_ONLY=check_no_unanchored_repo_paths"

setup() {
  cd "$REPO_ROOT"
  SCAN_ROOT="$BATS_TEST_TMPDIR/scanroot"
  mkdir -p "$SCAN_ROOT"
  FAKE="$BATS_TEST_TMPDIR/fake"
}

teardown() {
  # The phase-2 case drives a script that (before the fix) creates a worktree
  # in the CALLER's checkout. Clean it up so a regression cannot leave residue
  # in the repo — the very failure mode this change is about.
  if [ -d "$REPO_ROOT/.rddf/wt/demo" ]; then
    git -C "$REPO_ROOT" worktree remove --force "$REPO_ROOT/.rddf/wt/demo" >/dev/null 2>&1 || true
    rm -rf "$REPO_ROOT/.rddf/wt/demo"
  fi
  git -C "$REPO_ROOT" branch -D openspec/demo >/dev/null 2>&1 || true
}

write_script() {
  cat > "$SCAN_ROOT/x.sh"
  chmod +x "$SCAN_ROOT/x.sh"
}

# 假仓：一个 change 的最小文件集（proposal + 含 "### Task " 的 plan）
make_fake_change() {
  mkdir -p "$FAKE/openspec/changes/demo" "$FAKE/.rddf/plans" "$FAKE/.rddf/state"
  echo '# demo' > "$FAKE/openspec/changes/demo/proposal.md"
  printf '# plan\n\n### Task 1: demo\n' > "$FAKE/.rddf/plans/demo.md"
}

# ── 门禁（Task 1）───────────────────────────────────────────────────────────

@test "gate: 未锚定的 openspec/changes 相对路径 ⇒ exit 1 且报 file:line" {
  write_script <<'EOF'
PROPOSAL="openspec/changes/$CHANGE_NAME/proposal.md"
EOF
  run env $ONLY RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [ "$status" -ne 0 ]
  [[ "$output" == *"x.sh:"* ]]
}

@test "gate: 行尾 # isolation-ok 理由 ⇒ 放行" {
  write_script <<'EOF'
PROPOSAL="openspec/changes/$CHANGE_NAME/proposal.md"  # isolation-ok: 相对片段稍后与项目根拼接
EOF
  run env $ONLY RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [ "$status" -eq 0 ]
}

@test "gate: 同一行同时有未锚定与已锚定 token ⇒ 仍必须报（token 级，非行级）" {
  write_script <<'EOF'
cp "openspec/changes/x" "$PROJECT_ROOT/openspec/changes/x"
EOF
  run env $ONLY RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [ "$status" -ne 0 ]
}

@test "gate: 含路径的消息文本不是路径用法 ⇒ 不报" {
  write_script <<'EOF'
echo "plan file missing at .rddf/plans/$CHANGE_NAME.md" >&2
EOF
  run env $ONLY RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [ "$status" -eq 0 ]
}

@test "gate: 本仓的 isolation-ok 豁免恰好 2 条，且理由都 ≥10 字" {
  n=$(grep -h '# isolation-ok' "$REPO_ROOT"/skills/rdd-builder/scripts/*.sh | wc -l | tr -d ' ')
  [ "$n" -eq 2 ]
  bad=$(grep -h '# isolation-ok' "$REPO_ROOT"/skills/rdd-builder/scripts/*.sh \
        | sed -E 's/.*# isolation-ok:[[:space:]]*//' | awk 'length($0) < 10')
  [ -z "$bad" ]
}

@test "gate: 新 check 单独跑在本仓 ⇒ exit 0（修完之后）" {
  run env $ONLY bash "$GATE"
  [ "$status" -eq 0 ]
}

@test "gate: bypass 可计量（打印 skipped + 写 bypass 审计）" {
  AUDIT="$BATS_TEST_TMPDIR/audit-root"
  mkdir -p "$AUDIT/.rddf/state"
  printf 'PROPOSAL="openspec/changes/x"\n' > "$SCAN_ROOT/x.sh"
  run env ALLOW_TEST_POLLUTION=1 RDDF_PROJECT_ROOT="$AUDIT" \
      RDDF_ISOLATION_ONLY=check_no_unanchored_repo_paths \
      RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [[ "$output" == *"skipped: check_no_unanchored_repo_paths"* ]]
  grep -q "ALLOW_TEST_POLLUTION" "$AUDIT/.rddf/state/.bypass-audit.jsonl"
}

# ── phase1_plan.sh（Task 2）────────────────────────────────────────────────

@test "phase1_plan: PROJECT_ROOT 指向假仓 ⇒ 读假仓的 proposal（改前报 not found）" {
  make_fake_change
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" demo
  # 改前 rc=2（"proposal.md not found" —— 它在真仓里找）
  [ "$status" -ne 2 ]
  [ -f "$FAKE/openspec/changes/demo/tasks.md" ]
}

@test "phase1_plan: 写落点跟随 PROJECT_ROOT ⇒ 真仓零写入" {
  make_fake_change
  marker="$BATS_TEST_TMPDIR/marker"; : > "$marker"; sleep 1
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" demo
  # 只扫这两条路径：全仓扫描会被并联 session 的写误判（本次立项时已实证）
  dirty=$(find "$REPO_ROOT/openspec/changes/demo" "$REPO_ROOT/.rddf/plans" \
               -newer "$marker" -type f 2>/dev/null || true)
  [ -z "$dirty" ]
}

# ── phase1_5_deps.sh（Task 3）──────────────────────────────────────────────

@test "phase1_5_deps: legacy plan-handoff 从 PROJECT_ROOT 读（真仓那份作对照）" {
  make_fake_change
  printf '{"execution_mode_decisions":{"demo":{"mode":"lightweight"}}}\n' \
    > "$FAKE/.rddf/state/.plan-handoff.json"
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh" demo
  [ "$status" -eq 0 ]
  [[ "$output" == *"execution_mode='lightweight'"* ]]
}

# ── phase2_execute.sh（Task 4）─────────────────────────────────────────────

@test "phase2: lightweight 降级回 worktree 时，worktree 建在 PROJECT_ROOT（不是 cwd）" {
  make_fake_change
  mkdir -p "$FAKE/.rddf/state/builder"
  printf '{"execution_mode_decision":{"mode":"lightweight"}}\n' \
    > "$FAKE/.rddf/state/builder/demo.json"
  marker="$BATS_TEST_TMPDIR/marker"; : > "$marker"; sleep 1
  run env PROJECT_ROOT="$FAKE" \
      bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" demo --auto-approve
  # 真仓不得出现新 worktree（改前：worktree 建在真仓 .rddf/wt/demo）
  [ -z "$(find "$REPO_ROOT/.rddf/wt" -maxdepth 1 -name demo -newer "$marker" 2>/dev/null)" ]
}
