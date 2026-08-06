# Backward-compat shim for old `skills/_lib/discover_ship_changes.sh` path.
# Re-sources the new top-level `_lib/discover_ship_changes.sh` so existing code blocks and
# tests that reference skills/_lib/*.sh keep working.
# Kept for >=6 months per fix-rddf-init-broken-layout proposal.
_PARENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${HOME:?}/.agents/skills/_lib"/discover_ship_changes.sh
