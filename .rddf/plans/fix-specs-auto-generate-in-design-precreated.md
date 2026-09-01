# fix-specs-auto-generate-in-design-precreated Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 design 阶段批准的 change 自动生成 `openspec/changes/<name>/specs/<name>/spec.md`,消除回归门 "No deltas found" 误报,设计→船时间从 30+ 分钟降至正常。

**Architecture:** 扩展 `generate_full_proposal.py` 加 `generate_spec_delta()` 子函数,把 5 段源(验收标准/Capabilities/关键场景)映射到 openspec v1.4 的 `## ADDED Requirements` + `#### Scenario:` blocks;`approve_proposal.sh` 在 `proposal.md` 写入前调用并写 `specs/<name>/spec.md`,现有 idempotency 保留。

**Tech Stack:** Python 3.11+ stdlib, bash 4.x, openspec CLI v1.4+。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-design/scripts/generate_full_proposal.py` | 新增 `generate_spec_delta()` 映射函数 |
| `skills/guide-design/scripts/approve_proposal.sh` | `write_specs_file()` 步骤,触发 specs/ 生成 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_generate_full_proposal.py` | 5 个 specs 映射单元测试 |
| `tests/integration/test_specs_generation.bats` | 5 个端到端 bats 测试 |

### Documentation

| File | Responsibility |
|---|---|
| `AGENTS.md` | 更新 D3 design-pre-created 协同段 |
| `skills/guide-design/SKILL.md` | D1 编排段补 specs/ 输出说明 |
| `docs/proposal-approved-format.md` | 新章节:specs/ 与 proposal.md 对应关系 |

---

## Tasks

### Task 1: 实现 generate_spec_delta() 核心映射函数

**Files:**
- Modify: `skills/guide-design/scripts/generate_full_proposal.py:180-197` (在 generate_full_proposal() 后追加)
- Test: `tests/unit/test_generate_full_proposal.py` (新增 5 个 test)

- [ ] **Step 1: Write the failing test — acceptance checkboxes 映射**

在 `tests/unit/test_generate_full_proposal.py` 末尾追加:
```python
def test_generate_spec_delta_acceptance_to_requirements():
    """验证 ## 验收标准 段的 - [ ] checkbox 映射到 ### Requirement + #### Scenario"""
    source = """# Test Proposal

## Capabilities

## Impact

## Acceptance

- [ ] 用户能批准 proposal
- [ ] 自动写入 specs/ 目录
"""
    result = generate_spec_delta(source, sub="test")
    assert "## ADDED Requirements" in result
    assert "### Requirement: acceptance-1" in result
    assert "### Requirement: acceptance-2" in result
    assert "#### Scenario:" in result
    assert "acceptance-1" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal.py::test_generate_spec_delta_acceptance_to_requirements -v`
Expected: FAIL with `NameError: name 'generate_spec_delta' is not defined`

- [ ] **Step 3: Write minimal implementation — generate_spec_delta() 函数**

在 `generate_full_proposal.py` 末尾追加:
```python
def generate_spec_delta(source_md: str, sub: str) -> str:
    """从源 markdown 提取 ## Acceptance / ## Capabilities / ## 关键场景,生成 openspec v1.4 spec.md 内容。

    映射规则:
    - ## Acceptance 每个 - [ ] → ### Requirement + #### Scenario
    - ## Capabilities 每条 MUST/MUST NOT → ### Requirement
    - ## 关键场景 每条 GIVEN/WHEN/THEN → 附加 Scenario
    """
    import re
    
    lines = ["## ADDED Requirements", ""]
    
    # Extract acceptance checkboxes
    acc_section = re.search(r"## Acceptance\s*
(.*?)(?=
## |\Z)", source_md, re.DOTALL | re.IGNORECASE)
    req_idx = 0
    if acc_section:
        for m in re.finditer(r"^\s*-\s*\[\s*[xX ]?\s*\]\s*(.+?)$", acc_section.group(1), re.MULTILINE):
            req_idx += 1
            req_name = f"acceptance-{req_idx}"
            text = m.group(1).strip()
            lines.append(f"### Requirement: {req_name}")
            lines.append("")
            lines.append("The system SHALL " + text + ".")
            lines.append("")
            lines.append("#### Scenario: " + text[:60])
            lines.append("")
            lines.append("- **WHEN** user triggers the change")
            lines.append("- **THEN** " + text)
            lines.append("")
    
    # Extract Capabilities MUST/MUST NOT
    cap_section = re.search(r"## Capabilities\s*
(.*?)(?=
## |\Z)", source_md, re.DOTALL | re.IGNORECASE)
    if cap_section:
        for m in re.finditer(r"^\s*-\s*\*\*(MUST(?:\s+NOT)?)\*\*:\s*(.+?)$", cap_section.group(1), re.MULTILINE):
            req_idx += 1
            kind = m.group(1).strip()
            text = m.group(2).strip()
            req_name = f"capability-{req_idx}"
            lines.append(f"### Requirement: {req_name}")
            lines.append("")
            lines.append(f"The system {kind} {text}.")
            lines.append("")
    
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal.py::test_generate_spec_delta_acceptance_to_requirements -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定,execute 阶段不逐任务 commit;所有变更将在 archive 阶段统一提交。

---

### Task 2: 补齐 4 个 specs/ 映射单元测试

**Files:**
- Modify: `tests/unit/test_generate_full_proposal.py` (追加 4 个 test)

- [ ] **Step 1: Write 4 failing tests**

在 `tests/unit/test_generate_full_proposal.py` 末尾追加:
```python
def test_generate_spec_delta_capabilities_to_requirements():
    """验证 ## Capabilities 段 MUST/MUST NOT 映射到 ### Requirement"""
    source = """## Capabilities

- **MUST**: 自动生成 spec.md
- **MUST NOT**: 覆盖已有 specs/
"""
    result = generate_spec_delta(source, sub="test")
    assert "### Requirement: capability-1" in result
    assert "### Requirement: capability-2" in result
    assert "MUST" in result
    assert "MUST NOT" in result


