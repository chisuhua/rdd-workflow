## Why

ADR-0015 §后续待办 第一条要求 `guide-plan.md` 在 Phase 4 调用 `validate_report.write_report()` 刷新 `.rddf/state/openspec-validate.json`。当前 `gate.py::_check_openspec_validate` 在 plan-done 时运行 `openspec validate`，但结果只在 subprocess 返回值中存活几毫秒就被丢弃，下游 consumers（plan-done gate、未来 archive hook、`plan.review_validation` 人工节点）想读 validate 结果时只能再跑一次 CLI 或干脆不读。本 change 把 wiring 跑通，让 ADR-0015 §决策 5 设计的 view 文件契约真正生效。

## What Changes

- `skills/guide-plan/SKILL.md` Phase 4：在 `run_plan_done_gate` 之后、`write_plan_handoff` 之前新增 PYEOF 块，对每个 active change 运行 `openspec validate <name> --json` 并通过 `validate_report.write_report()` 持久化到 `.rddf/state/openspec-validate.json`。Non-fatal：CLI 缺失 / skeleton change validate 失败 / 写入异常 都只 emit warning。
- `docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md`：状态从 `待定` 改为 `已采纳`，追加 `### 修订记录` section 记录本 change 的实装内容、dual-run 说明、剩余后续待办。
- `tests/integration/test_adr_0015_wiring.bats`：新增 15 个回归测试，锁住 API surface（`write_report` 可 import）、ADR-0015 状态字段、wiring 块位置（在 gate 之后 handoff 之前）、Oracle C1 env-var 模式、non-fatal 行为、end-to-end roundtrip。
- `openspec/changes/refine-adr-0015-wiring/{design,tasks}.md`：本 change 的设计与任务分解。

## Out of Scope

- **不修改** `skills/_lib/gate.py`（dual-run 是已知短期方案，长期合并留给后续 change）
- **不修改** `skills/_lib/validate_report.py`（API 已足够）
- **不修改** `skills/_lib/human_nodes.py`（`plan.review_validation` 节点留给后续 ADR）
- **不修改** `archive.sh`（archive 前检查 validate 留给 ADR-0015 后续待办第二条）
- **不修改** 任何已存在的测试文件（只创建新测试文件）
