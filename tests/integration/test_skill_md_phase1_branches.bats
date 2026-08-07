#!/usr/bin/env bats
# Integration test for guide-design/SKILL.md Phase 1 branch logic
# Extracts the bash code block from SKILL.md and exercises each branch.

load ../test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/skillmd-$$"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
}

teardown() { rm -rf "$PROJECT_ROOT"; }

# Extract the Phase 1 branch-logic code block from SKILL.md and substitute paths
extract_phase1_block() {
  sed -n '/^```bash$/,/^```$/p' "$REPO_ROOT/skills/guide-design/SKILL.md" | \
    awk '/^```bash$/{flag=1; next} /^```$/{flag=0} flag' | \
    grep -A1000 'diagnostic' | head -60
}

@test "SKILL.md Phase 1: structural check — branch logic code block exists" {
  # Verify the SKILL.md contains the expected diagnostic-first + branch structure
  grep -q "design_preflight.sh" "$REPO_ROOT/skills/guide-design/SKILL.md"
  grep -q "design_preflight_status" "$REPO_ROOT/skills/guide-design/SKILL.md"
  grep -q 'soft_prompt_reconstruct' "$REPO_ROOT/skills/guide-design/SKILL.md"
  grep -q 'hard_reject_no_evidence' "$REPO_ROOT/skills/guide-design/SKILL.md"
  grep -q 'reconstruct_arch_handoff.sh' "$REPO_ROOT/skills/guide-design/SKILL.md"
}

@test "SKILL.md Phase 1: hard_reject branch blocks when no evidence" {
  # No arch-handoff, no ADRs, no roadmap → hard_reject_no_evidence
  run bash -c '
    set -euo pipefail
    source "$1/skills/guide-design/scripts/design_preflight.sh"
    PREFLIGHT_STATUS=$(design_preflight_status "$2")
    RECOMMENDATION=$(echo "$PREFLIGHT_STATUS" | jq -r ".recommendation")
    if [ "$RECOMMENDATION" = "hard_reject_no_evidence" ]; then
      echo "❌ arch-done 未完成，无法进入 design 阶段"
      exit 1
    fi
  ' _ "$REPO_ROOT" "$PROJECT_ROOT"

  [ "$status" -ne 0 ]
  echo "$output" | grep -q "arch-done 未完成"
}

@test "SKILL.md Phase 1: normal branch proceeds when arch-handoff exists" {
  # arch-handoff present → normal → no exit, no error message
  echo '{"version":1,"discovered":{"adr_dir":{"found":true,"created":false,"candidates_tried":1}}}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"

  run bash -c '
    set -euo pipefail
    source "$1/skills/guide-design/scripts/design_preflight.sh"
    PREFLIGHT_STATUS=$(design_preflight_status "$2")
    RECOMMENDATION=$(echo "$PREFLIGHT_STATUS" | jq -r ".recommendation")
    if [ "$RECOMMENDATION" = "normal" ]; then
      echo "proceed"
      exit 0
    else
      echo "unexpected: $RECOMMENDATION"
      exit 1
    fi
  ' _ "$REPO_ROOT" "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  echo "$output" | grep -q "proceed"
}

@test "SKILL.md Phase 1: soft_prompt branch + choice 1 invokes reconstruction" {
  # ADRs + roadmap exist, no handoff → soft_prompt_reconstruct
  mkdir -p "$PROJECT_ROOT/docs/adr"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  touch "$PROJECT_ROOT/roadmap.md"

  # Provide stdin "1" to choose reconstruction
  run bash -c '
    set -euo pipefail
    source "$1/skills/guide-design/scripts/design_preflight.sh"
    PREFLIGHT_STATUS=$(design_preflight_status "$2")
    RECOMMENDATION=$(echo "$PREFLIGHT_STATUS" | jq -r ".recommendation")
    if [ "$RECOMMENDATION" = "soft_prompt_reconstruct" ]; then
      echo "⚠️  arch-handoff 缺失但历史证据显示 arch-done 已完成" >&2
      read -r -p "选择 [1/2/3]: " recon_choice
      case "$recon_choice" in
        1) bash "$1/skills/guide-design/scripts/reconstruct_arch_handoff.sh" --force --project-root "$2" ;;
        *) exit 0 ;;
      esac
    fi
  ' _ "$REPO_ROOT" "$PROJECT_ROOT" <<< "1"

  [ "$status" -eq 0 ]
  [ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]
  jq -e '.reconstructed_from == "filesystem-evidence"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
}

@test "SKILL.md Phase 1: soft_prompt branch + choice 3 exits without reconstruction" {
  mkdir -p "$PROJECT_ROOT/docs/adr"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  touch "$PROJECT_ROOT/roadmap.md"

  run bash -c '
    set -euo pipefail
    source "$1/skills/guide-design/scripts/design_preflight.sh"
    PREFLIGHT_STATUS=$(design_preflight_status "$2")
    RECOMMENDATION=$(echo "$PREFLIGHT_STATUS" | jq -r ".recommendation")
    if [ "$RECOMMENDATION" = "soft_prompt_reconstruct" ]; then
      read -r -p "选择 [1/2/3]: " recon_choice
      case "$recon_choice" in
        1) bash "$1/skills/guide-design/scripts/reconstruct_arch_handoff.sh" --force --project-root "$2" ;;
        2) exit 1 ;;
        *) echo "已退出"; exit 0 ;;
      esac
    fi
  ' _ "$REPO_ROOT" "$PROJECT_ROOT" <<< "3"

  [ "$status" -eq 0 ]
  echo "$output" | grep -q "已退出"
  [ ! -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]
}
