"""skills/_lib/propose_change.py — helpers for propose.md Phase 4.

Extracted from inline PYEOF heredocs in propose.md lines 443-796
(P0-1 refactor, Metis plan 2026-07-16). Each function preserves the
exact behavior of the corresponding inline block, including output
strings and exception handling.
"""

import json
import os
from typing import Optional


def set_suggestion_status(
    project_root: str, name: str, new_status: str
) -> bool:
    """Update status field for matching entry in proposal-suggestions.md.

    Returns True if updated, False if file missing / malformed / name not found.
    Preserves all other fields. Matches original lines 531-548 inline behavior.
    """
    path = os.path.join(project_root, "proposal-suggestions.md")
    try:
        with open(path) as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    if not isinstance(entries, list):
        return False
    updated = False
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name") == name:
            entry["status"] = new_status
            updated = True
    if updated:
        try:
            with open(path, "w") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError:
            return False
    return updated


def create_skeleton_change(
    project_root: str,
    name: str,
    current_phase: str,
    category: str,
    priority: str,
) -> bool:
    """Create minimal skeleton artifacts for a change (propose.md lines 486-551).

    Writes:
    - openspec/changes/<name>/proposal.md (Why + What Changes skeleton)
    - openspec/changes/<name>/roadmap-meta.yaml
    - iteration.json (status=planned) — graceful skip on ImportError

    Returns True on full success, False if proposal/yaml write failed.
    Matches original inline behavior exactly, including:
    - openspec new change call (best-effort, swallows errors)
    - All output strings ("📦 Skeleton mode:", "  ✅ iteration.json updated:",
      "⚠️  iteration.json update failed (non-fatal):")
    """
    import os
    import subprocess
    import sys

    change_dir = os.path.join(project_root, "openspec", "changes", name)
    os.makedirs(change_dir, exist_ok=True)

    # openspec new change (best-effort, matches original)
    subprocess.run(
        ["openspec", "new", "change", name],
        cwd=project_root,
        capture_output=True,
    )

    # Write minimal proposal.md
    proposal_path = os.path.join(change_dir, "proposal.md")
    try:
        with open(proposal_path, "w") as f:
            f.write("## Why\n\n")
            f.write("<skeleton motivation - 1-2 sentences>\n\n")
            f.write("## What Changes\n\n")
            f.write("- <file path or module affected>\n")
            f.write("- <file path or module affected>\n")
    except OSError:
        return False

    # Write minimal roadmap-meta.yaml
    yaml_path = os.path.join(change_dir, "roadmap-meta.yaml")
    try:
        with open(yaml_path, "w") as f:
            f.write('roadmap:\n')
            f.write(f'  phase: "{current_phase}"\n')
            f.write(f'  category: "{category}"\n')
            f.write(f'  priority: "{priority}"\n')
            f.write(f'  gate_checklist: []\n')
            f.write(f'  cross_phase_deps: []\n')
            f.write(f'  manual_deps: []\n')
            f.write(f'  manual_blocks: []\n')
            f.write(f'  category_validation:\n')
            f.write(f'    valid: true\n')
            f.write(f'    reason: ""\n')
    except OSError:
        return False

    # Update iteration.json (graceful skip)
    try:
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        data = it_mod.add_or_update_change(
            data,
            name=name,
            status="planned",
            phase=None,
            category=None,
            priority=None,
        )
        it_mod.save(project_root, data)
        print(f"  ✅ iteration.json updated: {name} status=planned")
    except ImportError as e:
        print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  iteration.json update failed (non-fatal): {e}", file=sys.stderr)

    print(f"✅ Skeleton created: {name}")
    return True

