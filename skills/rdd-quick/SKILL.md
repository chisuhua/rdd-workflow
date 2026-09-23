---
name: rdd-quick
description: |
  Bypass path per ADR-0047: in-place execution, no openspec change, no worktree.
  TDD 5-step plan + Oracle self-contained verification.

  Invoke when: Change scope ≤ 2 files AND ≤ 3 tasks AND no public API change.
  Default: TDD 5-step + P4 retry up to `RDDF_QUICK_MAX_RETRIES` (default 3).
  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: requires Python 3.11+, bash 4+, git 2.25+. No external skill deps.
metadata:
  author: rdd-workflow
  version: "1.1"
  evolved-from: "rdd-verifier v2.0 self-contained pattern (ADR-0045) + ADR-0048 amendment"
  user-invocable: true
  forbidden_env_vars:
    - "QUICK_FINISH_DETECTED"
    - "SKIP_PROMETHEUS_PLANNING"
  forbidden_env_vars_rationale: "These are reserved by rdd-builder. rdd-quick MUST NOT read or write them. The literal names are kept in frontmatter only and NEVER appear in the SKILL.md body to prevent accidental code generation that references them."
role:
  title: "Quick Executor (快速执行者)"
  perspective: "Bypass openspec change ceremony for small, well-scoped changes while preserving TDD discipline and AC verification. Per ADR-0048: complexity triage reads planner advisory when invoked from builder P0."
  boundaries:
    owns:
      - ".rddf/plans/quick-*.md"
      - ".rddf/state/.quick-history.jsonl"
      - ".rddf/state/rdd-quick-context.json (临时, per ADR-0048)"
    not_owns:
      - "openspec/changes/<name>/"
      - "openspec/specs/<name>/"
      - ".rddf/wt/<name>/"
      - "docs/adr/ADR-*.md"
      - ".rddf/state/iteration.json"
      - ".rddf/state/sessions.json"
      - ".rddf/state/roadmap-state.json"
      - ".rddf/plans/<name>.md"
    human_involvement: "medium"
---

## Stage 1 Hook（强制前置步骤, per add-guide-polling-loop-implementation AC-10）

进入 rdd-quick 旁路前必须调用 hooks，让 guide session 知晓小改动进度：

```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"

# 进入前 (写 phase_started)
rddf_session_hook_entry stage_quick rdd-quick "quick-phase" "quick-done" \
    .rddf/state/.quick-history.jsonl

# 阶段完成时 (写 phase_completed)
trap 'rddf_session_hook_close stage_quick quick-done rdd-quick' EXIT INT TERM
```

# rdd-quick Skill

Bypass-path orchestration for small, well-scoped changes. P0–P4 prose state machine
modelled on the rdd-verifier v2.0 self-contained pattern (ADR-0045): the executing
AI agent IS the executor and verifier. No external LLM provider is invoked.

## Entry / Exit Contract

**Entry Mode (a) — from rdd-builder P0 (主路径, per ADR-0048)**:

```bash
# 由 rdd-builder P0 选项 5 触发:
skill_use("rdd-quick") --from-builder
# 读取 .rddf/state/rdd-quick-context.json (传递 proposal.md 内容)
# 读取 .planner-handoff.json::recommended_route (作为 P1 主信号)
```

**Entry Mode (b) — direct from guide recommender (旁路, per ADR-0048)**:

```bash
# Run from the project root (any branch, no worktree required).
skill_use("rdd-quick")
# Then describe the change in natural language.
```

The agent MUST (mode b):

1. Confirm a `<kebab-case-name>` with the user.
2. Run `bash skills/rdd-quick/scripts/scaffold_plan.sh --name <name> --proposal "<text>"`.
3. Edit the generated `.rddf/plans/quick-<name>.md` to fill in concrete TDD step bodies and the `## Acceptance` checkboxes.
4. Proceed to P1.

The agent MUST (mode a — invoked from builder P0):

1. 从 `.rddf/state/rdd-quick-context.json` 读取 change_name + proposal_path
2. 复用 rdd-builder 已生成的 `openspec/changes/<change>/proposal.md`（不重新生成）
3. 跳过 scaffold 步骤, 直接 `quick-<change>.md` 模板填充（从 proposal.md ## Acceptance 段提取 AC）
4. Proceed to P1

**Exit**:

- **Completion**: one JSONL line appended to `.rddf/state/.quick-history.jsonl` via
  `python3 skills/rdd-quick/scripts/append_history.py` with `outcome: "completed"`.
  - If invoked from builder (mode a): completion triggers `openspec archive <change> --yes` (skipping rdd-builder P1-P3)
  - If invoked directly (mode b): completion is final
- **Escalation** (per ADR-0048 AMENDMENT): one JSONL line appended with `outcome: "escalated"` plus a stdout upgrade summary. **升级契约修订**: `skill_use("rdd-builder")` 回 P0 重新决策 (而非 `skill_use("rdd-planner")`, 避免 planner→builder→quick→planner 循环). No file is created under `openspec/changes/` or `openspec/specs/`.

## P0 — Plan Generation

