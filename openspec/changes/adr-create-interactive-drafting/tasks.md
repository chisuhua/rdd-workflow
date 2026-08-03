## 1. Setup

- [ ] 1.1 Read proposal.md + design.md, confirm scope 对齐 improvements/adr-create-interactive-drafting.md In Scope
- [ ] 1.2 Verify dependencies: `skills/guide-arch/scripts/adr_gate.sh` 存在 + `tests/integration/test_adr_gate.bats` 4 cases green + `docs/adr/ADR-0000-template.md` 50 行结构稳定 + ADR-0016 handoff 契约 env var 可读
- [ ] 1.3 Check current branch + worktree strategy (本 change 轻量模式, 仅 `skills/guide-arch/SKILL.md` + `tests/integration/test_adr_gate_flow.bats` 2 文件变更, 无并发冲突)

## 2. Implementation (TDD 5 步)

### 2.1 Write failing test

- [ ] 2.1.1 创建 `tests/integration/test_adr_gate_flow.bats`, 覆盖提案 Acceptance #1 #3 #8 #9 #11
  - 3 分支 dispatch 静态断言: SKILL.md 包含 `ARCHITECTURE`/`GOVERNANCE`/`IMPLEMENTATION` 三个 case 分支字符串
  - confirm-skip: `SKIP_ADR_CONFIRM=yes` 在 mock 流程中被识别 (grep SKILL.md 含此 env var)
  - 取消清理: mock `read` 返回 `q`, 断言 `docs/adr/ADR-NNNN-*.md` 未被创建
  - 模板覆盖: 断言 SKILL.md 草稿生成指令覆盖 4 顶层 (`## Context`/`## Decision`/`## Consequences`/`## References`) + 5 子 (`### 影响范围`/`### 备选方案`/`### 正面`/`### 负面 / 风险`/`### 后续待办`) + 3 元数据行 (`> **状态**`/`> **日期**`/`> **决策者**`)
- [ ] 2.1.2 验证既有 `tests/integration/test_adr_gate.bats` 4 cases 仍 green (回归护栏)

### 2.2 Verify test fails (red)

- [ ] 2.2.1 跑 `bats tests/integration/test_adr_gate_flow.bats` — 断言全部 5+ 新 cases RED (SKILL.md 尚未含三段式对话/分支处理/confirm-skip 指令)
- [ ] 2.2.2 跑 `bats tests/integration/test_adr_gate.bats` — 断言 4 cases 仍 green (未触及 adr_gate.sh)

### 2.3 Implement change

- [ ] 2.3.1 修改 `skills/guide-arch/SKILL.md` Phase 2 选项 1 执行块 (lines 211-244):
  - 在 `read -r ADR_SLUG` 之前插入 `GATE_CLASS=$(bash skills/guide-arch/scripts/adr_gate.sh "$ADR_SLUG")` + 三 case 分支 dispatch (`case "$GATE_CLASS" in`)
  - **ARCHITECTURE 分支**: 三段式对话指令块 (现状挖掘 → 决策对话 3-5 轮 → 草稿呈现), 现状挖掘复用 `DISCOVERED_ADR_DIR`/`DISCOVERED_ADR_PATTERN`/`DISCOVERED_ARCHITECTURE_DIR` (ADR-0016 契约)
  - **GOVERNANCE 分支**: 显示二次确认 (推荐替代: RELEASE.md / ci-cd.md / CONTRIBUTING.md), 用户确认后才进入对话
  - **IMPLEMENTATION 分支**: 阻断并显示具体替代路径 (docs/、.github/、tasks.md、roadmap.md 子任务)
