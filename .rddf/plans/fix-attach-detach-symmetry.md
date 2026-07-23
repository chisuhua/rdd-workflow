# fix-attach-detach-symmetry Implementation Plan

**Goal:** Add `rddf_session_hook_attach` function and wire it into guide-plan/guide-ship call sites.

**Architecture:** New bash function in `rddf_session_hooks.sh` mirroring `rddf_session_hook_heartbeat` pattern, then add calls in guide-plan Phase 2 and guide-ship Phase 1.

**Tech Stack:** Bash, Python 3.11+

---

### Task 1: Add rddf_session_hook_attach to hooks.sh

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh` — add new function at end

- [ ] **Step 1: Add the function** (before the final newline)

```bash
# rddf_session_hook_attach <kind> <change_name>
#
# Called by guide-plan Phase 2 (after propose) and guide-ship Phase 1
# (after plan generation) to attach a change to the active rddf-session.
# Idempotent: duplicate calls have no effect.
rddf_session_hook_attach() {
  local kind="$1"
  local change_name="$2"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"

  KIND="$kind" \
  CHANGE_NAME="$change_name" \
  PROJECT_ROOT="$PROJECT_ROOT" \
  OPENCODE_SESSION_ID="$OPENCODE_SESSION_ID" \
  python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator

project_root = os.environ["PROJECT_ROOT"]
kind = os.environ["KIND"]
change_name = os.environ.get("CHANGE_NAME") or ""
opencode_sid = os.environ["OPENCODE_SESSION_ID"]

sessions_file = os.path.join(project_root, ".rddf", "state", "sessions.json")
if not os.path.exists(sessions_file):
    print("rddf-session: sessions.json not found, skipping attach")
    sys.exit(0)

coord = RddfSessionCoordinator(sessions_file=sessions_file)
try:
    sid = coord.create_session(
        kind=kind,
        owner_opencode_session_id=opencode_sid,
        goal={"intent": "guide-ship"},
    )
    if change_name:
        coord.attach_change(sid, change_name)
    print(f"rddf-session: {sid} change {change_name} attached")
except Exception as e:
    print(f"rddf-session attach skip: {e}")
PYEOF
}
```

- [ ] **Step 2: Run existing tests to verify no regression**

Run: `python3 -m pytest tests/ -x -q --tb=short -k "rddf" 2>&1 | tail -5`
Expected: all rddf tests pass (hook addition doesn't affect Python tests)

- [ ] **Step 3: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session_hooks.sh
git commit -m "feat(rddf-session): add rddf_session_hook_attach function"
```

---

### Task 2: Wire attach hook into guide-plan Phase 2

**Files:**
- Modify: `skills/guide-plan/SKILL.md` — add attach call after propose Phase 2

- [ ] **Step 1: Add call after propose completion** (search for "Propose 阶段完成" section)

Add before the post-propose summary:
```bash
# Attach changes to rddf-session
source "$(dirname "\${BASH_SOURCE[0]:-}")/../rddf-session/scripts/rddf_session_hooks.sh"
rddf_session_hook_attach stage_plan "<change_name>"
```

- [ ] **Step 2: Commit**

```bash
git add skills/guide-plan/SKILL.md
git commit -m "feat(guide-plan): call rddf_session_hook_attach after propose Phase 2"
```

---

### Task 3: Wire attach hook into guide-ship Phase 1

**Files:**
- Modify: `skills/guide-ship/SKILL.md` — add attach call after plan generation

- [ ] **Step 1: Add call after plan generation**

In the guide-ship plan generation script or Phase 1 section, after generating the implementation plan:
```bash
# Attach change to rddf-session
source "$(dirname "\${BASH_SOURCE[0]:-}")/../rddf-session/scripts/rddf_session_hooks.sh"
rddf_session_hook_attach stage_ship "$CHANGE_NAME"
```

- [ ] **Step 2: Commit**

```bash
git add skills/guide-ship/SKILL.md
git commit -m "feat(guide-ship): call rddf_session_hook_attach after plan generation"
```

---

### Task 4: Mark tasks complete

- [ ] **Step 1: Update tasks.md**

```bash
sed -i 's/- \[ \]/- [x]/g' openspec/changes/fix-attach-detach-symmetry/tasks.md
```

- [ ] **Step 2: Final commit**

```bash
git add openspec/changes/fix-attach-detach-symmetry/tasks.md
git commit -m "chore(fix-attach-detach-symmetry): mark all tasks complete"
```