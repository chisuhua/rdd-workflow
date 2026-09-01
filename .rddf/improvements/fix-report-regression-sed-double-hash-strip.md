# fix-report-regression-sed-double-hash-strip

**优先级**: P0 | **来源**: 2026-08-31 ship 阶段回归门发现 — KNOWN_FAILURES 条目 `every real ADR has a ## 决策 or ## Decision section` 无法被报告脚本承认
**阶段**: v2.2 | **分类**: infra-setup / 测试基建
**类型**: bug fix

> **症状**：`tests/scripts/report_regression.sh` 的 `sed -E 's/[[:space:]]+#.*$//'` 会把 bats TAP description 中含 `##` 的行错误截断，导致 baseline 条目与实际失败无法匹配，`report_regression.sh` 误报"新增失败：1"，阻塞回归门 pass。
> **根因**：`[[:space:]]+#` 正则中 `#` 匹配描述中的首个 `#`（即 `##` 的前导），而 `##` 是 bats description 的合法内容（如 `every real ADR has a ## 决策 or ## Decision section`）。
> **临时绕过**：本次会话把 KNOWN_FAILURES 条目改为不含 `#` 的纯 description（去掉 `adr_directory:` 前缀），第 2 轮回归门才收敛。

## 架构依据

**症状 (2026-08-31 ship 阶段, 2 个 P1 change 触发)**:

- `test_adr_directory.bats` 有 2 个 test 含 `##` 在 description 中：
  - `every real ADR has a ## 决策 or ## Decision section`（缺 Decision section）
  - `every real ADR has status and date fields`（缺 date field）
- 2 个 ADR 文件（ADR-0035 缺 Decision section、ADR-0034 缺 date field）触发 2 个 bats fail
- 手工往 `tests/KNOWN_FAILURES.txt` 加条目 `adr_directory: every real ADR has a ## 决策 or ## Decision section # ...`
- **但** `report_regression.sh` 用 `sed -E 's/[[:space:]]+#.*$//'` strip `#` 后，条目变成 `adr_directory: every real ADR has a`（`##` 被当作注释起点截断）
- bats TAP actual description 同样被 sed 截成 `every real ADR has a`（`##` 前导 `#` 被误判）
- 结果：`comm -23 actual baseline` 报 `every real ADR has a` 算**新增失败**——即使 baseline 里已有 `every real ADR has a ## 决策...` 条目
- 修复：把 KNOWN_FAILURES 条目 prefix 去掉 + 纯 description（不含 `adr_directory:`），第 2 轮才收敛

**根因分析**:

`tests/scripts/report_regression.sh` 的 description 处理链（L27-L31 附近）:

```bash
sed -nE 's/^not ok [0-9]+ (.*)$/\1/p' "$TMP_DIR/bats-output" \
  | sed -E 's/[[:space:]]+#.*$//' \
  | sed '/^[[:space:]]*$/d' \
  | sort -u >"$TMP_DIR/actual"
```

问题在 `sed -E 's/[[:space:]]+#.*$//'`：

- 意图：strip 每行 `#` 后的注释文本，只保留 description
- 缺陷：`[[:space:]]+#` 匹配任何"空白后跟 #"；当 description 本身含 ` #`（如 `a ## 决策`）时，`[[:space:]]+#` 匹配到首个 ` #`（`##` 的前导），把 `## 决策 or ...` 整个截掉
- 正确行为应是：strip ` #` 后接**非空白**内容的注释（如 ` # pre-existing: ...`），保留 ` ## 决策` 这类 description 内的 `##`

**影响范围**:

- 任何 bats description 含 `##` / `# `（如 markdown 引用、注释、矩阵标题）都会被 sed 误截
- 当前 133+ 条 KNOWN_FAILURES 中，含 `#` 的 description 全部受影响（potential silent false-postive）
- 回归门对"新增失败"的判断依赖此 strip 逻辑，误报直接阻塞 archive（P0 级影响）

## 范围

### In Scope

**A. 修正 sed 正则（`tests/scripts/report_regression.sh` L28 附近）**:

- 将 `sed -E 's/[[:space:]]+#.*$//'` 改为更严格模式
- 方案 1（推荐）：`sed -E 's/[[:space:]]+#[A-Za-z].*$//'` — 仅 strip ` #` 后接字母的注释（`# pre-existing:` / `# historical:` 模式）
- 方案 2（备选）：`awk` 实现状态机：遇到 ` #` 时检查后一个 char 非 `#` 才 strip
- 方案 3（最稳）：Python 单行处理（bash wrapper 内嵌 python3 -c，或提取到 `tests/scripts/report_regression_helper.py`）——按 ` # ` 分隔，仅当分割后 2+ 段且第 2 段以字母开头才算注释
- 无论方案，必须保持现有 ` # pre-existing:` / ` # historical:` 注释 strip 行为（132+ 条 baseline 依赖）