- [ ] 2.3.2 落盘逻辑: 草稿确认后写 `${NEW_ADR}.tmp` + `mv` 原子写, 强制 `trap 'rm -f ${NEW_ADR}.tmp' EXIT ERR`; `q`/`cancel`/`exit` 中断 → 立即退出 + 不留 temp
- [ ] 2.3.3 `SKIP_ADR_CONFIRM=yes` 判定: 草稿呈现段 if 包裹确认步骤, env var set 时跳过
- [ ] 2.3.4 决策对话硬上限 5 轮: SKILL.md 显式写「超过 5 轮强制 break 并询问用户是否继续」
- [ ] 2.3.5 草稿模板覆盖: 指令块明确生成 4 顶层 + 5 子 + 3 元数据行全部 12 个锚点

### 2.4 Verify test passes (green)

- [ ] 2.4.1 跑 `bats tests/integration/test_adr_gate_flow.bats` — 断言全部 5+ 新 cases GREEN
- [ ] 2.4.2 跑 `bats tests/integration/test_adr_gate.bats` — 断言 4 cases 仍 green (无回归)
- [ ] 2.4.3 跑 `bats tests/smoke.bats` — 断言基础设施冒烟仍 green
- [ ] 2.4.4 跑 `pytest tests/unit/ -q` — 断言 57 unit files 仍 green (本 change 不动 Python, 但需确认无副作用)
- [ ] 2.4.5 静态校验零脚本新增: `find skills/ -newer .openspec.yaml -name '*.sh'` 仅返回 `adr_gate.sh` 等既有文件 (或空)

### 2.5 Refactor + commit

- [ ] 2.5.1 复审 SKILL.md 修改 diff: 删除调试 echo / 统一缩进 / 注释清晰化
- [ ] 2.5.2 复审 test_adr_gate_flow.bats: 断言描述清晰 / 命名一致 / 无冗余
- [ ] 2.5.3 (ship 时执行) commit subject: `feat(guide-arch): wire adr_gate.sh 3-branch dispatch + interactive 3-5 round dialogue`

## 3. Verification

- [ ] 3.1 Run `openspec validate adr-create-interactive-drafting --json` — 接受 specs/ 缺失 ERROR (本次 fill 不写 specs/, plan 阶段决策)
- [ ] 3.2 Run `pytest tests/unit/ -q` — 57 unit files 仍 green
- [ ] 3.3 Run `bats tests/smoke.bats tests/integration/test_adr_gate.bats tests/integration/test_adr_gate_flow.bats` — 全部 green
- [ ] 3.4 (ship 时执行) `git show HEAD:skills/guide-arch/SKILL.md` — 含三段式对话 + 三分支 + `SKIP_ADR_CONFIRM`
- [ ] 3.5 (ship 时执行) `git show HEAD:tests/integration/test_adr_gate_flow.bats` — 新测试文件已落盘
- [ ] 3.6 (ship 时执行) `git show HEAD:openspec/changes/adr-create-interactive-drafting/design.md` — artifact committed
- [ ] 3.7 (ship 时执行) `git show HEAD:openspec/changes/adr-create-interactive-drafting/tasks.md` — artifact committed
- [ ] 3.8 (ship 时执行) `git show HEAD:openspec/changes/adr-create-interactive-drafting/.openspec.yaml` — metadata committed
- [ ] 3.9 静态校验零脚本新增: `git diff --stat HEAD~1 HEAD -- '*.sh'` 仅显示既有脚本修改 (或空)

## 4. Documentation

- [ ] 4.1 更新 `AGENTS.md` 关键约定 (状态文件表附近或环境变量小节) 登记新 env var `SKIP_ADR_CONFIRM=yes` (作用域: 跳过 adr-create 草稿确认直接落盘; 与 `SKIP_ADR_GATE=yes` 独立)
- [ ] 4.2 更新 `improvements/adr-create-interactive-drafting.md` 验收标准 checkbox (实施完成后勾选)
- [ ] 4.3 (可选) 更新 `docs/adr/README.md` 索引表 — 本次不新增 ADR (proposal Out of Scope 明确「不修改 ADR-0003 (另起 ADR 记录本次职责再分配)」, 留作后续)
- [ ] 4.4 (可选) `CHANGELOG.md` 条目 — 视项目惯例 (本仓库历史未强制)
