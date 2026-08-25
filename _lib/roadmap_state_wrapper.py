"""Thin env-var consuming wrapper for roadmap_state CLI invocations.

Routes to the appropriate function based on env vars set by the shell wrapper.
"""
import os
import sys
import traceback


def main():
    project_root = os.environ.get("PROJECT_ROOT", ".")
    change_name = os.environ.get("CHANGE_NAME")
    phase_refs_raw = os.environ.get("PHASE_REFS", "")
    theme = os.environ.get("THEME", "")
    status = os.environ.get("STATUS", "active")
    force = os.environ.get("FORCE", "false").lower() == "true"

    if not change_name:
        print("ERROR: CHANGE_NAME env var not set", file=sys.stderr)
        sys.exit(2)

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
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    print(f"OK created: {result['path']}")
    print(f"OK main doc refreshed: {result['main_doc_refreshed']}")


if __name__ == "__main__":
    main()