**B. 单元测试（新 `tests/unit/test_report_regression_strip.py`）**:

- 5 个 test 覆盖 strip 逻辑在各种输入上：
  - `strip removes # comment when followed by space+letter`
  - `keep ## inline double-hash description`
  - `keep # ADR-NNNN: header description`
  - `keep description with no comment`
  - `keep description with trailing # no comment`

**C. bats 集成测试（新 `tests/integration/test_report_regression_descriptions.bats`）**:

- 3 个 test 验证整个 `report_regression.sh` 解析链：
  - `regression-parse: ## description in real ADR test matched to baseline`
  - `regression-parse: # ADR-NNNN header description matched`
  - `regression-parse: baseline entry with # comment still strips correctly`

**D. 把本次会话的 KNOWN_FAILURES 修正固化为回归保护**:

- 现有 4 条 pre-existing WIP 条目（`cli_all_subcommands` / `adr_index` / `adr_directory` / `setup_file failed`）保留
- 断言 `every real ADR has a ## 决策 or ## Decision section` 现在能被脚本正确匹配

### Out Scope

- **不修改** `report_regression.sh` 的 overall 逻辑（comm -23 新增失败判定 / 退出码语义）
- **不修改** KNOWN_FAILURES.txt 现有内容（已全部修正，只加保护性测试）
- **不修改** bats test 本身的 description（`##` 是合法内容，不能改 test 来适配 bug）
- **不实现** sed 的完全通用 `#` 解析（只保证当前 repo 的 description 模式）

## 关键场景

### 场景 1: bats description 含 `##` 的 test

- **GIVEN** `test_adr_directory.bats` 的 `@test "every real ADR has a ## 决策 or ## Decision section"`
- **WHEN** `report_regression.sh` 处理实际失败
- **THEN**
  - strip 逻辑保留 `## 决策 or ## Decision section`（不截断到 `every real ADR has a`）
  - baseline 同文本条目被 `comm -12` 正确匹配
  - `新增失败: 0`

### 场景 2: 现有 132 条 baseline 的 ` # pre-existing:` 注释

- **GIVEN** baseline 条目 `adr_directory: ... # pre-existing: rdd_verifier_skip tests added post-baseline`
- **WHEN** strip 逻辑运行
- **THEN**
  - ` # pre-existing:` 被 strip（后接字母 `p`）
  - description `adr_directory: ...` 保留
  - `comm -12` 正确匹配实际失败

### 场景 3: description 含 `# ADR-NNNN:` 标题（如 `every real ADR has a # ADR-NNNN: header`）

- **GIVEN** hidden test scenario（当前不触发，但逃避本 bug 的同类）
- **WHEN** strip 逻辑运行
- **THEN** ` # ADR-NNNN:` 中 `# ADR-NNNN:` 后是字母 `A`（或数字）→ 被 strip？NO——本方案需区分：`# ADR-NNNN:` 是 description 一部分，不是注释
  - 方案 1（`# [A-Za-z]`）会把 `# ADR-NNNN:` 误 strip（`# ` + `A`）
  - **修正**：方案 1 需改为 ` #[A-Za-z]*:` 或使用更保守的 ` # pre| # hist| # b` 白名单模式
  - 最稳方案 3（Python）：`re.sub(r' # ([a-z]+):', ' # \\1:', line)` 或检查 strip 后 description 非空且与原 description 前缀一致

### 场景 4: 无注释的 description

- **GIVEN** `every real ADR has status and date fields`（无 `#`）
- **WHEN** strip 逻辑运行
- **THEN** 原样保留，comm 匹配不受影响

## 技术约束

- **MUST NOT**: 破坏 `report_regression.sh` 的 overall 行为（exit code / comm 语义 / 输出格式）
- **MUST NOT**: 修改 132+ 条既有 baseline 条目的内容（除非本 bug 影响的 2 条已按需修正，且受测试保护）
- **MUST NOT**: 引入新依赖（sed/awk 或 python3 均可用，任选但不能加第三方包）
- **MUST**: 优先选择能与现有 bash 脚本风格一致的实现（`report_regression.sh` 是纯 bash + sed/awk/python3）
- **SHOULD**: 如果提取 Python helper，遵循 `tests/scripts/` 下 `_env.py` 的 env-var 模式（Oracle C1）
- **SHOULD**: 单元测试跑完 < 1s（纯字符串操作）

