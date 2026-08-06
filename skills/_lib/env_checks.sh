# Backward-compat shim for old `skills/_lib/env_checks.sh` path.
# Re-sources the new top-level `_lib/env_checks.sh` so existing code blocks and
# tests that reference skills/_lib/*.sh keep working.
# Kept for >=6 months per fix-rddf-init-broken-layout proposal.
_PARENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$_PARENT_DIR/_lib/env_checks.sh"
