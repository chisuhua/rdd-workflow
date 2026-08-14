# add-phase-role-model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add formal role metadata to 4 phase SKILL.md frontmatter files, defining title, perspective, ownership boundaries, and human involvement level per phase.

**Architecture:** Documentation-only change. Add `role:` field to YAML frontmatter of 4 phase skills, create JSON schema for validation, add 1 comprehensive bats test, create ADR-0028, and update AGENTS.md reference. No AI behavior enforcement hooks (per proposal MUST NOT).

**Tech Stack:** 
- JSON Schema (draft 2020-12)
- YAML frontmatter (existing pattern from ADR-0007)
- bats (shell testing framework)
- ADR template (ADR-0000-template.md)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/schemas/skill_role_schema.json` | JSON Schema defining `role:` field structure (5 sub-fields) |
| `skills/guide-arch/SKILL.md` | Add `role:` frontmatter + reference in "职责边界" section |
| `skills/guide-design/SKILL.md` | Add `role:` frontmatter + reference in "职责边界" section |
| `skills/guide-plan/SKILL.md` | Add `role:` frontmatter + reference in "职责边界" section |
| `skills/guide-ship/SKILL.md` | Add `role:` frontmatter + reference in "职责边界" section |
| `docs/adr/ADR-0028-role-model-per-phase.md` | Architecture decision record for role formalization |
| `rdd-workflow/AGENTS.md` | Add reference to ADR-0028 in "关键约定" section |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_skill_role_all.bats` | Verify all 4 SKILL.md have complete role fields + schema compliance |

---

### Task 1: Create JSON Schema for role field

**Files:**
- Create: `_lib/schemas/skill_role_schema.json`

- [ ] **Step 1: Write the failing test for schema file existence**

```bash
# tests/integration/test_skill_role_all.bats
#!/usr/bin/env bats
load ../test_helper

setup() {
  SCHEMA_FILE="$REPO_ROOT/_lib/schemas/skill_role_schema.json"
}

@test "skill_role_schema.json exists in _lib/schemas/" {
  [ -f "$SCHEMA_FILE" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_role_all.bats -t "schema.json exists"`
Expected: FAIL with "file not found"

