# adr-creation-architecture-gate

**优先级**: P1 | **来源**: Oracle 审查 2026-07-25 — ADR 创建缺少架构影响力门控
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据

- ADR 的准确定义是"影响架构方向的决策"（模块边界、接口契约、分层规则、核心抽象），但当前 guide-arch Phase 2 (adr-create) **无条件允许创建任何 ADR**
- 本次 Session 中，8 个建议的 ADR 议题经 Oracle 校准后发现 **仅 2 个**（ADR-069 BAR/ioremap、ADR-072 可移植性验证）真正属于架构决策，其余是运维流程、工具配置、过程度量
- 项目中已有 65 个 ADR，弱 ADR 的存在（如 ADR-012 优化技术目录）稀释了 ADR 集合的信号密度
- ADR-035 Governance Policy 未定义 ADR 创建时的质量门控——只定义了编号、命名、状态流转规则
- 项目现有最強 ADR（ADR-036 3 区分、ADR-023 HAL 契约、ADR-043 CP 边界）的共同特征是在创建时经过了架构层面的判定

## 范围

- **In Scope**:
  - guide-arch Phase 2 (adr-create) **选项 1（创建新 ADR）之前**插入一个 "架构影响力判定" 步骤
  - 判定逻辑：要求用户先描述议题，然后单次 Oracle 调用评估：
    1. 是否定义模块边界/分层规则？
    2. 是否定义核心抽象/接口契约？
    3. 是否涉及数据结构/算法选型（基础性的，非实现细节）？
    4. 是否建立跨层依赖规则？
    5. 是否定义硬件行为建模策略？
  - Oracle 返回：`ARCHITECTURE`（影响架构）| `GOVERNANCE`（治理/流程 ADR，如版本策略、测试框架选型）| `IMPLEMENTATION`（实现细节，应放入设计文档/CI 配置/tasks.md，不应成为 ADR）
  - `ARCHITECTURE` → 允许创建 ADR
  - `GOVERNANCE` → 提示"治理类 ADR 应谨慎创建"，要求用户二次确认（推荐放入 RELEASE.md / ci-cd.md / CONTRIBUTING.md 等流程文档）
  - `IMPLEMENTATION` → 阻止创建 ADR，建议替代存放位置（如 `docs/`、`.github/`、`tasks.md`、`roadmap.md` 子任务说明）
  - 支持 `SKIP_ADR_GATE=yes` 跳过判定（紧急/低风险场景）
- **Out Scope**:
  - 不修改现有 65 个 ADR（不在 scope 内做 retroactive audit）
  - 不修改 ADR-035 Governance Policy 本身（门控是 guide-arch 执行层行为，不影响 ADR 元规则）
  - 不修改 ADR 模板格式
  - 不阻止治理类 ADR（仅要求二次确认）

## 关键场景

- GIVEN 用户描述一个议题, WHEN 判定为 ARCHITECTURE, THEN 正常创建 ADR（无额外确认）
- GIVEN 用户描述一个议题, WHEN 判定为 GOVERNANCE, THEN 显示"这是治理/流程决策，不是架构决策。建议放入 [替代路径]。确认创建？(y/N)"
- GIVEN 用户描述一个议题, WHEN 判定为 IMPLEMENTATION, THEN 阻止 ADR 创建，显示"这不是架构决策，建议放入 [具体替代路径]。仍要创建？设置 SKIP_ADR_GATE=yes 跳过"
- GIVEN SKIP_ADR_GATE=yes, WHEN 创建 ADR, THEN 跳过判定步骤，直接创建
- GIVEN 判定失败（Oracle 不可用）, WHEN 创建 ADR, THEN 降级为静默跳过（warn + 继续，不阻断）

## 技术约束

- MUST 在 guide-arch SKILL.md Phase 2 选项 1 执行路径中插入判定步骤
- MUST 可提取为独立脚本 `skills/guide-arch/scripts/adr_gate.sh`（调用 Python Oracle helper）
- MUST 超时 60s（Oracle 调用）后降级为跳过
- MUST 支持 `SKIP_ADR_GATE=yes` 环境变量
- SHOULD 判定结果写入 `.rddf/state/last-adr-gate-result.json`（可审计）
- SHOULD Oracle prompt 包含判定 rubric（5 项检查 + 分类标准 + 替代路径建议）

## 验收标准

- `skills/guide-arch/scripts/adr_gate.sh` 存在并可独立调用
- ARCHITECTURE 判定 → 无阻断，正常创建 ADR
- GOVERNANCE 判定 → 二次确认后才允许
- IMPLEMENTATION 判定 → 阻止，提供替代路径
- SKIP_ADR_GATE=yes → 跳过所有判定
- Oracle 超时/不可用 → 降级为 warn + 继续
- guide-arch SKILL.md Phase 2 文档更新（记录判定步骤）