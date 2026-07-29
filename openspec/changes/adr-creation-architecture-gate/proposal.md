## Why

ADR 的准确定义是"影响架构方向的决策"，但当前 guide-arch Phase 2 (adr-create) 无条件允许创建任何 ADR。8 个建议的 ADR 议题经 Oracle 校准后发现仅 2 个真正属于架构决策，其余是运维流程、工具配置、过程度量。弱 ADR 的存在稀释了 ADR 集合的信号密度。

## What Changes

- guide-arch Phase 2 (adr-create) 选项 1（创建新 ADR）之前插入"架构影响力判定"步骤
- Oracle 调用评估 5 项检查：模块边界/分层规则、核心抽象/接口契约、数据结构/算法选型、跨层依赖规则、硬件行为建模策略
- 返回分类：ARCHITECTURE（允许创建）、GOVERNANCE（二次确认）、IMPLEMENTATION（阻止创建）
- 支持 `SKIP_ADR_GATE=yes` 跳过判定

## Capabilities

### New Capabilities
- `adr-architecture-gate`: ADR 创建前的架构影响力门控

### Modified Capabilities
- `adr-creation-flow`: 在 guide-arch Phase 2 中增加判定步骤

## Impact

- 新建文件：skills/guide-arch/scripts/adr_gate.sh
- 修改文件：skills/guide-arch/SKILL.md
- 输出文件：.rddf/state/last-adr-gate-result.json（可审计）
- 环境变量：SKIP_ADR_GATE
