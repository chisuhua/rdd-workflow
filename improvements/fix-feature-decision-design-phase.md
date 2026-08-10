# fix-feature-decision-design-phase

**优先级**: P1 | **来源**: 用户讨论 2026-08-10 — feature 决策应在 design 阶段完成
**阶段**: v2.1 | **分类**: planning | **类型**: fix
**依赖**: | **特性**:

## 架构依据

- `add-proposal-deps-and-features` (P1，已批准并归档于 commit `2a15ba9`) 定义了 `**特性**` 字段为 design 阶段的 feature 标签，明确承诺 "feature 标签自动写入 iteration.json 的 parent_feature"
- 该字段在 `proposal-approved.md` 表格中已有 `特性` 列，但**没有任何生产代码路径解析这个字段**：
  - `skills/guide-design/scripts/approve_proposal.sh:142` 只读 `PARENT_FEATURE` 环境变量，不读 improvements 文件
  - `skills/propose/scripts/propose_change.py::create_skeleton_change` 只接受函数参数 `parent_feature`，不读 improvements 文件
- 影响：用户在 `improvements/<name>.md` 头部写 `**特性**: wave-core` 后，feature 视图（`feature` skill）不识别，只能回退到命名约定（`feature-<name>-<sub>` 前缀）或手动传 env var
- 与 ADR-0022 (manual_deps 字段) 的精神一致 — proposal 头部字段是 design 阶段决策的载体，应被下游路径尊重
- 与 ADR-0025 (design-proposal-creation) 的设计意图一致 — design 阶段"应有实质审查"，feature 归属属于此类决策

## 范围

- **In Scope**：
  - `skills/guide-design/scripts/approve_proposal.sh`：从 `**特性**` 头部解析 feature 名，作为 `PARENT_FEATURE` 的回退（env var 优先）
  - `skills/propose/scripts/propose_change.py::create_skeleton_change`：当 `parent_feature` 参数为 `None` 时，从 `**特性**` 头部读
  - Python 正则用 `[ \t]*` 而非 `\s*`，避免跨行匹配到下一节（latent bug 防御）
  - 新增 bats 集成测试（3 个 case）+ Python 单元测试（3 个 case）锁定行为
- **Out Scope**：
  - 不修 `**类型**` / `**阶段**` / `**分类**` 的 `\s*` 跨行 latent bug（独立提案，避免本次范围扩散）
  - 不改 `approve_proposal.sh` 里 `iteration.json` 写入部分（独立 bug — 已存在但未写入 parent_feature；超出本 fix 范围）
  - 不做 guide-design 阶段 feature preview UX 增强（B 方案）— 等本 fix 稳定且被使用后再评估
  - 不改 schema，不写 ADR，不改 proposal-suggestions.md 格式

## 关键场景

- GIVEN `improvements/demo.md` 头部含 `**依赖**: | **特性**: wave-core`，WHEN 调用 `approve_proposal.sh demo P1 $ROOT`（无 `PARENT_FEATURE` env var），THEN `openspec/changes/demo/roadmap-meta.yaml` 含 `parent_feature: "wave-core"`
- GIVEN improvements 头部含 `**特性**: from-file`，WHEN 设置 `PARENT_FEATURE=from-env` 调用 `approve_proposal.sh`，THEN roadmap-meta.yaml 含 `parent_feature: "from-env"`（env var 优先于文件）
- GIVEN improvements 头部含空 `**特性**: `，WHEN 调 `create_skeleton_change(parent_feature=None)`，THEN roadmap-meta.yaml 含 `parent_feature: null`（空 特性 不污染其他字段）
- GIVEN `create_skeleton_change(parent_feature="explicit")` 且 improvements 头部写 `**特性**: from-file`，THEN 写入 `"explicit"`（参数优先于文件）

## 技术约束

- MUST 镜像 `**类型**` 字段解析模式（grep + sed + xargs 或 re.search），保持代码一致性
- MUST `PARENT_FEATURE` env var 优先于 `**特性**` 字段（env var 是显式覆盖通道）
- MUST `parent_feature` 函数参数优先于 `**特性**` 字段（同上）
- MUST NOT 修改 `**类型**` / `**阶段**` / `**分类**` 的解析逻辑（out of scope）
- SHOULD Python 正则用 `[ \t]*` 而非 `\s*`，避免跨行匹配（与 bash grep 行为对齐）
- SHOULD 空 `**特性**: ` 视为"无 feature 标签"，不报错，落到 `parent_feature: null`

## 验收标准

- [ ] `tests/integration/test_approve_proposal_parent_feature.bats` 3 个 case 全绿
- [ ] `tests/unit/test_propose_change_parent_feature.py` 3 个 case 全绿
- [ ] 现有 `test_approve_proposal_*.bats` 中除 KNOWN_FAILURE 外的所有 case 仍绿
- [ ] 现有 `tests/unit/test_propose_change*.py` 全部仍绿
- [ ] 现有 Python 单元测试套件（1272 个）全部仍绿
- [ ] 全量 bats 套件无新增失败（与 `tests/KNOWN_FAILURES.txt` baseline 对比）
- [ ] `add-proposal-deps-and-features` 验收标准的 "feature 标签自动写入 iteration.json 的 parent_feature" 项现在被实际兑现（隐含回归覆盖）