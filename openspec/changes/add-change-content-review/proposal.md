## Why

change artifact (proposal.md / design.md / tasks.md) 生成后缺乏内容审查 — `propose_quality_check.py` 只做 5 项结构检查，不做内容质量判断。plan 阶段 plan-done gate 前是 plan → ship 衔接前的最后质量门。

## What Changes

- 新建 `change_content_review.py`: 调用 Metis agent 做 5 项内容审查（proposal 清晰度、design 完整性、tasks 粒度、一致性、依赖标注）
- 自动修订：Metis 发现可修订问题时直接编辑文件修订
- 升级条件：仅当 Metis 遇到无法自动决断的重大歧义时才升级到人工
- 挂载点：`guide-plan` Phase 4 plan-done gate 前
- 支持 `SKIP_CHANGE_CONTENT_REVIEW=yes` 跳过，`CHANGE_CONTENT_REVIEW_AUTO_REVISE=no` 仅出报告

## Capabilities

### New Capabilities
- `change-content-review`: plan-done 前的 change artifact 内容质量门

### Modified Capabilities
- `plan-done-gate`: 在 plan-done 双重门控前增加内容审查

## Impact

- 新建文件：skills/guide-plan/scripts/change_content_review.py
- 修改文件：skills/guide-plan/scripts/plan_done_gate.sh
- 输出文件：.rddf/state/change-review-<name>.json
- 环境变量：SKIP_CHANGE_CONTENT_REVIEW, CHANGE_CONTENT_REVIEW_AUTO_REVISE
