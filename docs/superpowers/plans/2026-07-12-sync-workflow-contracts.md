# sync-workflow-contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize README / USAGE / AGENTS / INSTALL / package.json / ADR index / OpenSpec specs so they agree with each other and with production skill code, then add three anti-drift contract tests that fail CI when any surface diverges.

**Architecture:** This is a documentation / spec / test change with **zero production code modifications**. Workflow is purely external (no `skills/_lib/*.py`, no `skills/*.md` frontmatter beyond INSTALL description). TDD discipline applies to the three anti-drift tests only — write the failing test, see it red, change docs to make it green.

**Tech Stack:** bats-core 1.10+, Python 3.11+ (pytest), openspec CLI v1.3.1+, grep / find / jq / python -c.

---

## File Structure

Files this change touches:

| File | Operation | Responsibility |
|---|---|---|
| `README.md` | Modify | Directory tree + phase description |
| `USAGE.md` | Modify (already on v2.0.1) | Top changelog note + state-file table note + skill table note (if Option B chosen) |
| `AGENTS.md` | Modify | Key directory tree (skills 13; ADR indices; openspec 25) |
| `skills/INSTALL.md` | Modify | Description skill list; add `npm test vs pytest` block at end |
| `package.json` | Modify | Add `_comment` field with src-only skill note (Option B) |
| `docs/adr/README.md` | Modify | Extend status table to cover ADR 0001-0019 + ADR-0013 dup flag |
| `openspec/specs/general/spec.md` | Modify (inside change only) | MODIFIED Requirements on `general-docs-match-code` |
| `openspec/specs/doc-truth-sync/spec.md` | Modify (inside change only) | ADDED Requirements on `doc-contract-tests-required` + `doc-surfaces-share-truth-source` |
| `openspec/changes/sync-workflow-contracts/{.openspec.yaml,proposal.md,design.md,tasks.md,specs/*/spec.md}` | Already created (PROPOSED) | Leave alone until plan-done |
| `tests/integration/test_doc_contracts.bats` | Create | 5 D-series bats assertions |
| `tests/integration/test_adr_index.bats` | Create | ADR index coherence bats assertions |
| `tests/unit/test_doc_contracts.py` | Create | Python cross-spec assertions |

Files explicitly not touched: `skills/_lib/*.py`, `skills/guide-*.md` prose, `.github/workflows/test.yml`, all archived changes.

---

## Truth-source hierarchy (apply throughout)

| Layer | Role | Examples | Authority for … |
|---|---|---|---|
| L1 | Runtime skill code | `skills/guide-ship.md`; `skills/_lib/iteration.py` | phase numbering, side-effect contracts |
| L2 | Filesystem ground truth | `ls skills/*.md`; `docs/adr/ADR-*.md` | disk-truth counts |
| L3 | Distribution + OpenSpec specs | `package.json::skills[]`; `openspec/specs/*/spec.md` | "promised" surface |
| L4 | Narrative docs | `README.md`, `USAGE.md`, `AGENTS.md`, `INSTALL.md`, `docs/v2-adr-summary.md` | explanatory prose |

Reconcile direction: L4 → L3 → L2 → L1. L1 is **never** modified to satisfy a doc.

---

## Task numbering convention

- Task `N.M` — top-level + sub-task id from the change's `tasks.md`.
- Implementation **must** preserve the order the change's `tasks.md` prescribes (baseline → docs/manifest → ADR → specs → tests → verify → archive).

---

# Phase 1 — Baseline verification

### Task 1.1: Confirm the seven drift classes are reproducible

**Files:** none (read-only).

- [ ] **Step 1: Snapshot current disk truth**

```bash
cd /workspace/project/rdd-workflow

echo "=== skills on disk ===" && ls skills/*.md | wc -l
echo "=== package.json skills count ===" && python3 -c "import json; print(len(json.load(open('package.json'))['skills']))"
echo "=== ADR files ===" && find docs/adr -maxdepth 1 -name 'ADR-*.md' | wc -l
echo "=== ADR unique numbers ===" && find docs/adr -maxdepth 1 -name 'ADR-*.md' | sed -E 's|.*ADR-([0-9]+).*|\1|' | sort -u
echo "=== openspec specs ===" && ls openspec/specs/ | wc -l
```

Expected output:
- 13 / 11 / 21 / `{0001..0019}` / 25

Notes:
- `find docs/adr -maxdepth 1 -name 'ADR-*.md' | wc -l` returns **21** = 19 unique numbers + 2 ADR-0013 duplicates.
- `sed -E` over the same list returns **19 unique numbers** because both `ADR-0013-*.md` collapse to `0013`.

- [ ] **Step 2: Snapshot narrative drift fields**

```bash
cd /workspace/project/rdd-workflow

echo "=== USAGE.md ship phase count ===" && grep -cE "Phase 1\.5" USAGE.md
echo "=== USAGE.md dotted arch-handoff ===" && grep -cE '\.rddf/state/\.arch-handoff\.json' USAGE.md
echo "=== general/spec.md ship phase wording ===" && grep -E "ship-side|5 阶段" openspec/specs/general/spec.md || true
echo "=== general/spec.md handoff path ===" && grep -E 'handoff\.json|".sisyphus/plans/"' openspec/specs/general/spec.md || true
echo "=== general/spec.md guide-spec consumer ===" && grep -nE "guide-spec" openspec/specs/general/spec.md || true
echo "=== AGENTS.md skill count line ===" && grep -nE "12 个 \.md|13 个 \.md" AGENTS.md || true
echo "=== docs/adr/README.md status table size ===" && awk 'NR>=1 && NR<=40' docs/adr/README.md | grep -cE '\| ADR-00[0-9]+ \|'
```

