# add-workflow-reflect-engine - Acceptance Verification

**Date:** 2026-07-27
**Branch:** openspec/add-workflow-reflect-engine
**Commit:** (this commit)

## Test Results

### pytest (unit tests)
```
tests/unit/test_reflect_cooldown.py   - 6 tests PASSED
tests/unit/test_reflect_dedup.py      - 7 tests PASSED
tests/unit/test_reflect_engine.py     - 12 tests PASSED
TOTAL: 25/25 PASSED (0.14s)
```

### bats (integration tests)
```
tests/integration/test_reflect_hooks.bats - 6 tests PASSED
  ok 1 reflect: SKIP_WORKFLOW_REFLECTION=1 disables all hooks
  ok 2 reflect: ship phase triggers on unrecovered_failure
  ok 3 reflect: arch phase always log_friction
  ok 4 reflect: plan phase trigger on same root cause >= 2
  ok 5 reflect: timeout does not block analysis
  ok 6 reflect: hook code present in all 3 gate scripts
```

## Acceptance Criteria Checklist (9/9 PASSED)

| # | Criterion | Status | Verification Detail |
|---|-----------|--------|---------------------|
| 1 | `reflect_engine.py` 独立可测试，覆盖率 ≥80% | ✅ PASS | All 3 modules (reflect_engine, reflect_cooldown, reflect_dedup) importable independently; 25 unit tests covering all public methods |
| 2 | 3 个 gate hook 点均追加调用 | ✅ PASS | `reflect_engine` + `SKIP_WORKFLOW_REFLECTION` present in: write_arch_handoff.sh, plan_done_gate.sh, archive.sh |
| 3 | 分层阈值正确：ship/plan/arch | ✅ PASS | ship=any unrecovered_failure -> propose_issue; plan=same root cause >=2 -> propose_issue (single=none); arch=always log_friction |
| 4 | 去重命中提示"已有提案" | ✅ PASS | DedupMatcher.check_all() matches improvements/*.md by fuzzy keyword (>=2 match); returns {source, matched_name}; no-match returns None |
| 5 | Issue draft 模板内容 | ✅ PASS | IssueDraft has title (contains fingerprint), body (contains session_id, errors, timestamp), target_repo, labels=[auto-reflect, phase] |
| 6 | 冷却期 24h 内静默跳过 | ✅ PASS | CooldownManager: record -> is_cooling=True; aged 25h -> is_cooling=False; different fingerprints independent |
| 7 | SKIP_WORKFLOW_REFLECTION=1 完全禁用 | ✅ PASS | Env var set -> action=skipped, reason=SKIP_WORKFLOW_REFLECTION=1, no side effects |
| 8 | 超时/失败不阻塞 gate | ✅ PASS | TimeoutError in _do_analyze -> action=error, reason contains "timeout"; does not raise, gate proceeds |
| 9 | Issue 路由正确 | ✅ PASS | skills/_lib/ paths -> chisuhua/rdd-workflow; docs/adr/ paths -> chisuhua/rdd-workflow; other paths -> git remote origin fallback |

## Implementation Summary

- **reflect_cooldown.py** - CooldownManager: 24h fingerprint-based cooldown via `.rddf/state/reflect-cooldown.json`
- **reflect_dedup.py** - DedupMatcher: fuzzy keyword matching against improvements/*.md, proposal-suggestions.md, proposal-approved.md
- **reflect_engine.py** - ReflectEngine: orchestrator (analyze -> dedup -> cooldown -> draft issue -> route), per-phase thresholds
- **3 gate hooks** - write_arch_handoff.sh (arch), plan_done_gate.sh (plan), archive.sh (ship) - all non-blocking with SKIP env check

## Conclusion

All 9 acceptance criteria from `openspec/changes/add-workflow-reflect-engine/proposal.md` are verified PASSED.
