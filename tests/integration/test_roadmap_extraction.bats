#!/usr/bin/env bats
# tests/integration/test_roadmap_extraction.bats
# Roadmap extraction regression: the Python heredocs in roadmap.md were
# moved to _lib/roadmap_state.py (mirrors P1-14 archive.sh +
# status_helpers.sh patterns).
#
# Extraction targets (all Python heredocs → roadmap_state.py):
#   init Step 4 → init_state()
#   status Step 1+2 → render_status_view()
#   edit 添加新阶段 → add_phase()
#   validate → validate_change()
#   advance → advance_phase() + update_roadmap_marker()
#   helpers → get_phase_categories() + update_change_count()
#
# These tests lock the refactor in place:
#   1. roadmap_state.py exists with all 9 exported functions.
#   2. roadmap.md positive-grep: source + call lines for each extraction.
#   3. roadmap.md negative-grep: old inline Python patterns gone.
#   4. Runtime: init_state creates valid state; render_status_view
#      returns 0 on existing roadmap; advance_phase fails incomplete.

load ../test_helper

# ---- Positive: helper existence ----

@test "_lib/roadmap_state.py exists with init_state function" {
  [ -f "$REPO_ROOT/_lib/roadmap_state.py" ]
  grep -qE '^def init_state\(' "$REPO_ROOT/_lib/roadmap_state.py"
}

@test "_lib/roadmap_state.py defines all 9 exported functions" {
  [ -f "$REPO_ROOT/_lib/roadmap_state.py" ]
  for fn in init_state read_state render_status_view validate_change \
            add_phase advance_phase update_roadmap_marker \
            get_phase_categories update_change_count; do
    grep -qE "^def ${fn}\(" "$REPO_ROOT/_lib/roadmap_state.py" || {
      echo "FAIL: missing function ${fn}"
      return 1
    }
  done
}

# ---- Positive: roadmap.md uses helpers ----

@test "roadmap.md init Step 4 calls roadmap_state.init_state" {
  [ -f "$REPO_ROOT/skills/roadmap/SKILL.md" ]
  grep -nE 'from skills\._lib\.roadmap_state import init_state' "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap.md status calls roadmap_state.render_status_view" {
  grep -nE 'from skills\._lib\.roadmap_state import render_status_view' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap.md edit calls roadmap_state.add_phase" {
  grep -nE 'from skills\._lib\.roadmap_state import add_phase' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap.md validate calls roadmap_state.validate_change" {
  grep -nE 'from skills\._lib\.roadmap_state import validate_change' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap.md advance calls roadmap_state.advance_phase" {
  grep -nE 'from skills\._lib\.roadmap_state import advance_phase' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap.md helpers call get_phase_categories + update_change_count" {
  grep -nE 'from skills\._lib\.roadmap_state import get_phase_categories' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
  grep -nE 'from skills\._lib\.roadmap_state import update_change_count' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
}

# ---- Negative: no inline Python heredocs remaining ----

@test "roadmap.md no longer inlines init_state JSON template" {
  [ -f "$REPO_ROOT/skills/roadmap/SKILL.md" ]
  # The old code used a large inline Python heredoc with state dict literal
  # containing phase-1/phase-2/phase-3 definitions. After extraction,
  # roadmap.md must not contain the raw Python dict template.
  ! grep -nE "'core-impl'.*'core-test'" "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap.md no longer inlines status render Python heredoc" {
  # The old status render used `for phase_id, phase_data in
  # state.get('phases', {}).items():` inline. After extraction this
  # lives in render_status_view().
  ! grep -nE 'for phase_id, phase_data in state\.get\(.phases.' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap.md no longer inlines advance pre-check Python heredoc" {
  # The old advance pre-check iterated categories inline:
  #   for cat_id, cat_data in phase_data.get('categories', {}).items():
  ! grep -nE 'for cat_id, cat_data in phase_data\.get\(.categories.' \
    "$REPO_ROOT/skills/roadmap/SKILL.md"
}

# ---- Runtime sanity ----

@test "roadmap_state.init_state creates valid state file" {
  TEST_REPO=$(mktemp -d)
  mkdir -p "$TEST_REPO/.rddf/state"
  STATE_FILE="$TEST_REPO/.rddf/state/roadmap-state.json"

  PYTHONPATH="$REPO_ROOT" python3 -c "
import os, sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.roadmap_state import init_state
state = init_state('$STATE_FILE')
assert state['current_phase'] == 'phase-1'
assert 'arch-design' in state['phases']['phase-1']['categories']
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "roadmap_state.render_status_view returns 0 on valid roadmap" {
  TEST_REPO=$(mktemp -d)
  mkdir -p "$TEST_REPO/.rddf/state"
  ROADMAP_FILE="$TEST_REPO/roadmap.md"
  STATE_FILE="$TEST_REPO/.rddf/state/roadmap-state.json"

  printf '**当前阶段**: phase-1\n\n### Phase 1: test (phase-1)\n**状态**: ⏳ 未开始\n\n#### 任务分类\n| 分类ID | 名称 | 描述 | 优先级 |\n|--------|------|------|--------|\n| infra-setup | 基础设施 | CI/CD 等 | P0 |\n' > "$ROADMAP_FILE"

  PYTHONPATH="$REPO_ROOT" python3 -c "
import os, sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.roadmap_state import init_state, render_status_view
init_state('$STATE_FILE')
rc = render_status_view('$ROADMAP_FILE', '$STATE_FILE')
assert rc == 0, f'render_status_view returned {rc}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "roadmap_state.advance_phase fails on incomplete phase" {
  TEST_REPO=$(mktemp -d)
  mkdir -p "$TEST_REPO/.rddf/state"
  ROADMAP_FILE="$TEST_REPO/roadmap.md"
  STATE_FILE="$TEST_REPO/.rddf/state/roadmap-state.json"

  printf '**当前阶段**: phase-1\n\n### Phase 1: test (phase-1)\n**状态**: ⏳ 未开始\n\n#### 任务分类\n| 分类ID | 名称 | 描述 | 优先级 |\n|--------|------|------|--------|\n| infra-setup | 基础设施 | CI/CD 等 | P0 |\n\n### Phase 2: next (phase-2)\n' > "$ROADMAP_FILE"

  PYTHONPATH="$REPO_ROOT" python3 -c "
import os, sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.roadmap_state import init_state, advance_phase
init_state('$STATE_FILE')
rc = advance_phase('$ROADMAP_FILE', '$STATE_FILE')
assert rc == 1, f'advance_phase should fail incomplete, got {rc}'
print('OK')
"
  rm -rf "$TEST_REPO"
}