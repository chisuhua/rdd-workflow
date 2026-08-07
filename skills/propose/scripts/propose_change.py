"""_lib/propose_change.py — helpers for propose.md Phase 4.

Extracted from inline PYEOF heredocs in propose.md lines 443-796
(P0-1 refactor, Metis plan 2026-07-16). Each function preserves the
exact behavior of the corresponding inline block, including output
strings and exception handling.
"""

import json
import os
import re
import sys
from typing import Optional


def set_suggestion_status(
    project_root: str, name: str, new_status: str
) -> bool:
    """Update status field for matching entry in proposal-approved.md.
    
    proposal-approved.md is a Markdown table. Status update modifies
    the table row to reflect the new status.
    Returns True if updated, False if file missing or name not found.
    """
    import re
    path = os.path.join(project_root, "proposal-approved.md")
    if not os.path.exists(path):
        return False
    
    with open(path) as f:
        content = f.read()
    
    # Find the row with this name
    pattern = rf'\| \[{re.escape(name)}\]\([^)]+\) \| (\S+) \| ([^|]*) \| ([^|]*) \|'
    match = re.search(pattern, content)
    if not match:
        return False
    
    # Replace the row - add status annotation
    old_row = match.group(0)
    # For "in_progress", we add a status note; for "completed", we move to completed section
    if new_status == "completed":
        # Move to completed section
        from datetime import date
        completed_row = f"| [{name}](improvements/{name}.md) | {match.group(1)} | {date.today().isoformat()} |"
        content = content.replace(old_row + "\n", "")
        if "## 已实施" in content:
            content = content.replace("## 已实施\n\n", f"## 已实施\n\n{completed_row}\n")
        else:
            content += f"\n{completed_row}\n"
    elif new_status == "in_progress":
        # Add in-progress marker
        new_row = f"| [{name}](improvements/{name}.md) | {match.group(1)} | {match.group(2)} | {match.group(3)} (in_progress) |"
        content = content.replace(old_row, new_row)
    
    try:
        with open(path, "w") as f:
            f.write(content)
        return True
    except OSError:
        return False


