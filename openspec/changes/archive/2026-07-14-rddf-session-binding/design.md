# rddf-session Binding — Design Summary

> Full design: `docs/superpowers/specs/2026-07-14-rddf-session-binding-design.md`
> Implementation plan: `docs/superpowers/plans/2026-07-14-rddf-session-binding.md`

## Architecture

**Layered, additive, read-only:**

```
Layer 1: RddfSessionCoordinator.find_current_binding() / find_next_recommendation()
         ↑ (pure read methods, _with_file_lock pattern, no schema change)
         
Layer 2: rddf-session current subcommand (bash case in rddf-session.md)
         rddf-session.scan_session_binding() (bash function in scan-state.sh)
         ↑ (thin CLI/bash wrappers around Layer 1)
         
Layer 3: guide recommender (skills/guide.md)
         ↑ (after scan_state, append BINDING_LINES output)
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Binding semantic | `owner_opencode_session_id` 现有字段 | 无新 schema 字段；ADR-0017 已定义 |
| Recommendation algorithm | orphaned + most recent `started_at` desc | YAGNI：spec/14 §3 列出更复杂选项但首版不需要 |
| Mandatory binding location | `guide-arch/plan/ship` 入口 hooks（既有） | ADR-0017 P2 已完成；不重复执行 |
| `BINDING_LINES` ownership | 全局 bash 数组，由 `scan_session_binding` 写、guide 读 | 与 `RECOMMEND`/`REASON` 风格一致 |
| `BINDING_LINES` 输出位置 | `RECOMMEND/REASON` 之后 | 不改变 RECOMMEND 优先级；只追加 |

## Files Touched

| File | Change | LOC |
|------|--------|-----|
| `skills/_lib/rddf_session.py` | +2 methods | +52 |
| `skills/rddf-session.md` | +1 subcommand + frontmatter | +29/-3 |
| `skills/_lib/scan-state.sh` | +1 function | +45 |
| `skills/guide.md` | +bash example + Output Format | +18 |
| `AGENTS.md` | +subsection | +4 |
| `docs/adr/ADR-0017-rddf-session.md` | +Cross-Reference | +6/-1 |
| `tests/unit/test_rddf_binding.py` | NEW | +147 |
| `tests/integration/test_rddf_session_current.bats` | NEW | +153 |
| `tests/integration/test_guide_binding_alert.bats` | NEW | +158 |

**Total: 9 files changed, 609 insertions, 3 deletions**

## Test Coverage

- 10 unit tests (pytest) — covers both new methods: active match / terminal-only / different owner / multiple actives / empty file / most-recent orphaned / no orphaned / mixed states / heartbeat promotion
- 8 bats integration tests for `rddf-session current` — bound/unbound/orphaned paths, missing/corrupt files, OPENCODE_SESSION_ID, hostname fallback, no mutation
- 10 bats integration tests for `scan_session_binding` + guide integration — same paths + RECOMMEND preservation + source ordering + no file mutation
- Total: **28 new tests, all green**

## Backward Compatibility

- `sessions_schema.json` v1 unchanged (verified via `git diff` empty)
- 11 existing RddfSessionCoordinator public methods unchanged
- `scan_state` 11-priority unchanged (RECOMMEND/REASON semantics identical)
- 5 existing rddf-session subcommands unchanged (list/show/resume/abandon/archive-history)
- Guide recommender output is additive; if `BINDING_LINES` is empty, output looks identical to v2.0.x

## Migration

None. The change is purely additive and detected by callers opportunistically. No CLI flags, no env vars, no new files.