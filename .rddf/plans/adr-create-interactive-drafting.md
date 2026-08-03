# adr-create-interactive-drafting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将既有 `adr_gate.sh` 门禁脚本接入 guide-arch Phase 2 选项 1 执行路径，实现三分支分发（ARCHITECTURE/GOVERNANCE/IMPLEMENTATION）+ ARCHITECTURE 分支下的三段式交互对话（现状挖掘 → 决策对话 3-5 轮 → 草稿呈现），支持 `SKIP_ADR_CONFIRM=yes` 跳过确认、q/cancel/exit 中途取消不留半成品文件。

**Architecture:** 纯 SKILL.md 指令块实现（零新增脚本）：在选项 1 执行块中 `read -r ADR_SLUG` 之后插入 `GATE_CLASS=$(bash .../adr_gate.sh "$ADR_SLUG")` + `case "$GATE_CLASS" in` 三分支。ARCHITECTURE 分支内嵌三段式对话指令；GOVERNANCE 二次确认后放行；IMPLEMENTATION 阻断并给出替代路径。落盘采用 `${NEW_ADR}.tmp` + `mv` 原子写 + `trap` 清理。现状挖掘复用 ADR-0016 handoff 契约 env var（`DISCOVERED_ADR_DIR`/`DISCOVERED_ADR_PATTERN`/`DISCOVERED_ARCHITECTURE_DIR`）。

**Tech Stack:** Bash (SKILL.md 指令块), bats-core (测试), adr_gate.sh (既有, 不修改), ADR-0016 发现契约 env var (既有, 不新增)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-arch/SKILL.md` | 唯一生产文件：Phase 2 选项 1 执行块 (lines 211-244) 替换为门禁接线 + 三分支 dispatch + 三段式对话指令 |
| `AGENTS.md` | 关键约定登记新 env var `SKIP_ADR_CONFIRM=yes`（文档变更） |
| `improvements/adr-create-interactive-drafting.md` | 验收标准 checkbox 勾选（文档变更） |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_adr_gate_flow.bats` | 新建：6 用例覆盖三分支 dispatch 静态断言 / 三段式对话锚点 / SKIP_ADR_CONFIRM / 12 锚点模板覆盖 / 原子写+cancel guard / adr_gate.sh 回归 |
| `tests/integration/test_adr_gate.bats` | 既有 4 用例，回归护栏（不修改） |

---

### Task 1: 编写失败测试（RED）— 创建 test_adr_gate_flow.bats

**Files:**
- Create: `tests/integration/test_adr_gate_flow.bats`

对应 tasks.md 2.1.1 / 2.1.2 / 2.2.1 / 2.2.2。

- [ ] **Step 1: Write the failing test**

创建 `tests/integration/test_adr_gate_flow.bats`，完整内容：

```bash
load ../test_helper

SKILL_FILE="$REPO_ROOT/skills/guide-arch/SKILL.md"

@test "adr_gate_flow: SKILL.md wires adr_gate.sh with 3-branch dispatch" {
  assert_file_contains "$SKILL_FILE" 'adr_gate\.sh'
  assert_file_contains "$SKILL_FILE" 'GATE_CLASS='
  assert_file_contains "$SKILL_FILE" 'case "\$GATE_CLASS" in'
  assert_file_contains "$SKILL_FILE" 'ARCHITECTURE)'
  assert_file_contains "$SKILL_FILE" 'GOVERNANCE)'
  assert_file_contains "$SKILL_FILE" 'IMPLEMENTATION)'
}

@test "adr_gate_flow: SKILL.md contains 3-stage dialogue instructions" {
  assert_file_contains "$SKILL_FILE" '现状挖掘'
  assert_file_contains "$SKILL_FILE" '决策对话'
  assert_file_contains "$SKILL_FILE" '草稿呈现'
  assert_file_contains "$SKILL_FILE" '5 轮'
}

@test "adr_gate_flow: SKILL.md recognizes SKIP_ADR_CONFIRM independent of SKIP_ADR_GATE" {
  assert_file_contains "$SKILL_FILE" 'SKIP_ADR_CONFIRM'
  assert_file_contains "$SKILL_FILE" 'SKIP_ADR_GATE'
}

@test "adr_gate_flow: draft covers template 12 anchors in option-1 block" {
  local block
  block=$(awk '/\*\*选项 1（创建新 ADR）执行内容\*\*/,/^\*\*选项 [23]/' "$SKILL_FILE")
  for anchor in '## Context' '## Decision' '## Consequences' '## References' \
                '### 影响范围' '### 备选方案' '### 正面' '### 负面 / 风险' '### 后续待办' \
                '> **状态**' '> **日期**' '> **决策者**'; do
    grep -qF "$anchor" <<< "$block" || { echo "missing anchor: $anchor" >&2; return 1; }
  done
}

@test "adr_gate_flow: atomic write + cancel guard (q/cancel/exit leaves no file)" {
  assert_file_contains "$SKILL_FILE" '\.tmp'
  assert_file_contains "$SKILL_FILE" 'rm -f'
  assert_file_contains "$SKILL_FILE" 'q[|]cancel[|]exit'
  assert_file_contains "$SKILL_FILE" 'mv '
}

@test "adr_gate_flow: adr_gate.sh classification preserved (regression)" {
  run bash "$PROJECT_ROOT/skills/guide-arch/scripts/adr_gate.sh" "Define module boundary"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_adr_gate_flow.bats`
