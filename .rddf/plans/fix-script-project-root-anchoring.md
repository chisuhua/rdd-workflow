# fix-script-project-root-anchoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `rdd-builder` 的 phase 脚本（`phase1_plan.sh` / `phase1_5_deps.sh` / `phase2_execute.sh`）的读写落点只由 `$PROJECT_ROOT` 决定，并加一道**静态门禁**（`check_test_isolation.sh` 新增 check）让「cwd 相对路径」以后无法再溜进来。

**Architecture:** 修 3 个脚本里 5 处 cwd 相对路径（其中 `phase2_execute.sh` 的 lightweight→worktree 降级路径是**活 bug**，与已修的主路径同型）；门禁侧用 **token 级**判定（不是行级）扫 `skills/rdd-builder/scripts/*.sh`，命中「引号内以 `openspec/changes/` 或 `.rddf/` 开头且未被 11 个锚定前缀包裹」的 token ⇒ 报 `file:line`；同物理行的 `# isolation-ok: <理由>` 可豁免（全仓预算是 **2** 条）。

**Tech Stack:** bash 4+、python3（token 扫描用）、bats 1.13.0、GNU coreutils。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-builder/scripts/phase1_plan.sh` | proposal / plans 目录 / tasks 三条路径锚定 `$PROJECT_ROOT` |
| `skills/rdd-builder/scripts/phase1_5_deps.sh` | legacy `.rddf/state/.plan-handoff.json` 读取锚定 `$PROJECT_ROOT` |
| `skills/rdd-builder/scripts/phase2_execute.sh` | :126 / :209 / :241 三处去 cwd 依赖（:209 是降级路径的**活 bug**） |
| `tests/scripts/check_test_isolation.sh` | 新增 `check_no_unanchored_repo_paths`（token 级 + 豁免 + bypass 计量） |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_phase_root_anchoring.bats`（新增） | 9 例：phase1 读/写落点、phase1_5 legacy、phase2 降级路径、门禁正例/豁免/token 级、豁免预算 = 2、不改 CI |

---

### Task 1: 门禁的 token 级扫描器（先建可测的门）

**Files:**
- Modify: `tests/scripts/check_test_isolation.sh`
- Test: `tests/integration/test_phase_root_anchoring.bats`

- [ ] **Step 1: Write the failing test**

新建 `tests/integration/test_phase_root_anchoring.bats`，先写门禁的 3 个用例（正例 / 豁免 / token 级）：

```bash
#!/usr/bin/env bats
# tests/integration/test_phase_root_anchoring.bats
# phase 脚本的项目根锚定 + 「未锚定路径」静态门禁（fix-script-project-root-anchoring）

load ../test_helper

GATE="$REPO_ROOT/tests/scripts/check_test_isolation.sh"

setup() {
  cd "$REPO_ROOT"
  SCAN_ROOT="$BATS_TEST_TMPDIR/scanroot"
  mkdir -p "$SCAN_ROOT"
}

write_script() {
  cat > "$SCAN_ROOT/x.sh"
  chmod +x "$SCAN_ROOT/x.sh"
}

@test "gate: 未锚定的 openspec/changes 相对路径 ⇒ exit 1 且报 file:line" {
  write_script <<'EOF'
PROPOSAL="openspec/changes/$CHANGE_NAME/proposal.md"
EOF
  run env RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [ "$status" -ne 0 ]
  [[ "$output" == *"x.sh:"* ]]
}

@test "gate: 行尾 # isolation-ok 理由 ⇒ 放行" {
  write_script <<'EOF'
PROPOSAL="openspec/changes/$CHANGE_NAME/proposal.md"  # isolation-ok: 相对片段稍后与项目根拼接
EOF
  run env RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [ "$status" -eq 0 ]
}

@test "gate: 同一行同时有未锚定与已锚定 token ⇒ 仍必须报（token 级，非行级）" {
  write_script <<'EOF'
cp "openspec/changes/x" "$PROJECT_ROOT/openspec/changes/x"
EOF
  run env RDDF_ISOLATION_SCAN_ROOTS="$SCAN_ROOT" bash "$GATE"
  [ "$status" -ne 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_phase_root_anchoring.bats`
Expected: FAIL —— `RDDF_ISOLATION_SCAN_ROOTS` 还不被识别（门不扫这个根）⇒ 用例 1/3 的 `status -ne 0` 失败。

- [ ] **Step 3: Write minimal implementation**

在 `tests/scripts/check_test_isolation.sh` 里新增（并在文件头「Adding a new check」处补 rationale）：

