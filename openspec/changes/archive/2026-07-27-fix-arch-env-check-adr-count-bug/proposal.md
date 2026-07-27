# fix-arch-env-check-adr-count-bug

**优先级**: P2 | **来源**: 2026-07-27 会话复盘
**阶段**: default | **分类**: core-impl
**类型**: bug

## 架构依据

- **ADR-0016** §Layer 2：arch-handoff schema 的 `adr_pattern` 字段定义了通配符模式（`ADR-*.md`），
  `discover-arch-artifacts.sh` 通过 `discover_adr_pattern()` 导出 `DISCOVERED_ADR_PATTERN` 变量。
  该变量是 glob 模式（含 `*`），不可被双引号包裹——否则 shell 不展开通配符。
- **bash 引号语义**：双引号内变量展开有效，但路径名展开（glob）被抑制。
  `"$DIR/$PATTERN"` → `$PATTERN` 中的 `*` 成为字面字符。
- **`arch_done_gate.sh` 不受影响**：该脚本用 `ls -d "$DIR"/ADR-*.md | grep -v template` 做计数，
  引号在 glob 之前结束，`*` 正确展开。arch_env_check.sh 应保持一致方式。

## 范围

- **In Scope**:
  - 修复 `skills/guide-arch/scripts/arch_env_check.sh` 第 90 行 ADR 计数中的引号位置
  - 确保 `ls -d` 的 glob 模式可被 shell 正确展开
  - 添加 2 个 bats 回归测试（有 N 个 ADR 时计数正确、空目录时计数为 0）

- **Out Scope**:
  - 不修改第 92（GAP_COUNT）、第 93 行（ACTIVE_CHANGES）— 它们引号已正确
  - 不修改 `discover-arch-artifacts.sh` 的任何逻辑
  - 不修改 `arch_done_gate.sh`（已正确）
  - 不引入 `nullglob` / `find` / bash 数组（保持改一行原则）
  - 暂不在此 change 中排除 `ADR-0000-template.md` 计数（独立 issue）

## 关键场景

- GIVEN `docs/adr/` 目录含 24 个 ADR-*.md 文件（含 ADR-0000-template.md）
  WHEN `run_arch_env_check` 被调用
  THEN 输出 `📋 现有 ADR: 24`（修复前输出 0）

- GIVEN `docs/adr/` 目录不存在或为空
  WHEN `run_arch_env_check` 被调用
  THEN 输出 `📋 现有 ADR: 0`

- GIVEN `DISCOVERED_ADR_PATTERN` 为合法 glob 模式（如 `ADR-*.md`）
  WHEN `ls -d` 用该模式列出文件
  THEN shell 正确展开通配符，返回匹配文件列表

- GIVEN `DISCOVERED_ADR_DIR` 包含空格（如 `my docs/adr`）
  WHEN 计数命令执行
  THEN 目录路径被正确引用保护，不因空格丢词

## 技术约束

- **MUST**：修复后 glob 在双引号外展开，保持与 `arch_done_gate.sh` 一致的引号方式
- **MUST**：DIFF 仅一行变更（第 90 行引号位置移动）
- **MUST NOT**：不引入 `nullglob` / `find` / bash 数组（保持改一行原则）
- **MUST NOT**：不过滤 `ADR-0000-template.md` — 模板排除是独立 issue
- **SHOULD**：添加 2 个 bats 回归测试锁定

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | `run_arch_env_check` 在有 N 个 ADR 的仓库中输出 `现有 ADR: N`（非 0） | `bats` 集成测试：fixture 放 N 个 ADR-*.md，grep 断言输出 |
| 2 | 空 ADR 目录时输出 `现有 ADR: 0` | `bats` 集成测试：空 fixture 目录 |
| 3 | GAP_COUNT、ACTIVE_CHANGES 计数不受修复影响 | 现有 bats 全部通过 |
| 4 | DIFF 只有一行变更（第 90 行引号位置移动） | `git diff --stat` 确认 |
