# add-workflow-reflect-engine — Design & Implementation Plan

## Architecture Overview

`reflect_engine.py` is a standalone, read-only reflection engine that analyzes workflow failures and proposes GitHub issues. It plugs into the 3 phase-done gates as a post-hook.

```
                    ┌────────────────────────────────┐
                    │       reflect_engine.py         │
                    │   (独立 Python 模块, 只读)       │
                    ├────────────────────────────────┤
Inputs (read-only)  │  event_log  tasks.md  sessions │
                    │                                │
┌───────────┐       │  ┌──────────┐  ┌─────────────┐ │
│  arch-done│──────►│  │ Dedup    │  │  Cooldown   │ │
│  gate     │       │  │ Matcher  │  │  Checker    │ │
└───────────┘       │  └──────────┘  └─────────────┘ │
                    │         │              │        │
┌───────────┐       │         ▼              ▼        │
│ plan-done │──────►│  ┌──────────────────────────┐  │
│  gate     │       │  │    Issue Draft Generator  │  │
└───────────┘       │  │    (模板化标题+正文)        │  │
                    │  └──────────────────────────┘  │
┌───────────┐       │         │                      │
│ archive   │──────►│         ▼                      │
│  done     │       │  ┌──────────────────────────┐  │
└───────────┘       │  │   User Confirmation (Y/n) │  │
                    │  └──────────────────────────┘  │
                    │         │                      │
                    │         ▼                      │
                    │  ┌──────────────────────────┐  │
                    │  │   gh issue create         │  │
                    │  └──────────────────────────┘  │
                    └────────────────────────────────┘
```

## Module Structure

```
skills/_lib/reflect_engine.py          # 主引擎 (~350 LOC)
  - class ReflectEngine(phase, context)
  - analyze() → ReflectResult
  - deduplicate(fingerprint) → DedupResult
  - check_cooldown(fingerprint) → bool
  - draft_issue(result) → IssueDraft
  - route_issue(issue_draft) → target_repo
  - file_issue(issue_draft) → issue_url

skills/_lib/reflect_cooldown.py        # 冷却管理
  - class CooldownManager(cooldown_file)
  - is_cooling(fingerprint) → bool
  - record(fingerprint)
  - cleanup_expired(max_age=24h)

skills/_lib/reflect_dedup.py           # 去重匹配
  - check_improvements(signature) → DedupResult
  - check_suggestions(signature) → DedupResult
  - check_approved(signature) → DedupResult

tests/unit/test_reflect_engine.py       # 单元测试 (≥80% coverage)
tests/unit/test_reflect_cooldown.py
tests/unit/test_reflect_dedup.py
```

## Hook Points

| Phase | Hook Location | Trigger | Threshold |
|-------|--------------|---------|-----------|
| arch | `write_arch_handoff.sh` 末尾 | Gate pass | Log-only (friction signal) |
| plan | `plan_done_gate.sh` 末尾 | Same root cause ≥2 | Ask user to confirm |
| ship | `archive.sh::archive_change()` 末尾 | Any unrecovered failure | Ask user to confirm |

## Data Flow

```
event_log (追加式)     tasks.md (进度)      sessions.json
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                     reflect_engine.py
                            │
                    ┌───────┴───────┐
                    │               │
              deduplicate()    cooldown_check()
                    │               │
                    └───────┬───────┘
                            │
                    Issue Draft
                            │
                    User Confirm (Y/n)
                            │
                    gh issue create
```

## Key Design Decisions

1. **Read-only**: No state file mutation — eliminates circular dependency risk
2. **Non-blocking**: Timeout 10s, gate continues regardless of reflect result
3. **Fingerprint format**: `{phase}:{gate_name}:{error_category}` (literal match only, no semantic clustering)
4. **Issue routing**: `skills/_lib/` or `docs/adr/` path → chisuhua/rdd-workflow; user paths → `git remote -v` origin
5. **User confirmation**: v1 always requires confirmation before filing; auto-file deferred to v2 after data collection