Expected:
- `Phase 1.5` count in USAGE.md ≥ 1
- Dotted arch-handoff in USAGE.md ≥ 1
- `general/spec.md` reports `5 阶段` style wording (stale)
- `general/spec.md` references undotted `handoff.json` or `.sisyphus/plans/` (stale)
- `general/spec.md` references `guide-spec` (stale — removed in v2.0)
- `AGENTS.md` skill-count line still says `12 个 .md` (stale)
- `docs/adr/README.md` status table size ≤ 13 (current implementation limit)

If any expected line is absent, capture the diff but do not block — the seven drift classes are still the change's reason for existence.

- [ ] **Step 3: Run pre-existing test suite for the baseline green state**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short
bats tests/smoke.bats
```

Expected:
- pytest: all 28-45 unit files (current count) pass.
- bats: 7 smoke cases pass.

If pytest or bats are unavailable in this environment, capture the failure and continue — `openspec validate` of the change is the proxy for change correctness.

---

# Phase 2 — Decision: `package.json::skills[]` and ADR-0013 handling

### Task 2.1: Record the maintainer decision in `openspec/changes/sync-workflow-contracts/proposal.md`

**Files:**
- Modify: `openspec/changes/sync-workflow-contracts/proposal.md` (append a short Decision Log section before `## Why`)

Note: this is **changing a draft**, not narrative docs. The change is still PROPOSED.

- [ ] **Step 1: Append a Decision Log section**

Append the following block immediately after the YAML frontmatter of `proposal.md` (so it sits before `## Why`):

```markdown

## Decision Log (added during plan-done)

- **DL-1 (skill publish surface)**: choose **Option B** from `## What Changes` — keep `package.json::skills[]` at 11 entries; add a top-level `_comment` field naming `feature` and `rddf-session` as src-only skills. INSTALL.md description is **not** modified by Option B; it keeps its current 13-skill enumeration.
- **DL-2 (ADR-0013)**: choose **Option C** from `## What Changes` — keep both `ADR-0013-*.md` files and add an explicit ⚠️ flag in `docs/adr/README.md` pointing to a follow-up change.
- **DL-3 (worktree / lightweight)**: keep current branch `master`. The change implements docs + tests only; no worktree is required, all work happens in place.
```

- [ ] **Step 2: Verify the frontmatter still parses**

```bash
cd /workspace/project/rdd-workflow
openspec validate sync-workflow-contracts --strict
```

Expected: `Change 'sync-workflow-contracts' is valid`.

- [ ] **Step 3: Commit the change draft update (only this PR's PROPOSED change draft)**

```bash
cd /workspace/project/rdd-workflow
git add openspec/changes/sync-workflow-contracts/proposal.md
git commit -m "chore(plan): record decision log for sync-workflow-contracts"
```

### Task 2.2: Apply Option B to `package.json` and revalidate

**Files:**
- Modify: `package.json` (add `_comment` field; do **not** add `feature` or `rddf-session` to `skills[]`).

- [ ] **Step 1: Write the failing test for src-only annotation**

Create `tests/integration/test_doc_contracts.bats` first (only Task 2.2-relevant assertion):

```bash
mkdir -p tests/integration
cat > tests/integration/test_doc_contracts.bats <<'EOF'
#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "doc_truth_sync: package.json declares src-only skills via _comment" {
  run python3 - <<'PY'
import json, sys
data = json.load(open("package.json"))
comment = data.get("_comment", "")
assert "feature" in comment and "rddf-session" in comment, (
    "expected `_comment` to mention src-only skills feature, rddf-session; got: "
    + repr(comment)
)
PY
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
EOF
```

- [ ] **Step 2: Run the failing test**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: 1 test, **failing** (the test exits non-zero; the `_comment` field does not yet exist).

- [ ] **Step 3: Add the `_comment` field to `package.json`**

Edit `package.json` to add `"_comment"` immediately after `"name": "rdd-workflow"`, *before* `"version"`. Use `python3` for safe JSON edit:

```bash
cd /workspace/project/rdd-workflow
python3 - <<'PY'
import json, sys
from pathlib import Path

p = Path("package.json")
data = json.loads(p.read_text())
data["_comment"] = (
    "src-only skills (not published via npm manifest): feature, rddf-session. "
    "Listed under skills/ in the repo for internal use; npm install exposes "
    "the 11 skills defined in skills[] below."
)
p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
p.write_text(p.read_text() + "\n")
PY
```

Verify:

```bash
python3 -c "import json; d=json.load(open('package.json')); print(d['_comment'])"
```

Expected: prints the comment string and exits 0.

- [ ] **Step 4: Run the test again**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: 1 test, **passing**.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add package.json tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): annotate package.json src-only skills + first anti-drift test"
```

---

# Phase 3 — Synchronize narrative docs

