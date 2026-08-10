# wire-plan-done-quality-gates

## Why

- ADR-0007 定义了 plan_done 门控及 error/warning 两级严重度，warning 默认不阻断，error 才阻断阶段切换。
- ADR-0019 定义了 `change_alignment` 的三个 plan_done 对齐检查，并规定默认 warning、`STRICT_CHANGE_GATE=yes` 时升级为 error。
- 当前代码中已有 `run_plan_checks` 与 `change_alignment` 检查，但正常 `guide-plan` 的 `plan_done_gate` 执行路径可能未调用它们，导致已采纳的质量决策停留在可用但未生效的检查资产上。
- `propose-quality-autohook` 已讨论质量检查自动挂载的必要性，`add-change-content-review` 则覆盖 change artifact 的内容审查。本文只解决现有 plan-done 检查的实际路径接线，不重复这些提案的检查内容。

## What Changes

**In Scope**:

- 将现有 `run_plan_checks` 接入 `guide-plan` 的 `plan_done_gate` 正常执行路径。
- 将现有 `change_alignment` 检查接入同一 plan-done 路径，并保持其独立的 `STRICT_CHANGE_GATE=yes` 严格升级语义。
- 默认以 warning 展示检查失败并允许 plan 阶段继续，严格环境变量启用时将对应失败升级为 error 并阻止阶段切换。
- 确保检查结果在正常 gate 输出中可见，并与现有门控结果保持一致。

### 关键场景

- GIVEN `guide-plan` 已生成待完成的 change artifacts, WHEN 正常执行 `plan_done_gate`, THEN `run_plan_checks` 与 `change_alignment` 均被调用，失败项以 warning 输出，且默认不阻断阶段切换。
- GIVEN plan artifact 触发一个 `change_alignment` 失败, WHEN `STRICT_CHANGE_GATE=yes`, THEN 该失败项升级为 error，plan-done gate 返回失败并阻止进入下一阶段。
- GIVEN `run_plan_checks` 与 `change_alignment` 全部通过, WHEN `plan_done_gate` 执行, THEN gate 输出包含两类检查的通过结果，并保持现有 plan-done 检查行为不变。
- GIVEN 某项检查不可用或返回结构化失败结果, WHEN `plan_done_gate` 汇总结果, THEN gate 清晰标识该检查及原因，不静默跳过，也不把默认 warning 错误升级为阻断。

**Out of Scope**:

- 不新增或重写 `run_plan_checks`、`change_alignment` 的检查规则。
- 不实现 `propose-quality-autohook` 的 proposal 检查，也不实现 `add-change-content-review` 的内容审查或自动修订。
- 不修改 ADR、change artifact 格式、提案索引或其他阶段的门控行为。

## Capabilities

- MUST 在实际 `guide-plan` `plan_done_gate` 执行路径中调用现有 `run_plan_checks` 和 `change_alignment` 检查。
- MUST 遵循 ADR-0007 的 error/warning 门控语义，默认质量检查失败为 warning，不阻断流程。
- MUST 遵循 ADR-0019 的 `STRICT_CHANGE_GATE=yes` 独立环境变量升级机制，不复用或替换其他阶段的严格变量。
- MUST NOT 修改现有检查逻辑来掩盖失败，也 MUST NOT 通过默认跳过、静默捕获或改变检查名称来规避结果。
- MUST NOT 将 `add-change-content-review` 或 `propose-quality-autohook` 的职责混入本提案。
- SHOULD 让检查结果沿用现有 gate 输出和事件记录约定，便于诊断实际执行路径是否覆盖。

## Impact

- MUST 在实际 `guide-plan` `plan_done_gate` 执行路径中调用现有 `run_plan_checks` 和 `change_alignment` 检查。
- MUST 遵循 ADR-0007 的 error/warning 门控语义，默认质量检查失败为 warning，不阻断流程。
- MUST 遵循 ADR-0019 的 `STRICT_CHANGE_GATE=yes` 独立环境变量升级机制，不复用或替换其他阶段的严格变量。
- MUST NOT 修改现有检查逻辑来掩盖失败，也 MUST NOT 通过默认跳过、静默捕获或改变检查名称来规避结果。
- MUST NOT 将 `add-change-content-review` 或 `propose-quality-autohook` 的职责混入本提案。
- SHOULD 让检查结果沿用现有 gate 输出和事件记录约定，便于诊断实际执行路径是否覆盖。

## Acceptance

- 在正常 `guide-plan` 执行中，`plan_done_gate` 对每个 change 至少调用一次 `run_plan_checks` 和 `change_alignment`，并有自动化测试证明调用发生。
- 默认环境下，任一新增检查失败都显示为 warning，plan-done gate 仍可成功完成，且不存在静默跳过结果。
- 设置 `STRICT_CHANGE_GATE=yes` 时，任一 `change_alignment` 失败都显示为 error 并使 plan-done gate 返回非零或等价失败状态。
- 设置严格模式只影响 `change_alignment` 的升级行为，不改变 `run_plan_checks` 及现有 error checks 的既有语义。
- Gate 输出或事件记录包含 `run_plan_checks`、`change_alignment` 的检查名称、通过状态和失败原因，覆盖通过、warning、strict error 三类结果。
- 现有 plan-done、proposal quality、change content review 相关测试保持通过，且未修改 proposal-suggestions.md、现有 proposals、ADR 或 git 历史。