def update_roadmap_meta(
    project_root: str,
    name: str,
    current_phase: str,
    change_category: str,
    priority: str,
    valid_categories: str,
) -> bool:
    """Update roadmap-meta.yaml for a change (propose.md lines 617-686).

    Looks up phase/category from proposal-suggestions.md, falls back to
    arguments. ALWAYS falls back to 'general' on invalid category (matches
    original inline behavior at line 671 which hard-codes
    CHANGE_CATEGORY='general' regardless of valid_categories).
    Returns False if openspec/changes/<name>/ doesn't exist or yaml write fails.
    """
    import os
    change_dir = os.path.join(project_root, "openspec", "changes", name)
    if not os.path.isdir(change_dir):
        return False

    # Lookup phase/category from proposal-suggestions.md (matches lines 622-658)
    suggestions_path = os.path.join(project_root, "proposal-suggestions.md")
    lookup_phase = current_phase
    lookup_category = change_category
    try:
        with open(suggestions_path) as f:
            entries = json.load(f)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and entry.get("name") == name:
                    if entry.get("phase"):
                        lookup_phase = entry["phase"]
                    if entry.get("category"):
                        lookup_category = entry["category"]
                    break
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # fall back to arguments

    # Validate category (matches lines 660-672)
    valid_cat_set = set()
    for line in (valid_categories or "").split("\n"):
        if ":" in line:
            valid_cat_set.add(line.split(":")[0].strip())

    if lookup_category not in valid_cat_set:
        # ALWAYS fallback to "general" regardless of valid_categories content.
        # Matches original inline behavior at propose.md line 671.
        print(
            f"⚠️  Change '{name}' 的分类 '{lookup_category}' "
            f"不在当前阶段 '{current_phase}' 的有效分类中"
        )
        print(f"   有效分类: {' '.join(sorted(valid_cat_set))}")
        lookup_category = "general"

    # Write roadmap-meta.yaml (matches lines 675-685)
    yaml_path = os.path.join(change_dir, "roadmap-meta.yaml")
    try:
        with open(yaml_path, "w") as f:
            f.write('roadmap:\n')
            f.write(f'  phase: "{lookup_phase}"\n')
            f.write(f'  category: "{lookup_category}"\n')
            f.write(f'  priority: "{priority}"\n')
            f.write(f'  gate_checklist: []\n')
            f.write(f'  cross_phase_deps: []\n')
            f.write(f'  manual_deps: []\n')
            f.write(f'  manual_blocks: []\n')
            f.write(f'  category_validation:\n')
            f.write(f'    valid: true\n')
            f.write(f'    reason: ""\n')
    except OSError:
        return False

    print(f"  已创建: roadmap-meta.yaml (phase: {lookup_phase}, category: {lookup_category})")
    return True


def update_roadmap_state(
    project_root: str,
    name: str,
    change_phase: str,
    change_category: str,
) -> Optional[bool]:
    """Update roadmap-state.json with the new change (propose.md lines 688-711).

    Uses existing roadmap_state.update_change_count helper. Gracefully skips
    when state file is missing, or phase/category doesn't exist in state
    (matches original inline behavior at lines 707-709 which catches
    FileNotFoundError, json.JSONDecodeError, KeyError).

    Per baseline verification (2026-07-16): update_change_count is a
    SILENT no-op when phase/category is missing — does NOT raise KeyError.
    Therefore we explicitly check state BEFORE calling, and read state
    AFTER to detect silent no-op. Returns False on no-op (not raised).

    Returns True on actual update, False/None on graceful skip.
    """
    import os
    import sys
    state_file = os.path.join(project_root, ".rddf", "state", "roadmap-state.json")
    if not os.path.isfile(state_file):
        print("  ⚠️  roadmap-state.json 不存在, 跳过 roadmap state 更新")
        return None

    try:
        from skills._lib import roadmap_state as rs

        # Pre-check: confirm phase/category exists (matches original inline check)
        state = rs.read_state(state_file)
        if not (
            change_phase in state.get("phases", {})
            and change_category in state["phases"][change_phase].get("categories", {})
        ):
            print(
                f"  ⚠️  roadmap-state.json 中 phase='{change_phase}' "
                f"category='{change_category}' 不存在, 跳过"
            )
            return False

        rs.update_change_count(
            state_file=state_file,
            change_name=name,
            phase=change_phase,
            category=change_category,
            operation="add",
        )
        print("  已更新: .roadmap-state.json")
        return True
    except (KeyError, OSError) as e:
        print(f"⚠️  更新 .roadmap-state.json 失败: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠️  更新 .roadmap-state.json 失败: {e}", file=sys.stderr)
        return False


def update_iteration_proposed(
    project_root: str,
    name: str,
    phase: str,
    category: str,
    priority: str,
) -> Optional[bool]:
    """Update iteration.json with status=proposed (propose.md lines 713-760).

    Uses iteration.add_or_update_change (NOT set_deps_info — deps set
    by deps.md Step 6). Graceful skip on ImportError.

    Per Oracle audit: this MUST only call add_or_update_change (not
    set_deps_info) to preserve deps.md Step 6's responsibility boundary.
    """
    import sys
    try:
        from skills._lib import iteration as it_mod
    except ImportError as e:
        print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
        return None
    try:
        data = it_mod.load(project_root)
        data = it_mod.add_or_update_change(
            data,
            name=name,
            status="proposed",
            phase=phase,
            category=category,
            priority=priority,
        )
        it_mod.save(project_root, data)
        print("  已更新: iteration.json (status=proposed)")
        return True
    except (FileNotFoundError,) as e:
        print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"⚠️  更新 iteration.json 失败: {e}", file=sys.stderr)
        return False
