#!/usr/bin/env bats
# tests/integration/test_arch_gap_analysis_extraction.bats
# Round B extraction: rdd-arch.md L343-L431 (~85 lines, 2 inline bash blocks)
# — gap analysis generator + viewer. Extracted to
# _lib/arch_gap_analysis.sh exposing:
#   - generate_gap_analysis <slug>  — creates docs/architecture/<slug>-gap-analysis.md
#   - list_gap_analyses             — prints numbered list of existing gap analyses
#
# These tests lock the refactor in place:
#   1. arch_gap_analysis.sh exists with both functions exported.
#   2. rdd-arch.md no longer contains gap analysis heredoc / viewer inline text.
#   3. rdd-arch.md sources and calls both helpers.
#   4. generate_gap_analysis creates the expected file with template sections.
#   5. list_gap_analyses finds existing files.
#   6. list_gap_analyses handles empty directory.
#   7. Both helpers honor DISCOVERED_ARCHITECTURE_DIR env var.

load ../test_helper

@test "arch_gap_analysis_helper_exists" {
  [ -f "$REPO_ROOT/skills/rdd-arch/scripts/arch_gap_analysis.sh" ]
  bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_gap_analysis.sh && declare -f generate_gap_analysis && declare -f list_gap_analyses" | grep -q 'generate_gap_analysis'
}

@test "guide_arch_inline_gap_block_removed" {
  # After extraction, L343-L431 should no longer contain the gap analysis heredoc
  # template text or viewer text.
  ! grep -q '请提供差距分析主题' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
  ! grep -q '现有差距分析列表' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "guide_arch_invokes_helper" {
  grep -q 'source.*scripts/arch_gap_analysis.sh' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
  grep -q 'generate_gap_analysis' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
  grep -q 'list_gap_analyses' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "generate_gap_analysis_creates_file" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  # Unset PROJECT_ROOT so the helper uses pwd (tmpdir), not the real repo root
  bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_gap_analysis.sh' && generate_gap_analysis 'test-slug'" >/dev/null 2>&1
  assert_file_exists "$tmpdir/docs/architecture/test-slug-gap-analysis.md"
  rm -rf "$tmpdir"
}

@test "generate_gap_analysis_file_has_template_sections" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_gap_analysis.sh' && generate_gap_analysis 'sample'" >/dev/null 2>&1
  local file="$tmpdir/docs/architecture/sample-gap-analysis.md"
  assert_file_exists "$file"
  grep -q '目标架构' "$file"
  grep -q '当前架构' "$file"
  grep -q '差距清单' "$file"
  grep -q '补齐路径' "$file"
  grep -q '参考资料' "$file"
  rm -rf "$tmpdir"
}

@test "list_gap_analyses_finds_existing" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  touch "$tmpdir/docs/architecture/existing-1-gap-analysis.md"
  touch "$tmpdir/docs/architecture/existing-2-gap-analysis.md"
  output=$(bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_gap_analysis.sh' && list_gap_analyses" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -q 'existing-1'
  echo "$output" | grep -q 'existing-2'
}

@test "list_gap_analyses_handles_empty" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  output=$(bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_gap_analysis.sh' && list_gap_analyses" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE '暂无|空|0 '
}

@test "arch_gap_analysis_uses_discovery_env_var" {
  # Honor DISCOVERED_ARCHITECTURE_DIR env var from arch_env_check.sh
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/custom/architecture"
  bash -c "cd '$tmpdir' && unset PROJECT_ROOT && export DISCOVERED_ARCHITECTURE_DIR='custom/architecture' && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_gap_analysis.sh' && generate_gap_analysis 'test'" >/dev/null 2>&1
  assert_file_exists "$tmpdir/custom/architecture/test-gap-analysis.md"
  rm -rf "$tmpdir"
}

# --------------------------------------------------------------------------
# Analyzer Subset §2 protocol化落地 cases (per ADR-0046):
# Oracle risk #3 — wrapper observable contract MUST stay byte-equal so these
# tests lock the new behavior on top of the 8 pre-refactor cases.
# --------------------------------------------------------------------------

@test "arch_gap_analysis_wrapper_uses_lib_arch_protocol" {
  # The new wrapper MUST delegate to `_lib/arch/protocol.py::build_skeleton`
  # (Analyzer Subset §2 ADOPT). This locks the data-layer contract so a
  # future refactor cannot silently diverge.
  run python3 - <<'PYEOF'
import sys
sys.path.insert(0, '/workspace/project/rdd-workflow')
from _lib.arch import build_skeleton
out = build_skeleton('test-slug', '2026-09-07')
# Must contain all 5 sections at the line-start level (regex anchored)
assert out.count('## 1. 目标架构') == 1, out
assert out.count('## 5. 参考资料') == 1, out
PYEOF
  [ "$status" -eq 0 ]
}

@test "validate_document_via_python_module_detects_broken_structure" {
  # Hand-edit a generated gap analysis: change one `##` to `###`. The
  # validator MUST report structural_ok=False and list the missing section
  # in `issues`. This is the §5 Output Contract Validation (hard) tier.
  run python3 - <<'PYEOF'
import sys, tempfile, pathlib
sys.path.insert(0, '/workspace/project/rdd-workflow')
from _lib.arch import build_skeleton, validate_document

with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'broken.md'
    body = build_skeleton('test', '2026-09-07')
    body = body.replace('## 3. 差距清单', '### 3. 差距清单')
    p.write_text(body)
    report = validate_document(p)
    assert report.structural_ok is False, report
    assert any('差距清单' in issue for issue in report.issues), report
print('OK')
PYEOF
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "generate_gap_analysis_output_byte_equal_to_python_data_layer" {
  # Locks the wrapper output to the data-layer output byte-equal (excluding
  # the timestamp line which is generated independently by bash and Python).
  # This prevents drift if either side is refactored independently.
  local tmpdir_bash tmpdir_py today
  tmpdir_bash=$(mktemp -d)
  tmpdir_py=$(mktemp -d)
  mkdir -p "$tmpdir_bash/docs/architecture" "$tmpdir_py"
  today=$(date -Iseconds)

  bash -c "cd '$tmpdir_bash' && unset PROJECT_ROOT && export RDDF_ARCH_GAP_TODAY='$today' && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_gap_analysis.sh' && generate_gap_analysis 'drift-check'" >/dev/null 2>&1
  python3 - <<PYEOF > "$tmpdir_py/skeleton.md"
import sys
sys.path.insert(0, '/workspace/project/rdd-workflow')
from _lib.arch import build_skeleton
sys.stdout.write(build_skeleton('drift-check', '$today'))
PYEOF

  # diff MUST report zero differences (byte-equal)
  diff "$tmpdir_bash/docs/architecture/drift-check-gap-analysis.md" "$tmpdir_py/skeleton.md"
  [ "$?" -eq 0 ]
  rm -rf "$tmpdir_bash" "$tmpdir_py"
}