Expected: FAIL — 除最后一个回归用例外全部 RED（SKILL.md 尚未含 `GATE_CLASS=`/三分支/三段式对话/`SKIP_ADR_CONFIRM`/12 锚点/原子写）。

- [ ] **Step 3: Run regression baseline**

Run: `bats tests/integration/test_adr_gate.bats`
Expected: 4 cases PASS（既有门禁脚本测试不受影响）。

- [ ] **Step 4: 记录失败用例清单**

将 Step 2 输出的失败用例名复制到 Task 2 的对照基准（供 Task 2 Step 5 全绿核对）。

- [ ] **Step 5: （暂不 commit — 测试与实现同批提交，见 Task 2 Step 5）**

---

### Task 2: 实现 SKILL.md 三分支接线 + 三段式对话（GREEN）

**Files:**
- Modify: `skills/guide-arch/SKILL.md:211-244`（选项 1 执行块整体替换）
- Create（随 commit）: `.rddf/plans/adr-create-interactive-drafting.md`（本计划文件）

对应 tasks.md 2.3.1 / 2.3.2 / 2.3.3 / 2.3.4 / 2.3.5。

- [ ] **Step 1: 定位选项 1 执行块**

读取 `skills/guide-arch/SKILL.md` lines 211-244（`**选项 1（创建新 ADR）执行内容**：` 的 bash 块，含 `read -r ADR_SLUG`）。用 Edit 工具将该 bash 块整体替换为 Step 2 的代码。**保留** `PROJECT_ROOT`/`ADR_DIR`/`TEMPLATE`/`NEXT_NUM` 逻辑不变，只替换 `read -r ADR_SLUG` 之后的部分。

- [ ] **Step 2: 写入替换代码块**

将选项 1 执行块替换为以下完整内容（`read -r ADR_SLUG` 之后的全部逻辑替换，前面编号逻辑保留）：

