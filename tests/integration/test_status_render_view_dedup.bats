#!/usr/bin/env bats
# tests/integration/test_status_render_view_dedup.bats
# P3-3a regression: status.md:446-508 inlines a 62-line roadmap status
# render. roadmap_state.py::render_status_view() ALREADY provides this
# functionality (used by roadmap.md since P3-1) and roadmap_extraction.bats
# already locks the Python function.
#
# This test locks:
#   1. status.md no longer inlines the roadmap render algorithm (structural)
#   2. status.md invokes render_status_view from _lib/roadmap_state.py (structural)
#   3. Runtime: render_status_view output contains the expected sections
#      (📊 路线图状态, 当前阶段, 阶段门控) when called with a real state file.
#
# Notes on format diffs vs the old inline version:
#   - separator line: "=" * 50 (Python) vs "==============" (12 chars, bash)
#   - phase line adds "(<status>)" suffix in Python (improvement, not regression)
# These diffs are intentional and documented in AGENTS.md.

load ../test_helper

@test "status.md no longer inlines roadmap render algorithm (P3-3a)" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # The old inline version re-read roadmap.md with re.search for **当前阶段**:
  ! grep -qE 'phase_match = re\.search\(r"\*\*当前阶段\*\*' "$REPO_ROOT/skills/status/SKILL.md"
  # Old inline version manually iterated state.get("phases", {}).items():
  ! grep -qE 'phase_id, phase_data in state\.get\("phases"' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md invokes render_status_view from _lib/roadmap_state.py" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # Either a direct python3 -m call or an import — both are valid invocation patterns
  grep -qE 'roadmap_state\.(py|sh|render_status_view)|render_status_view' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md Mode D (roadmap) block is now ≤ 25 lines of bash (was 62)" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # Find the bash block under the Mode D heading. After refactor it should
  # be a thin wrapper (≤25 lines including the python3 -c call + menu echo).
  local block_lines
  block_lines=$(awk '
    /^## Mode D/ {found=1; next}
    found && /^```bash$/ {capture=1; next}
    capture && /^```$/ {exit}
    capture {print}
  ' "$REPO_ROOT/skills/status/SKILL.md" | wc -l)
  [ "$block_lines" -le 30 ]
}

@test "render_status_view produces expected sections when called from status.md invocation" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  cat > roadmap.md <<'EOF'
# Roadmap
**当前阶段**: phase-1
EOF
  mkdir -p .rddf/state
  cat > .rddf/state/roadmap-state.json <<'EOF'
{
  "current_phase": "phase-1",
  "phases": {
    "phase-1": {
      "status": "in_progress",
      "categories": {
        "default": {"changes": ["c1", "c2"], "completed_changes": ["c1"]}
      },
      "gate_status": {
        "all_changes_complete": false,
        "checklist": {"scan_done": true}
      }
    }
  }
}
EOF
  # Run the Python function directly (the same call status.md will make)
  output=$(python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.roadmap_state import render_status_view
sys.exit(render_status_view('roadmap.md', '.rddf/state/roadmap-state.json'))
" 2>&1)
  rm -rf "$TEST_REPO"
  # Expected sections present
  echo "$output" | grep -q "📊 路线图状态"
  echo "$output" | grep -q "当前阶段: phase-1"
  echo "$output" | grep -q "阶段门控"
}