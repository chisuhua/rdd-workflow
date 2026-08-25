# Design: Submodule-Aware Project Root Resolution

**Change**: submodule-aware-project-root
**ADR**: ADR-0033
**Phase**: v2.2 | **Category**: core-impl | **Priority**: P0
**Date**: 2026-08-25

## Architecture Reference

Full architectural decision: [ADR-0033](../../../docs/adr/ADR-0033-submodule-aware-project-root-resolution.md)
Source proposal: [.rddf/improvements/submodule-aware-project-root.md](../../../.rddf/improvements/submodule-aware-project-root.md)

## Technical Approach

### Detection Function Pattern

**Bash** (用于 `_lib/worktree.sh::main_repo_root()`):
```bash
main_repo_root() {
  local superproject
  superproject=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
  if [ -n "$superproject" ]; then
    # Submodule: --show-toplevel returns the submodule's own working tree root
    git rev-parse --show-toplevel 2>/dev/null || pwd
    return
  fi
  # Original worktree / main-repo logic (preserved for P0-8 contract)
  local common_dir
  common_dir=$(git rev-parse --git-common-dir 2>/dev/null) || { pwd; return; }
  case "$common_dir" in
    /*) ;;
    *) common_dir="$(pwd)/$common_dir" ;;
  esac
  case "$common_dir" in
    */.git) dirname "$common_dir" ;;
    */.git/worktrees/*) dirname "$(dirname "$common_dir")" ;;
    *) dirname "$common_dir" ;;
  esac
}
```

**Python** (用于 `_lib/cli/__main__.py::resolve_project_root()` 和 `_is_in_worktree()`):
```python
def resolve_project_root() -> str:
    # Submodule-aware priority: --show-toplevel wins in submodule
    try:
        r_super = subprocess.run(
            ["git", "rev-parse", "--show-superproject-working-tree"],
            capture_output=True, text=True, timeout=10,
        )
        if r_super.returncode == 0 and r_super.stdout.strip():
            r_toplevel = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10,
            )
            if r_toplevel.returncode == 0 and r_toplevel.stdout.strip():
                return os.path.abspath(r_toplevel.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Existing worktree / main-repo logic (preserved)
    ...
```

### Behavior Matrix (post-fix)

| Context | `--show-superproject-working-tree` | Branch | Returns |
|---------|-----------------------------------|--------|---------|
| Main repo | empty | worktree (`--git-common-dir`) | main repo root |
| Linked worktree | empty | worktree (`--git-common-dir`) | main repo root |
| Git submodule | non-empty | submodule (`--show-toplevel`) | submodule own root |
| Nested submodule | non-empty | submodule (`--show-toplevel`) | submodule own root |
| Non-git dir | (cmd fails) | fallback | `pwd` |

### File Changes Summary

1. **`_lib/worktree.sh:67` `main_repo_root()`** — Add submodule detection at function entry
2. **`_lib/cli/__main__.py:39` `resolve_project_root()`** — Add submodule detection before worktree branch
3. **`_lib/cli/__main__.py:82` `_is_in_worktree()`** — Return False immediately when in submodule
4. **`_lib/cli/validate_cmd.py:63`** — Change `--git-dir` to `--show-toplevel` for git repo check
5. **`skills/execute/scripts/select_worktree.sh:52,54`** — Update containment check to use `--show-toplevel`
6. **5 处 `--git-dir` 用法** (`install.sh:349`, `roadmap_migrate.sh:176`, `archive_on_main.sh:90`, `deploy.sh:69`, `_lib/cli/__main__.py:98`) — Add comments documenting submodule behavior; semantics still correct

### Why This Design

- **Detects via `--show-superproject-working-tree`** (non-empty = submodule): Standard git flag, supported in 2.25+ (2019 release, well below project's 2.25+ baseline)
- **Returns via `--show-toplevel`** in submodule: Consistent with ~200 existing `--show-toplevel` call sites that already work correctly in submodule
- **Preserves `--git-common-dir` for non-submodule**: P0-8 contract maintained, no worktree regression
- **Idempotent and pure**: No state, no caching, deterministic result
- **POSIX bash + Python**: Matches existing `_lib/worktree.sh` (POSIX) and `_lib/cli/*.py` (subprocess.run) style

### Constraints Preserved

- `main_repo_root()` P0-8 contract (worktree → main repo root) preserved by NOT changing the worktree branch
- `--show-toplevel` 200+ existing call sites unaffected (they were already submodule-correct)
- No new dependencies (git 2.25+ + Python 3.11+ only)
- No schema changes
- No Oracle C1 bash `$VAR` injection (env-var pattern only)