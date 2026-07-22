# 实施计划: sync-workflow-contracts

> 对应 change: `openspec/changes/sync-workflow-contracts/`（PROPOSED）
> 实施位置: 主仓库 master（**无 worktree**，原因是本 change 不修改 production skill 代码，仅 docs / specs / 测试）
> 完整设计: `docs/superpowers/plans/2026-07-12-sync-workflow-contracts.md`（1149 行，TDD 5 步任务群）
> 本文件是 ship 端可执行 contract 摘要，命令字段已 ready-to-run

## 概览

| Phase | Task Group | 操作面 | 风险 |
|---|---|---|---|
| 1 — 基线 | Task 1.1 | 仅验证（read-only） | 无 |
| 2 — package.json 决策 | Task 2.1 + 2.2 | `package.json` + 1 bats | 低 |
> 决策锁定:Decision 3 翻 A(详见 design.md),Task 2.3(B 路径)已废弃,只剩 A 路径。`fix-install-lib-distribution`(commit 171f565)是本决策的前置。 |
| 3 — narrative docs | Task 3.1-3.4 | `AGENTS.md` + `INSTALL.md` + `README.md` + `USAGE.md` | 低 |
| 4 — ADR index + specs | Task 4.1-4.3 | `docs/adr/README.md` + `openspec/specs/general/spec.md` | 低 |
| 5 — 验证 | Task 5.1-5.2 | pytest + bats + openspec + 干扰反漂移 | 低 |
| 6 — 验收 | Task 6.1-6.2 | tick acceptance + 统一最终状态 | 低 |

TDD 顺序（每条任务都遵循）：

```text
写失败 @test → bats/pytest 看红 → 改文档/代码 → 再跑看绿 → git commit
```

## 关键文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `openspec/changes/sync-workflow-contracts/proposal.md` | MODIFY | 加 Decision Log（DL-1/B、DL-2/C、DL-3/in-place） |
| `package.json` | MODIFY | 加 `_comment` 字段声明 src-only skills；**不**改 `skills[]` |
| `AGENTS.md` | MODIFY | skill 计数 12 → 13；ADR 计数 → 19 / 20；openspec specs 计数 → 25 |
| `skills/INSTALL.md` | MODIFY | 末尾追加 `## npm test vs pytest` 块 |
| `README.md` | MODIFY | 目录结构补全（13 .md + `loop_engine.py` + `_lib/`） |
| `USAGE.md` | MODIFY | 顶部 changelog note + state-file 表（保留 `roadmap-state.json` 点/无点并存标识） |
| `docs/adr/README.md` | MODIFY | status table 扩展到 0001-0019 + ADR-0013 dup flag |
| `openspec/specs/general/spec.md` | MODIFY | `general-docs-match-code` Scenarios 重写到 v2.0.1 |
| `tests/integration/test_doc_contracts.bats` | CREATE | 5+ D-series bats assertions |
| `tests/integration/test_adr_index.bats` | CREATE | ADR index coherence bats assertions |
| `tests/unit/test_doc_contracts.py` | CREATE | 跨 surface Python cross-spec 断言 |
| **不修改** | | `skills/_lib/*.py`、`skills/guide-*.md` prose、`.github/workflows/test.yml`、所有 archived changes |

## 实施步骤（详细命令群，Ready-to-Run）

### Phase 1 — 基线验证

```bash
cd /workspace/project/rdd-workflow

# Step 1.1.1: 捕获磁盘真相
echo "skills on disk:" && ls skills/*.md | wc -l          # expected 13
echo "package.json skills count:" && python3 -c "import json; print(len(json.load(open('package.json'))['skills']))"  # expected 11
echo "ADR files:" && find docs/adr -maxdepth 1 -name 'ADR-*.md' | wc -l  # expected 21
echo "ADR unique numbers:" && find docs/adr -maxdepth 1 -name 'ADR-*.md' | sed -E 's|.*ADR-([0-9]+).*|\1|' | sort -u | wc -l  # expected 19
echo "openspec specs:" && ls openspec/specs/ | wc -l     # expected 25

# Step 1.1.2: 捕获 narrative drift
grep -cE "Phase 1\.5" USAGE.md                             # expected ≥ 1
grep -cE 'guide-spec' openspec/specs/general/spec.md        # expected 0
grep -E "12 个 \.md|13 个 \.md" AGENTS.md                    # expected '13 个 .md' (stale → '12')
grep -nE "ship-side|5 阶段" openspec/specs/general/spec.md  # expected contains 'ship-side'

# Step 1.1.3: pre-existing tests baseline (Capture current state — DO NOT modify)
python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
bats tests/smoke.bats 2>&1 | tail -5
```

