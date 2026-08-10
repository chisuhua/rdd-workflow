# wire-design-content-review-gate

## Why

- ADR-0025 已将 guide-design 的批准动作定义为生成、确认、落盘，并规定 improvements 层审查检查五段完整性、ADR 引用、可量化验收和必填头部字段。
- ADR-0025 D4 规定默认 warning，`STRICT_DESIGN_GATE=yes` 才阻断，并保留 `SKIP_CONTENT_REVIEW=yes` 作为内容审查 escape hatch。
- 既有 `skills/guide-design/scripts/design_content_review.py` 与 `design_content_review.sh` 已提供 improvements 层检查，脚本入口也已实现 warning-default、strict blocking 和 `SKIP_CONTENT_REVIEW` 语义。
- 既有 `skills/guide-design/scripts/generate_full_proposal.py`、`approve_proposal.sh` 以及 `propose_quality_check.py::run_design_checks` 分别承担 proposal 生成、批准编排和 proposal 层检查。本提案只补齐批准执行路径对既有 review 的调用，不重复 `add-propose-content-review` 或 `add-change-content-review` 的审查设计。

## What Changes

**In Scope**:

- 将既有 `design_content_review.sh` 接入 guide-design 的 approve flow，在批准动作完成前按既定入口调用 improvements 内容审查。
- 确保单项批准和批量批准逐项执行相同的 review 调用路径，并将 warning 或 blocking 结果传递给现有交互流程。
- 保持默认 warning 行为，保留 `STRICT_DESIGN_GATE=yes` 的阻断升级，以及 `SKIP_CONTENT_REVIEW=yes` 的显式跳过路径。
- 增加脚本执行路径回归覆盖，证明 review 被调用、结果被处理且 escape hatch 生效。

### 关键场景

- GIVEN guide-design 正在处理一个待批准的 improvement，WHEN approve flow 进入批准动作且 `SKIP_CONTENT_REVIEW` 不是 `yes`，THEN 它必须调用既有 `design_content_review.sh`，并在批准结果落盘前处理 review 返回状态。
- GIVEN 既有 review 发现缺少 ADR、必填字段、五段章节或可量化验收标准，WHEN `STRICT_DESIGN_GATE` 不是 `yes`，THEN approve flow 必须展示 warning 并继续既有批准交互或落盘路径，不得把 warning 当作失败退出。
- GIVEN 既有 review 发现问题，WHEN `STRICT_DESIGN_GATE=yes`，THEN approve flow 必须尊重 review 的阻断结果，不得写入批准完成状态或继续执行依赖批准成功的落盘步骤。
- GIVEN `SKIP_CONTENT_REVIEW=yes`，WHEN approve flow 处理 improvement，THEN 它必须跳过既有 review 调用并保留当前批准路径，不得因缺少 review 输出而改变其他批准语义。
- GIVEN guide-design 使用批量批准，WHEN 批量项中存在多个 improvement，THEN 每个 improvement 必须在各自批准前经过同一 review 调用路径，单项 warning 或 blocking 结果不得被批量循环静默吞掉。
- GIVEN review 脚本返回其既有成功、warning 或 blocking 状态，WHEN approve flow 读取该状态，THEN 它必须保留可诊断的终端输出，并让后续行为与 `STRICT_DESIGN_GATE` 和 `SKIP_CONTENT_REVIEW` 约定一致。

**Out of Scope**:

- 不重新设计或扩展 `design_content_review.py` 的检查项、提示词或严重度规则。
- 不重复 `add-propose-content-review` 的 Oracle 审查，也不重复 `add-change-content-review` 的 plan 阶段 change artifact 审查。
- 不修改 ADR-0025、proposal 内容格式、openspec proposal 层检查、proposal-approved 状态语义或后续 plan 阶段流程。
- 不把默认 warning 改为阻断，不移除 `SKIP_CONTENT_REVIEW`，也不新增独立 review 阶段。

## Capabilities

- MUST 在 guide-design approve 执行路径中调用现有 `design_content_review.sh`，不得复制 `design_content_review.py` 的检查逻辑。
- MUST 在批准状态写入、proposal 落盘或其他批准完成副作用发生前完成 review 结果处理。
- MUST 保持默认 warning、不阻断的现有行为。
- MUST 保留 `SKIP_CONTENT_REVIEW=yes` 作为显式 escape hatch，并只跳过内容 review，不跳过其他批准门控或用户确认步骤。
- MUST 尊重 `STRICT_DESIGN_GATE=yes` 的既有阻断语义，避免在 wrapper 层把 blocking 状态降级为成功。
- MUST 对单项和批量批准使用同一条可验证的 review 调用路径。
- MUST NOT 修改 `add-propose-content-review` 或 `add-change-content-review` 所定义的审查职责范围。
- MUST NOT 新增第二套 improvements 内容审查实现、独立状态格式或未被 ADR-0025 要求的质量门。
- SHOULD 通过环境变量或现有脚本参数传递项目根目录和 improvement 路径，避免把用户内容拼接进 shell 或 Python 代码。

## Impact

- MUST 在 guide-design approve 执行路径中调用现有 `design_content_review.sh`，不得复制 `design_content_review.py` 的检查逻辑。
- MUST 在批准状态写入、proposal 落盘或其他批准完成副作用发生前完成 review 结果处理。
- MUST 保持默认 warning、不阻断的现有行为。
- MUST 保留 `SKIP_CONTENT_REVIEW=yes` 作为显式 escape hatch，并只跳过内容 review，不跳过其他批准门控或用户确认步骤。
- MUST 尊重 `STRICT_DESIGN_GATE=yes` 的既有阻断语义，避免在 wrapper 层把 blocking 状态降级为成功。
- MUST 对单项和批量批准使用同一条可验证的 review 调用路径。
- MUST NOT 修改 `add-propose-content-review` 或 `add-change-content-review` 所定义的审查职责范围。
- MUST NOT 新增第二套 improvements 内容审查实现、独立状态格式或未被 ADR-0025 要求的质量门。
- SHOULD 通过环境变量或现有脚本参数传递项目根目录和 improvement 路径，避免把用户内容拼接进 shell 或 Python 代码。

## Acceptance

- [ ] 单项 approve flow 的回归测试证明，在 `SKIP_CONTENT_REVIEW` 未设置为 `yes` 时，既有 `design_content_review.sh` 在批准副作用前被调用一次。
- [ ] 回归测试证明默认 warning 场景继续完成既有批准路径，且终端输出包含 review warning。
- [ ] 回归测试证明 `STRICT_DESIGN_GATE=yes` 下 review blocking 会阻止批准状态写入或等价的批准完成副作用。
- [ ] 回归测试证明 `SKIP_CONTENT_REVIEW=yes` 不调用既有 review，并保留原有批准结果和其他交互行为。
- [ ] 回归测试证明批量 approve 对每个 improvement 独立调用 review，并分别处理 warning 或 blocking 结果。
- [ ] 静态检查或脚本测试证明 approve flow 只引用既有 `design_content_review.sh`，没有复制其检查规则。
- [ ] 现有 guide-design 内容 review、proposal 生成、design-handoff 和相关回归测试全部通过。