```bash
# 门禁分类 (adr_gate.sh; SKIP_ADR_GATE=yes 旁路 → 直接按 ARCHITECTURE)
GATE_CLASS=$(bash "$PROJECT_ROOT/skills/guide-arch/scripts/adr_gate.sh" "$ADR_SLUG")

NEW_ADR="$ADR_DIR/ADR-$NEXT_NUM_PADDED-$ADR_SLUG.md"
trap 'rm -f "${NEW_ADR}.tmp"' EXIT ERR

case "$GATE_CLASS" in
  ARCHITECTURE)
    # ── 段 1: 现状挖掘 (agent 自动, 不向用户提问可查事实) ──
    #   已有相关 ADR: ls "${DISCOVERED_ADR_DIR:-docs/adr}"/${DISCOVERED_ADR_PATTERN:-ADR-*.md} | grep -v 0000-template
    #   架构文档:     find "${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}" -type f
    #   代码模式:     grep -l "$ADR_SLUG" docs/adr/ 2>/dev/null
    #   输出 3 段式摘要: 已有相关 ADR / 架构文档 / 代码模式

    # ── 段 2: 决策对话 (严格 3-5 轮, 一次一问 + 附推荐答案) ──
    DIALOGUE_ROUND=0
    CANCELLED=no
    while [ "$DIALOGUE_ROUND" -lt 5 ] && [ "$CANCELLED" = "no" ]; do
      DIALOGUE_ROUND=$((DIALOGUE_ROUND + 1))
      echo "决策点 $DIALOGUE_ROUND/5 (输入: y 接受推荐 / 改写文本 / s 跳过; q/cancel/exit 退出):"
      read -r DECISION_ANSWER
      case "$DECISION_ANSWER" in
        q|cancel|exit) echo "⏹ 退出对话 — 未写任何文件"; CANCELLED=yes ;;
        s) echo "⏭ 跳过该决策点" ;;
        *) echo "已记录: $DECISION_ANSWER" ;;
      esac
    done
    if [ "$CANCELLED" = "yes" ]; then
      continue  # 返回菜单, 不留半成品
    fi
    if [ "$DIALOGUE_ROUND" -ge 5 ]; then
      echo "⚠️  超过 5 轮 — 强制 break。是否继续? (y/n):"
      read -r CONTINUE_ROUND
      [ "$CONTINUE_ROUND" = "y" ] || echo "⏹ 以当前信息生成草稿"
    fi

    # ── 段 3: 草稿呈现 (对话中呈现完整草稿, 覆盖模板全部 section) ──
    #   元数据行:
    #     > **状态**: 待定
    #     > **日期**: $(date +%Y-%m-%d)
    #     > **决策者**: <name(s)>
    #   顶层 section:
    #     ## Context (含 **架构依据** 子项)
    #     ## Decision (含 ### 影响范围 + ### 备选方案)
    #     ## Consequences (含 ### 正面 + ### 负面 / 风险 + ### 后续待办)
    #     ## References
    #   agent 在对话中逐段呈现完整草稿, 等用户确认

    if [ "${SKIP_ADR_CONFIRM:-no}" != "yes" ]; then
      echo "确认草稿并写入 $NEW_ADR? (y/n, q/cancel/exit 取消):"
      read -r CONFIRM
      case "$CONFIRM" in
        q|cancel|exit|n) echo "⏹ 未写入任何文件"; continue ;;
      esac
    else
      echo "⏭ SKIP_ADR_CONFIRM=yes — 跳过确认直接落盘"
    fi

    # 原子写: temp + rename
    cp "$TEMPLATE" "${NEW_ADR}.tmp"
    sed -i "s/ADR-NNNN: <标题>/ADR-$NEXT_NUM_PADDED: <$ADR_SLUG>/" "${NEW_ADR}.tmp"
    sed -i "s/^> \*\*编号\*\*: NNNN/> **编号**: $NEXT_NUM_PADDED/" "${NEW_ADR}.tmp"
    mv "${NEW_ADR}.tmp" "$NEW_ADR"
    echo "✅ 已创建: $NEW_ADR"
    ;;
  GOVERNANCE)
    echo "⚠️  该议题偏向治理/流程决策, 更适合: RELEASE.md / ci-cd.md / CONTRIBUTING.md"
    echo "   仍要创建 ADR? (y/n):"
    read -r GOV_CONFIRM
    [ "$GOV_CONFIRM" = "y" ] || continue
    cp "$TEMPLATE" "$NEW_ADR"
    sed -i "s/ADR-NNNN: <标题>/ADR-$NEXT_NUM_PADDED: <$ADR_SLUG>/" "$NEW_ADR"
    echo "✅ 已创建: $NEW_ADR"
    ;;
  IMPLEMENTATION)
    echo "⛔ 该议题是实现类工作, 不应写成 ADR。"
    echo "   替代路径: docs/ 文档 / .github/ 配置 / tasks.md 任务 / roadmap.md 子任务"
    continue
    ;;
esac
trap - EXIT ERR
```

**要点**（对照 tasks.md 2.3.1-2.3.5）：
- 三分支 dispatch：`case "$GATE_CLASS" in` + `ARCHITECTURE)`/`GOVERNANCE)`/`IMPLEMENTATION)` 各分支独立处理
- 现状挖掘复用 ADR-0016 env var（`DISCOVERED_ADR_DIR`/`DISCOVERED_ADR_PATTERN`/`DISCOVERED_ARCHITECTURE_DIR`），带 `:-` 默认值 fallback
- 决策对话硬上限 5 轮：`while [ "$DIALOGUE_ROUND" -lt 5 ]` + 超限后显式询问是否继续
- 原子写：`cp "$TEMPLATE" "${NEW_ADR}.tmp"` → `mv "${NEW_ADR}.tmp" "$NEW_ADR"`
- cancel guard：`trap 'rm -f "${NEW_ADR}.tmp"' EXIT ERR` + `q|cancel|exit` 各 `read` 点拦截 → `continue` 返回菜单
- `SKIP_ADR_CONFIRM` 判定独立于 `SKIP_ADR_GATE`：if 包裹确认步骤，set 时跳过

- [ ] **Step 3: Run test to verify it fails（实现前确认仍 RED）**