### Task 3.1: Bump AGENTS.md skill and ADR counts to disk truth

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Add the AGENTS.md coherence failure test**

Append a new `@test` to `tests/integration/test_doc_contracts.bats`:

```bash
cat >> tests/integration/test_doc_contracts.bats <<'EOF'

@test "doc_truth_sync: AGENTS.md skill count matches ls skills/*.md" {
  disk=$(ls skills/*.md | wc -l)
  if ! grep -qE "13 个 \.md" AGENTS.md; then
    echo "AGENTS.md missing '13 个 .md' (disk has $disk)"
    return 1
  fi
}
EOF
```

- [ ] **Step 2: Confirm the test is red**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: at least 1 test **failing** on the new assertion (AGENTS.md still says `12 个 .md`).

- [ ] **Step 3: Update AGENTS.md skill count**

Use Edit on the line that currently states the `12 个 .md` figure inside the `skills/` directory-tree block of `AGENTS.md`, replace it with `13 个 .md`，并在其下方紧跟一行说明：

```markdown
- `skills/` — Markdown skill 文件（v2.0 总计 13 个 `.md`）；其中 11 个通过 npm manifest 发布，`feature` 与 `rddf-session` 仅在仓库内（src-only）
```

(Keep the broader AGENTS.md structure intact; only edit the line/section mentioning the skill count.)

- [ ] **Step 4: Run the test**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: 1 failing test now passes.

- [ ] **Step 5: Bump ADR count + openspec specs count in AGENTS.md**

Add a new `@test`:

```bash
cat >> tests/integration/test_doc_contracts.bats <<'EOF'

@test "doc_truth_sync: AGENTS.md ADR table lists 0001-0019 with ADR-0013 dup note" {
  for n in 0001 0010 0019 0013; do
    if ! grep -qE "ADR-${n}\b" AGENTS.md; then
      echo "AGENTS.md missing ADR-${n}"
      return 1
    fi
  done
  if ! grep -qE "ADR-0013.*重复|重复.*ADR-0013|extract-scan-state.*incremental-skeleton-planning" AGENTS.md; then
    echo "AGENTS.md missing ADR-0013 dup annotation"
    return 1
  fi
}
EOF
```

Run:

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: new test **failing** until step 3 edits below.

- [ ] **Step 6: Update AGENTS.md ADR / openspec sentences**

In `AGENTS.md::当前最新编号: ADR-0012` line, replace `ADR-0012` with the precise disk-truth text:

