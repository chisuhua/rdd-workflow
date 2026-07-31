# fix-deps-render-report-multi-candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `deps_render_report.sh` 中 CANDIDATES → Python 列表转换 bug（空格包裹无逗号导致相邻字符串拼接），以及 fallback 分支未重算 `candidates_py` 的 bug，使多候选 Mermaid 图正确渲染。

**Architecture:** 用 `python3` + `shlex.split`/`json.dumps` 替代 sed 字符串处理生成逗号分隔的 Python 列表；fallback 读取 `.deps-candidates.json` 后重新计算 `candidates_py`。bats 测试锁定 3+ 候选与 fallback 场景。

**Tech Stack:** bash + sed（现有）, python3 (转换), bats-core 1.10+

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/deps/scripts/deps_render_report.sh:30-47` | 修复 CANDIDATES → Python list 转换 + fallback 重算 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_deps_report_render_extraction.bats` | 新增 3+ 候选渲染 + fallback 非空候选渲染用例 |

---

### Task 1: 修复 CANDIDATES → Python list 转换

**Files:**
- Modify: `skills/deps/scripts/deps_render_report.sh:32-41`
- Test: `tests/integration/test_deps_report_render_extraction.bats`

- [ ] **Step 1: Write the failing test**

在 `tests/integration/test_deps_report_render_extraction.bats` 末尾追加测试（3 候选必须渲染为 3 个独立节点）：

```bash
@test "render_deps_report: 3 candidates render as 3 independent mermaid nodes" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  mkdir -p openspec/changes/c1 openspec/changes/c2 openspec/changes/c3
  for c in c1 c2 c3; do
    echo "# design" > "openspec/changes/$c/design.md"
    cat > "openspec/changes/$c/roadmap-meta.yaml" <<'EOF'
roadmap:
  phase: "v2.1"
  category: "core-impl"
EOF
  done
  source "$REPO_ROOT/skills/deps/scripts/deps_render_report.sh"
  CANDIDATES="c1 c2 c3" PROJECT_ROOT="$TEST_REPO" render_deps_report >/dev/null 2>&1
  [ -f "$TEST_REPO/.rddf/state/.deps-output.md" ]
  # Mermaid 图必须含 3 个独立节点（而非拼接节点 c1c2c3）
  run grep -c 'c1\[\[c1\]\]\|c2\[\[c2\]\]\|c3\[\[c3\]\]' "$TEST_REPO/.rddf/state/.deps-output.md"
  [ "$status" -eq 0 ]
  # 断言不存在拼接节点
  run grep -q 'c1c2c3' "$TEST_REPO/.rddf/state/.deps-output.md"
  [ "$status" -ne 0 ]
  rm -rf "$TEST_REPO"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_deps_report_render_extraction.bats`
Expected: FAIL — Mermaid 图含单个拼接节点 `c1c2c3`（sed 无逗号 → Python 相邻字符串拼接）

- [ ] **Step 3: Write minimal implementation**

修改 `skills/deps/scripts/deps_render_report.sh:32-41`。当前逻辑：

```bash
  # Convert CANDIDATES string to Python list format
  local candidates_py="[$(echo "$CANDIDATES" | sed "s/[^ ]*/'&'/g" | sed "s/''//" | sed "s/',' /', '/g")]"
  # If CANDIDATES is empty, fall back to reading deps-candidates.json
  if [ -z "$CANDIDATES" ]; then
    local deps_input="$PROJECT_ROOT/.rddf/state/.deps-candidates.json"
    CANDIDATES=$(python3 -c "import json; d=json.load(open('$deps_input')); print(' '.join(d.get('candidates',[])))" 2>/dev/null)
    if [ -z "$CANDIDATES" ]; then
      candidates_py="[]"
    fi
  fi
```

修复为用 `shlex.split` + `json.dumps` 生成逗号分隔列表，且 **fallback 后重新计算 candidates_py**：