### Phase 2 — decision + package.json

```bash
cd /workspace/project/rdd-workflow

# Step 2.1: 在 proposal.md 加 Decision Log（插入到 YAML frontmatter 后，`## Why` 前）
# Manual edit with Edit tool: insert text below YAML block
cat <<'EOF' | head -1
## Decision Log (added during plan-done)
- **DL-1 (skill publish surface)**: Option B — `package.json::skills[]` 保持 11；在顶部加 `_comment` 字段声明 `feature` 和 `rddf-session` 为 src-only
- **DL-2 (ADR-0013)**: Option C — 保留两个文件并在 `docs/adr/README.md` 顶部加 ⚠️ flag
- **DL-3 (worktree)**: in-place — 本 change 无 production skill 代码变更，无需 worktree
EOF

# Step 2.2.1: 写第一个 failing bats（断言 package.json::skills[] 已发布全部 13 个 skill）
mkdir -p tests/integration
cat > tests/integration/test_doc_contracts.bats <<'BATS_EOF'
#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "doc_truth_sync: package.json::skills[] publishes all 13 disk skills (Decision 3 = A)" {
  run python3 - <<'PY'
import json, sys
disk = len(__import__("pathlib").Path("skills").glob("*.md"))
data = json.load(open("package.json"))
skills = data.get("skills", [])
assert len(skills) == disk, (
    f"package.json declares {len(skills)} skills, disk has {disk}; "
    f"Decision 3 翻 A 后长度必须相等（无 src-only 例外）"
)
assert "feature" in skills, f"feature not in skills[]: {skills}"
assert "rddf-session" in skills, f"rddf-session not in skills[]: {skills}"
assert "_comment" not in data, (
    "Decision 3 = A 后 package.json 不应再有 `_comment` 字段声明 src-only; got: "
    + repr(data.get("_comment"))
)
PY
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
BATS_EOF
chmod +x tests/integration/test_doc_contracts.bats

# Step 2.2.2: 看红
bats tests/integration/test_doc_contracts.bats  # expected: 1 failed（package.json 还只有 11 项）

# Step 2.2.3: 改 package.json 把 feature + rddf-session 加入 skills[]（无 _comment）
python3 - <<'PY'
import json
from pathlib import Path
p = Path("package.json")
data = json.loads(p.read_text())
for name in ("feature", "rddf-session"):
    if name not in data["skills"]:
        data["skills"].append(name)
# Decision 3 = A:删除任何遗留的 _comment 字段
data.pop("_comment", None)
p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
p.write_text(p.read_text() + "\n")
PY

# Step 2.2.4: 看绿
bats tests/integration/test_doc_contracts.bats  # expected: 1 passed

# Step 2.2.5: 提交
git add package.json tests/integration/test_doc_contracts.bats openspec/changes/sync-workflow-contracts/proposal.md
git commit -m "feat(contracts): Decision 3 翻 A — publish feature + rddf-session in package.json"
```

> 前置依赖:本 task 必须在 `fix-install-lib-distribution` change(commit `171f565`)归档**后**执行,否则 npm 用户拿到 broken skill。

### Phase 3 — narrative docs 同步

```bash
cd /workspace/project/rdd-workflow

# === Task 3.1: AGENTS.md ===
cat >> tests/integration/test_doc_contracts.bats <<'BATS_EOF'

