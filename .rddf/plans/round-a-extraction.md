# Round A: Inline Bash Extraction Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract ~580 lines of inline bash from 6 skill files into `_lib/` helpers, following established pattern (bash wrapper + Python helper + bats/pytest tests).

**Architecture:** Each inline bash block maps to exactly one `_lib/<name>.sh` bash wrapper (env-var IO) and optionally one `_lib/<name>.py` Python helper. The skill file keeps a 3-line `source + call` replacement. Every extraction is locked by 6-18 new bats integration tests + Python unit tests, matching the pattern from `ship_plan.sh` / `propose_change.{sh,py}` / `deps_render_report.sh`.

**Tech Stack:** bash (wrappers), Python 3.11+ (non-trivial helpers), bats-core (integration), pytest (unit)

---

### Task 1: guide-arch env check + artifact discovery (L92-L189, ~96 lines)

**Problem:** Phase 1 Step 1-5 inline bash mixes environment checks (openspec CLI, git, build dir, project type) with artifact discovery delegation. The discovery part already has `_lib/discover-arch-artifacts.sh` but its callers are still inline.

**Files:**
- Modify: `skills/guide-arch.md` (remove L92-L189, insert source + 1-2 line call)
- Create: `skills/_lib/arch_env_check.sh` — new wrapper exposing `run_arch_env_check()`
- Test: `tests/integration/test_arch_env_check_extraction.bats`
- Modify: `skills/_lib/discover-arch-artifacts.sh` — no changes (already exists)

**Helper signature:**
```bash
# skills/_lib/arch_env_check.sh
# run_arch_env_check: Prints env status + sets PROJECT_ROOT.
# Idempotent. Returns 1 if openspec CLI missing.
run_arch_env_check() {
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT
  # ... echo checks + discover artifacts ...
}
```

- [ ] **Step 1: Write failing bats tests**

Create `tests/integration/test_arch_env_check_extraction.bats` with 8 tests:
1. Helper exists with `run_arch_env_check` function
2. L92-L189 inline block no longer in guide-arch.md (check for "openspec CLI 未找到" pattern in code fence)
3. guide-arch.md invokes helper via `source`
4. `run_arch_env_check` runs without error in repo root
5. Sets `PROJECT_ROOT` env var
6. Fails gracefully when openspec not in PATH (mock PATH)
7. Discovers ADR count correctly
8. Sources discover-arch-artifacts.sh when present