```bash
  # Convert CANDIDATES string to Python list format (comma-separated,
  # avoids adjacent-string concat bug: 'a' 'b' 'c' != ['a','b','c'])
  local candidates_py
  candidates_py=$(PY_CANDIDATES="$CANDIDATES" python3 -c '
import json, os, shlex
cands = shlex.split(os.environ.get("PY_CANDIDATES", ""))
print(json.dumps(cands))
' 2>/dev/null)
  # If CANDIDATES is empty, fall back to reading deps-candidates.json
  if [ -z "$CANDIDATES" ]; then
    local deps_input="$PROJECT_ROOT/.rddf/state/.deps-candidates.json"
    CANDIDATES=$(python3 -c "import json; d=json.load(open('$deps_input')); print(' '.join(d.get('candidates',[])))" 2>/dev/null)
    if [ -z "$CANDIDATES" ]; then
      candidates_py="[]"
    else
      # fallback 读取成功后重新计算 candidates_py（原实现漏掉此行）
      candidates_py=$(PY_CANDIDATES="$CANDIDATES" python3 -c '
import json, os, shlex
cands = shlex.split(os.environ.get("PY_CANDIDATES", ""))
print(json.dumps(cands))
' 2>/dev/null)
    fi
  fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_deps_report_render_extraction.bats`
Expected: PASS — 3 个独立节点渲染成功，无拼接节点

- [ ] **Step 5: Commit**

```bash
git add skills/deps/scripts/deps_render_report.sh tests/integration/test_deps_report_render_extraction.bats
git commit -m "fix: comma-separate CANDIDATES->python list in deps render"
```

---

### Task 2: fallback 分支重算 candidates_py

**Files:**
- Modify: `skills/deps/scripts/deps_render_report.sh:35-41`
- Test: `tests/integration/test_deps_report_render_extraction.bats`

- [ ] **Step 1: Write the failing test**

追加 fallback 测试（CANDIDATES 为空 + `.deps-candidates.json` 有 3 候选 → 报告显示 3 候选）：

```bash
@test "render_deps_report: empty CANDIDATES falls back to deps-candidates.json and renders all" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  mkdir -p openspec/changes/a1 openspec/changes/a2 openspec/changes/a3
  for c in a1 a2 a3; do
    echo "# design" > "openspec/changes/$c/design.md"
    cat > "openspec/changes/$c/roadmap-meta.yaml" <<'EOF'
roadmap:
  phase: "v2.1"
  category: "core-impl"
EOF
  done
  mkdir -p .rddf/state
  cat > .rddf/state/.deps-candidates.json <<'EOF'
{"candidates": ["a1", "a2", "a3"]}
EOF
  source "$REPO_ROOT/skills/deps/scripts/deps_render_report.sh"
  CANDIDATES="" PROJECT_ROOT="$TEST_REPO" render_deps_report >/dev/null 2>&1
  [ -f "$TEST_REPO/.rddf/state/.deps-output.md" ]
  # 报告必须显示 3 个候选（而非 0 候选）
  run grep -c 'a1\[\[a1\]\]\|a2\[\[a2\]\]\|a3\[\[a3\]\]' "$TEST_REPO/.rddf/state/.deps-output.md"
  [ "$status" -eq 0 ]
  rm -rf "$TEST_REPO"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_deps_report_render_extraction.bats`
Expected: FAIL — 报告显示 0 候选（fallback 更新 CANDIDATES 但 candidates_py 仍是空串算出的 `[]`）

- [ ] **Step 3: Write minimal implementation**

Task 1 的修复已包含 fallback 后的 `candidates_py` 重算（`else` 分支）。若此步失败，确认 fallback 分支的 `candidates_py` 赋值在 `CANDIDATES` 更新之后执行。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_deps_report_render_extraction.bats`
Expected: PASS — fallback 路径渲染 3 个候选节点

- [ ] **Step 5: Commit**

```bash
git add skills/deps/scripts/deps_render_report.sh tests/integration/test_deps_report_render_extraction.bats
git commit -m "fix: recompute candidates_py after fallback read in deps render"
```

---

### Task 3: 单候选回归 + 全量验证

**Files:**
- Test: `tests/integration/test_deps_report_render_extraction.bats`
- Modify: `skills/deps/scripts/deps_render_report.sh`（若有单候选回归问题）

- [ ] **Step 1: Write the failing test**

无新测试——现有单候选用例（`render_deps_report writes .deps-output.md with all sections`）作为回归基线。

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_deps_report_render_extraction.bats`
Expected: 现有单候选用例通过（回归基线无失败）

- [ ] **Step 3: Write minimal implementation**

无实现变更。若单候选用例失败，检查 `shlex.split` 对单值的处理（`"c1"` → `['c1']`）。

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
bats tests/integration/test_deps_report_render_extraction.bats
python3 -m pytest tests/unit/test_deps_output.py -q
```
Expected: 全部通过

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: verify single-candidate behavior unchanged + unit regression"
```