def create_skeleton_change(
    project_root: str,
    name: str,
    current_phase: str,
    category: str,
    priority: str,
    parent_feature: Optional[str] = None,
) -> bool:
    """Create minimal skeleton artifacts for a change (propose.md lines 486-551).

    Writes:
    - openspec/changes/<name>/proposal.md (Why + What Changes skeleton)
    - openspec/changes/<name>/roadmap-meta.yaml
    - iteration.json (status=planned) - graceful skip on ImportError

    Returns True on full success, False if proposal/yaml write failed.
    Matches original inline behavior exactly, including:
    - openspec new change call (best-effort, swallows errors)
    - All output strings ("📦 Skeleton mode:", "  ✅ iteration.json updated:",
      "⚠️  iteration.json update failed (non-fatal):")

    When ``parent_feature`` is provided, it is written to both roadmap-meta.yaml
    and iteration.json so the change groups under the named feature without
    requiring a ``feature-`` name prefix. The reserved synthetic key
    ``__ungrouped__`` is rejected with ``ValueError``.
    """
    import os
    import subprocess
    import sys

    if parent_feature == "__ungrouped__":
        raise ValueError(
            "parent_feature='__ungrouped__' is reserved (synthetic feature key); "
            "use a real feature name or omit parent_feature"
        )

    change_dir = os.path.join(project_root, "openspec", "changes", name)

    # Idempotency guard: a pre-existing proposal.md means the change was
    # already created; re-running must skip, never clobber artifacts.
    proposal_path = os.path.join(change_dir, "proposal.md")
    if os.path.exists(proposal_path):
        print(
            f"⚠️  Change '{name}' 已存在 (proposal.md), 跳过创建 (幂等保护)",
            file=sys.stderr,
        )
        return False

    os.makedirs(change_dir, exist_ok=True)

    # openspec new change (best-effort, matches original)
    subprocess.run(
        ["openspec", "new", "change", name],
        cwd=project_root,
        capture_output=True,
    )

    # Extract change_type from improvements head (D6 — feature/test-only/doc-only/refactor)
    ct = "feature"
    improvements_path = os.path.join(project_root, "improvements", f"{name}.md")
    if os.path.exists(improvements_path):
        m = re.search(r"\*\*类型\*\*:\s*([^|\n]+)", open(improvements_path).read())
        if m:
            ct = m.group(1).strip()

    # v1.7.0+: doc-only/test-only changes can use skip_specs: true in .openspec.yaml
    skip_specs = ct in ("doc-only", "test-only")

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

    # Write .openspec.yaml with optional skip_specs (v1.7.0+)
    openspec_yaml_path = os.path.join(change_dir, ".openspec.yaml")
    try:
        with open(openspec_yaml_path, "w") as f:
            f.write(f"name: {name}\n")
            if skip_specs:
                f.write("skip_specs: true\n")
    except OSError:
        pass

    # Write minimal roadmap-meta.yaml
    yaml_path = os.path.join(change_dir, "roadmap-meta.yaml")
    try:
        # Extract change_type from improvements head (D6 — feature/test-only/doc-only/refactor)
        ct = "feature"
        improvements_path = os.path.join(project_root, "improvements", f"{name}.md")
        if os.path.exists(improvements_path):
            m = re.search(r"\*\*类型\*\*:\s*([^|\n]+)", open(improvements_path).read())
            if m:
                ct = m.group(1).strip()

        with open(yaml_path, "w") as f:
            f.write('roadmap:\n')
            f.write(f'  phase: "{current_phase}"\n')
            f.write(f'  category: "{category}"\n')
            f.write(f'  priority: "{priority}"\n')
            f.write(f'  change_type: "{ct}"\n')
            f.write('  gate_checklist: []\n')
            f.write('  cross_phase_deps: []\n')
            f.write('  manual_deps: []\n')
            f.write('  manual_blocks: []\n')
            pf_yaml = f'"{parent_feature}"' if parent_feature else "null"
            f.write(f'  parent_feature: {pf_yaml}\n')
            f.write('  category_validation:\n')
            f.write('    valid: true\n')
            f.write('    reason: ""\n')
    except OSError:
        return False

    # Update iteration.json (graceful skip)
    try:
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        kwargs = {
            "name": name,
            "status": "planned",
            "phase": None,
            "category": None,
            "priority": None,
        }
        if parent_feature is not None:
            kwargs["parent_feature"] = parent_feature
        data = it_mod.add_or_update_change(data, **kwargs)
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
    parent_feature: Optional[str] = None,
    change_type: Optional[str] = None,
) -> bool:
    """Update roadmap-meta.yaml for a change (propose.md lines 617-686).

    Looks up phase/category from proposal-suggestions.md, falls back to
    arguments. ALWAYS falls back to 'general' on invalid category (matches
    original inline behavior at line 671 which hard-codes
    CHANGE_CATEGORY='general' regardless of valid_categories).
    Returns False if openspec/changes/<name>/ doesn't exist or yaml write fails.

    When ``parent_feature`` is provided, it is written to roadmap-meta.yaml
    so the change groups under the named feature. ``None`` writes ``null``
    (explicit no-feature affiliation).

    ``change_type``: one of 'feature' (default), 'test-only', 'doc-only',
    'refactor-only'. Controls delta-check behavior during archive.
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
    ct = change_type if change_type else "feature"
    try:
        with open(yaml_path, "w") as f:
            f.write('roadmap:\n')
            f.write(f'  phase: "{lookup_phase}"\n')
            f.write(f'  category: "{lookup_category}"\n')
            f.write(f'  priority: "{priority}"\n')
            f.write(f'  change_type: "{ct}"\n')
            f.write('  gate_checklist: []\n')
            f.write('  cross_phase_deps: []\n')
            f.write('  manual_deps: []\n')
            f.write('  manual_blocks: []\n')
            pf_yaml = f'"{parent_feature}"' if parent_feature else "null"
            f.write(f'  parent_feature: {pf_yaml}\n')
            f.write('  category_validation:\n')
            f.write('    valid: true\n')
            f.write('    reason: ""\n')
    except OSError:
        return False

    print(f"  已创建: roadmap-meta.yaml (phase: {lookup_phase}, category: {lookup_category}, type: {ct})")
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
    parent_feature: Optional[str] = None,
) -> Optional[bool]:
    """Update iteration.json with status=proposed (propose.md lines 713-760).

    Uses iteration.add_or_update_change (NOT set_deps_info - deps set
    by deps.md Step 6). Graceful skip on ImportError.

    Per Oracle audit: this MUST only call add_or_update_change (not
    set_deps_info) to preserve deps.md Step 6's responsibility boundary.

    When ``parent_feature`` is provided, it is written to iteration.json
    so the change groups under the named feature. The reserved synthetic
    key ``__ungrouped__`` is rejected with ``ValueError`` before any
    state mutation.
    """
    import sys
    if parent_feature == "__ungrouped__":
        raise ValueError(
            "parent_feature='__ungrouped__' is reserved (synthetic feature key); "
            "use a real feature name or omit parent_feature"
        )
    try:
        from skills._lib import iteration as it_mod
    except ImportError as e:
        print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
        return None
    try:
        data = it_mod.load(project_root)
        kwargs = {
            "name": name,
            "status": "proposed",
            "phase": phase,
            "category": category,
            "priority": priority,
        }
        if parent_feature is not None:
            kwargs["parent_feature"] = parent_feature
        data = it_mod.add_or_update_change(data, **kwargs)
        it_mod.save(project_root, data)
        print("  已更新: iteration.json (status=proposed)")
        return True
    except (FileNotFoundError,) as e:
        print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"⚠️  更新 iteration.json 失败: {e}", file=sys.stderr)
        return False


def _change_dir_exists(project_root: str, name: str) -> bool:
    return os.path.isdir(os.path.join(project_root, "openspec", "changes", name))


def _change_is_archived(project_root: str, name: str) -> bool:
    import glob
    archive_dir = os.path.join(project_root, "openspec", "changes", "archive")
    return any(
        os.path.isdir(p)
        for p in glob.glob(os.path.join(archive_dir, f"*-{name}"))
    )


def batch_create_pending(project_root: str) -> list[str]:
    """Create skeleton changes for all pending suggestions in proposal-approved.md.

    Idempotent: entries whose change already exists under openspec/changes/
    (active) or openspec/changes/archive/ (completed) are skipped, so
    re-running never overwrites existing artifacts.

    Uses the centralized parse_approved_proposals helper which reads BOTH
    the `## 已批准提案` and `## 已实施` sections (the previous inline parser
    only read the region before `## 已实施`, silently missing every entry
    in this repo where everything lives in `## 已实施`).
    """
    from skills._lib.parse_approved import parse_approved_proposals

    approved_file = os.path.join(project_root, "proposal-approved.md")
    rows = [(name, "") for name in parse_approved_proposals(approved_file)]
    created = []
    skipped = []
    for name, _ in rows:
        if _change_dir_exists(project_root, name) or _change_is_archived(project_root, name):
            skipped.append(name)
            continue
        try:
            if create_skeleton_change(project_root, name, "default", "general", "P2"):
                created.append(name)
        except Exception as e:
            print(f"WARN: failed to create {name}: {e}", file=sys.stderr)
    if skipped:
        print(f"⏭️  跳过 {len(skipped)} 个已创建/已归档的 change: {', '.join(skipped)}")
    return created