@test "doc_truth_sync: AGENTS.md skill count matches ls skills/*.md" {
  disk=$(ls skills/*.md | wc -l)
  if ! grep -qE "13 个 \.md" AGENTS.md; then
    echo "AGENTS.md missing '13 个 .md' (disk has $disk)"
    return 1
  fi
}

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
BATS_EOF

# 看红 → 改 AGENTS.md（替换 `12 个 .md` 为 `13 个 .md` + ADR 范围更新）
# 然后看绿
bats tests/integration/test_doc_contracts.bats

git add AGENTS.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync AGENTS.md skill + ADR counts"

# === Task 3.2: INSTALL.md ===
cat >> tests/integration/test_doc_contracts.bats <<'BATS_EOF'

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
BATS_EOF
bats tests/integration/test_doc_contracts.bats  # 看红

# 改 INSTALL.md（替换 `全部 12 个子技能` 为 `全部 13 个子技能` + 追加 `npm test vs pytest` block）
bats tests/integration/test_doc_contracts.bats  # 看绿
git add skills/INSTALL.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync INSTALL.md description + add npm-vs-pytest block"

# === Task 3.3: README.md ===
cat >> tests/integration/test_doc_contracts.bats <<'BATS_EOF'

@test "doc_truth_sync: README.md directory tree lists guide-arch / guide-plan / loop_engine / _lib" {
  for name in guide-arch.md guide-plan.md loop_engine.py "_lib"; do
    if ! grep -qE "$name" README.md; then
      echo "README.md missing '$name' in tree"
      return 1
    fi
  done
}
BATS_EOF
bats tests/integration/test_doc_contracts.bats  # 看红
# 改 README.md 目录树（13 .md 文件 + loop_engine.py + _lib/）
bats tests/integration/test_doc_contracts.bats  # 看绿
git add README.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync README.md directory tree to disk"

# === Task 3.4: USAGE.md ===
cat >> tests/integration/test_doc_contracts.bats <<'BATS_EOF'

@test "doc_truth_sync: USAGE.md changelog banner names v2.0.1 + sync-workflow-contracts" {
  if ! grep -qE "v2\.0\.1" USAGE.md; then echo "missing v2.0.1"; return 1; fi
  if ! grep -qE "sync-workflow-contracts" USAGE.md; then echo "missing sync-workflow-contracts"; return 1; fi
}

@test "doc_truth_sync: USAGE.md state-file table uses dotted prefixes for handoff-style + canonical/legacy note" {
  for tail in ".arch-handoff.json" ".plan-handoff.json" ".deps-candidates.json" ".deps-output.md"; do
    full=".rddf/state/${tail}"
    if ! grep -qF "$full" USAGE.md; then echo "missing $full"; return 1; fi
  done
  for tail in "deps-analysis.json" "iteration.json" "sessions.json" "index.md"; do
    full=".rddf/state/${tail}"
    if ! grep -qF "$full" USAGE.md; then echo "missing $full"; return 1; fi
  done
}
BATS_EOF
bats tests/integration/test_doc_contracts.bats  # 看红（如果 USAGE.md 已修好则为绿，可跳过 edit）
git add USAGE.md tests/integration/test_doc_contracts.bats
git commit -m "feat(contracts): sync USAGE.md state-file table to production paths"
```

### Phase 4 — ADR index + spec deltas

```bash
cd /workspace/project/rdd-workflow

# === Task 4.1: ADR index ===
cat > tests/integration/test_adr_index.bats <<'BATS_EOF'
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
  [ -z "$bad" ]
}

@test "adr_index: duplicated ADR-0013 is explicitly flagged in README.md" {
  grep -qE "ADR-0013.*重复|重复.*ADR-0013|extract-scan-state.*incremental-skeleton-planning" docs/adr/README.md
}

@test "adr_index: docs/adr/README.md status table is consistent with disk" {
  missing=""
  for adr in $(find docs/adr -maxdepth 1 -name 'ADR-*.md' | sort); do
    base=$(basename "$adr")
    if ! grep -qF "$base" docs/adr/README.md; then
      missing="${missing}${base} "
    fi
  done
  [ -z "$missing" ]
}
BATS_EOF
chmod +x tests/integration/test_adr_index.bats

bats tests/integration/test_adr_index.bats  # 看红
# 改 docs/adr/README.md（在 status table 上方插入 ADR-0013 dup flag；扩展 status table 覆盖 0001-0019）
bats tests/integration/test_adr_index.bats  # 看绿
git add docs/adr/README.md tests/integration/test_adr_index.bats
git commit -m "feat(contracts): extend ADR index status table to 0001-0019 + flag ADR-0013 dup"

# === Task 4.2: general/spec.md ===
mkdir -p tests/unit
cat > tests/unit/test_doc_contracts.py <<'PY_EOF'
"""Cross-doc / cross-spec contract tests for sync-workflow-contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


def test_general_spec_phase_count_matches_usaged() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "7 numbered subphases" in spec or "7 编号子阶段" in spec
    assert "5 阶段 + 1 退出" not in spec, (
        "general/spec.md still references the v1.x '5 阶段 + 1 退出' ship-side"
    )


def test_general_spec_no_guide_spec_reference() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "guide-spec" not in spec, (
        "general/spec.md still references 'guide-spec' which was removed in v2.0"
    )


def test_general_spec_consumers_drop_guide_spec_add_arch_plan() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "guide-arch" in spec
    assert "guide-plan" in spec


def test_install_description_skill_count_matches_disk() -> None:
    disk = len(list((REPO_ROOT / "skills").glob("*.md")))
    inst = _read("skills/INSTALL.md")
    m = re.search(r"全部\s*(\d+)\s*个子技能", inst)
    assert m is not None, "INSTALL.md description missing '全部 N 个子技能'"
    assert int(m.group(1)) == disk, (
        f"INSTALL.md claims {m.group(1)} skills, disk has {disk}"
    )


def test_package_json_skills_count_within_delta() -> None:
    pkg = json.loads(_read("package.json"))
    disk = len(list((REPO_ROOT / "skills").glob("*.md")))
    assert len(pkg["skills"]) <= disk + 2, (
        f"package.json declares {len(pkg['skills'])} skills, disk has {disk}"
    )


def test_state_file_paths_in_general_spec_use_canonical_paths() -> None:
    spec = _read("openspec/specs/general/spec.md")
    for tail in (".arch-handoff.json", ".plan-handoff.json",
                 ".deps-candidates.json", ".deps-output.md"):
        assert f".rddf/state/{tail}" in spec, f"missing '.rddf/state/{tail}'"
    assert ".rddf/state/deps-analysis.json" in spec
    assert ".sisyphus/plans" not in spec


def test_npm_test_trap_caveat_locked() -> None:
    pkg = json.loads(_read("package.json"))
    assert pkg["scripts"]["test"] == "bats tests/", (
        f"package.json::scripts.test is {pkg['scripts']['test']!r}"
    )


def test_adr_index_references_real_files() -> None:
    adr_dir = REPO_ROOT / "docs/adr"
    real = {p.name for p in adr_dir.glob("ADR-*.md")}
    readme = _read("docs/adr/README.md")
    referenced = set(re.findall(r"ADR-\d{4}-[\w-]+\.md", readme))
    missing = referenced - real
    assert not missing, f"docs/adr/README.md references missing: {sorted(missing)}"
PY_EOF

python3 -m pytest tests/unit/test_doc_contracts.py -v  # 看红
# 改 openspec/specs/general/spec.md（更新 general-docs-match-code Scenarios 到 v2.0.1；移除 guide-spec consumer）
python3 -m pytest tests/unit/test_doc_contracts.py -v  # 看绿
git add openspec/specs/general/spec.md tests/unit/test_doc_contracts.py
git commit -m "feat(contracts): update general/spec.md to v2.0.1 + lock with python tests"

# === Task 4.3: 不要手动改 base doc-truth-sync spec.md（openspec archive 时自动 merge） ===
! git status --short -- openspec/specs/doc-truth-sync/spec.md
# Expected: 退出码 0（base spec 未动）
```

### Phase 5 — 验证

```bash
cd /workspace/project/rdd-workflow

# Step 5.1.1: pytest unit
python3 -m pytest tests/unit/ -q --tb=short

# Step 5.1.2: pytest integration
python3 -m pytest tests/integration/ -q --tb=short

# Step 5.1.3: bats all
bats tests/

# Step 5.1.4: openspec validate
openspec validate sync-workflow-contracts --strict
openspec validate

# Step 5.1.5: CI 质量门控（恒真断言）
! grep -rn 'assert.*or True\|assert True' tests/

# Step 5.2.1: 干扰反漂移验证（Phase 计数被篡改 → 测试应报错，恢复后转绿）
cp USAGE.md /tmp/USAGE.md.bak
sed -i 's/Phase 1\.5/Phase 1\.6/' USAGE.md
bats tests/integration/test_doc_contracts.bats 2>&1 | tail -5  # expected: 失败
mv /tmp/USAGE.md.bak USAGE.md
bats tests/integration/test_doc_contracts.bats 2>&1 | tail -3  # expected: pass

# Step 5.2.2: ADR index 篡改
cp docs/adr/README.md /tmp/README.md.bak
sed -i 's/ADR-0017/ADR-0017-DUMMY/' docs/adr/README.md
bats tests/integration/test_adr_index.bats 2>&1 | tail -5  # expected: 失败
mv /tmp/README.md.bak docs/adr/README.md
bats tests/integration/test_adr_index.bats 2>&1 | tail -3  # expected: pass
```

### Phase 6 — 验收 + handoff

```bash
cd /workspace/project/rdd-workflow

# Step 6.1: tick 所有 acceptance 项（把 - [ ] 替换为 - [x]）
# 用 Edit tool 编辑 openspec/changes/sync-workflow-contracts/proposal.md

# Step 6.2: 最终状态
echo "=== openspec validate ===" && openspec validate sync-workflow-contracts --strict
echo "=== pytest unit ===" && python3 -m pytest tests/unit/ -q --tb=short
echo "=== pytest integration ===" && python3 -m pytest tests/integration/ -q --tb=short
echo "=== bats all ===" && bats tests/
echo "=== CI gate ===" && ! grep -rn 'assert.*or True\|assert True' tests/ && echo "PASS"
echo "=== git status ===" && git status --short
```

## 验收标准

1. `package.json::scripts.test` 仍等于 `bats tests/`（npm test 陷阱仍锁定）
2. `package.json::skills[]` 仍 11 项；新 `_comment` 字段声明 `feature` / `rddf-session` 为 src-only
3. AGENTS.md 反映：13 个 skill、ADR 19 唯一编号 / 20 实体文件、openspec 25 specs
4. INSTALL.md description 保留 13 + 末尾有 `npm test vs pytest` block
5. README.md 目录结构列出 13 .md + loop_engine.py + _lib/
6. USAGE.md 顶部 changelog、state-file 表对齐生产路径
7. docs/adr/README.md 顶部 ⚠️ flag 标注 ADR-0013 dup；status table 覆盖 0001-0019
8. openspec/specs/general/spec.md 的 `general-docs-match-code` Scenarios 重写到 v2.0.1（移除 `guide-spec`、phase 7 子阶段、dotted paths）
9. 3 个 anti-drift 测试全部 @test 绿：bats / bats / pytest
10. 既有 pytest + bats zero regression
11. `openspec validate sync-workflow-contracts --strict` PASS
12. CI 恒真断言 grep `! grep -rn 'assert.*or True\|assert True' tests/` 退出 0

## Out-of-scope reminders

- ❌ 不修改 `skills/_lib/*.py`
- ❌ 不修改 `skills/guide-*.md` prose
- ❌ 不修改 `.github/workflows/test.yml`
- ❌ 不处理 ADR-0013 dup 重编号（留给 `init-deep` 决策 / 后续 `fix-adr-index-and-numbering` change）
- ❌ 不把 `feature` / `rddf-session` 加入 `package.json::skills[]`（决策 B：保留 src-only）
- ❌ 不重命名 `roadmap-state.json`（点/无点混用为后续 `fix-roadmap-state-canonical` change 范围）

## Anti-patterns to avoid

- ❌ `assert True` / `assert ... or True`（CI grep 拦截）
- ❌ 先改后测（破坏 TDD 红 → 绿循环）
- ❌ 改 `skills/_lib/*.py`（违反 Decision 1 的 L1 不动原则）
- ❌ 把 change 内部 artifact（`design.md`、`tasks.md`、`.openspec.yaml`、change 的 `specs/general/spec.md`）一并 commit 出去——它们已在 `openspec/changes/sync-workflow-contracts/` PROPOSED，与 contract plan 分开管理

---

**END OF CONTRACT PLAN**

After all phases complete and final commit lands:

```bash
cd /workspace/project/rdd-workflow
openspec validate sync-workflow-contracts --strict
git log --oneline -20
git status --short
```

Then handoff via `skill_use("guide-plan")` (Phase 4 plan-done) — at which point `openspec archive sync-workflow-contracts --yes` can be run after `guide-ship` Phase 3 in the next session.