## 验收标准

### 单元与集成测试

- [ ] `tests/unit/test_report_regression_strip.py` 5 个 test PASS
- [ ] `tests/integration/test_report_regression_descriptions.bats` 3 个 test PASS
- [ ] 复测 `bash tests/scripts/report_regression.sh` 输出 `✅ 0 新增失败`（现共赢，回归保护）
- [ ] 显式复测 2 条含 `##` 的 ADR test description 被正确匹配（`every real ADR has a ## 决策 or ## Decision section`）

### 端到端验证

- [ ] `./test.sh --full --regression` 在当前 2 个已修复 ADR 场景跑出 0 新增失败（回归门 pass）
- [ ] 故意引入 1 个 description 含 `##` 的新 test fail → 报告脚本正确报"新增失败：1"且列出完整 description
- [ ] 与 `fix-specs-auto-generate-in-design-precreated` (P0-1) 无交互：spec 修复不影响 report_regression 解析

### 文档化

- [ ] `docs/change-quality-guide.md` 加"回归门 description 解析"新段（解释 `##` 陷阱 + 正确格式）
- [ ] `tests/scripts/report_regression.sh` 头注释加说明"description 处理规则"

### 兼容性验证

- [ ] 复测当前 KNOWN_FAILURES.txt 132+ 条全量匹配（无新增失败、无 stale）
- [ ] 复测 pre-existing WIP 条目（`cli_all_subcommands` 等）仍被正确 strip + match
- [ ] 与 `add-known-failures-baseline` 提案（既有）不冲突：baseline 格式不变

### 副作用监测

- [ ] ship 后 30 天观察期：回归门"新增失败"误报率降至 0（历史：因本 bug 误报 1 次，需手工修）
- [ ] 不引入新的 KNOWN_FAILURES 条目（改动仅在第 3 阶段）

## Why

- **现状痛点**：bats description 常含 `##`（markdown 风格标题、引用），`report_regression.sh` 无法正确解析，导致回归门误报"新增失败"并阻塞 archive。每次触发需人工诊断 30-60 分钟（本会话：4 轮回归门 + sed 分析）。
- **修复价值**：消除回归门 1 类系统性误报源，让"新增失败" 判定可靠。当前 132+ 条 baseline 中所有含 `##` 的 description 都可能暗藏误报风险，本修复系统性消除。
- **Why now**: 2026-08-31 session 首次真实触发（ADR-0035/0034 结构漂移），且未来任何需求含 `##` 的 bats 新增都会踩中。P0 而非 P1 因为它直接影响回归门可信度（核心 QA gate），且当前 KNOWN_FAILURES 依赖 strip 逻辑才能正确收敛。

## What Changes

- `tests/scripts/report_regression.sh`: 修正 sed strip 正则（~5 行改动）
- `tests/unit/test_report_regression_strip.py`: 新文件，5 个单元测试
- `tests/integration/test_report_regression_descriptions.bats`: 新文件，3 个集成测试
- `docs/change-quality-guide.md`: 新增"回归门 description 解析"段
- `tests/scripts/report_regression.sh`: 头注释更新

## Capabilities

- MUST: 正确 strip ` # pre-existing:` / ` # historical:` 后缀注释
- MUST NOT: 截断 description 内合法的 `##` / `# ADR-NNNN:` 内容
- MUST NOT: 破坏 `comm -23` 新增失败判定语义

## Impact

- MUST: `report_regression.sh` 解析逻辑改动不改变退出码语义（0 = 无新增 = pass）
- MUST: 单元测试覆盖 strip 规则变更，防止未来回归
- SHOULD: 与 `bypass-audit-mechanism` (P2 延迟提案) 无交互：不触碰 proposal-suggestions.md
- MUST NOT: 在 KNOWN_FAILURES.txt 添加本 bug 的 workaround 条目（应修根因而非加 baseline）

## Acceptance

- [ ] `tests/unit/test_report_regression_strip.py` 5 个 test PASS
- [ ] `tests/integration/test_report_regression_descriptions.bats` 3 个 test PASS
- [ ] `bash tests/scripts/report_regression.sh` 输出 `✅ 0 新增失败`（回归保护）
- [ ] 复测含 `##` 的 2 条 ADR test description 正确匹配
- [ ] 人工复测：临时加 1 条含 `##` 的 fail test → 报告正确列出完整 description（非截断）
- [ ] `documentation / tests / report_regression.sh` 头注释同步更新