```bash
# Check 5: 未锚定项目根的仓库相对路径
# Reason: phase 脚本的 IO 落点必须由 $PROJECT_ROOT 决定。cwd 相对写法在生产里
# 碰巧正确（cwd == 项目根），只在「cwd ≠ PROJECT_ROOT」时暴露 —— 而那时它会写进
# **调用方所在的仓库**（实测：真仓被塞进 openspec/<name> 分支 + 整树检出，
# 两次被当成负载 flake 放过）。判定必须按 token 而非按行：行级会让
# `cp "openspec/x" "$PROJECT_ROOT/openspec/x"` 整行放行 ⇒ 门空转。
check_no_unanchored_repo_paths() {
  local roots="${RDDF_ISOLATION_SCAN_ROOTS:-skills/rdd-builder/scripts}"
  local result
  result="$(RDDF_ISOLATION_SCAN_ROOTS="$roots" python3 - <<'PYEOF'
import os, re, sys

roots = [r for r in os.environ.get("RDDF_ISOLATION_SCAN_ROOTS", "").split(":") if r]
ANCHORS = (
    "$PROJECT_ROOT", "$project_root", "$RDDF_PROJECT_ROOT", "$REPO_ROOT",
    "$main_root", "$TASKS_ROOT", "$WT_PATH", "$EXEC_DIR", "$root",
    "$BOOTSTRAP_REPO_ROOT", "$(git rev-parse --show-toplevel)",
)
# 只匹配仓库内的**目录**形态；裸 `openspec/` 是 git ref（openspec/<name>）的形态。
TOKEN_RE = re.compile(r"""["']([^"']*(?:openspec/changes/|\.rddf/)[^"']*)["']""")
EXEMPT_RE = re.compile(r"#\s*isolation-ok:\s*(\S.*)")

violations = []
for root in roots:
    if not os.path.isdir(root):
        continue
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith((".sh", ".py")):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    stripped = line.lstrip()
                    if stripped.startswith("#"):      # 注释行不算
                        continue
                    ex = EXEMPT_RE.search(line)
                    if ex and len(ex.group(1).strip()) >= 10:
                        continue                        # 显式豁免（理由 ≥10 字）
                    for tok in TOKEN_RE.findall(line):
                        if any(a in tok for a in ANCHORS):
                            continue                    # 已锚定
                        violations.append(f"{path}:{lineno}: {tok}")
                        break                          # 一行只报一次
for v in violations:
    print(v)
sys.exit(1 if violations else 0)
PYEOF
)"
  if [ -n "$result" ]; then
    echo "❌ 未锚定项目根的仓库相对路径（cwd 相对 ⇒ 会写进调用方所在的仓库）:" >&2
    echo "$result" >&2
    return 1
  fi
  return 0
}
```

并把它注册进 `main()` 的 `checks` 数组（`checks=(check_no_os_chdir check_no_raw_env_writes check_no_mkdtemp_without_cleanup check_no_assert_tautologies check_no_unanchored_repo_paths)`）。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_phase_root_anchoring.bats`
Expected: PASS（3 例）

- [ ] **Step 5: Defer commit**

---

### Task 2: `phase1_plan.sh` —— 三条路径锚定

**Files:**
- Modify: `skills/rdd-builder/scripts/phase1_plan.sh`
- Test: `tests/integration/test_phase_root_anchoring.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "phase1_plan: PROJECT_ROOT 指向假仓 ⇒ 读假仓的 proposal（改前报 not found）" {
  FAKE="$BATS_TEST_TMPDIR/fake"
  mkdir -p "$FAKE/openspec/changes/demo" "$FAKE/.rddf/plans"
  echo '# demo' > "$FAKE/openspec/changes/demo/proposal.md"
  printf '# plan\n\n### Task 1: demo\n' > "$FAKE/.rddf/plans/demo.md"
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" demo
  # 改前：rc=2（"proposal.md not found"，它在真仓里找）
  [ "$status" -ne 2 ]
  [ -f "$FAKE/openspec/changes/demo/tasks.md" ]
}