```markdown
当前 ADR 范围：`0001`~`0019`（19 个唯一编号，20 个实体 ADR 文件，因 `ADR-0013-extract-scan-state` 与 `ADR-0013-incremental-skeleton-planning` 共编号；22 个 `docs/adr/*.md` 含 `README.md` 与 `ADR-0000-template.md`）
```

In `openspec/specs/ (22 个)` line, set the count to:

```markdown
openspec/specs/ (25 个)
```

Use `ls openspec/specs/` to confirm 25 directories before editing.

- [ ] **Step 7: Re-run the test**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
cd /workspace/project/rdd-workflow
git add AGENTS.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync AGENTS.md skill + ADR counts"
```

### Task 3.2: Update INSTALL.md to declare the npm-vs-pytest contract and 13-skill description

**Files:**
- Modify: `skills/INSTALL.md`

- [ ] **Step 1: Add a new bats assertion**

```bash
cat >> tests/integration/test_doc_contracts.bats <<'EOF'

@test "doc_truth_sync: INSTALL.md description lists 13 skills + npm-test-vs-pytest block" {
  if ! grep -qE "全部 13 个子技能" skills/INSTALL.md; then
    echo "INSTALL.md description missing '全部 13 个子技能'"
    return 1
  fi
  if ! grep -qE "npm test 只跑 bats" skills/INSTALL.md; then
    echo "INSTALL.md missing 'npm test vs pytest' reminder block"
    return 1
  fi
}
EOF
```

- [ ] **Step 2: Run; confirm red**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: at least one failing assertion regarding INSTALL.md.

- [ ] **Step 3: Append the `npm test vs pytest` block to INSTALL.md**

Append (verbatim) at the end of `skills/INSTALL.md`:

```markdown

## npm test vs pytest

> rdd-workflow 的 CI 陷阱：`npm test` 只跑 `bats tests/`，**不**跑 `pytest`。
> 任何 Python 代码改动后必须显式执行 `pytest tests/` 或 `pytest tests/unit/`。
> 反漂移测试 `tests/integration/test_doc_contracts.bats` 会断言本约束不被违反。
```

- [ ] **Step 4: Re-run**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add skills/INSTALL.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync INSTALL.md description + add npm-vs-pytest block"
```

### Task 3.3: Update README.md directory tree and v2 feature table

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the test**

```bash
cat >> tests/integration/test_doc_contracts.bats <<'EOF'

@test "doc_truth_sync: README.md directory tree lists guide-arch / guide-plan / loop_engine / _lib" {
  for name in guide-arch.md guide-plan.md loop_engine.py "_lib"; do
    if ! grep -qE "$name" README.md; then
      echo "README.md missing '$name' in tree"
      return 1
    fi
  done
}
EOF
```

- [ ] **Step 2: Run; confirm red**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: at least one failure in README.md.

- [ ] **Step 3: Update README.md directory structure block**

Replace the existing `skills/` directory-tree block in `README.md` so it lists each of the following (use the exact text below as a guide; preserve existing prose around it):

```markdown
└── skills/
    ├── INSTALL.md             # 安装程序（第一入口）
    ├── guide.md               # 推荐器入口
    ├── guide-arch.md          # Arch 阶段状态机(v2.0+)
    ├── guide-plan.md          # Plan 阶段状态机(v2.0+)
    ├── guide-ship.md          # Ship 端状态机（Phase 1, 1.5, 2, 2.5, 3, 4, 5）
    ├── feature.md             # feature 管理 (v1.0)
    ├── rddf-session.md        # 跨 OpenCode session 恢复 (ADR-0017)
    ├── propose.md             # 子技能(被 guide-plan 调用)
    ├── execute.md             # 子技能(被 guide-ship 调用)
    ├── roadmap.md             # 子技能(被 guide-arch 调用)
    ├── deps.md                # 子技能(被 guide-plan 调用)
    ├── status.md              # 子技能(被 guide-ship 调用或独立使用)
    ├── rdd-workflow-writing-plans.md  # 实施计划生成器 (TDD 5 步, v2.0 自包含)
    ├── loop_engine.py         # v2.0 Loop 引擎入口
    └── _lib/                  # v2.0 共享辅助（state / worktree / archive / deps / iteration 等）
```

Use Edit with the existing tree as `oldString` and the above as `newString`. The exact list — 13 `.md` files + `loop_engine.py` + `_lib/` subdir — is the canonical list to embed.

- [ ] **Step 4: Re-run**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add README.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync README.md directory tree to disk"
```

### Task 3.4: Update USAGE.md top changelog note + state-file table (non-destructive)

**Files:**
- Modify: `USAGE.md`

- [ ] **Step 1: Add test asserting the changelog banner**

```bash
cat >> tests/integration/test_doc_contracts.bats <<'EOF'

@test "doc_truth_sync: USAGE.md changelog banner names v2.0.1 + sync-workflow-contracts" {
  if ! grep -qE "v2\.0\.1" USAGE.md; then
    echo "USAGE.md missing 'v2.0.1' in header"
    return 1
  fi
  if ! grep -qE "sync-workflow-contracts" USAGE.md; then
    echo "USAGE.md missing 'sync-workflow-contracts' changelog note"
    return 1
  fi
}
EOF
```

- [ ] **Step 2: Run; confirm red**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: failing assertions about USAGE.md changelog.

- [ ] **Step 3: Insert a changelog note into USAGE.md header**

Add (immediately above the existing first paragraph `> 基于 guide 推荐器 ...`):

```markdown
> **v2.0.2 / sync-workflow-contracts**：本版本同步多 surface 文档契约（README / AGENTS / INSTALL / package.json / ADR index / OpenSpec specs），并加 anti-drift contract 测试；运行时工作流不变。本 change 不引入新运行时行为。
```

- [ ] **Step 4: Re-run**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: all tests pass.

- [ ] **Step 5: Add a state-file table coherence test (D4 + canonical/legacy note)**

```bash
cat >> tests/integration/test_doc_contracts.bats <<'EOF'

@test "doc_truth_sync: USAGE.md state-file table uses dotted prefixes for handoff-style + canonical/legacy note" {
  # handoff-style files must use dotted prefix
  for tail in ".arch-handoff.json" ".plan-handoff.json" ".deps-candidates.json" ".deps-output.md"; do
    full=".rddf/state/${tail}"
    if ! grep -qF "$full" USAGE.md; then
      echo "USAGE.md missing state-file path '$full'"
      return 1
    fi
  done
  # undotted but non-handoff state files must also appear with their canonical path
  for tail in "deps-analysis.json" "iteration.json" "sessions.json" "index.md"; do
    full=".rddf/state/${tail}"
    if ! grep -qF "$full" USAGE.md; then
      echo "USAGE.md missing state-file path '$full'"
      return 1
    fi
  done
  # roadmap-state.json: dotted and undotted both acceptable; MUST have legacy note
  if grep -qF ".rddf/state/.roadmap-state.json" USAGE.md; then
    if ! grep -qF ".rddf/state/roadmap-state.json" USAGE.md; then
      echo "USAGE.md lists dotted roadmap-state but lacks legacy undotted alias note"
      return 1
    fi
  fi
}
EOF
```

- [ ] **Step 6: Run; confirm green if USAGE.md is already on v2.0.1**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

If green: leave the table as the implementer updated in a prior audit (Step 6 done). If red: proceed to Step 7.

- [ ] **Step 7: (Only if Step 6 red) Edit the state-file table in USAGE.md to match the test anchors**

In USAGE.md, ensure the state-file table contains these exact path strings (use Edit with the existing rows as `oldString`, swap to the equivalents below):

```markdown
| `.rddf/state/.arch-handoff.json` | `.rddf/state/`（gitignored） | arch → plan 阶段交接（ADR-0016 发现契约） | `guide-arch` / `guide-plan` |
| `.rddf/state/.plan-handoff.json` | `.rddf/state/`（gitignored） | plan → ship 阶段交接 | `guide-plan` / `guide-ship` |
| `.rddf/state/deps-analysis.json` | `.rddf/state/`（gitignored） | deps 结构化 JSON（schema 在 `skills/_lib/schemas/deps_analysis_schema.json`） | `deps` Step 5b/6 |
| `.rddf/state/.deps-candidates.json` | `.rddf/state/`（gitignored） | deps 候选 change 列表 | `guide-plan` deps / Review 自动增量 |
| `.rddf/state/.deps-output.md` | `.rddf/state/`（gitignored） | deps 人类可读报告（旧 `deps-output.md` 仅作兼容） | `deps` Step 5 |
| `.rddf/state/sessions.json` | `.rddf/state/`（gitignored） | rddf-session 生命周期（ADR-0017） | `guide-arch` / `guide-plan` / `guide-ship` |
| `.rddf/state/iteration.json` | `.rddf/state/`（gitignored） | sprint 视图（v2.0.1） | `propose` / `guide-ship` / `execute` / `deps` / `archive` |
| `.rddf/state/roadmap-state.json` 与 `.rddf/state/.roadmap-state.json` | `.rddf/state/`（gitignored） | 点 / 无点引用均存在于生产 skill 文档中，canonical 决策留待后续 change | `propose` / `guide-arch` / `roadmap` / `sync_state.py` |
| `.rddf/state/index.md` | `.rddf/state/`（gitignored） | change 索引 | `guide-arch` / `guide-plan` |
```

Note: `roadmap-state.json` line intentionally keeps BOTH the dotted and undotted forms visible; the doc must label them as a canonicalization decision rather than silently normalizing. The next change (`fix-roadmap-state-canonical`) will resolve this.

- [ ] **Step 8: Re-run**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_doc_contracts.bats
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
cd /workspace/project/rdd-workflow
git add USAGE.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync USAGE.md state-file table to production paths"
```

---

# Phase 4 — Update ADR index and OpenSpec specs

### Task 4.1: Extend `docs/adr/README.md` status table to ADR 0001-0019

**Files:**
- Modify: `docs/adr/README.md`

- [ ] **Step 1: Drop in the `test_adr_index.bats` first**

Create `tests/integration/test_adr_index.bats`:

```bash
mkdir -p tests/integration
cat > tests/integration/test_adr_index.bats <<'EOF'
#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "adr_index: docs/adr/README.md status table covers all real ADRs (0001-0019)" {
  for n in 0001 0005 0010 0015 0017 0018 0019; do
    if ! grep -qE "ADR-${n}\b" docs/adr/README.md; then
      echo "docs/adr/README.md missing ADR-${n} reference"
      return 1
    fi
  done
}

@test "adr_index: docs/adr/README.md does NOT reference ADR-NNN beyond 0019" {
  bad=$(grep -oE "ADR-0[0-9]{3}" docs/adr/README.md | sort -u | grep -E "ADR-0(0[0-9]{2}|[2-9][0-9]{2})" || true)
  if [ -n "$bad" ]; then
    echo "docs/adr/README.md references out-of-range ADRs: $bad"
    return 1
  fi
}

@test "adr_index: duplicated ADR-0013 is explicitly flagged in README.md" {
  if ! grep -qE "ADR-0013.*重复|重复.*ADR-0013|extract-scan-state.*incremental-skeleton-planning" docs/adr/README.md; then
    echo "docs/adr/README.md missing ADR-0013 dup flag"
    return 1
  fi
}

@test "adr_index: docs/adr/README.md status table is consistent with disk" {
  missing=""
  for adr in $(find docs/adr -maxdepth 1 -name 'ADR-*.md' | sort); do
    num=$(echo "$adr" | sed -E 's|.*ADR-([0-9]+).*|\1|')
    base=$(basename "$adr")
    if ! grep -qF "$base" docs/adr/README.md; then
      missing="${missing}${base} "
    fi
    # Number is already covered by the explicit numbering grep in the previous test
    unset num
  done
  if [ -n "$missing" ]; then
    echo "docs/adr/README.md does not reference real ADR files: $missing"
    return 1
  fi
}
EOF
```

- [ ] **Step 2: Run; expect failures**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_adr_index.bats
```

Expected: at least one failure for ADR 0013, 0017, 0018, 0019.

- [ ] **Step 3: Insert the ADR-0013 flag block above the status table**

Open `docs/adr/README.md`. Immediately above the existing status table (the table that lists ADR-0001 through ADR-0016 with implementation status), insert:

```markdown
> ⚠️ **ADR-0013 dup**：仓库内有两个 `ADR-0013-*.md`：`extract-scan-state` 与 `incremental-skeleton-planning`。
> 处理方案由后续 `fix-adr-index-and-numbering` 决策决定；当前保留两个文件并在 index 中显式标注。
```

- [ ] **Step 4: Extend the status table to cover all of ADR 0001 through 0019**

Find the existing status table. For any ADR number from `0001` through `0019` **that is missing** from the table, append an additional row referencing the existing ADR file. Use `find docs/adr -maxdepth 1 -name 'ADR-NNNN-*.md' | sort` to enumerate real files. The new rows for missing ADRs should follow this template (replace `<num>` and `<topic>` with the ADR-specific text from each file's title):

```markdown
| `ADR-<num>-<topic>.md` | ✅ 已采纳（v2.0.1） | … |
```

If you cannot determine the topic from the file's title, fall back to:

```markdown
| `ADR-<num>-*.md` | ✅ 已采纳（v2.0.1） | (see file for content) |
```

After extending, the total number of table rows for the v2.0 status block SHALL equal the count of `find docs/adr -maxdepth 1 -name 'ADR-*.md' | wc -l` = **21** entries.

- [ ] **Step 5: Re-run**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_adr_index.bats
```

Expected: all 4 tests pass.

- [ ] **Step 6: Commit**

```bash
cd /workspace/project/rdd-workflow
git add docs/adr/README.md tests/integration/test_adr_index.bats
git commit -m "feat(contracts): extend ADR index status table to 0001-0019 + flag ADR-0013 dup"
```

### Task 4.2: Update `openspec/specs/general/spec.md` to MODIFIED Requirements

**Files:**
- Modify: `openspec/specs/general/spec.md` (this is the **base** file, not the change copy)

- [ ] **Step 1: Add a Python test asserting general/spec.md updates land**

Add this assertion to `tests/unit/test_doc_contracts.py`:

```bash
mkdir -p tests/unit
cat > tests/unit/test_doc_contracts.py <<'EOF'
"""Cross-doc / cross-spec contract tests for sync-workflow-contracts."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


def test_general_spec_phase_count_matches_usaged() -> None:
    """openspec/specs/general/spec.md must use the v2.0.1 7-subphase phrasing."""
    spec = _read("openspec/specs/general/spec.md")
    # New phrasing must be present.
    assert "7 numbered subphases" in spec or "7 编号子阶段" in spec
    # Old phrasing must be gone from the canonical scenario.
    assert "5 阶段 + 1 退出" not in spec, (
        "general/spec.md still references the v1.x '5 阶段 + 1 退出' ship-side"
    )


def test_general_spec_no_guide_spec_reference() -> None:
    """guide-spec was removed in v2.0; general/spec.md must not list it."""
    spec = _read("openspec/specs/general/spec.md")
    assert "guide-spec" not in spec, (
        "general/spec.md still references 'guide-spec' which was removed in v2.0"
    )


def test_general_spec_consumers_drop_guide_spec_add_arch_plan() -> None:
    """general/spec.md consumer list must include guide-arch + guide-plan."""
    spec = _read("openspec/specs/general/spec.md")
    assert "guide-arch" in spec
    assert "guide-plan" in spec


def test_install_description_skill_count_matches_disk() -> None:
    """INSTALL.md description's skill-count claim must equal ls skills/*.md."""
    disk = len(list((REPO_ROOT / "skills").glob("*.md")))
    inst = _read("skills/INSTALL.md")
    m = re.search(r"全部\s*(\d+)\s*个子技能", inst)
    assert m is not None, "INSTALL.md description missing '全部 N 个子技能'"
    assert int(m.group(1)) == disk, (
        f"INSTALL.md claims {m.group(1)} skills, disk has {disk}"
    )


def test_package_json_skills_count_within_delta() -> None:
    """package.json::skills[] length MUST be <= disk count + 2 (src-only slack)."""
    import json

    pkg = json.loads(_read("package.json"))
    disk = len(list((REPO_ROOT / "skills").glob("*.md")))
    assert len(pkg["skills"]) <= disk + 2, (
        f"package.json declares {len(pkg['skills'])} skills, disk has {disk}; "
        f"delta > 2 violates src-only rule"
    )


def test_state_file_paths_in_general_spec_use_canonical_paths() -> None:
    """general/spec.md state-file table must reference production paths."""
    spec = _read("openspec/specs/general/spec.md")
    # Production dotted paths
    for tail in (
        ".arch-handoff.json",
        ".plan-handoff.json",
        ".deps-candidates.json",
        ".deps-output.md",
    ):
        assert f".rddf/state/{tail}" in spec, (
            f"general/spec.md missing production path '.rddf/state/{tail}'"
        )
    # Production undotted paths
    for tail in ("deps-analysis.json",):
        assert f".rddf/state/{tail}" in spec, (
            f"general/spec.md missing production path '.rddf/state/{tail}'"
        )
    # Forbidden stale references
    assert "handoff.json" not in spec or ".arch-handoff.json" in spec
    # .sisyphus/plans/... must not appear anywhere in spec
    assert ".sisyphus/plans" not in spec


def test_npm_test_trap_caveat_locked() -> None:
    """npm test must continue to run only bats."""
    import json

    pkg = json.loads(_read("package.json"))
    assert pkg["scripts"]["test"] == "bats tests/", (
        f"package.json::scripts.test is {pkg['scripts']['test']!r}; "
        f"expected exactly 'bats tests/'"
    )


def test_adr_index_references_real_files() -> None:
    """docs/adr/README.md must not reference deleted ADRs."""
    adr_dir = REPO_ROOT / "docs/adr"
    real = {p.name for p in adr_dir.glob("ADR-*.md")}
    readme = _read("docs/adr/README.md")
    referenced = set(re.findall(r"ADR-\d{4}-[\w-]+\.md", readme))
    missing = referenced - real
    assert not missing, f"docs/adr/README.md references missing ADR files: {sorted(missing)}"
EOF
```

- [ ] **Step 2: Run; expect a few failing tests**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_doc_contracts.py -v
```

Expected: failures in `test_general_spec_phase_count_matches_usaged`, `test_general_spec_no_guide_spec_reference`, `test_state_file_paths_in_general_spec_use_canonical_paths` (the **base** spec file is still stale).

- [ ] **Step 3: Edit `openspec/specs/general/spec.md`**

Apply edits to the **base** general spec file (not the change copy) so the test passes:

1. `#### Scenario: USAGE.md ship-side phase count` — replace `5 阶段 + 1 退出` with:

```markdown
#### Scenario: USAGE.md ship-side phase count
- **WHEN** `USAGE.md` is read
- **THEN** it SHALL describe ship-side as **7 numbered subphases (Phase 1, 1.5,
  2, 2.5, 3, 4, 5)** with sequence
  `plan → verification → execute → review → archive → cleanup → ship-done`
- **AND** Phase 2.5 Review SHALL be explicitly named (execute 后债务扫描)
```

2. `#### Scenario: USAGE.md state-file table` — replace the line list with the canonical version:

```markdown
#### Scenario: USAGE.md state-file table uses production paths
- **WHEN** `USAGE.md` is read
- **THEN** the state-file table SHALL list only files that exist on disk
- **AND** dotted handoff-style files SHALL be referenced with the leading dot:
  - `.rddf/state/.arch-handoff.json`
  - `.rddf/state/.plan-handoff.json`
  - `.rddf/state/.deps-candidates.json`
  - `.rddf/state/.deps-output.md`
- **AND** `deps-analysis.json` SHALL be referenced without the leading dot:
  - `.rddf/state/deps-analysis.json`
- **AND** `.rddf/state/roadmap-state.json` and `.rddf/state/.roadmap-state.json`
  may both appear if and only if the doc labels which is canonical and which is legacy
- **AND** the table SHALL NOT contain `handoff.json` (undotted) or
  `.sisyphus/plans/<name>.md` (wrong directory)
```

3. `#### Scenario: proposal-suggestions-format lists all 5 consumers` — replace the consumer list:

```markdown
#### Scenario: proposal-suggestions-format lists current consumers
- **WHEN** `docs/proposal-suggestions-format.md` is read
- **THEN** the consumer list SHALL include `propose`, `guide-arch`,
  `guide-plan`, `guide`, `status`, and `deps`
- **AND** it SHALL NOT list `guide-spec` (removed in v2.0)
```

- [ ] **Step 4: Re-run**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_doc_contracts.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add openspec/specs/general/spec.md tests/unit/test_doc_contracts.py
git commit -m "feat(contracts): update general/spec.md to v2.0.1 + lock with python tests"
```

### Task 4.3: Promote change's spec deltas into base specs via `openspec archive` later

This task is a **placeholder** — the `openspec` archiving workflow in this project copies spec deltas from change copies to base specs automatically during `openspec archive`. No manual merge is required here.

- [ ] **Step 1: Verify `openspec/specs/doc-truth-sync/spec.md` is NOT manually edited during this change**

The change's `openspec/changes/sync-workflow-contracts/specs/doc-truth-sync/spec.md` already declares the `ADDED Requirements` for `doc-contract-tests-required` and `doc-surfaces-share-truth-source`, plus `MODIFIED Requirements` for `install-usage-readme-metadata-sync` and `v2-adr-summary-accurate`. Per OpenSpec convention, these deltas land in the base spec upon archive (Task 7.2 in `tasks.md`).

The base `openspec/specs/doc-truth-sync/spec.md` MUST NOT be edited by this plan. Verify the guard by checking git status at the end of this plan:

```bash
cd /workspace/project/rdd-workflow
# Base spec must not appear in this change's working tree diff
! git status --short -- openspec/specs/doc-truth-sync/spec.md
```

Expected: exit 0 (`!` flips git-status-exit-1 to 0 when the file has no diff).

If the guard fails (exit non-zero, meaning the base spec was edited), revert the file with:

```bash
cd /workspace/project/rdd-workflow
git checkout -- openspec/specs/doc-truth-sync/spec.md
```

…and stop, because manually editing the base spec out-of-band breaks the archive-time delta merge.

- [ ] **Step 2: Run validation to confirm**

```bash
cd /workspace/project/rdd-workflow
openspec validate sync-workflow-contracts --strict
```

Expected: `Change 'sync-workflow-contracts' is valid`.

---

# Phase 5 — Final verification

### Task 5.1: Full suite green

- [ ] **Step 1: pytest unit**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short
```

Expected: exit 0, all unit tests pass (≥ 30 files including `test_doc_contracts.py`).

- [ ] **Step 2: pytest integration**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/integration/ -q --tb=short
```

Expected: exit 0, all Python integration tests pass.

- [ ] **Step 3: bats all**

```bash
cd /workspace/project/rdd-workflow
bats tests/
```

Expected: exit 0, all bats tests pass (smoke + static + git-worktree + adr-index + doc-contracts).

- [ ] **Step 4: openspec validate**

```bash
cd /workspace/project/rdd-workflow
openspec validate sync-workflow-contracts --strict
openspec validate
```

Expected: both exit 0; "Change 'sync-workflow-contracts' is valid".

- [ ] **Step 5: CI 质量门控**

```bash
cd /workspace/project/rdd-workflow
! grep -rn 'assert.*or True\|assert True' tests/
```

Expected: exit 0 (`!` inverts: zero matches means `grep` returns 1, `!` flips to 0).

### Task 5.2: Drift regression drill (sanity)

- [ ] **Step 1: Provoke a phase-count drift and confirm anti-drift test catches it**

```bash
cd /workspace/project/rdd-workflow
cp USAGE.md /tmp/USAGE.md.bak
sed -i 's/Phase 1\.5/Phase 1\.6/' USAGE.md
bats tests/integration/test_doc_contracts.bats 2>&1 | tail -10
exit_code=$?
mv /tmp/USAGE.md.bak USAGE.md
echo "observed exit_code=$exit_code"
[ "$exit_code" -ne 0 ] && bats tests/integration/test_doc_contracts.bats 2>&1 | tail -3
```

Expected: the first `bats` run exits non-zero AND stderr mentions `Phase` mismatch; after restore, the second `bats` run exits 0.

- [ ] **Step 2: Provoke an ADR index drift and confirm `test_adr_index.bats` catches it**

```bash
cd /workspace/project/rdd-workflow
cp docs/adr/README.md /tmp/README.md.bak
sed -i 's/ADR-0017/ADR-0017-DUMMY/' docs/adr/README.md
bats tests/integration/test_adr_index.bats 2>&1 | tail -10
exit_code=$?
mv /tmp/README.md.bak docs/adr/README.md
echo "observed exit_code=$exit_code"
[ "$exit_code" -ne 0 ] && bats tests/integration/test_adr_index.bats 2>&1 | tail -3
```

Expected: exit_code non-zero on the first run; restored run exits 0.

---

# Phase 6 — Acceptance + handoff

### Task 6.1: Mark all acceptance checkboxes in the change proposal

- [ ] **Step 1: Update the proposal acceptance criteria (replace `- [ ]` with `- [x]` for completed items)**

Edit `openspec/changes/sync-workflow-contracts/proposal.md` and replace every `- [ ]` line in `## Acceptance Criteria` with `- [x]`. Do not change wording.

Verify:

```bash
cd /workspace/project/rdd-workflow
grep -c "^- \[ \]" openspec/changes/sync-workflow-contracts/proposal.md || true
```

Expected: zero matches in the proposal's `## Acceptance Criteria` section.

- [ ] **Step 2: Commit the acceptance tick**

```bash
cd /workspace/project/rdd-workflow
git add openspec/changes/sync-workflow-contracts/proposal.md
git commit -m "chore(contracts): mark acceptance criteria complete"
```

### Task 6.2: Print final status

- [ ] **Step 1: Run the unified verification block**

```bash
cd /workspace/project/rdd-workflow

echo "=== openspec validate ==="
openspec validate sync-workflow-contracts --strict
echo "=== pytest unit ==="
python3 -m pytest tests/unit/ -q --tb=short
echo "=== pytest integration ==="
python3 -m pytest tests/integration/ -q --tb=short
echo "=== bats all ==="
bats tests/
echo "=== CI quality gate (assert-or-True / assert True) ==="
if grep -rn 'assert.*or True\|assert True' tests/; then
  echo "FAIL: tautological asserts present"
  exit 1
else
  echo "PASS: no tautological asserts"
fi
echo "=== git status ==="
git status --short
```

Expected:
- All four validators exit 0.
- Final `git status --short` shows no uncommitted edits to source files beyond the change's PROPOSED draft.

---

# Out-of-scope reminders

These are explicitly **NOT** part of this plan; treat as future-change prep:

1. **ADR-0013 dup handling** — `init-deep` decision. This change only flags it.
2. **`package.json` Option A (publish `feature` + `rddf-session`)** — gated on their API stabilizing (per Decision 3 in `design.md`).
3. **`roadmap-state.json` dotted/undotted canonicalization** — separate `fix-roadmap-state-canonical` change. This change only labels the alias.
4. **`docs/v2-adr-summary.md` audit** — out of scope; not part of this change's synced surfaces.

---

# Anti-patterns to avoid during execution

- **Do not edit `skills/_lib/*.py`** — violates Decision 1 (L1 immutability) and the proposal's `## 不做什么`.
- **Do not edit production skill prose** (`skills/guide-*.md`) — `writing-plans` would be a different change.
- **Do not commit without running the relevant `bats` / `pytest` block** — violates TDD discipline declared in Decision 6.
- **Do not reformat spec files** — preserve field order so future Contract tests stay anchored.
- **Do not add `assert True` or `assert ... or True`** — CI quality gate (`grep`) will reject the change.

---

# After plan-done

When all tasks complete and final commit lands:

```bash
cd /workspace/project/rdd-workflow
openspec validate sync-workflow-contracts --strict
git log --oneline -20
git status --short
```

Then hand-off summary (printed to user):

```text
sync-workflow-contracts implementation plan executed.
- 1 decision log entry added
- 1 package.json src-only annotation
- 4 narrative docs synced (README, USAGE, AGENTS, INSTALL)
- 1 ADR index extended (0001-0019 + 0013 dup flag)
- 1 base spec updated (general/spec.md)
- 2 bats test files + 1 pytest test file added
- All bats + pytest suites green; openspec validate passes; CI gate intact
```

---

**END OF PLAN**