- [ ] **Step 3: Write minimal schema implementation**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.dev/schemas/skill_role_schema.json",
  "title": "SkillRoleMetadata",
  "description": "Role metadata for phase skills: title, perspective, ownership boundaries, human involvement level. See ADR-0028.",
  "type": "object",
  "required": ["title", "perspective", "boundaries"],
  "additionalProperties": false,
  "properties": {
    "title": {
      "type": "string",
      "minLength": 1,
      "description": "Human-readable role name (bilingual: e.g., 'Architect (架构治理者)')."
    },
    "perspective": {
      "type": "string",
      "minLength": 1,
      "description": "Thinking perspective for this phase (1-2 sentences)."
    },
    "boundaries": {
      "type": "object",
      "required": ["owns", "not_owns", "human_involvement"],
      "additionalProperties": false,
      "properties": {
        "owns": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 1,
          "description": "File paths this phase owns (e.g., 'docs/adr/ADR-*.md')."
        },
        "not_owns": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 1,
          "description": "File paths this phase explicitly does NOT own."
        },
        "human_involvement": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Human involvement level per ADR-0003 gradient."
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "schema.json exists"`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。
如需在 execute 阶段逐任务 commit（不推荐），可设置 `COMMIT_IN_EXECUTE=yes`。

---

### Task 2: Add role field to guide-arch SKILL.md

**Files:**
- Modify: `skills/guide-arch/SKILL.md:1-30` (frontmatter)
- Modify: `skills/guide-arch/SKILL.md` ("职责边界" section, ~line 100)

- [ ] **Step 1: Write test for guide-arch role field presence**

```bash
# Add to tests/integration/test_skill_role_all.bats
@test "guide-arch has role.title field" {
  python3 <<'PYEOF'
import yaml, sys
with open("$REPO_ROOT/skills/guide-arch/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  assert "role" in data, "Missing role field"
  assert "title" in data["role"], "Missing role.title"
  print("PASS")
PYEOF
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-arch has role.title"`
Expected: FAIL with "Missing role field"

- [ ] **Step 3: Add role field to frontmatter**

Insert after line 8 (`user-invocable: true`):

```yaml
role:
  title: "Architect (架构治理者)"
  perspective: "Think in terms of long-term architectural coherence, ADR-driven decision-making, and roadmap alignment. Avoid premature implementation details."
  boundaries:
    owns:
      - "docs/adr/ADR-*.md"
      - "roadmap.md"
      - "docs/architecture/*-gap-analysis.md"
      - ".rddf/state/.arch-handoff.json"
    not_owns:
      - "openspec/changes/<name>/{proposal,design,tasks}.md"
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
    human_involvement: "high"
```

- [ ] **Step 4: Update "职责边界" section to reference frontmatter**

Replace the existing "职责边界" prose (around line 100) with:

```markdown
**职责边界**：
- **角色定义**：见 frontmatter `role:` 字段（ADR-0028）
- **拥有**：`role.boundaries.owns` 字段列出的文件路径
- **不拥有**：`role.boundaries.not_owns` 字段列出的文件路径
- **人工介入程度**：`role.boundaries.human_involvement` = `high`
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-arch has role.title"`
Expected: PASS

---

### Task 3: Add role field to guide-design SKILL.md

**Files:**
- Modify: `skills/guide-design/SKILL.md:1-30` (frontmatter)
- Modify: `skills/guide-design/SKILL.md` ("职责边界" section)

- [ ] **Step 1: Write test for guide-design role field**

```bash
@test "guide-design has complete role fields (5 sub-fields)" {
  python3 <<'PYEOF'
import yaml, sys
with open("$REPO_ROOT/skills/guide-design/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  role = data.get("role", {})
  assert "title" in role, "Missing role.title"
  assert "perspective" in role, "Missing role.perspective"
  assert "boundaries" in role, "Missing role.boundaries"
  assert "owns" in role["boundaries"], "Missing boundaries.owns"
  assert "not_owns" in role["boundaries"], "Missing boundaries.not_owns"
  assert "human_involvement" in role["boundaries"], "Missing boundaries.human_involvement"
  print("PASS: all 5 sub-fields present")
PYEOF
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-design has complete"`
Expected: FAIL

- [ ] **Step 3: Add role field to frontmatter**

```yaml
role:
  title: "Proposal Manager (提案经理)"
  perspective: "Manage proposal lifecycle: creation, content review, approval/rejection/deferral. Ensure proposals align with roadmap themes and ADR decisions."
  boundaries:
    owns:
      - "proposal-suggestions.md"
      - "proposal-approved.md"
      - ".rddf/improvements/*.md"
      - ".rddf/state/.design-handoff.json"
    not_owns:
      - "docs/adr/ADR-*.md"
      - "openspec/changes/<name>/{proposal,design,tasks}.md"
      - ".rddf/plans/<name>.md"
    human_involvement: "medium"
```

- [ ] **Step 4: Update "职责边界" section**

Replace existing section with reference to frontmatter (same pattern as Task 2 Step 4).

- [ ] **Step 5: Run test to verify it passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-design has complete"`
Expected: PASS

---

### Task 4: Add role field to guide-plan SKILL.md

**Files:**
- Modify: `skills/guide-plan/SKILL.md:1-30` (frontmatter)
- Modify: `skills/guide-plan/SKILL.md` ("职责边界" section)

- [ ] **Step 1: Write test for guide-plan role field**

```bash
@test "guide-plan has complete role fields (5 sub-fields)" {
  python3 <<'PYEOF'
import yaml, sys
with open("$REPO_ROOT/skills/guide-plan/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  role = data.get("role", {})
  required = ["title", "perspective"]
  boundaries = ["owns", "not_owns", "human_involvement"]
  for k in required:
    assert k in role, f"Missing role.{k}"
  for k in boundaries:
    assert k in role.get("boundaries", {}), f"Missing boundaries.{k}"
  print("PASS")
PYEOF
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-plan has complete"`
Expected: FAIL

- [ ] **Step 3: Add role field to frontmatter**

```yaml
role:
  title: "Tech Lead (技术主管)"
  perspective: "Bridge architecture and implementation: consume proposals, generate OpenSpec changes, analyze dependencies, emit plan-done handoff."
  boundaries:
    owns:
      - "openspec/changes/<name>/{proposal,design,specs,tasks}.md"
      - "openspec/changes/<name>/roadmap-meta.yaml"
      - ".rddf/state/.plan-handoff.json"
      - ".rddf/state/deps-analysis.json"
      - ".rddf/state/iteration.json"
    not_owns:
      - "docs/adr/ADR-*.md"
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
    human_involvement: "medium"
```

- [ ] **Step 4: Update "职责边界" section**

Replace with frontmatter reference (same pattern).

- [ ] **Step 5: Run test to verify it passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-plan has complete"`
Expected: PASS

---

### Task 5: Add role field to guide-ship SKILL.md

**Files:**
- Modify: `skills/guide-ship/SKILL.md:1-30` (frontmatter)
- Modify: `skills/guide-ship/SKILL.md` ("职责边界" section)

- [ ] **Step 1: Write test for guide-ship role field**

```bash
@test "guide-ship has complete role fields (5 sub-fields)" {
  python3 <<'PYEOF'
import yaml, sys
with open("$REPO_ROOT/skills/guide-ship/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  role = data.get("role", {})
  assert len(role.get("boundaries", {}).get("owns", [])) >= 1, "owns must have at least 1 path"
  assert len(role.get("boundaries", {}).get("not_owns", [])) >= 1, "not_owns must have at least 1 path"
  assert role.get("boundaries", {}).get("human_involvement") in ["high", "medium", "low"], "Invalid human_involvement"
  print("PASS")
PYEOF
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-ship has complete"`
Expected: FAIL

- [ ] **Step 3: Add role field to frontmatter**

```yaml
role:
  title: "DevOps (交付工程师)"
  perspective: "Execution focus: create worktrees, generate implementation plans, monitor task progress, archive completed changes. Minimal human involvement."
  boundaries:
    owns:
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
      - "openspec/changes/<name>/tasks.md"
      - "git worktree for openspec/<name>"
    not_owns:
      - "docs/adr/ADR-*.md"
      - "openspec/changes/<name>/{proposal,design,specs}.md"
      - "proposal-suggestions.md"
    human_involvement: "low"
```

- [ ] **Step 4: Update "职责边界" section**

Replace with frontmatter reference (same pattern).

- [ ] **Step 5: Run test to verify it passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "guide-ship has complete"`
Expected: PASS

---

### Task 6: Add comprehensive bats test validating all 4 skills

**Files:**
- Create: `tests/integration/test_skill_role_all.bats`

- [ ] **Step 1: Write test skeleton**

```bash
#!/usr/bin/env bats
# tests/integration/test_skill_role_all.bats
#
# Verifies all 4 phase SKILL.md files have complete role fields.
# Per ADR-0028: role.title, role.perspective, role.boundaries.owns,
# role.boundaries.not_owns, role.boundaries.human_involvement.

load ../test_helper

setup() {
  SCHEMA_FILE="$REPO_ROOT/_lib/schemas/skill_role_schema.json"
  SKILLS=(guide-arch guide-design guide-plan guide-ship)
}

@test "all 4 phase skills exist" {
  for skill in "${SKILLS[@]}"; do
    [ -f "$REPO_ROOT/skills/$skill/SKILL.md" ]
  done
}
```

- [ ] **Step 2: Run test to verify base passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "all 4 phase skills exist"`
Expected: PASS

- [ ] **Step 3: Add test for schema validation**

```bash
@test "all 4 skills have role field with 5 sub-fields" {
  for skill in "${SKILLS[@]}"; do
    python3 <<PYEOF
import yaml, sys
skill_name = "$skill"
with open("$REPO_ROOT/skills/$skill/SKILL.md") as f:
  content = f.read()
  parts = content.split("---\\n")
  if len(parts) < 3:
    print(f"ERROR: {skill_name} missing frontmatter", file=sys.stderr)
    sys.exit(1)
  frontmatter = parts[1]
  data = yaml.safe_load(frontmatter)
  role = data.get("role")
  if not role:
    print(f"ERROR: {skill_name} missing role field", file=sys.stderr)
    sys.exit(1)
  required_top = ["title", "perspective", "boundaries"]
  for k in required_top:
    if k not in role:
      print(f"ERROR: {skill_name} missing role.{k}", file=sys.stderr)
      sys.exit(1)
  boundaries = role["boundaries"]
  required_bounds = ["owns", "not_owns", "human_involvement"]
  for k in required_bounds:
    if k not in boundaries:
      print(f"ERROR: {skill_name} missing boundaries.{k}", file=sys.stderr)
      sys.exit(1)
  if boundaries["human_involvement"] not in ["high", "medium", "low"]:
    print(f"ERROR: {skill_name} invalid human_involvement", file=sys.stderr)
    sys.exit(1)
print("PASS: $skill has all 5 sub-fields")
PYEOF
  done
}
```

- [ ] **Step 4: Run test to verify it passes (after Tasks 2-5)**

Run: `bats tests/integration/test_skill_role_all.bats`
Expected: All tests PASS

- [ ] **Step 5: Defer commit**

按仓库约定，所有变更在 archive 阶段统一提交。

---

### Task 7: Create ADR-0028

**Files:**
- Create: `docs/adr/ADR-0028-role-model-per-phase.md`

- [ ] **Step 1: Write test for ADR file existence**

```bash
@test "ADR-0028 file exists" {
  [ -f "$REPO_ROOT/docs/adr/ADR-0028-role-model-per-phase.md" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_role_all.bats -t "ADR-0028 file exists"`
Expected: FAIL

- [ ] **Step 3: Write ADR-0028 following template structure**

```markdown
# ADR-0028: Role Model Per Phase

> **状态**: 已采纳
> **日期**: 2026-08-14
> **决策者**: sisyphus

## 问题

rdd-workflow v2.1 的 4 个阶段技能 (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) 的"职责边界"段落是叙述性文字，缺乏结构化的角色元数据。这导致：
1. 新开发者无法在 frontmatter 快速理解角色边界
2. AI 代理可能意外跨阶段边界（如 arch 阶段写 openspec/changes/）
3. 角色一致性依赖提示词隐性引导而非显式约束

## 决策

在 4 个阶段 SKILL.md 的 YAML frontmatter 中添加 `role:` 顶层字段，包含 5 个子字段：

```yaml
role:
  title: "Architect (架构治理者)"  # 双语角色名
  perspective: "..."  # 思考视角（1-2 句）
  boundaries:
    owns: [...]  # 文件路径清单
    not_owns: [...]  # 明确禁止的文件路径
    human_involvement: "high"  # 高/中/低（ADR-0003 梯度）
```

新建 JSON Schema (`_lib/schemas/skill_role_schema.json`) 定义字段类型。

SKILL.md 正文的"职责边界"段落改为引用 frontmatter 字段（单一事实来源）。

## 后果

**正面**：
- 新开发者在 frontmatter 即可了解角色边界
- git blame frontmatter 可追溯角色定义历史
- 角色一致性有显式文档基础（虽未强制 AI 行为）

**负面**：
- 新字段增加 frontmatter 解析负担（向后兼容：缺字段时仍可加载）
- 文档化角色不自动强制 AI 行为（需独立提案）

**中立**：
- 不修改现有 ADR-0003 / ADR-0017 / ADR-0025
- 不引入子技能角色继承（propose/execute/status 等留后续）

## 参考

- ADR-0003: 三阶段架构（现为四阶段）
- ADR-0007: Skill frontmatter 规范
- ADR-0017: rddf-session
- ADR-0025: 设计阶段独立化
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "ADR-0028 file exists"`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 8: Update AGENTS.md with ADR-0028 reference

**Files:**
- Modify: `rdd-workflow/AGENTS.md` (关键约定 section, around line 50)

- [ ] **Step 1: Write test for AGENTS.md reference**

```bash
@test "AGENTS.md references ADR-0028" {
  grep -q "ADR-0028" "$REPO_ROOT/AGENTS.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_role_all.bats -t "AGENTS.md references ADR-0028"`
Expected: FAIL

- [ ] **Step 3: Add reference to AGENTS.md**

Insert after line 60 (in "关键约定 (容易踩坑)" section):

```markdown
### Skill 角色模型 (ADR-0028)

4 个阶段技能 (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) 的 frontmatter 包含 `role:` 字段，定义角色、视角、边界：
- `role.title`: 双语角色名（如 "Architect (架构治理者)"）
- `role.perspective`: 思考视角（1-2 句）
- `role.boundaries.owns`: 文件路径清单（此阶段拥有）
- `role.boundaries.not_owns`: 明确禁止的文件路径
- `role.boundaries.human_involvement`: 高/中/低（对应 ADR-0003 梯度）

详见 [ADR-0028](docs/adr/ADR-0028-role-model-per-phase.md)。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_skill_role_all.bats -t "AGENTS.md references ADR-0028"`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 9: Verify backward compatibility

**Files:**
- Test: Temporarily remove `role:` field from one SKILL.md

- [ ] **Step 1: Add backward compatibility test**

```bash
@test "SKILL.md without role field still loads" {
  # Create a temp SKILL.md without role field
  TEMP_DIR="$BATS_TMPDIR/backward_compat_test"
  mkdir -p "$TEMP_DIR/skills/guide-arch"
  
  # Copy guide-arch but strip role field
  python3 <<'PYEOF'
import sys
with open("$REPO_ROOT/skills/guide-arch/SKILL.md") as f:
  content = f.read()
parts = content.split("---\n")
frontmatter_lines = parts[1].split("\n")
# Remove lines starting with "role:" or indented (role sub-fields)
filtered = []
skip_role_block = False
for line in frontmatter_lines:
  if line.startswith("role:"):
    skip_role_block = True
    continue
  if skip_role_block and (line.startswith("  ") or line.startswith("\t")):
    continue
  skip_role_block = False
  filtered.append(line)
new_frontmatter = "\n".join(filtered)
with open("$TEMP_DIR/skills/guide-arch/SKILL.md", "w") as out:
  out.write("---\n" + new_frontmatter + "\n---\n" + parts[2])
PYEOF
  
  # Verify it still parses (no YAML error)
  python3 <<'PYEOF'
import yaml
with open("$TEMP_DIR/skills/guide-arch/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  assert data is not None, "Frontmatter parse failed"
  print("PASS: SKILL.md without role field parses successfully")
PYEOF
}
```

- [ ] **Step 2: Run test to verify backward compatibility**

Run: `bats tests/integration/test_skill_role_all.bats -t "SKILL.md without role field still loads"`
Expected: PASS

- [ ] **Step 3: Document the result**

No implementation needed — test proves backward compatibility.

- [ ] **Step 4: Verify original files unchanged**

Run: `git status skills/guide-arch/SKILL.md`
Expected: File still has `role:` field (temp file was in BATS_TMPDIR)

- [ ] **Step 5: Defer commit**

---

### Task 10: Run full test suite

**Files:**
- Test: Run `./test.sh --full --regression`

- [ ] **Step 1: Run smoke tests first**

Run: `./test.sh --quick`
Expected: All smoke + unit tests PASS

- [ ] **Step 2: Run full bats + pytest**

Run: `./test.sh --full`
Expected: All tests PASS (or only KNOWN_FAILURES.txt baseline failures)

- [ ] **Step 3: Check for new failures vs baseline**

Run: `./test.sh --full --regression`
Expected: No new failures (only pre-existing failures in KNOWN_FAILURES.txt)

- [ ] **Step 4: If new failures found, fix them**

If new failures appear:
1. Read the failure output
2. Identify the root cause
3. Fix the issue (most likely: YAML syntax error in frontmatter)
4. Re-run `./test.sh --full --regression`
5. Repeat until no new failures

- [ ] **Step 5: Document test results**

No commit — verification step only.

---

### Task 11: Final worktree commit (聚合 commit)

**Files:**
- All modified files from Tasks 1-10

- [ ] **Step 1: Verify all tasks completed**

Run: `grep -c "^- \[ \]" openspec/changes/add-phase-role-model/tasks.md`
Expected: 0 (all checkboxes should be `- [x]`)

- [ ] **Step 2: Review uncommitted changes**

Run: `git status --short`
Expected: 
```
M  _lib/schemas/skill_role_schema.json
M  skills/guide-arch/SKILL.md
M  skills/guide-design/SKILL.md
M  skills/guide-plan/SKILL.md
M  skills/guide-ship/SKILL.md
M  docs/adr/ADR-0028-role-model-per-phase.md
M  AGENTS.md
A  tests/integration/test_skill_role_all.bats
```

- [ ] **Step 3: Stage all changes**

Run: `git add -A`

- [ ] **Step 4: Create聚合 commit with conventional message**

Run: 
```bash
git commit -m "feat(role-model): add formal role metadata to 4 phase SKILL.md frontmatter

- Add role: field to guide-arch/guide-design/guide-plan/guide-ship SKILL.md
- Create _lib/schemas/skill_role_schema.json (5 sub-fields)
- Add tests/integration/test_skill_role_all.bats (comprehensive validation)
- Create docs/adr/ADR-0028-role-model-per-phase.md
- Update AGENTS.md with ADR-0028 reference
- Update each SKILL.md 职责边界 section to reference frontmatter

Per ADR-0028: Documentation-only change, no AI behavior enforcement.
Backward compatible: skills without role field still load."
```

- [ ] **Step 5: Verify commit created**

Run: `git log -1 --oneline`
Expected: Shows the new commit with subject starting with "feat(role-model):"

---

## Notes

**Existing Patterns Referenced:**
- Schema structure: `_lib/schemas/sessions_schema.json` (JSON Schema draft 2020-12)
- Frontmatter format: `skills/guide-arch/SKILL.md` lines 1-9
- Bats test pattern: `tests/integration/test_adr_directory.bats`
- ADR template: `docs/adr/ADR-0000-template.md`

**Key Constraints:**
- Schema path: `_lib/schemas/` (project root), NOT `skills/_lib/schemas/`
- Role field: optional (backward compatible)
- Human involvement: enum ["high", "medium", "low"] only
- Single PR: all 4 SKILL.md + schema + test + ADR in one commit

**Verification Checklist:**
- [ ] All 4 SKILL.md have `role:` field with 5 sub-fields
- [ ] Schema file exists at `_lib/schemas/skill_role_schema.json`
- [ ] Bats test passes for all 4 skills
- [ ] ADR-0028 created with correct numbering (follows ADR-0027)
- [ ] AGENTS.md references ADR-0028
- [ ] `./test.sh --full --regression` shows no new failures
- [ ] Backward compatibility test passes
- [ ] Worktree has聚合 commit ready for archive
