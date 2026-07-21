#!/usr/bin/env bash
# ship_parallel.sh - parallel change execution with throttling
source "$(dirname "${BASH_SOURCE[0]:-$0}")/parallel_throttle.sh"

DEFAULT_MAX_CONCURRENT=3

parse_parallel_args() {
    local max_conc="$DEFAULT_MAX_CONCURRENT"
    while [ $# -gt 0 ]; do
        case "$1" in
            --max-concurrent=*)
                max_conc="${1#*=}"
                ;;
            --max-concurrent)
                shift; max_conc="${1:-$DEFAULT_MAX_CONCURRENT}"
                ;;
        esac
        shift
    done
    echo "$max_conc"
}
