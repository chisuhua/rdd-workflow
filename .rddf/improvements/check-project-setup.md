# check-project-setup

**优先级**: P1 | **来源**: 用户反馈 — 启动无 gitignore 知识门槛 + 硬/软门控不对称
**阶段**: v2.2 | **分类**: infra-setup
**类型**: feature

## 架构依据

- **AGENTS.md:9-13** (`.gitignore` 现状契约)：
  ```
  # spec-workflow runtime state and worktree directories
  # .rddf/plans/ is tracked; .rddf/state/ and .rddf/wt/ are runtime-only
  .rddf/state/
  .rddf/wt/
  .rddf/detectors/
  .rddf/actions/
  ```
  rdd-workflow 自身对 `.rddf/*` 的 tracked/ignored 划分有**明确契约**，但契约只活在仓库内，未传播到使用 rdd-workflow 的下游项目。

- **COMMIT GATE 不对称** (`skills/guide-ship/scripts/ship_plan.sh:78-103`)：
  "该提交的必须提交" 已被 `check_artifacts_committed` **硬阻断** (`return 1`)，worktree 创建前必查 openspec artifacts 与 `.rddf/plans/` 提交状态。但"不该提交的必须 gitignored" 只有 `guide/scan-state.sh:408-424` 软提示（"建议加到 .gitignore 或清理"），无任何入口会阻断启动流程。这是当前最明显的**硬/软门控不对称**——前者强制，后者放任，导致状态文件可能被误跟踪。

- **测试自身把契约当断言** (`tests/integration/test_plan_review_phase.bats:62-66`)：
  rdd-workflow 自身测试要求目标项目 `.gitignore` 含 `.rddf/state/` 才能跑通，但普通用户的下游项目不会跑这测试，所以契约"潜规则化"——只在 rdd-workflow 自己的仓库里生效。

- **ADR-0016 (arch artifact discovery contract)**：本提案复用其"先发现路径，再 fallback 到默认"模式。gitignore 检查也走同样模式——先看 `.rddf/state/` 模式，再看兜底 `.rddf/`，避免对自定义布局产生 false negative。

- **ADR-0019 (change-arch-alignment)**：本提案无架构变更，仅扩展现有 `arch_env_check.sh` + `scan-state.sh`，不引入新概念层，保持 ADR-0019 一致性约束。

- **空白填补**：`improvements/` 目录现存 87 个文件中**无 `check-*` 命名**，无 `.gitignore` 相关提案，无项目设置体检相关提案。本提案**填补空白**，不与任何现有提案重复。

## 范围

**In Scope**:
- 新建 `skills/_lib/check_project_setup.sh`（~80 行 bash）+ 对应 bats 单元测试 `tests/integration/test_check_project_setup.bats`（~6 cases）
- helper 单函数签名：`check_project_setup <project_root>`，stdout 输出 JSON 数组（与 `WT_ISSUES_JSON` 同 schema）
- 每个 issue 结构：`{name, status, severity, fix_command, detail}`
  - `status`: `pass` / `fail` / `warn`
  - `severity`: `error`（硬阻断候选）/ `safe_auto_fix`（菜单展示候选）/ `info`
- 检查项 6 条：
  ① `.rddf/state/` 必须 gitignored
  ② `.rddf/wt/` 必须 gitignored
  ③ `.rddf/plans/` **未** gitignored（regression 检测）
  ④ openspec CLI 可用（已存在，调用 `arch_env_check.sh` 已有的检测段复用）
  ⑤ git HEAD 存在（已存在，调用 `check_artifacts_committed` 已有的检测段复用）
  ⑥ 大未跟踪目录（>10MB build 产物）——已部分存在（`scan-state.sh:408-424`），本提案提取到共享 helper 避免重复
