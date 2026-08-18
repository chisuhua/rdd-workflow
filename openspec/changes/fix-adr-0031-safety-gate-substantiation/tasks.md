# fix-adr-0031-safety-gate-substantiation — Tasks

> Schema: spec-driven
> See: `proposal.md` (动机/范围) + `design.md` (技术决策).
> Source: Oracle review of ADR-0030/ADR-0031 (ses_fecf9715affebqMTQnuYJMEEL7) 2026-08-18.

## Implementation

- [x] 1. `tests/integration/test_strict_human_approval.bats` 新增 5 个 case，总计 9 个 case 全绿
- [x] 2. **fail-open 防御**: 测试场景 1 中 `--auto-accept` 在首次调用时必须 exit 3（不依赖 change dir 存在）
- [x] 3. **username 强制**: 测试场景 2 中空 stdin / 30s timeout 必须 exit 4
- [x] 4. **env var 升级**: 测试场景 3 中 `RDDF_REQUIRE_HUB_APPROVAL=yes` + username + hub approved label → accept；缺 label → exit 5
- [x] 5. **hub re-fetch**: 测试场景 4 中 issue closed → exit 6；network error → exit 0 + warning
- [x] 6. **audit 写入**: 测试场景 5 中 accept 后 `.cross-repo-audit.jsonl` 含新行（含 actor / hub_state / hub_labels / decision）
- [x] 7. **既有回归**: `tests/unit/test_cross_repo_audit.py` 全绿, `tests/unit/test_approve_proposal*.py` 全绿
- [x] 8. **全量回归**: `./test.sh --full --regression` 通过（无新增失败）
- [x] 9. **ADR-0031 修订**: 状态 `待定 → 已采纳`, §实现细节与本次实际代码一致
- [x] 10. **AC 文档同步**: `2026-08-16-add-strict-human-approval-for-cross-repo-changes` 的 AC 清单据实修正, 不再声称 5/5 实现
- [x] 11. **Audit trail**: `.rddf/state/.cross-repo-audit.jsonl` 经端到端测试后**非空**（验证 dead-code 修复）