Run: `bats tests/integration/test_arch_env_check_extraction.bats`
Expected: 8/8 RED (helper doesn't exist yet)

- [ ] **Step 2: Implement `_lib/arch_env_check.sh`**

```bash
# skills/_lib/arch_env_check.sh — extracted from guide-arch.md Phase 1 Steps 1-5 (L92-L189)
# Exports: run_arch_env_check()

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

run_arch_env_check() {
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  echo "🔍 环境检查..."
  echo ""

  # 1. openspec CLI 检测
  OPENSPEC_PATH=""
  for p in $(command -v openspec 2>/dev/null) /home/ubuntu/.npm-global/bin/openspec /usr/local/bin/openspec /opt/homebrew/bin/openspec; do
    [ -x "$p" ] && OPENSPEC_PATH="$p" && break
  done
  if [ -z "$OPENSPEC_PATH" ]; then
      echo "❌ openspec CLI 未找到"
      echo "   请安装: npm install -g openspec-cli"
      return 1
  fi
  if [ -x "$OPENSPEC_PATH" ]; then
      OPENSPEC_VER=$("$OPENSPEC_PATH" --version 2>/dev/null || echo "?")
      echo "✅ openspec CLI: $OPENSPEC_VER"
  fi

  # 2. git 状态
  GIT_CLEAN=$(git status --porcelain | grep -c . || true)
  if [ "$GIT_CLEAN" -eq 0 ]; then
      echo "✅ git 工作区干净"
  else
      echo "⚠️  git 工作区有 $GIT_CLEAN 个未跟踪/修改文件"
  fi

  # 3. 当前分支
  CURRENT_BRANCH=$(git branch --show-current)
  echo "📌 当前分支: $CURRENT_BRANCH"

  # 4. 构建目录
  if [ -f "Cargo.toml" ]; then
    BUILD_DIR="target"; PROJECT_TYPE="Rust"
  elif [ -f "package.json" ]; then
    BUILD_DIR="node_modules"; PROJECT_TYPE="Node.js"
  elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    BUILD_DIR="venv"; PROJECT_TYPE="Python"
  elif [ -f "CMakeLists.txt" ] || [ -f "Makefile" ]; then
    BUILD_DIR="build"; PROJECT_TYPE="C++/Make"
  else
    BUILD_DIR="build"; PROJECT_TYPE="Unknown"
  fi
  [ -d "$BUILD_DIR" ] && echo "✅ 构建目录存在 ($BUILD_DIR/, $PROJECT_TYPE)" \
                     || echo "⚠️  构建目录不存在 ($BUILD_DIR/, $PROJECT_TYPE)"

  # 5. arch 阶段专用检查
  ADR_COUNT=$(ls -d "$PROJECT_ROOT/docs/adr/ADR-0"*.md 2>/dev/null | wc -l)
  ROADMAP_EXISTS=$([ -f "$PROJECT_ROOT/roadmap.md" ] && echo "yes" || echo "no")
  GAP_COUNT=$(ls "$PROJECT_ROOT/docs/architecture/"*-gap-analysis.md 2>/dev/null | wc -l)
  ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
  echo "📋 现有 ADR: $ADR_COUNT"
  echo "📋 Roadmap: $ROADMAP_EXISTS"
  echo "📋 架构差距分析: $GAP_COUNT"
  echo "📋 活动 changes: $ACTIVE_CHANGES"

  # === Phase 1 Step 5: 工件发现 (ADR-0016 Layer 1) ===
  if [ -f "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh" ]; then
      source "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh"
      discover_adr_dir          >/dev/null
      discover_roadmap          >/dev/null
      discover_architecture_dir >/dev/null
      discover_adr_pattern      >/dev/null
      echo ""
      echo "🔍 工件发现 (ADR-0016):"
      echo "   ADR 目录:      $DISCOVERED_ADR_DIR ($DISCOVERED_ADR_DIR_FOUND)"
      echo "   ADR 模式:      $DISCOVERED_ADR_PATTERN"
      echo "   Roadmap:       $DISCOVERED_ROADMAP_PATH ($DISCOVERED_ROADMAP_FOUND)"
      echo "   Architecture:  $DISCOVERED_ARCHITECTURE_DIR ($DISCOVERED_ARCH_FOUND)"
  else
      DISCOVERED_ADR_DIR="docs/adr"
      DISCOVERED_ROADMAP_PATH="roadmap.md"
      DISCOVERED_ARCHITECTURE_DIR="docs/architecture"
      DISCOVERED_ADR_PATTERN="ADR-*.md"
      DISCOVERED_ADR_DIR_FOUND="false"
      DISCOVERED_ROADMAP_FOUND="false"
      DISCOVERED_ARCH_FOUND="false"
  fi
}
```

- [ ] **Step 3: Run bats tests to verify GREEN**

Run: `bats tests/integration/test_arch_env_check_extraction.bats`
Expected: 8/8 PASS

- [ ] **Step 4: Migrate guide-arch.md**

Replace lines L92-L189 with:
```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/arch_env_check.sh"
run_arch_env_check || exit 1
```

Run: verify inline block removed (`grep -c 'openspec CLI 未找到' skills/guide-arch.md` should be 0 inside code fences... actually the string is still in the _lib helper. Let's verify: `grep "for p in \$" skills/guide-arch.md` should not match inside a bash code block)

- [ ] **Step 5: Run full regression**

```bash
python3 -m pytest tests/ -q --tb=line
bats tests/integration/test_arch_env_check_extraction.bats
```

Expected: all pass (existing tests unchanged, new tests GREEN)

- [ ] **Step 6: Commit**

```bash
git add skills/_lib/arch_env_check.sh skills/guide-arch.md tests/integration/test_arch_env_check_extraction.bats
git commit -m "refactor(arch): extract env check + artifact discovery to _lib/arch_env_check.sh

Move guide-arch.md Phase 1 Steps 1-5 inline bash (L92-L189, ~96 lines)
into _lib/arch_env_check.sh::run_arch_env_check().

The helper:
- Runs openspec CLI detection
- Checks git state + branch
- Detects build directory by project type
- Collects ADR/roadmap/gap/change counts
- Delegates ADR-0016 artifact discovery to discover-arch-artifacts.sh

8 new bats integration tests lock the contract."
```

---

### Task 2: guide-arch handoff JSON writer (L711-L800, ~88 lines)

**Problem:** `.arch-handoff.json` write logic is a standalone 88-line inline block with complex JSON generation (ADR glob, ID extraction, phase detection, discovery candidates serialization). Pattern matches `propose_change.py` exactly.

**Files:**
- Create: `skills/_lib/write_arch_handoff.py` — Python function `write_arch_handoff(project_root, ...)`
- Create: `skills/_lib/write_arch_handoff.sh` — bash wrapper exposing `write_arch_handoff()`
- Modify: `skills/guide-arch.md` (remove L711-L800, insert source + call)
- Test: `tests/unit/test_write_arch_handoff.py` (10 tests)
- Test: `tests/integration/test_arch_handoff_extraction.bats` (6 tests)
- Modify: `skills/_lib/schemas/arch_handoff_schema.json` (reference — no changes)

**Helper signatures:**

```python
# skills/_lib/write_arch_handoff.py
def write_arch_handoff(
    project_root: str,
    discovered_adr_dir: str = "docs/adr",
    discovered_roadmap_path: str = "roadmap.md",
    discovered_architecture_dir: str = "docs/architecture",
    discovered_adr_pattern: str = "ADR-*.md",
    discovered_adr_dir_found: str = "false",
    discovered_roadmap_found: str = "false",
    discovered_arch_found: str = "false",
    discovered_adr_dir_tried: str = "[]",
    discovered_roadmap_tried: str = "[]",
    discovered_arch_tried: str = "[]",
    roadmap_exists_bool: str = "false",
) -> dict:
    """Build and write .arch-handoff.json. Returns the written dict."""
```

```bash
# skills/_lib/write_arch_handoff.sh
write_arch_handoff() {
    # Reads env vars: PROJECT_ROOT, DISCOVERED_ADR_DIR, DISCOVERED_ROADMAP_PATH, etc.
    # Delegates to write_arch_handoff.py
}
```

- [ ] **Step 1: Write failing Python unit tests**

Create `tests/unit/test_write_arch_handoff.py` with 10 tests:
1. `test_write_arch_handoff_basic` — writes valid JSON with correct schema
2. `test_adr_glob` — discovers ADR files matching pattern
3. `test_adr_id_extraction` — extracts IDs like "0001" from "ADR-0001-foo.md"
4. `test_custom_adr_pattern` — works with `DEC-*.md`, `RFD-*.md`
5. `test_empty_adr_dir` — handles missing ADR directory gracefully
6. `test_roadmap_phase_extraction` — extracts `**当前阶段**` from roadmap
7. `test_discovery_fields` — populates `discovered.adr_dir.found` etc.
8. `test_version_field` — sets `version: 1`
9. `test_arch_complete_at` — sets ISO timestamp
10. `test_roadmap_exists_bool` — sets `roadmap_exists` boolean

Run: `python3 -m pytest tests/unit/test_write_arch_handoff.py -v`
Expected: 10/10 RED (module doesn't exist)

- [ ] **Step 2: Write failing bats integration tests**

Create `tests/integration/test_arch_handoff_extraction.bats` with 6 tests:
1. Helper exists with `write_arch_handoff` function
2. L711-L800 no longer inlines the handoff JSON heredoc (`cat > "$HANDOFF_FILE"`)
3. guide-arch.md invokes helper via `source`
4. `write_arch_handoff` creates `.arch-handoff.json` with valid structure
5. Handoff file contains `adr_count`, `current_phase`, `version`
6. Fails gracefully when `discover-arch-artifacts.sh` missing

Run: `bats tests/integration/test_arch_handoff_extraction.bats`
Expected: 6/6 RED

- [ ] **Step 3: Implement `_lib/write_arch_handoff.py`**

Python function `write_arch_handoff()` that:
1. Takes project_root + discovery env vars as parameters
2. Globs ADR files using discovered_adr_pattern (with find -maxdepth 1)
3. Excludes `*-0000-template.md`
4. Extracts numeric IDs from filenames
5. Reads roadmap phase from `**当前阶段**:`
6. Generates `completed_adr_ids` as sorted comma-separated list
7. Constructs full JSON matching `arch_handoff_schema.json` v1
8. Writes to `.rddf/state/.arch-handoff.json`
9. Returns the dict for test inspection

- [ ] **Step 4: Implement `_lib/write_arch_handoff.sh`**

Bash wrapper that:
1. Reads env vars (PROJECT_ROOT, DISCOVERED_ADR_DIR, etc.)
2. Delegates to Python function via env-var passing
3. `mkdir -p` before writing
4. Echoes result message on success/failure

- [ ] **Step 5: Run Python unit tests — verify GREEN**

Run: `python3 -m pytest tests/unit/test_write_arch_handoff.py -v`
Expected: 10/10 PASS

- [ ] **Step 6: Run bats integration tests — verify GREEN (or adjust)**

Run: `bats tests/integration/test_arch_handoff_extraction.bats`
Expected: 6/6 PASS

- [ ] **Step 7: Migrate guide-arch.md**

Replace L711-L800 with:
```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/write_arch_handoff.sh"
write_arch_handoff
```

- [ ] **Step 8: Full regression**

```bash
python3 -m pytest tests/ -q --tb=line
bats tests/
```

Expected: all pass

- [ ] **Step 9: Commit**

```bash
git add skills/_lib/write_arch_handoff.py skills/_lib/write_arch_handoff.sh \
      skills/guide-arch.md \
      tests/unit/test_write_arch_handoff.py \
      tests/integration/test_arch_handoff_extraction.bats
git commit -m "refactor(arch): extract .arch-handoff.json writer to _lib/write_arch_handoff.{py,sh}

Move guide-arch.md L711-L800 inline heredoc-based JSON generation
(~88 lines) into Python function + bash wrapper.

The Python helper:
- Globs ADR files using discoverable pattern (ADR-*, DEC-*, etc.)
- Extracts numeric IDs with template exclusion
- Reads roadmap phase from markdown
- Generates v1 schema JSON with discovery metadata
- mkdir-p before write

10 Python unit + 6 bats integration tests lock the contract."
```

---

### Task 3: guide-plan Phase 0 intake (L95-L175, ~79 lines)

**Problem:** Plan phase environment check duplicates ~40% of arch env check logic (openspec CLI detection, git state). The unique part is arch-handoff JSON reading.

**Files:**
- Create: `skills/_lib/plan_intake.sh` — bash wrapper exposing `run_plan_intake()`
- Modify: `skills/guide-plan.md` (remove L95-L175)
- Test: `tests/integration/test_plan_intake_extraction.bats`

**Helper signature:**
```bash
# skills/_lib/plan_intake.sh
run_plan_intake() {
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT
  # openspec CLI check (same as arch_env_check pattern)
  # git state + branch check
  # arch-handoff existence check (hard gate)
  # jq-based handoff field reading (ADR_DIR, ROADMAP_PATH, etc.)
  # Python-based ADR_IDS + CURRENT_PHASE extraction from handoff
  # echo summary
}
```

- [ ] **Step 1: Write failing bats tests** (6 tests)

1. Helper exists with `run_plan_intake` function
2. L95-L175 inline block no longer in guide-plan.md
3. guide-plan.md invokes helper via `source`
4. `run_plan_intake` blocks when no `.arch-handoff.json`
5. Reads ADR directory from handoff when present
6. Reads roadmap phase from handoff when present

- [ ] **Step 2: Implement `_lib/plan_intake.sh`**

```bash
run_plan_intake() {
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT
  echo "🔍 Plan 阶段环境检查..."
  echo ""

  # openspec CLI check (same pattern as arch_env_check)
  OPENSPEC_PATH=""
  for p in $(command -v openspec 2>/dev/null) /home/ubuntu/.npm-global/bin/openspec /usr/local/bin/openspec /opt/homebrew/bin/openspec; do
    [ -x "$p" ] && OPENSPEC_PATH="$p" && break
  done
  if [ -x "$OPENSPEC_PATH" ]; then
      OPENSPEC_VER=$("$OPENSPEC_PATH" --version 2>/dev/null || echo "?")
      echo "✅ openspec CLI: $OPENSPEC_VER"
  else
      echo "❌ openspec CLI 未找到"
      echo "   请安装: npm install -g openspec-cli"
      exit 1
  fi

  # git state
  GIT_CLEAN=$(git status --porcelain | grep -c . || true)
  [ "$GIT_CLEAN" -eq 0 ] && echo "✅ git 工作区干净" \
                         || echo "⚠️  git 工作区有 $GIT_CLEAN 个未跟踪/修改文件"

  CURRENT_BRANCH=$(git branch --show-current)
  echo "📌 当前分支: $CURRENT_BRANCH"

  # arch-handoff check
  ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  if [ ! -f "$ARCH_HANDOFF" ]; then
      echo "❌ 未检测到 arch-done handoff (.rddf/state/.arch-handoff.json)"
      echo "   → 请先运行: skill_use(\"guide-arch\")"
      exit 1
  fi
  # ... rest of handoff field reading via jq + python3 ...
}
```

- [ ] **Step 3: Run tests GREEN + migrate guide-plan.md**

Replace L95-L175 with:
```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/plan_intake.sh"
run_plan_intake
```

- [ ] **Step 4: Full regression + commit**

---

### Task 4: guide-plan plan-done gate + handoff (L594-L753, ~150 lines)

**Problem:** Two adjacent blocks that form a single logical unit: triple-gate validation (100 lines) + handoff JSON write (51 lines). ~150 lines total, the biggest extraction in Round A.

**Files:**
- Create: `skills/_lib/plan_done_gate.sh` — bash wrapper exposing `run_plan_done_gate()` and `write_plan_handoff()`
- Create: `skills/_lib/plan_done_gate.py` — Python function `write_plan_handoff()`
- Modify: `skills/guide-plan.md` (remove L594-L753)
- Test: `tests/unit/test_plan_done_gate.py` (8 tests)
- Test: `tests/integration/test_plan_done_gate_extraction.bats` (8 tests)

**Helper signatures:**

```python
# skills/_lib/plan_done_gate.py
def write_plan_handoff(project_root: str, change_count: int, current_change: str) -> dict:
    """Write .rddf/state/.plan-handoff.json. Returns the written dict."""
```

```bash
# skills/_lib/plan_done_gate.sh
run_plan_done_gate() {
  # Reads PROJECT_ROOT
  # Gate 0: deps AI suggestion echo (read .deps-output.md, check fallback)
  # Gate 1: ready-for-ship count (delegates to iteration.list_ready_for_ship)
  # Gate 2: active changes count
  # Gate 3: artifacts committed check (git show HEAD: for each change)
  # Any gate fails → exit 1
}
write_plan_handoff() {
  # Reads PROJECT_ROOT
  # CHANGE_COUNT = ls openspec/changes/*/ | grep -v archive/ | wc -l
  # Runs validate_baseline.py + validate_delta_targets.py per change
  # Calls write_plan_handoff.py
}
```

- [ ] **Step 1: Write failing Python unit tests** (8 tests)

1. `test_write_plan_handoff_basic` — valid JSON with correct schema
2. `test_change_count` — sets `active_changes: N`
3. `test_current_change` — sets `current_change` to first active change
4. `test_empty_changes` — handles no active changes
5. `test_plan_complete_at` — sets ISO timestamp
6. `test_ship_started_at_null` — initial value is null
7. `test_all_artifacts_committed_true` — hardcoded true
8. `test_handoff_file_written` — file created on disk

- [ ] **Step 2: Write failing bats integration tests** (8 tests)

1. Helper exists with `run_plan_done_gate` function
2. Helper exists with `write_plan_handoff` function
3. L594-L695 + L701-L753 no longer inline in guide-plan.md
4. guide-plan.md invokes both helpers via `source`
5. `run_plan_done_gate` passes when 1+ change with committed artifacts
6. `run_plan_done_gate` fails when 0 active changes
7. `write_plan_handoff` creates `.plan-handoff.json`
8. Handoff file contains `active_changes`, `current_change`, `plan_complete_at`

- [ ] **Step 3: Implement `_lib/plan_done_gate.py`**

```python
def write_plan_handoff(project_root: str, change_count: int, current_change: str) -> dict:
    handoff = {
        "plan_complete_at": datetime.now(timezone.utc).isoformat(),
        "active_changes": change_count,
        "all_artifacts_committed": True,
        "ship_started_at": None,
        "current_change": current_change,
    }
    handoff_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(handoff_dir, exist_ok=True)
    with open(os.path.join(handoff_dir, ".plan-handoff.json"), "w") as f:
        json.dump(handoff, f, indent=2)
    return handoff
```

- [ ] **Step 4: Implement `_lib/plan_done_gate.sh`**

Two functions:
1. `run_plan_done_gate()` — pure bash (env var for deps choice, python for iteration query, subshell for artifact commit check)
2. `write_plan_handoff()` — delegate to Python, run validators, echo result

- [ ] **Step 5: Tests GREEN + migrate guide-plan.md**

Replace L594-L753 with:
```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/plan_done_gate.sh"
run_plan_done_gate
write_plan_handoff
```

- [ ] **Step 6: Full regression + commit**

---

### Task 5: guide-ship Phase 2 monitor (L260-L315, ~54 lines)

**Problem:** Progress reading across worktree + lightweight branches. Standalone 54-line bash with mapfile + awk + git branch enumeration. Cleanest extraction candidate in guide-ship.md.

**Files:**
- Create: `skills/_lib/ship_monitor.sh` — bash wrapper exposing `run_ship_monitor()`
- Modify: `skills/guide-ship.md` (remove L260-L315)
- Test: `tests/integration/test_ship_monitor_extraction.bats`

**Helper signature:**
```bash
# skills/_lib/ship_monitor.sh
run_ship_monitor() {
  # Reads PROJECT_ROOT
  # mapfile worktree list → read tasks.md progress
  # Supplement with lightweight branches
  # Echo formatted progress table
}
```

- [ ] **Step 1: Write failing bats tests** (6 tests)

1. Helper exists with `run_ship_monitor` function
2. L260-L315 no longer inlined in guide-ship.md
3. guide-ship.md invokes helper via `source`
4. `run_ship_monitor` prints progress for worktree branches
5. Handles empty worktree list gracefully
6. Detects lightweight branches (no worktree)

- [ ] **Step 2: Implement `_lib/ship_monitor.sh`**

```bash
run_ship_monitor() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  echo "📋 所有 Changes 实际进度:"
  local LAST_CHECK
  LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")

  # Worktree branches
  local -a wt_list=()
  if command -v mapfile &>/dev/null; then
    mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}' 2>/dev/null)
  else
    while IFS= read -r line; do wt_list+=("$line"); done < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}' 2>/dev/null)
  fi
  local wt branch name tasks_file total done progress mode
  for wt in "${wt_list[@]}"; do
      branch=$(git worktree list | grep -F "$wt" | awk '{print $3}')
      name=$(echo "$branch" | sed 's|openspec/||')
      tasks_file="$wt/openspec/changes/$name/tasks.md"
      mode="worktree"
      [ -f "$tasks_file" ] && total=$(grep -c '^- \[' "$tasks_file" 2>/dev/null || echo 0) \
                            && done=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null || echo 0) \
                            && progress="${done}/${total}" \
                          || progress="? (文件不存在)"
      echo "  $name → $progress [$mode]"
  done

  # Lightweight branches
  if git branch | grep -q "openspec/"; then
      local branch_name in_wt wt_branch
      for branch_name in $(git branch | grep "openspec/" | sed 's/.*openspec\///'); do
          in_wt=false
          for wt in "${wt_list[@]}"; do
              wt_branch=$(git worktree list | grep -F "$wt" | awk '{print $3}' | sed 's|openspec/||')
              [ "$wt_branch" = "$branch_name" ] && in_wt=true && break
          done
          $in_wt && continue
          tasks_file="$PROJECT_ROOT/openspec/changes/$branch_name/tasks.md"
          local CURRENT_BRANCH
          CURRENT_BRANCH=$(git branch --show-current)
          [ "$CURRENT_BRANCH" = "openspec/$branch_name" ] && mode="轻量(当前)" || mode="轻量"
          [ -f "$tasks_file" ] && total=$(grep -c '^- \[' "$tasks_file" 2>/dev/null || echo 0) \
                                && done=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null || echo 0) \
                                && progress="${done}/${total}" \
                              || progress="? (文件不存在)"
          echo "  $branch_name → $progress [$mode]"
      done
  fi
  echo ""
  echo "上次检测: $LAST_CHECK"
}
```

- [ ] **Step 3: Tests GREEN + migrate guide-ship.md + commit**

---

### Task 6: execute.md worktree auto-detect/select (L54-L168, ~113 lines)

**Problem:** Largest remaining inline block in any skill file. ~113 lines of pure worktree detection/selection logic. Already uses `_lib/worktree.sh` for `main_repo_root`. The selection menu uses `EXECUTE_CHOICE` env var (P0-9 fix).

**Files:**
- Create: `skills/_lib/select_worktree.sh` — bash wrapper exposing `auto_detect_worktree_context()`
- Modify: `skills/execute.md` (remove L54-L168)
- Test: `tests/integration/test_select_worktree_extraction.bats`

**Helper signature:**
```bash
# skills/_lib/select_worktree.sh
auto_detect_worktree_context() {
  # Source worktree.sh (main_repo_root, wt_path_for_branch, find_default_branch)
  # Set PROJECT_ROOT, CURRENT_BRANCH, GIT_ROOT
  # Detect if inside worktree → set CHANGE_NAME, WORKTREE_PATH, HAS_WORKTREE
  # If not in worktree: list openspec worktrees, prompt via EXECUTE_CHOICE, cd
  # If no worktrees exist: exit with error + list changes
}
```

- [ ] **Step 1: Write failing bats tests** (8 tests)

1. Helper exists with `auto_detect_worktree_context` function
2. L54-L168 no longer inlined in execute.md
3. execute.md invokes helper via `source`
4. Detects worktree context when inside `openspec/` branch
5. Lists worktrees when outside worktree
6. Respects `EXECUTE_CHOICE` env var for selection
7. Blocks when no worktrees exist
8. Sets `CHANGE_NAME`, `HAS_WORKTREE` env vars

- [ ] **Step 2: Implement `_lib/select_worktree.sh`**

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

auto_detect_worktree_context() {
  # Source worktree.sh for main_repo_root
  if [ -f "$SCRIPT_DIR/worktree.sh" ]; then
    source "$SCRIPT_DIR/worktree.sh"
  fi

  PROJECT_ROOT=$(main_repo_root 2>/dev/null || git rev-parse --show-toplevel 2>/dev/null || pwd)
  [ -d "$PROJECT_ROOT" ] || PROJECT_ROOT=$(pwd)
  export PROJECT_ROOT

  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
  GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")
  WORKTREE_LIST=$(git worktree list)

  # Inside worktree?
  if echo "$CURRENT_BRANCH" | grep -q '^openspec/'; then
      CHANGE_NAME=$(echo "$CURRENT_BRANCH" | sed 's/^openspec\///')
      WORKTREE_PATH=$(pwd)
      HAS_WORKTREE=true
      # Verify match
      MAIN_WT_PATH=$(echo "$WORKTREE_LIST" | grep "openspec/$CHANGE_NAME" | awk '{print $1}')
      if [ "$MAIN_WT_PATH" != "$(pwd)" ]; then
          echo "⚠️ 分支名与 worktree 路径不匹配"
      fi
  else
      # Not in worktree — show selection or error
      echo "⚠️  当前不在 worktree 内"
      local WT_INFO
      WT_INFO=$(git worktree list | grep "openspec/" | awk '{print $1, $3}')
      if [ -z "$WT_INFO" ]; then
          echo "❌ 无已创建的 worktree"
          echo "请先执行 guide-ship 技能创建 worktree："
          echo "  skill_use(\"guide-ship\")"
          ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | while read dir; do
              echo "  - $(basename "$dir")"
          done
          exit 1
      fi
      # ... worktree selection menu with EXECUTE_CHOICE ...
  fi
}
```

- [ ] **Step 3: Tests GREEN + migrate execute.md + commit**

---

**Plan complete and saved to `.rddf/plans/round-a-extraction.md`.** Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task with isolated review checkpoints

**2. Inline Execution** — execute tasks in this session with verification checkpoints

Which approach?