- 3 个集成点：
  - **`guide-arch` Phase 1** (`skills/guide-arch/scripts/arch_env_check.sh`)：末尾追加 `check_project_setup` 调用，若 `severity == "error"` 项 fail 则 `return 1` **硬阻断**，输出对应 `fix_command`
  - **`guide` 推荐器** (`skills/guide/scripts/scan-state.sh`)：所有 issue 走 `safe_auto_fix` 软路径，AI 在菜单前分析展示，**不阻断**
  - **`skills/INSTALL.md`**：末尾新增 Section "5. 项目设置检查"，作为 post-install sanity check，逐项列出当前状态（✅/❌），不阻断安装流程
- 测试整合：`tests/integration/test_plan_review_phase.bats:62-66` 现有的 `.rddf/state/` 断言改为对 `check_project_setup` helper 的断言（消除重复）
- 文档更新：`USAGE.md` / `INSTALL.md` / `docs/v2-workflow-overview.md` 简短文档（合计 ~25 行）说明"项目设置检查何时触发 + 用户期望什么"

**Out Scope**:
- ❌ 不修改任何 `.gitignore` 模板文件（用户项目可能有 monorepo 自定义 ignore 模式）
- ❌ 不引入新 skill / menu 项（check 不出现在 `ALL_OPTIONS_JSON`，是隐式断言，不是用户主动调用的工具）
- ❌ 不做 `--auto-fix` CLI flag 或环境变量（auto-fix 边界已确认只显示 `fix_command`）
- ❌ 不修改 `guide-ship` 的 COMMIT GATE（已是硬门控，无需加强）
- ❌ 不动 ADR-0016 / 0017 / 0019（无架构变更）
- ❌ 不引入 Python helper（gitignore 检查是纯文本 `grep`，bash 更轻；与 `arch_env_check.sh` / `scan-state.sh` 现有风格一致）
- ❌ 不做 IDE / 编辑器层 hook（超出 rdd-workflow 边界）

## 关键场景

- **GIVEN** 用户项目根有 `.gitignore` 但**缺少** `.rddf/state/` 和 `.rddf/wt/` 规则
  **WHEN** 用户运行 `skill_use("guide-arch")` 进入 Phase 1 `arch_env_check`
  **THEN** helper 检测到 2 个 issue，在 arch-done gate 前**硬阻断**，输出每个 issue 的 `fix_command`（如 `echo ".rddf/state/" >> .gitignore && echo ".rddf/wt/" >> .gitignore`），退出码非零

- **GIVEN** 用户已正确配置 `.gitignore`（含 `.rddf/state/` 且**不含** `.rddf/plans/`）
  **WHEN** 任何入口（`guide` / `guide-arch` / `INSTALL`）触发 check
  **THEN** 全部通过，helper 输出绿色 ✅ 列表，不展示任何 `fix_command`，流程正常继续

- **GIVEN** 用户项目误将 `.rddf/plans/` 加进了 `.gitignore`（regression）
  **WHEN** check 执行
  **THEN** 检测到反向 issue（"MUST NOT" 违反），`severity=error`，给出移除命令（如 `sed -i '/^\.rddf\/plans\//d' .gitignore`），`guide-arch` 阶段硬阻断

- **GIVEN** 项目根存在 `node_modules/` 等大未跟踪目录（>10MB）
  **WHEN** check 在 `guide` 或 `INSTALL` 触发
  **THEN** 报告为 `severity=safe_auto_fix`，AI 展示 `fix_command`，需用户输入 `y` 才执行；**不在 `guide-arch` 阻断**

- **GIVEN** 项目根**没有** `.gitignore` 文件
  **WHEN** check 执行
  **THEN** 报告为 `severity=error`，建议 `touch .gitignore && cat <<EOF >> .gitignore\n.rddf/state/\n.rddf/wt/\nEOF`；`guide-arch` 阶段硬阻断

- **GIVEN** check 在 `INSTALL.md` 末尾首次触发
  **WHEN** 用户刚完成 rdd-workflow 安装
  **THEN** 输出友好信息（"建议在第一次使用前完成以下项目设置检查"），逐项列出当前状态（✅/❌ + `fix_command`），**不阻断**安装流程

## 技术约束