@test "phase1_plan: 写落点跟随 PROJECT_ROOT ⇒ 真仓零写入" {
  FAKE="$BATS_TEST_TMPDIR/fake"
  mkdir -p "$FAKE/openspec/changes/demo" "$FAKE/.rddf/plans"
  echo '# demo' > "$FAKE/openspec/changes/demo/proposal.md"
  printf '# plan\n\n### Task 1: demo\n' > "$FAKE/.rddf/plans/demo.md"
  marker="$BATS_TEST_TMPDIR/marker"; : > "$marker"; sleep 1
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" demo
  # 真仓那两条路径零写入（只扫这两个路径，避免全仓扫描被并联 session 的写误判）
  [ -z "$(find "$REPO_ROOT/openspec/changes/demo" "$REPO_ROOT/.rddf/plans" -newer "$marker" -type f 2>/dev/null)" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats -f "phase1_plan" tests/integration/test_phase_root_anchoring.bats`
Expected: FAIL —— 改前 rc=2。

- [ ] **Step 3: Write minimal implementation**

```bash
PROPOSAL_PATH="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/proposal.md"
PLAN_OUTPUT_DIR="$PROJECT_ROOT/.rddf/plans"
TASKS_PATH="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats -f "phase1_plan" tests/integration/test_phase_root_anchoring.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 3: `phase1_5_deps.sh` —— legacy 读取锚定

**Files:**
- Modify: `skills/rdd-builder/scripts/phase1_5_deps.sh`
- Test: `tests/integration/test_phase_root_anchoring.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "phase1_5_deps: legacy plan-handoff 从 PROJECT_ROOT 读（真仓那份作对照）" {
  FAKE="$BATS_TEST_TMPDIR/fake"
  mkdir -p "$FAKE/openspec/changes/demo" "$FAKE/.rddf/state"
  echo '# demo' > "$FAKE/openspec/changes/demo/proposal.md"
  printf '{"execution_mode_decisions":{"demo":{"mode":"lightweight"}}}\n' \
    > "$FAKE/.rddf/state/.plan-handoff.json"
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh" demo
  [ "$status" -eq 0 ]
  [[ "$output" == *"execution_mode='lightweight'"* ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL —— 改前读的是 cwd（真仓）那份 ⇒ 没有 `lightweight` 的 WARNING。

- [ ] **Step 3: Write minimal implementation**

```bash
if [ -f "$PROJECT_ROOT/.rddf/state/.plan-handoff.json" ]; then
    LEGACY_EXEC_MODE=$(python3 -c "
import json
data = json.load(open('$PROJECT_ROOT/.rddf/state/.plan-handoff.json'))
print(data.get('execution_mode_decisions', {}).get('$CHANGE_NAME', {}).get('mode', ''))
" 2>/dev/null || echo "")
fi
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 4: `phase2_execute.sh` —— 降级路径（活 bug）+ 两处消豁免

**Files:**
- Modify: `skills/rdd-builder/scripts/phase2_execute.sh`
- Test: `tests/integration/test_phase_root_anchoring.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "phase2: lightweight 降级回 worktree 时，worktree 建在 PROJECT_ROOT（不是 cwd）" {
  FAKE="$BATS_TEST_TMPDIR/fake"
  mkdir -p "$FAKE/openspec/changes/demo" "$FAKE/.rddf/state" "$FAKE/.rddf/plans"
  echo '# demo' > "$FAKE/openspec/changes/demo/proposal.md"
  printf '# plan\n\n### Task 1: demo\n' > "$FAKE/.rddf/plans/demo.md"
  printf '{"execution_mode_decision":{"mode":"lightweight"}}\n' \
    > "$FAKE/.rddf/state/builder/demo.json"
  marker="$BATS_TEST_TMPDIR/marker"; : > "$marker"; sleep 1
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" demo --auto-approve
  # 真仓不得出现新 worktree / 新分支（改前：worktree 建在真仓 .rddf/wt/demo）
  [ -z "$(find "$REPO_ROOT/.rddf/wt" -maxdepth 1 -name demo -newer "$marker" 2>/dev/null)" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL —— 改前降级路径的 `WT_PATH` 是 cwd 相对 ⇒ worktree 落在**真仓**。

- [ ] **Step 3: Write minimal implementation**

三处（:126 主路径、:209 降级路径、:241 执行目录内检查）：

```bash
WT_PATH="$PROJECT_ROOT/.rddf/wt/$CHANGE_NAME"      # :126 与 :209
if [ -f "$EXEC_DIR/.rddf/plans/$CHANGE_NAME.md" ]; then   # :241
```

⚠ `:122` 的 fallback `WT_PATH="$PROJECT_ROOT"` 保持不变（绝对路径同样成立）。

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 5: 豁免落位（预算 = 2）+ 变异验证 + 不改 CI

**Files:**
- Modify: `skills/rdd-builder/scripts/phase2_execute.sh`（:100 片段行加标记）
- Modify: `skills/rdd-builder/scripts/phase0_approval.sh`（:327 描述字段行加标记）
- Test: `tests/integration/test_phase_root_anchoring.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "gate: 本仓的 isolation-ok 豁免恰好 2 条，且都有 ≥10 字理由" {
  n=$(grep -c '# isolation-ok' "$REPO_ROOT"/skills/rdd-builder/scripts/*.sh | awk -F: '{s+=$2} END {print s+0}')
  [ "$n" -eq 2 ]
  # 每条理由 ≥10 字
  bad=$(grep -h '# isolation-ok' "$REPO_ROOT"/skills/rdd-builder/scripts/*.sh \
        | sed -E 's/.*# isolation-ok:[[:space:]]*//' | awk 'length($0) < 10')
  [ -z "$bad" ]
}

@test "gate: bypass 可计量（打印 skipped + 写 bypass 审计）" {
  AUDIT="$BATS_TEST_TMPDIR/audit-root"; mkdir -p "$AUDIT/.rddf/state"
  SCAN="$BATS_TEST_TMPDIR/scanroot"; mkdir -p "$SCAN"
  printf 'PROPOSAL="openspec/changes/x"\n' > "$SCAN/x.sh"
  run env ALLOW_TEST_POLLUTION=1 RDDF_PROJECT_ROOT="$AUDIT" \
      RDDF_ISOLATION_SCAN_ROOTS="$SCAN" bash "$GATE"
  [[ "$output" == *"skipped: check_no_unanchored_repo_paths"* ]]
  grep -q "ALLOW_TEST_POLLUTION" "$AUDIT/.rddf/state/.bypass-audit.jsonl"
}
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL —— 还没有豁免行、bypass 也还没计量。

- [ ] **Step 3: Write minimal implementation**

- `skills/rdd-builder/scripts/phase2_execute.sh:100`（相对片段行）行尾加：
  `# isolation-ok: 相对片段，稍后分别与 $PROJECT_ROOT / $EXEC_DIR 拼接`
- `skills/rdd-builder/scripts/phase0_approval.sh:327`（记录给调用方的描述字段）行尾加：
  `# isolation-ok: 记录的是相对路径描述字段，本脚本不据此做 IO`
- 门禁的 bypass 分支：`ALLOW_TEST_POLLUTION=1` 时**仍**执行本 check，但改为报告模式，并
  打印 `skipped: check_no_unanchored_repo_paths` + 调 `_lib/bypass_audit.sh` 写
  `.rddf/state/.bypass-audit.jsonl`。

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

**变异验证**（必须做）：临时把 `phase2_execute.sh:100` 的 `# isolation-ok:` 标记删掉 ⇒
「豁免恰好 2 条」用例必须变红 ⇒ 还原。

- [ ] **Step 5: Defer commit**

---

### Task 6: 端到端 + 全量门

**Files:**
- Test: `tests/integration/test_phase_root_anchoring.bats`（AC-M：不改 CI）

- [ ] **Step 1: Write the failing test**

```bash
@test "gate: 本次改动不含 CI workflow 变更（新 check 复用既有 CI step）" {
  run git -C "$REPO_ROOT" diff --name-only HEAD~5..HEAD -- .github/workflows/test.yml
  [ "$status" -ne 0 ] || [ -z "$output" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Expected: PASS（该用例是守护用的，改动前后都应绿）

- [ ] **Step 3: Write minimal implementation**

无需新代码。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_phase_root_anchoring.bats` ⇒ 全绿
Run: `bats tests/integration/test_phase_auto_approve.bats tests/integration/test_phase0_auto_approve.bats tests/integration/test_rdd_builder_phases.bats tests/integration/test_phase0_iteration_register.bats tests/integration/test_lightweight_branch_and_archive.bats` ⇒ 全绿
Run: `./test.sh --full --regression` ⇒ `评估 M/M 个文件` + `未评估 0` + `新增失败 0`

- [ ] **Step 5: Defer commit**

---

## Self-Review

**Spec 覆盖**：AC-A/B（Task 2）、AC-C（Task 3）、AC-D（Task 4）、AC-E/F/G（Task 1）、
AC-H/AC-I（Task 5）、AC-J（Task 2 的「tasks.md 不存在」场景）、AC-K（Task 6）、
AC-L（Task 6 的全量门）、AC-M（Task 6）。

**类型一致性**：env 变量名 `RDDF_ISOLATION_SCAN_ROOTS`（门）+ `ALLOW_TEST_POLLUTION`（既有）；
豁免标记 `# isolation-ok: <理由>`；allowlist 11 个前缀（Task 1 的 `ANCHORS` 与
improvement 的表逐条对应）。

**占位符扫描**：无 TBD / TODO / 「类似 Task N」。
