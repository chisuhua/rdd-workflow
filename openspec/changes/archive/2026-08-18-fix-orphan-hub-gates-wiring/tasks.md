# fix-orphan-hub-gates-wiring — Tasks

> Schema: spec-driven
> See: `proposal.md` (动机/范围) + `design.md` (技术决策).
> Source: Oracle review of ADR-0030/ADR-0031 (ses_fecf9715affebqMTQnuYJMEEL7) 2026-08-18.

## Implementation

- [x] 1. `skills/guide-design/SKILL.md` Phase 4 `check_design_done_gate()` 末尾追加 2 个新 check
- [x] 2. `tests/integration/test_design_done_hub_gates.bats` 新增, 4 个场景全绿
- [x] 3. 默认 + hub pending → exit 1
- [x] 4. 默认 + cross_repo_audit 含未批准 → exit 1
- [x] 5. `SKIP_HUB_CHECK=true` → exit 0 (含 audit)
- [x] 6. 空 audit + 空 pending → exit 0 默认通过
- [x] 7. `rdd-doctor` 新增 `--check orphan-gates` 巡检模式, 当 orphan 函数被检测到时 CRITICAL 报告
- [x] 8. `tests/unit/test_design_done_gate.py` 全绿（既有）
- [x] 9. `tests/unit/test_rdd_doctor.py` 新增 orphan-gates 单测覆盖
- [x] 10. `README.md` §"紧急跳过 `SKIP_HUB_CHECK=true`" 章节明确"默认 OFF, 紧急时 ON"语义
- [x] 11. **既有回归**: `./test.sh --full --regression` 通过
- [x] 12. **审计 trail**: `git log --grep='fix-orphan-hub-gates'` 含清晰 conventional commit
- [x] 13. **依赖记录**: proposal-suggestions.md 表头注明 "阻塞: fix-adr-0031-safety-gate-substantiation"