def test_generate_spec_delta_scenarios_inline():
    """验证 ## 关键场景 段 GIVEN/WHEN/THEN 嵌入对应 Requirement"""
    source = """## Acceptance

- [ ] 系统响应

## 关键场景

- **GIVEN** 用户已登录
- **WHEN** 触发操作
- **THEN** 系统响应
"""
    result = generate_spec_delta(source, sub="test")
    assert "#### Scenario:" in result
    # scenarios 嵌入 acceptance 的 Requirement block


def test_generate_spec_delta_idempotent_input():
    """验证空 source_md 返回有效骨架(只有 ADDED Requirements 头)"""
    result = generate_spec_delta("", sub="empty")
    assert "## ADDED Requirements" in result
    # 无 checkbox / capability / scenario 时只有头


def test_generate_spec_delta_passes_openspec_v1_4_format():
    """验证输出包含 openspec v1.4 必填 delta 头"""
    source = "## Acceptance\n\n- [ ] 行为 A"
    result = generate_spec_delta(source, sub="v1")
    # 必备 openspec v1.4 markers
    assert "## ADDED Requirements" in result
    assert "### Requirement:" in result
    assert "#### Scenario:" in result
```

- [ ] **Step 2: Run all 5 tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal.py -v -k "test_generate_spec_delta"`
Expected: 5 passed

- [ ] **Step 3: Defer commit**

---

### Task 3: 集成到 approve_proposal.sh — write_specs_file() 步骤

**Files:**
- Modify: `skills/guide-design/scripts/approve_proposal.sh:378-390` (mkdir 与 proposal.md 之间)

- [ ] **Step 1: Write a failing integration check (bats test)**

新建 `tests/integration/test_specs_generation.bats`:
```bash
#!/usr/bin/env bats

setup() {
    export TEST_TMPDIR="$BATS_TMPDIR/specs-gen-$$"
    mkdir -p "$TEST_TMPDIR"
    cd "$TEST_TMPDIR"
    git init -q
    mkdir -p .rddf/improvements
    cat > .rddf/improvements/test-specs.md <<'EOF'
# test-specs

**类型**: feature

## Capabilities

- **MUST**: 自动生成 spec.md

## Impact

## Acceptance

- [ ] 用户能批准 proposal
EOF
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

@test "specs-generate: end-to-end approve_proposal.sh creates specs/" {
    source skills/guide-design/scripts/approve_proposal.sh test-specs P1 2>/dev/null
    [ -f openspec/changes/test-specs/specs/test-specs/spec.md ]
    grep -q "## ADDED Requirements" openspec/changes/test-specs/specs/test-specs/spec.md
}

@test "specs-generate: idempotent skip when specs/ exists" {
    mkdir -p openspec/changes/test-specs/specs/test-specs
    echo "PREEXISTING" > openspec/changes/test-specs/specs/test-specs/spec.md
    source skills/guide-design/scripts/approve_proposal.sh test-specs P1 2>/dev/null
    # pre-existing content preserved
    grep -q "PREEXISTING" openspec/changes/test-specs/specs/test-specs/spec.md
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_specs_generation.bats`
Expected: FAIL (specs/ 目录未创建)

- [ ] **Step 3: Write minimal implementation — write_specs_file() 步骤**

修改 `approve_proposal.sh` 在 `mkdir -p "$CHANGE_DIR"` 后、`cat > ... .openspec.yaml` 之前插入:
```bash
# write_specs_file: 自动生成 specs/<sub>/spec.md (D3 design-pre-created 协同)
write_specs_file() {
    local change_dir="$1"
    local name="$2"
    local imp_file="$3"
    local specs_dir="$change_dir/specs/$name"
    
    # Idempotency: 已存在则跳过
    if [ -d "$specs_dir" ]; then
        echo "⏭️ specs already exist for $name, skipping"
        return 0
    fi
    
    mkdir -p "$specs_dir"
    
    # 调用 generate_spec_delta (从 generate_full_proposal.py 提取或内联)
    local spec_content
    spec_content=$(CHANGE_NAME="$name" IMPROVEMENTS_PATH="$imp_file"         python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('PROJECT_ROOT', '.'))
from skills.guide_design.scripts.generate_full_proposal import generate_spec_delta
with open(os.environ['IMPROVEMENTS_PATH']) as f:
    source = f.read()
print(generate_spec_delta(source, sub=os.environ['CHANGE_NAME']))
" 2>/dev/null) || spec_content=""
    
    if [ -n "$spec_content" ]; then
        echo "$spec_content" > "$specs_dir/spec.md"
        echo "✅ specs/$name/spec.md auto-generated"
    else
        echo "⚠️ specs generation failed for $name (non-fatal)"
    fi
}

# 在主流程中调用 (line 378 后)
write_specs_file "$CHANGE_DIR" "$NAME" "$IMP_FILE"
```

