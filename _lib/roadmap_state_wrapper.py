"""Thin env-var consuming wrapper for roadmap_state CLI invocations.

Routes to the appropriate function based on MODE env var set by the shell wrapper:
  - MODE=add-feature (default) — calls add_feature()
  - MODE=list-features — calls list_features()
  - MODE=update-agent-md — calls update_agent_md()
  - MODE=refresh-fragments — calls render_fragment_index + update_agent_md
"""
import os
import sys
import traceback
from pathlib import Path

# Co-located with _lib/roadmap_state.py; add repo root so `from _lib import` works
# even when PROJECT_ROOT points at a temp test repo without _lib/.
_LIB_PARENT = str(Path(__file__).resolve().parent.parent)
if _LIB_PARENT not in sys.path:
    sys.path.insert(0, _LIB_PARENT)


def _mode_add_feature(project_root: str) -> int:
    change_name = os.environ.get("CHANGE_NAME")
    phase_refs_raw = os.environ.get("PHASE_REFS", "")
    theme = os.environ.get("THEME", "")
    status = os.environ.get("STATUS", "active")
    force = os.environ.get("FORCE", "false").lower() == "true"

    if not change_name:
        print("ERROR: CHANGE_NAME env var not set", file=sys.stderr)
        return 2

    phase_refs = [p.strip() for p in phase_refs_raw.split(",") if p.strip()]

    sys.path.insert(0, project_root)
    from _lib.roadmap_state import add_feature

    try:
        result = add_feature(
            name=change_name,
            phase_refs=phase_refs,
            theme=theme,
            status=status,
            force=force,
            project_root=project_root,
        )
    except (ValueError, FileExistsError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception:
        traceback.print_exc()
        return 1

    print(f"OK created: {result['path']}")
    print(f"OK main doc refreshed: {result['main_doc_refreshed']}")
    return 0


def _mode_list_features(project_root: str) -> int:
    fmt = os.environ.get("FMT", "table")
    fragments_dir = os.environ.get("FRAGMENTS_DIR") or os.path.join(
        project_root, ".rddf", "roadmap"
    )
    if not os.path.isabs(fragments_dir):
        fragments_dir = os.path.join(project_root, fragments_dir)

    sys.path.insert(0, project_root)
    from _lib.roadmap_state import list_features

    try:
        out = list_features(fragments_dir, fmt=fmt)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 1
    print(out, end="" if out.endswith("\n") else "\n")
    return 0


def _mode_update_agent_md(project_root: str) -> int:
    agents_md_path = os.environ.get("AGENTS_MD_PATH") or "AGENTS.md"
    fragments_dir = os.environ.get("FRAGMENTS_DIR") or ".rddf/roadmap"

    sys.path.insert(0, project_root)
    from _lib.roadmap_state import update_agent_md

    try:
        result = update_agent_md(
            project_root=project_root,
            agents_md_path=agents_md_path,
            fragments_dir=fragments_dir,
        )
    except Exception:
        traceback.print_exc()
        return 1

    verb = "inserted" if result["inserted"] else "updated"
    print(
        f"OK AGENTS.md {verb}: {result['feature_count']} feature fragments rendered"
    )
    return 0


def _mode_refresh_fragments(project_root: str) -> int:
    """Refresh both .rddf/roadmap.md AUTO-INDEX + AGENTS.md AUTO block.

    Per add-refresh-fragments-cli (2026-10-08, post-rdd-doctor-coverage-completion):
    avoids manual sync drift surfaced by `rdd-doctor roadmap-feature` check.

    Env vars:
      MAIN_DOC_PATH   override default .rddf/roadmap.md
      AGENTS_MD_PATH  override default AGENTS.md
      FRAGMENTS_DIR   override default .rddf/roadmap
    """
    from pathlib import Path

    main_doc_path = os.environ.get("MAIN_DOC_PATH") or ".rddf/roadmap.md"
    agents_md_path = os.environ.get("AGENTS_MD_PATH") or "AGENTS.md"
    fragments_dir = os.environ.get("FRAGMENTS_DIR") or ".rddf/roadmap"

    if not Path(fragments_dir).is_absolute():
        fragments_dir = str(Path(project_root) / fragments_dir)
    if not Path(main_doc_path).is_absolute():
        main_doc_path = str(Path(project_root) / main_doc_path)
    if not Path(agents_md_path).is_absolute():
        agents_md_path = str(Path(project_root) / agents_md_path)

    sys.path.insert(0, project_root)
    from _lib.roadmap_state import render_fragment_index, update_agent_md

    try:
        render_fragment_index(fragments_dir, main_doc_path)
        result = update_agent_md(
            project_root=project_root,
            agents_md_path=agents_md_path,
            fragments_dir=fragments_dir,
        )
    except Exception:
        traceback.print_exc()
        return 1

    print(f"OK {main_doc_path} refreshed")
    verb = "inserted" if result["inserted"] else "updated"
    print(f"OK {agents_md_path} {verb}: {result['feature_count']} feature fragments rendered")
    return 0

    try:
        render_fragment_index(fragments_dir, main_doc_path)
        result = update_agent_md(
            project_root=project_root,
            agents_md_path=agents_md_path,
            fragments_dir=fragments_dir,
        )
    except Exception:
        traceback.print_exc()
        return 1

    print(f"OK {main_doc_path} refreshed")
    verb = "inserted" if result["inserted"] else "updated"
    print(f"OK {agents_md_path} {verb}: {result['feature_count']} feature fragments rendered")
    return 0


def main():
    project_root = os.environ.get("PROJECT_ROOT", ".")
    mode = os.environ.get("MODE", "add-feature")

    if mode == "list-features":
        sys.exit(_mode_list_features(project_root))
    elif mode == "update-agent-md":
        sys.exit(_mode_update_agent_md(project_root))
    elif mode == "refresh-fragments":
        sys.exit(_mode_refresh_fragments(project_root))
    else:
        sys.exit(_mode_add_feature(project_root))


if __name__ == "__main__":
    sys.exit(main())