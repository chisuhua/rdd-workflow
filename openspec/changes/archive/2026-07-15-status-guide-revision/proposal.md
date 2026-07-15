---
name: status-guide-revision
schemaName: spec-driven
created: 2026-07-15
---

## Why

Audit of `skills/guide.md` and `skills/status.md` (performed during a real execution session on 2026-07-15) identified **15 distinct defects** across 3 severity tiers. These defects were exposed by:

- Running the `guide` recommender on a state with one committed-but-unworked change
- Running `status` Mode A on the same state
- Cross-checking the skill docs against their underlying bats integration tests

The defects included correctness (P0) issues like duplicate `version:` keys in frontmatter and an unsafe archive flow, usability (P1) issues like missing input routing and dead code, and consistency (P2) issues like missing style guides. None of these block current workflows but all degrade auditability and will compound as the project grows.

**Goal:** Bring both skills to a self-consistent, defensible, test-locked state by resolving the 15 audit findings, ordered by severity (P0 → P1 → P2), with each change gated by a bats regression test.

## What Changes

修改 2 个 skill 文档 + 1 个 helper + 新增 12 个回归测试：

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `skills/guide.md` | **修改** | 修复 frontmatter `version:` 重复键；校正优先级计数声明；binding block 加 graceful-skip 语义；新增 `--help`/`--no-binding` 入参 |
| `skills/status.md` | **修改** | Mode A 状态列与 iteration.json 5 态对齐（含新增 `💼 committed-no-wt`）；Mode C 加 y/n 确认 gate；Mode B 路径统一 `$PROJECT_ROOT` 前缀，移除 dead-source，补全 awk 列说明；Mode D 改用 `os.environ`；Mode E 删 `exec $0` 并复用 `iteration.list_planned()`；Mode A 去重 worktree 列表 + 加 `i` handler；新增"输出风格指南"小节 |
| `skills/_lib/scan-state.sh` | **修改** | 增加 `EXPORTED_VARS` 注释头；新增并调用 `check_stale_workflow_state()` 帮手 |
| `tests/integration/test_*.bats` (12 个) | **新增** | 12 个回归测试文件锁定上述各项不变量 |
| `openspec/changes/status-guide-revision/specs/general/spec.md` | **新增** | delta 规范（迁移到 `general` capability，附 11 个 Scenario） |

## Scope

- **In:** `skills/guide.md`, `skills/status.md` Markdown revisions; `skills/_lib/scan-state.sh` comment + stale-state hook; `skills/_lib/iteration.py` usage docs; 12 new bats integration tests at `tests/integration/test_*.bats`
- **Out:** Behavior changes to runtime helpers beyond `check_stale_workflow_state()`; ADR creation (deferred); new OpenSpec changes (caller of this change); refactoring status.md Modes into separate files

## Approach

Follow the implementation plan at `.rddf/plans/status-guide-revision.md` (12 work-units across 3 tiers). Every Markdown change is preceded by a failing bats test (red), and merged only after the test passes (green) + existing tests still pass (regression).

## Audit Map

| Audit | Severity | Work-Unit | Summary |
|---|---|---|---|
| G1 | P0 | 1.1 | guide.md `version:` duplicate key in frontmatter |
| C1 | P0 | 1.1 | status.md `version:` duplicate key in frontmatter |
| S1 | P0 | 1.2 | Mode A missing "📦 committed" / "💼 committed-no-wt" state |
| S2 | P0 | 1.2 | Mode A 3-state table diverges from iteration.json 5-state enum |
| S7 | P0 | 1.3 | Mode C calls `archive_change` without y/n confirmation (irreversible) |
| G2 | P1 | 2.1 | scan_state() export vars not documented |
| G4 | P1 | 2.1 | guide.md priority count (11) ≠ scan-state.sh bullets (12) |
| S8 | P1 | 2.2 | status.md input table lacks top-level router code |
| S4 | P1 | 2.3 | PLAN_FILE relative vs TASKS_FILE absolute path inconsistency |
| S5 | P1 | 2.3 | dead `source _lib/worktree.sh` at top-of-skill |
| S6 | P1 | 2.3 | awk comment at line 382 omits `$1` column description |
| S12 | P1 | 2.4 | Mode D python source uses `$PROJECT_ROOT` interpolation (injection) |
| S9 | P1 | 2.5 | Mode E `exec $0` doesn't work (markdown, not script) |
| S10 | P1 | 2.5 | Mode E opens iteration.json twice instead of using `iteration.list_planned()` |
| S3 | P2 | 3.1 | Mode A duplicates `git worktree list` call |
| S11 | P2 | 3.1 | Mode A case handler ignores user `i` choice |
| G3 | P2 | 3.2 | guide.md binding block has no graceful-skip semantics |
| G5 | P2 | 3.2 | guide.md lacks `--help` / `--no-binding` flags |
| G6 | P2 | 3.3 | stale `workflow-state.md` check is doc-only |
| C2 | P2 | 3.4 | no output style guide for status/guide |

**20 audit rows / 15 distinct findings** (G1+C1, S1+S2, S4+S5+S6, S9+S10, S3+S11, G3+G5 are grouped into single work-units each).

## Acceptance Criteria

1. All 12 plan work-units complete in tier order (1.1 → 1.2 → 1.3 → 2.1 → 2.5 → 3.1 → 3.2 → 3.3 → 3.4)
2. Every change preceded by a bats test that fails red → passes green
3. Baseline tests (`smoke.bats` + `test_guide_skill.bats` + `test_status_skill.bats` = 16 cases) remain green
4. New bats test files total ≥ 30 cases across 12 files
5. Python unit tests pass (`pytest tests/unit/`)
6. `metadata.version` resolves to the most-recent semver string in both skill files
7. `skills/status.md` Mode C archive flow requires y/n (or `--yes`) confirmation before invoking `archive_change`
8. `openspec/changes/status-guide-revision/` archived via `openspec archive` after completion

## Risks

- **Behavior change (medium):** `scan_state()` now invokes `check_stale_workflow_state()` — projects with a legacy `workflow-state.md` will see a one-line warning in `guide` output. Mitigated by read-only design (no auto-deletion).
- **Workflow change (medium):** Mode C requires confirmation — any existing script that calls `archive_change` directly will need to pass `--yes` or `--y`. Existing tests do not call this path directly.
- **No behavior change:** 11 of 12 work-units are doc-only or test-only.

## Reference

- `.rddf/plans/status-guide-revision.md` — implementation plan (TDD 5-step per work-unit)
- `docs/adr/ADR-0017-rddf-session.md` — referenced by work-unit 1.1 for frontmatter conventions
- `tests/_lib/skill.bash` — bats parser API reused by all 12 new tests
