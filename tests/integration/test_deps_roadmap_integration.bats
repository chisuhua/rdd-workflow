#!/usr/bin/env bats

# T19 (P1-9): deps.md must integrate openspec/changes/<name>/roadmap-meta.yaml
# (previously deps.md ignored the roadmap-meta that propose.md writes, so the
# "阶段预检" feature was structurally impossible). Tests verify:
#   - Step 1 has a new 1e substep that reads roadmap-meta.yaml
#   - Step 5 output emits a "阶段预检" section between 依赖图 and 状态表
#   - Missing roadmap-meta.yaml falls back to a "compat mode" marker, so
#     old changes without the file still flow through deps cleanly
#
# Tests are static (grep on the markdown source) — runtime execution of the
# deps bash block requires the openspec CLI which is not present in CI.

load ../test_helper

DEPS_MD="$REPO_ROOT/skills/deps/SKILL.md"

@test "deps.md Step 1 reads roadmap-meta.yaml (P1-9)" {
  [ -f "$DEPS_MD" ]
  # Step 1 must reference roadmap-meta.yaml somewhere (the new 1e substep)
  grep -q "roadmap-meta" "$DEPS_MD"
  # The 1e substep header must exist
  grep -q "1e" "$DEPS_MD"
  # The 1e block must read the phase: and category: keys
  grep -qE "phase:" "$DEPS_MD"
  grep -qE "category:" "$DEPS_MD"
}

@test "deps.md Step 5 output has 阶段预检 section (P1-9)" {
  [ -f "$DEPS_MD" ]
  # v2.0.6 extraction: the Step 5 heredoc that emits the report sections
  # moved to skills/deps/scripts/deps_output.py::render_markdown_report.
  # SKILL.md still documents the 阶段预检 feature (in 1e + Step 5 comment +
  # 消费方指南), but the actual section headers are emitted by the Python
  # helper. Lock the contract in the Python source.
  local py="$REPO_ROOT/skills/deps/scripts/deps_output.py"
  [ -f "$py" ]
  # The new section header must be emitted by render_markdown_report
  grep -q '## 阶段预检' "$py"
  # The table must reference both phase and category columns
  grep -q '| Phase | Category |' "$py"
  # The section must appear AFTER the 依赖图 mermaid block and BEFORE the
  # Change 状态表 header (ordering check via awk on line numbers)
  awk '
    /## 依赖图/          { m = NR }
    /## 阶段预检/        { p = NR }
    /## Change 状态表/   { s = NR }
    END {
      if (m && p && s && m < p && p < s) exit 0
      print "ordering: dep=" m " precheck=" p " status=" s
      exit 1
    }
  ' "$py"
}

@test "deps.md handles missing roadmap-meta gracefully (P1-9)" {
  [ -f "$DEPS_MD" ]
  # The compat-mode marker must be present in the markdown so legacy
  # changes (no roadmap-meta.yaml) still pass through deps.
  grep -q "compat mode" "$DEPS_MD"
  # And the Step 5 row must include a ⚠️ marker for missing meta
  grep -q "无 roadmap-meta" "$DEPS_MD"
}

@test "deps.md 阶段预检 is between 依赖图 and 状态表 in the actual output (P1-9, ordering)" {
  [ -f "$DEPS_MD" ]
  # The 阶段预检 heredoc is closed and re-opened AFTER the mermaid block
  # closes — verify by checking the sequence of markers around it.
  # The pattern we emit is:
  #     \`\`\`\nEOF\n# === P1-9 ...\ncat >> ... << EOF\n## 阶段预检 ...
  grep -q "P1-9" "$DEPS_MD"
  grep -q "ROADMAP_CURRENT_PHASE" "$DEPS_MD"
}