**MUST**:
- 新 helper `skills/_lib/check_project_setup.sh` 暴露单函数 `check_project_setup <project_root>`，stdout 输出合法 JSON 数组（与 `WT_ISSUES_JSON` 兼容）
- 每个 issue 必须含字段：`name`（字符串）、`status`（`pass` / `fail` / `warn`）、`severity`（`error` / `safe_auto_fix` / `info`）、`fix_command`（可选 bash 字符串）、`detail`（中文一行说明）
- `arch_env_check.sh` 调用 check 时，若任一 `severity == "error"` 项 `status == "fail"`，则 `return 1` 阻断 phase；并 stdout 输出对应 `fix_command`
- `scan-state.sh` 调用 check 时，所有 issue 一律走 `safe_auto_fix` 软路径（**不阻断**），由 AI 在菜单前按 `guide/SKILL.md` 的清理分析流程展示
- bats 测试必须 ≥ 6 个：① 通过项目；② 缺 `.rddf/state/`；③ 误含 `.rddf/plans/`（regression）；④ 无 `.gitignore`；⑤ 大目录检测；⑥ helper 输出 JSON schema 合规
- 复用 `tests/integration/test_plan_review_phase.bats:62-66` 的现有断言（提取为对 helper 的断言）
- 每次 gitignore 检查同时输出"现状"和"期望"，方便用户 diff 对比

**MUST NOT**:
- ❌ 不在 helper 内修改 `.gitignore`（auto-fix 边界已确认）
- ❌ 不引入新的 skill / menu 项（不进 `ALL_OPTIONS_JSON`）
- ❌ 不把 `.gitignore` 检查逻辑塞进 `guide-arch` SKILL.md 内联（必须放 `_lib/` helper，保持 Round A/B 提取纪律）
- ❌ 不修改 `arch_env_check.sh` 已有的 openspec CLI / build dir / ADR count 等 5 个检查（保持向后兼容；只在末尾追加新调用）
- ❌ 不写死任何 build 产物目录名（如 "node_modules"），只检查 `.rddf/*` 系列
- ❌ 不创建 Python helper（bash 足够；与现有风格一致）

**SHOULD**:
- `INSTALL.md` 集成时建议放在 Section "5. 项目设置检查"（而非顶部，避免打断安装流程）
- helper 单次执行 < 50ms（git 操作不进入 hot path）
- 在 `USAGE.md` "常见陷阱" 章节追加一条："若首次 `guide-arch` 失败并提示修复 `.gitignore`，按 `fix_command` 执行后重跑"

## 验收标准

- [ ] **AC1**: `bats tests/integration/test_check_project_setup.bats` 全部 ≥ 6 用例通过
- [ ] **AC2**: `python3 -m pytest tests/` 全绿（确保无 Python 回归）
- [ ] **AC3**: `npm test`（bats 全量）全绿
- [ ] **AC4**: 手工 e2e：3 个 fixture 项目（正确 / 缺 state / 误含 plans）跑 `skill_use("guide-arch")` Phase 1，行为符合 §3 关键场景描述
- [ ] **AC5**: helper 单次执行 `time check_project_setup /tmp/test` < 50ms（在 SSD 上）
- [ ] **AC6**: `improvements/check-project-setup.md` 和 `proposal-suggestions.md` 注册行均存在；后者格式匹配 `docs/proposal-suggestions-format.md:26-30` 示例
- [ ] **AC7**: `USAGE.md` / `INSTALL.md` / `docs/v2-workflow-overview.md` 文档更新提到"项目设置检查何时触发 + 用户期望什么"
- [ ] **AC8**: 实施 commit 至少包含：① helper 文件 + bats 测试；② `arch_env_check.sh` 集成；③ `scan-state.sh` 集成；④ `INSTALL.md` Section 5；⑤ `proposal-suggestions.md` 注册（合并到第 ① 个 commit 也可）
- [ ] **AC9**: `git diff --stat` 净增行 ≤ 400 行（与 Round A/B 提取纪律一致）
- [ ] **AC10**: 无新 ADR 写入（属于增量改进，不构成架构变更）