Generate `.rddf/plans/quick-<name>.md` containing the canonical TDD 5-step structure
AND a `## Acceptance` section with at least one checkbox. The scaffold script
(`scaffold_plan.sh`) emits a template; the AI agent MUST edit it to:

- Replace placeholder Goals with the actual change goal.
- Replace placeholder Files with concrete Create/Modify/Test paths.
- Fill in each TDD step body with concrete actions.
- Replace placeholder AC bullets with at least 1 verifiable acceptance criterion.

The `quick-` prefix is mandatory and is enforced by `scaffold_plan.sh` (kebab-case
validated, target file existence check, regex `^quick-[a-z0-9-]+$` enforced by the
audit-log schema).

## P1 — Complexity Triage (REVISED per ADR-0048)

The AI agent MUST determine complexity by **优先读 planner advisory** (mode a) 或 fallback to self-triage (mode b).

### Mode (a) from rdd-builder P0 (主路径, per ADR-0048)

```bash
# 读取 .planner-handoff.json
RECOMMENDED=$(jq -r .recommended_route .rddf/state/.planner-handoff.json)

case "$RECOMMENDED" in
  simple)
    # planner 已判定为 simple → 仅向用户确认
    echo "Planner advisory: simple"
    echo "⚡ 推荐进入 P2 (跳过 Metis/Oracle 审查)"
    read -p "确认? (y/n) "
    ;;
  complex)
    # planner 已判定为 complex → 必须双审 (不能跳过)
    echo "Planner advisory: complex"
    echo "⚠️ 必须 Metis + Oracle 双审 + 用户确认"
    # fallthrough to complex branch
    ;;
  unknown|*)
    # planner 未给出 advisory (mode b 或 edge case) → fallback to self-triage
    echo "Planner advisory: unknown, fallback to self-triage"
    # fallthrough to original 5-signal heuristic
    ;;
esac
```

### Mode (b) direct (旁路, fallback) — 原 5-signal heuristic

The AI agent MUST determine complexity by reasoning about ALL of the following
signals. There is NO hardcoded numeric threshold — judgement is by synthesis.

#### Complex signals (any ONE is sufficient to warrant review)

- The change touches a public interface, cross-module contract, or library API.
- The change modifies or extends an existing gate, handoff schema, or state-file schema.
- The change has data-migration, breaking-change, or rollback risk.
- The change spans 3 or more modules OR touches `_lib/core/` / `_lib/schemas/`.
- The user's description admits multiple plausible interpretations.

#### Simple signals (ALL must hold to skip review)

- The change is contained within a single module.
- The change has no public-interface impact.
- The change has clear, automatically verifiable success criteria.
- The change is fully reversible via `git checkout` with no side effects.

### Complex branch (both modes)

When any complex signal is detected, the AI agent MUST (prose spawn instructions,
no programmatic subagent exists for Metis/Oracle):

1. Spawn Metis to surface ambiguities and unstated assumptions in the user's
   description. Metis output goes into the plan file as a "Risks / Assumptions"
   section.
2. Spawn Oracle to review the technical approach for soundness, edge cases, and
   adherence to existing project conventions. Oracle output goes into the plan file
   as a "Review notes" section.
3. Use the `question` tool to present the user's original request alongside the
   Metis and Oracle findings, and obtain explicit user confirmation before proceeding
   to P2.

If the user chooses to proceed, the audit log records `complexity: "complex"` and
`reviewed_by: ["metis", "oracle"]`.

### Simple branch

When all simple signals hold, proceed directly to P2. The audit log records
`complexity: "simple"` and `reviewed_by: []`.

`RDDF_QUICK_SKIP_REVIEW=true` is an emergency-only override that skips this entire
branch; the audit log records `reviewed_by: []` and the user assumes the risk.

## P2 — In-Place Execution

Execute each Task from the generated plan file, following the TDD 5-step discipline.
The AI agent MUST:

- Run on the current branch (NEVER `git worktree add`; NEVER create an `openspec/*` branch).
- NEVER write to `openspec/changes/<name>/tasks.md` (no tasks.md writeback).
- NEVER invoke `openspec change create` / `openspec archive`.
- Track progress by updating the plan file's own `- [ ]` checkboxes (not tasks.md).
- Stop and return to P1 if a discovered complication changes the complexity signal
  (e.g. a "simple" change turns out to touch `_lib/schemas/`).

## P3 — AC Verification

The AI agent MUST verify every checkbox in the plan file's `## Acceptance` section
against the committed code, and emit a verdict JSON array whose item fields EXACTLY
match rdd-verifier's `VERDICT_ITEM_SCHEMA`:

```json
[
  {
    "ac_id": "AC-1",
    "description": "<verbatim AC bullet text>",
    "status": "pass | fail | partial",
    "confidence": 0.0,
    "evidence": [{"tool": "Read|Grep|...", "query": "...", "result_summary": "..."}],
    "reasoning": "<one or two sentences; if status is fail or partial, this MUST embed a gap keyword ('not implement', 'missing', 'absent', 'todo: implement') or a drift keyword ('exists but', 'discrepan', 'mismatch', 'differs from ac') so the routing layer can classify correctly>"
  }
]
```

