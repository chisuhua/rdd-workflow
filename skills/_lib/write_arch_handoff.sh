#!/usr/bin/env bash
# skills/_lib/write_arch_handoff.sh — extracted from guide-arch.md L618-L707
# Exports: write_arch_handoff()
#
# Re-runs ADR-0016 artifact discovery (if helper available) and writes
# .rddf/state/.arch-handoff.json via the Python helper.
#
# Oracle C1: env-var only passing, no bash string interpolation into python.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

write_arch_handoff() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT

  # Re-run discovery to ensure latest values (Phase 5 idempotency)
  if [ -f "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh" ]; then
      source "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh"
      discover_adr_dir          >/dev/null
      discover_roadmap          >/dev/null
      discover_architecture_dir >/dev/null
      discover_adr_pattern      >/dev/null
  fi

  mkdir -p "$PROJECT_ROOT/.rddf/state"

  # Compute ROADMAP_EXISTS_BOOL from filesystem (don't rely on env var — may not propagate
  # between bash code blocks in markdown). DISCOVERED_ROADMAP_PATH is set by discover_roadmap
  # call in this same function above.
  ROADMAP_EXISTS_BOOL=$([ -f "$PROJECT_ROOT/${DISCOVERED_ROADMAP_PATH}" ] && echo "true" || echo "false")

  # Delegate to Python helper via env-var passing only (Oracle C1: no bash string interp)
  PROJECT_ROOT="$PROJECT_ROOT" \
  DISCOVERED_ADR_DIR="$DISCOVERED_ADR_DIR" \
  DISCOVERED_ROADMAP_PATH="$DISCOVERED_ROADMAP_PATH" \
  DISCOVERED_ARCHITECTURE_DIR="$DISCOVERED_ARCHITECTURE_DIR" \
  DISCOVERED_ADR_PATTERN="$DISCOVERED_ADR_PATTERN" \
  DISCOVERED_ADR_DIR_FOUND="${DISCOVERED_ADR_DIR_FOUND:-false}" \
  DISCOVERED_ROADMAP_FOUND="${DISCOVERED_ROADMAP_FOUND:-false}" \
  DISCOVERED_ARCH_FOUND="${DISCOVERED_ARCH_FOUND:-false}" \
  DISCOVERED_ADR_DIR_TRIED="${DISCOVERED_ADR_DIR_TRIED:-0}" \
  DISCOVERED_ROADMAP_TRIED="${DISCOVERED_ROADMAP_TRIED:-0}" \
  DISCOVERED_ARCH_TRIED="${DISCOVERED_ARCH_TRIED:-0}" \
  ROADMAP_EXISTS_BOOL="$ROADMAP_EXISTS_BOOL" \
  python3 "$SCRIPT_DIR/write_arch_handoff_env.py"
}