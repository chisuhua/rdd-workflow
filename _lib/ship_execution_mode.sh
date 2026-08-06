#!/usr/bin/env bash
# skills/_lib/ship_execution_mode.sh
# Per improvements/guide-ship-default-serial-execution.md:
# - Default execution mode = serial (1 concurrent)
# - Opt-in parallel via --parallel flag or RDD_SHIP_PARALLEL=yes
# - CLI flag > env var precedence
# - --max-concurrent=N only effective in parallel mode
#
# Public functions:
#   parse_execution_mode <args...>     -> echo "serial" | "parallel"
#   execute_wave_serial <changes...>  -> runs changes sequentially
#   execute_wave_parallel <changes...> -> runs changes with throttling
#   print_serial_progress <change> <n> <total>  -> per-change progress line

set -euo pipefail

# Default execution mode
DEFAULT_MODE="serial"

# Print usage
_print_usage() {
  cat <<EOF
Usage: ship_execution_mode [options] <subcommand> [args...]

Options:
  --parallel             Enable parallel execution (opt-in)
  --max-concurrent=N     Max parallel workers (default 3, parallel mode only)
  --help                 Show this help

Environment:
  RDD_SHIP_PARALLEL=yes  Equivalent to --parallel flag
  RDD_SHIP_MAX_CONCURRENT=N  Equivalent to --max-concurrent=N

Subcommands:
  parse_execution_mode [args...]   -> echo "serial" or "parallel"
  execute_wave_serial <changes...> -> run changes serially
  execute_wave_parallel <changes...> -> run changes with throttling
EOF
}

# parse_execution_mode -- determine execution mode from args + env
# Returns: "serial" | "parallel"
# Precedence: CLI flag (--parallel) > env var (RDD_SHIP_PARALLEL) > default
parse_execution_mode() {
  local cli_mode=""
  local cli_max_concurrent=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --parallel)
        cli_mode="parallel"
        shift
        ;;
      --max-concurrent=*)
        cli_max_concurrent="${1#*=}"
        shift
        ;;
      --serial)
        cli_mode="serial"
        shift
        ;;
      --help)
        _print_usage
        return 0
        ;;
      *)
        shift
        ;;
    esac
  done

  # CLI flag takes precedence
  if [[ -n "$cli_mode" ]]; then
    echo "$cli_mode"
    return 0
  fi

  # Fall back to env var
  if [[ "${RDD_SHIP_PARALLEL:-}" == "yes" ]]; then
    echo "parallel"
    return 0
  fi

  # Default
  echo "$DEFAULT_MODE"
}

# get_max_concurrent -- resolve max concurrent workers
# CLI flag > env var > default (3)
get_max_concurrent() {
  local max="${RDD_SHIP_MAX_CONCURRENT:-3}"
  echo "$max"
}

# execute_wave_serial -- run changes sequentially with progress output
# Args: list of change names
execute_wave_serial() {
  local total=$#
  local n=0
  for change in "$@"; do
    n=$((n + 1))
    print_serial_progress "$change" "$n" "$total"
    # Caller invokes execute_change here (stub for now)
    execute_change "$change"
  done
}

# execute_wave_parallel -- run changes with throttling
# Args: list of change names
execute_wave_parallel() {
  local max_concurrent
  max_concurrent=$(get_max_concurrent)
  echo "🚀 Wave parallel (${max_concurrent} concurrent)"
  # Caller invokes parallel_executor here (stub)
  # For now, fall through to serial
  execute_wave_serial "$@"
}

# print_serial_progress -- single line per change
# Format: "✓ change-name (n/total)"
print_serial_progress() {
  local change="$1"
  local n="$2"
  local total="$3"
  echo "✓ ${change} (${n}/${total})"
}

# execute_change -- stub for actual change execution
# In production, this calls guide-ship Phase 2 execute for each change
execute_change() {
  local change="$1"
  echo "  → executing ${change}"
}

# print_serial_mode_warning -- warn when --max-concurrent used in serial mode
print_serial_mode_warning() {
  local mode="$1"
  if [[ "$mode" == "serial" ]]; then
    if [[ "${RDD_SHIP_MAX_CONCURRENT:-}" =~ ^[0-9]+$ ]] && [[ "$RDD_SHIP_MAX_CONCURRENT" != "1" ]]; then
      echo "⚠ --max-concurrent ignored in serial mode"
    fi
  fi
}

# Main entry point (when sourced)
# Allows: source ship_execution_mode.sh && parse_execution_mode ...
# Or:    bash ship_execution_mode.sh parse_execution_mode --parallel
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Script invoked directly
  subcmd="${1:-}"
  shift || true
  case "$subcmd" in
    parse_execution_mode|parse)
      parse_execution_mode "$@"
      ;;
    execute_wave_serial|serial)
      execute_wave_serial "$@"
      ;;
    execute_wave_parallel|parallel)
      execute_wave_parallel "$@"
      ;;
    get_max_concurrent|max)
      get_max_concurrent
      ;;
    *)
      _print_usage
      exit 1
      ;;
  esac
fi
