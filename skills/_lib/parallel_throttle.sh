#!/usr/bin/env bash
# parallel_throttle.sh - concurrent execution limiter
# Provides throttle_acquire and throttle_release for parallel job control.
#
# Usage:
#   source parallel_throttle.sh
#   throttle_acquire <max_concurrent>
#   (your parallel job) &
#   throttle_release

_THROTTLE_SLOTS=0
_THROTTLE_MAX=0

throttle_acquire() {
    local max_concurrent="${1:-3}"

    _THROTTLE_MAX=$max_concurrent

    while [ "$_THROTTLE_SLOTS" -ge "$_THROTTLE_MAX" ]; do
        wait -n 2>/dev/null || true
        _THROTTLE_SLOTS=$((_THROTTLE_SLOTS - 1))
        [ "$_THROTTLE_SLOTS" -lt 0 ] && _THROTTLE_SLOTS=0
    done

    _THROTTLE_SLOTS=$((_THROTTLE_SLOTS + 1))
}

throttle_release() {
    true
}

throttle_drain() {
    while [ "${_THROTTLE_SLOTS:-0}" -gt 0 ]; do
        wait -n 2>/dev/null || true
        _THROTTLE_SLOTS=$((_THROTTLE_SLOTS - 1))
    done
}