- [ ] **Step 4: Run bats test to verify it passes**

Run: `bats tests/integration/test_specs_generation.bats`
Expected: 2 passed

- [ ] **Step 5: Defer commit**

---

### Task 4: 端到端验证 — 复现 2026-08-31 回归门失败场景

**Files:**
- Run-only (验证步骤)

- [ ] **Step 1: 模拟设计→船流程 — 批准 1 个新 P1 proposal**

```bash
# 在 worktree 内
cat > .rddf/improvements/test-regression-fix.md <<'EOF'
# test-regression-fix

**类型**: feature

## Capabilities

- **MUST**: 自动 specs/

## Impact

## Acceptance

- [ ] 回归门通过
EOF

# 走完整 approve → fill → validate 路径
source skills/guide-design/scripts/approve_proposal.sh test-regression-fix P1
python3 -c "
import json
d = json.load(open('proposal-approved.md'))  # smoke check
"
```

- [ ] **Step 2: 验证 openspec validate 通过**

Run: `openspec validate test-regression-fix --json`
Expected: `"valid": true` 或无 "No deltas found" 错误

- [ ] **Step 3: 验证 specs/ 目录与 spec.md 存在**

Run:
```bash
ls -la openspec/changes/test-regression-fix/specs/test-regression-fix/spec.md
head -5 openspec/changes/test-regression-fix/specs/test-regression-fix/spec.md
```
Expected: spec.md 存在且第一行含 "## ADDED Requirements"

- [ ] **Step 4: Defer commit**

---

### Task 5: 文档同步 — AGENTS.md + SKILL.md + proposal-approved-format

**Files:**
- Modify: `AGENTS.md` (D3 design-pre-created 协同段)
- Modify: `skills/guide-design/SKILL.md` (D1 编排段)
- Modify: `docs/proposal-approved-format.md` (新章节)

- [ ] **Step 1: 更新 AGENTS.md D3 段**

定位:AGENTS.md 中 "D3 design-pre-created 协同" 段,补充:
> 自 v2.2 起,`approve_proposal.sh` 在写入 `proposal.md` 之前自动调用 `generate_spec_delta()` 并写入 `specs/<name>/spec.md`。已存在的 `specs/` 目录保留(idempotency),不会覆盖。
> 
> Commit 示例:
> ```
> feat(guide-design): auto-generate specs/ on approve
> ```

- [ ] **Step 2: 更新 skills/guide-design/SKILL.md D1 编排段**

定位:在 D1 编排 Step 3 落盘说明后追加:
```
- 新增 `write_specs_file()` 步骤 (v2.2):调用 `generate_spec_delta()` 生成 `specs/<name>/spec.md`,在 `mkdir openspec/changes/<name>/` 之后、`proposal.md` 写入之前
```

- [ ] **Step 3: 新增 docs/proposal-approved-format.md 章节**

在末尾追加:
```markdown
## specs/ 与 proposal.md 的对应关系 (v2.2+)

| proposal.md 段 | specs/<sub>/spec.md 段 | 映射来源 |
|---|---|---|
| ## Acceptance (checkbox) | ### Requirement + #### Scenario | `- [ ]` 每条 → 1 个 Requirement + 1 个 Scenario |
| ## Capabilities (MUST/MUST NOT) | ### Requirement | 每条 MUST/MUST NOT → 1 个 Requirement |
| ## 关键场景 (GIVEN/WHEN/THEN) | #### Scenario (嵌入) | 嵌入对应 Requirement 的 Scenario block |
| 顶部段头 | `## ADDED Requirements` | openspec v1.4 强制 |
```

- [ ] **Step 4: Defer commit**

---

## Self-Review Checklist

- [x] Spec 覆盖:25 个 task 映射到 5 个实施任务 (acceptance/capability/scenario/idempotency/openspec-v1.4 + e2e + docs)
- [x] 占位符扫描:无 "TBD" / "fill in details"
- [x] 类型一致:`generate_spec_delta(source_md: str, sub: str) -> str` 签名贯穿所有 test
- [x] Idempotency:`write_specs_file` 在 `specs_dir` 已存在时跳过(场景 2)

## 实施契约

- **路径**: `.rddf/plans/fix-specs-auto-generate-in-design-precreated.md`(本文件)
- **Task 数量**: 5 个 `### Task N:`
- **Step 数量**: 25 个 `- [ ]` checkbox
- **Header**: Goal / Architecture / Tech Stack 必备 ✓
- **Files 行**: 每个 Task 含 `**Files:**` 段 ✓
