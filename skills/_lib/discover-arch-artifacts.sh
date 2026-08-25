# Backward-compat shim for old `skills/_lib/discover-arch-artifacts.sh` path.
# Re-sources the new top-level `_lib/discover-arch-artifacts.sh` so existing code blocks and
# tests that reference skills/_lib/*.sh keep working.
# Kept for >=6 months per fix-rddf-init-broken-layout proposal.
_PARENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# FIX (2026-08-25): prefer local repo copy first to avoid silent staleness
# in worktree mode (.rddf/wt/<change>) where ~/.agents/skills/_lib symlink
# points to main repo, not the worktree. Falls back to global install path.
if [ -f "${_PARENT_DIR}/_lib/discover-arch-artifacts.sh" ]; then
  source "${_PARENT_DIR}/_lib/discover-arch-artifacts.sh"
else
  source "${HOME:?}/.agents/skills/_lib"/discover-arch-artifacts.sh
fi
