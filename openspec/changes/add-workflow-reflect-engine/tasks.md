# add-workflow-reflect-engine — Tasks

## Phase 1: reflect_engine.py 核心引擎

- [ ] Create `skills/_lib/reflect_engine.py` with ReflectEngine class
  - `__init__(phase, context)` — initialize with phase (arch/plan/ship) and context dict
  - `analyze()` → ReflectResult — analyze event_log + tasks.md + sessions.json
  - `deduplicate(fingerprint)` → DedupResult — check improvements/suggestions/approved
  - `check_cooldown(fingerprint)` → bool — check 24h cooldown
  - `draft_issue(result)` → IssueDraft — generate issue title/body from template
  - `route_issue(draft)` → target_repo — route based on file paths
  - `file_issue(draft, dry_run=False)` → issue_url — gh issue create or dry-run

## Phase 2: 去重与冷却

- [ ] Create `skills/_lib/reflect_dedup.py` with dedup matching
  - `check_improvements(signature)` → searches improvements/*.md
  - `check_suggestions(signature)` → searches proposal-suggestions.md
  - `check_approved(signature)` → searches proposal-approved.md
- [ ] Create `skills/_lib/reflect_cooldown.py` with CooldownManager
  - `.rddf/state/reflect-cooldown.json` file management
  - 24h cooldown per fingerprint
  - Cleanup expired entries

## Phase 3: Hook Points

- [ ] Add hook in `skills/guide-arch/scripts/write_arch_handoff.sh` (after gate pass)
- [ ] Add hook in `skills/guide-plan/scripts/plan_done_gate.sh` (after gate pass)
- [ ] Add hook in `skills/_lib/archive.sh` (after `archive_change` completion)
- [ ] Each hook: `SKIP_WORKFLOW_REFLECTION=1` early exit check

## Phase 4: 测试

- [ ] `tests/unit/test_reflect_engine.py` — unit tests for core engine (≥80% coverage)
- [ ] `tests/unit/test_reflect_cooldown.py` — cooldown logic tests
- [ ] `tests/unit/test_reflect_dedup.py` — dedup matching tests
- [ ] Integration tests for each gate hook (arch-done, plan-done, archive-done)

## Phase 5: 验收

- [ ] All 9 acceptance criteria from proposal.md verified
- [ ] `SKIP_WORKFLOW_REFLECTION=1` complete disable verified
- [ ] Timeout (10s) non-blocking gate verified
- [ ] `gh issue create --dry-run` template content verified
