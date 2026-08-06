# Backward-compat shim for old `skills/_lib/ship_execution_mode.sh` path.
# Re-sources the new top-level `_lib/ship_execution_mode.sh` so existing code blocks and
# tests that reference skills/_lib/*.sh keep working.
# Kept for >=6 months per fix-rddf-init-broken-layout proposal.
_PARENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${HOME:?}/.agents/skills/_lib"/ship_execution_mode.sh