Run: `bats tests/integration/test_adr_gate_flow.bats`
Expected: 与 Task 1 Step 4 清单一致的用例 FAIL（确认修改前基线）。若已意外 GREEN，检查 SKILL.md 是否被提前修改。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_adr_gate_flow.bats`
Expected: 全部 6 用例 PASS（含 12 锚点覆盖、原子写、cancel guard、SKIP_ADR_CONFIRM 识别）。

Run: `bats tests/integration/test_adr_gate.bats`
Expected: 4 cases 仍 PASS（`adr_gate.sh` 未被触碰，回归护栏）。

- [ ] **Step 5: Commit**

```bash
git add skills/guide-arch/SKILL.md tests/integration/test_adr_gate_flow.bats .rddf/plans/adr-create-interactive-drafting.md
git commit -m "feat(guide-arch): wire adr_gate.sh 3-branch dispatch + interactive 3-5 round dialogue"
```

---

### Task 3: 全量验证 + 文档登记（Verification + Documentation）

**Files:**
- Modify: `AGENTS.md`（关键约定登记 `SKIP_ADR_CONFIRM=yes`）
- Modify: `improvements/adr-create-interactive-drafting.md`（验收标准 checkbox 勾选）

对应 tasks.md 3.x + 4.1 / 4.2。

- [ ] **Step 1: 运行 openspec validate**

Run: `openspec validate adr-create-interactive-drafting --json`
Expected: 接受 specs/ 缺失 ERROR（本次 fill 不写 specs/，plan 阶段决策）；其余校验通过。

- [ ] **Step 2: 运行 Python 单元测试**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: 全 GREEN（本 change 不动 Python，确认无副作用）。

- [ ] **Step 3: 运行 bats 冒烟 + 门禁回归**

Run: `bats tests/smoke.bats tests/integration/test_adr_gate.bats tests/integration/test_adr_gate_flow.bats`
Expected: 全部 GREEN。

- [ ] **Step 4: 文档登记**

在 `AGENTS.md` 关键约定（Arch Discovery Contract 小节之后、Session Binding Policy 之前）追加：

```markdown
- `SKIP_ADR_CONFIRM=yes` — 跳过 guide-arch Phase 2 选项 1 adr-create 草稿确认直接落盘 (作用域: ARCHITECTURE 分支段 3; 与既有 `SKIP_ADR_GATE=yes` 语义独立, 可组合使用)
```

在 `improvements/adr-create-interactive-drafting.md` 勾选本次已完成的验收标准 checkbox（对应 Acceptance 各项）。

- [ ] **Step 5: 静态校验 + commit**

```bash
# 零新增脚本校验: 应无新增 .sh (仅既有 adr_gate.sh 等)
git diff HEAD~1 HEAD --stat -- '*.sh'
# 验收校验: 三段式对话 + 三分支 + SKIP_ADR_CONFIRM 已落盘
git show HEAD:skills/guide-arch/SKILL.md | grep -E 'GATE_CLASS=|现状挖掘|决策对话|草稿呈现|SKIP_ADR_CONFIRM'
```

```bash
git add AGENTS.md improvements/adr-create-interactive-drafting.md
git commit -m "docs(guide-arch): register SKIP_ADR_CONFIRM env var + close acceptance"
```

---

### Task 4: 收尾复核（Self-Review + ship-done 交接）

**Files:** 无新增修改（仅核对）。

- [ ] **Step 1: 核对 tasks.md 进度同步**

将 `openspec/changes/adr-create-interactive-drafting/tasks.md` 中已完成项标记 `- [x]`（2.1-2.5 / 3.x / 4.x 对应步骤）。

- [ ] **Step 2: 复核 SKILL.md diff**

Run: `git log --oneline -3 && git show --stat HEAD`
核对：仅 `skills/guide-arch/SKILL.md` + `tests/integration/test_adr_gate_flow.bats` + `AGENTS.md` + `improvements/*.md` + `.rddf/plans/*.md` 变更；无调试 echo 残留、无 `adr_gate.sh` 改动、无 ADR 模板改动。

- [ ] **Step 3: 全量 bats 冒烟最终确认**

Run: `bats tests/smoke.bats`
Expected: GREEN（7 smoke cases）。

- [ ] **Step 4: 类型/锚点一致性复核**

对照 ADR-0000-template.md 逐项核对 12 锚点（4 顶层 + 5 子 + 3 元数据行）在 SKILL.md 草稿指令中全部出现；`SKIP_ADR_CONFIRM` 与 `SKIP_ADR_GATE` 在 AGENTS.md 与 SKILL.md 中语义一致（独立 AND 关系）。

- [ ] **Step 5: 交接 summary**

输出执行摘要（改动文件、测试结果、遗留事项——如 specs/ 缺失属预期），供 guide-ship Phase 2.5 review / Phase 3 archive 使用。