**AC source is the plan file's `## Acceptance` section.** The AI agent MUST NOT read
`openspec/changes/<name>/proposal.md` for AC extraction — there is no openspec change
in this path. AC source is the plan file, period.

If all items pass, proceed to P4 (completion). If any item fails, branch to P4
(retry-or-escalate).

`SKIP_RDDF_QUICK_VERIFY=true` skips verification entirely (emergency-only). The
audit log records `outcome: "unverified"` and the user assumes the risk.

## P4 — Completion, Retry, or Escalation

### All AC pass → completion

Append one audit-log entry via `append_history.py` with `outcome: "completed"`,
`commit_sha: "<HEAD sha>"`, `verdict_summary: {total, pass, fail: 0}`. Done.

### Some AC fail with retries available

`retry_count < RDDF_QUICK_MAX_RETRIES` (default 3). Increment `retry_count`, return
to P2 to apply corrections guided by the verdict `reasoning`, then re-run P3.

### Retries exhausted → escalation

Append one audit-log entry with `outcome: "escalated"`, `retry_count` = ceiling,
`commit_sha` = last attempt (may be empty if the change was reverted), and print
the upgrade summary to stdout:

```
=== rdd-quick: escalation summary ===
Original proposal: <verbatim>
Files modified: <git diff --stat against the starting commit>
Failing ACs:
  - AC-<n>: <status> | <reasoning excerpt>
  - ...
Recommendation: re-frame by running skill_use("rdd-builder") — 回到 P0 重新决策
                (per ADR-0048 §Decision 3 amended D1; 不再回到 rdd-planner,
                 避免 planner→builder→quick→planner 循环).
                Provide the proposal text above plus the failing ACs as the
                initial design input for rdd-builder P0 选项 5 重新决策.
=== rdd-quick: escalation summary end ===
```

The agent MUST NOT create any file under `openspec/changes/` or `openspec/specs/`
during escalation. Escalation is guidance-only.

> **变更说明 (per ADR-0048, 2026-09-09)**: 原升级契约 `skill_use("rdd-planner")` 已修订为 `skill_use("rdd-builder")` 回 P0 重新决策. 原因: (a) rdd-planner 阶段已完成, 不再接收从 quick 升级的 change; (b) rdd-builder P0 是变更执行的权威决策点, 用户在 5-option 中重新选择 (1-5).

## Environment Variables

| Variable | Default | Semantics |
|---|---|---|
| `RDDF_QUICK_MAX_RETRIES` | `3` | P4 retry ceiling |
| `RDFF_QUICK_PLAN_DIR` | `.rddf/plans` | Plan file directory |
| `RDDF_QUICK_HISTORY_FILE` | `.rddf/state/.quick-history.jsonl` | Audit log path |
| `RDDF_QUICK_SKIP_REVIEW` | `false` | Skip P1 Metis/Oracle review (emergency only) |
| `SKIP_RDDF_QUICK_VERIFY` | `false` | Skip P3 verification (emergency only) |

**FORBIDDEN — do NOT read or write the rdd-builder-reserved environment variables
listed in the frontmatter `metadata.forbidden_env_vars` block**. Touching any
reserved variable is the most likely way for rdd-quick to corrupt the formal
workflow. The variable names use a deliberately distinct `RDDF_QUICK_` prefix
and the forbidden list is mirrored in `tests/integration/test_rdd_quick.bats`.

## Hard Constraints (verbatim, never violate)

- MUST NOT create `openspec/changes/<name>/` or `openspec/specs/<name>/`.
- MUST NOT create `.rddf/wt/<name>/`.
- MUST NOT invoke `git worktree add` or `openspec archive`.
- MUST NOT write to `iteration.json` / `sessions.json` / `roadmap-state.json`.
- MUST NOT read `openspec/changes/<name>/proposal.md` for AC extraction.
- MUST NOT read or write the rdd-builder-reserved environment variables listed in frontmatter `metadata.forbidden_env_vars`.
- MUST keep `select_worktree.sh` / `tasks_writeback.sh` / `_lib/archive.sh`
  byte-identical (sha256-locked by `tests/integration/test_rdd_quick_isolation.bats`).

## See also

- `skills/rdd-verifier/SKILL.md` — verdict JSON contract source (AC verbatim + scoring)
- `skills/rdd-builder/SKILL.md` — P0 dispatch-quick 触发方 (per ADR-0048 §Decision 3)
- `docs/adr/ADR-0047-rdd-quick-bypass-path.md` — decision record (AMENDED per ADR-0048)
- `docs/adr/ADR-0048-v4-stage-merge-revision.md` — v4 stage-merge revision (D1 立场反转)
- `.rddf/improvements/add-rdd-quick-skill.md` — design rationale
- `.rddf/improvements/guide-ship-quick-finish.md` — coexistence boundary (different scenario)
- `_lib/quick_history.py` + `_lib/schemas/quick_history_schema.json` — audit log data layer