## 1. 创建 `auto_advance.py` 模块 — 入口 hook 状态推进 (T1)

- [ ] 1.1 **Write failing test**: Create `tests/unit/test_iteration.py` — call `auto_advance_status()` with `current_stage="plan"` on an iteration.json containing `planned` status changes, assert they become `proposed`
- [ ] 1.2 **Verify fail**: Run `python3 -m pytest tests/unit/test_iteration.py::test_auto_advance_plan -xvs` — confirm it fails (module doesn't exist)
- [ ] 1.3 **Implement**: Create `skills/_lib/iteration/auto_advance.py` with `auto_advance_status()`:
  ```python
  def auto_advance_status(iteration_path: str, current_stage: str) -> dict:
      """Auto-advance iteration.json statuses based on workflow stage.
      
      State machine: planned→proposed (plan stage),
                     proposed→in_worktree (ship stage)
      """
      with open(iteration_path) as f:
          data = json.load(f)
      changes = data.get("changes", [])
      updated = 0
      updated_names = []
      for change in changes:
          status = change.get("status", "")
          if current_stage == "plan" and status == "planned":
              change["status"] = "proposed"
              updated += 1
              updated_names.append(change.get("name", ""))
          elif current_stage == "ship" and status == "proposed":
              change["status"] = "in_worktree"
              updated += 1
              updated_names.append(change.get("name", ""))
      if updated > 0:
          with open(iteration_path, "w") as f:
              json.dump(data, f, indent=2, ensure_ascii=False)
              f.write("\n")
      return {"updated": updated, "changes": updated_names}
  ```
- [ ] 1.4 **Verify pass**: Re-run the test — confirm it passes
- [ ] 1.5 **N/A** (no commit per MUST NOT DO)

## 2. 集成 `auto_advance_status` 到 guide-arch/guide-plan/guide-ship 入口 hook (T2)

- [ ] 2.1 **Write failing test**: Add bats test in `tests/integration/test_iteration_lifecycle.bats` — simulate guide-plan entry, assert iteration.json changes get `proposed` status
- [ ] 2.2 **Verify fail**: Run `bats tests/integration/test_iteration_lifecycle.bats` — confirm it fails
- [ ] 2.3 **Implement**: Add Python call in each guide skill's entry phase:
  ```bash
  # In guide-plan Phase 0 (or guide-arch/guide-ship entry)
  if [ -f "$PROJECT_ROOT/.rddf/state/iteration.json" ]; then
      python3 -c "
  import sys; sys.path.insert(0, '$PROJECT_ROOT/skills/_lib')
  from iteration.auto_advance import auto_advance_status
  result = auto_advance_status('$PROJECT_ROOT/.rddf/state/iteration.json', '$STAGE')
  if result['updated'] > 0:
      print(f'  ↻ 状态推进: {result[\"updated\"]} 个 change 已更新')
  "
  fi
  ```
  Where `$STAGE` is `"arch"`, `"plan"`, or `"ship"` depending on which guide skill is running.
- [ ] 2.4 **Verify pass**: Re-run — confirm it passes
- [ ] 2.5 **N/A** (no commit per MUST NOT DO)

## 3. 创建 archive hook blocker 检测函数 (T3)

- [ ] 3.1 **Write failing test**: Create `tests/unit/test_iteration.py` — test `detect_unblocked()` logic: iteration.json with change-a (planned, manual_deps=["change-b"]), archive change-b, assert change-a is detected as unblocked
- [ ] 3.2 **Verify fail**: Run the test — confirm it fails
- [ ] 3.3 **Implement**: Add `detect_unblocked()` in `auto_advance.py`:
  ```python
  def detect_unblocked(iteration_path: str, archived_name: str) -> list:
      """Find planned changes whose manual_deps include archived_name and all deps are archived."""
      with open(iteration_path) as f:
          data = json.load(f)
      changes = data.get("changes", [])
      archived_names = {c["name"] for c in changes if c.get("status") == "archived"}
      unblocked = []
      for change in changes:
          if change.get("status") != "planned":
              continue
          deps = change.get("manual_deps", [])
          if archived_name in deps:
              # Check if all deps are archived
              if all(d in archived_names for d in deps):
                  unblocked.append(change.get("name", ""))
      return unblocked
  ```
- [ ] 3.4 **Verify pass**: Re-run — confirm it passes
- [ ] 3.5 **N/A** (no commit per MUST NOT DO)

## 4. 集成 blocker 检测到 archive.sh (T4)

- [ ] 4.1 **Write failing test**: Add bats test in `tests/integration/test_archive_hook.bats` — set up iteration.json with change-a (planned, manual_deps=["change-b"]), simulate archive change-b, assert output contains "bloker 已解除: change-a"
- [ ] 4.2 **Verify fail**: Run the test — confirm it fails
- [ ] 4.3 **Implement**: Add to `skills/_lib/archive.sh` after `commit_archive_moves`:
  ```bash
  detect_unblocked_changes() {
      local archived_name="$1"
      local project_root="$2"
      local iteration_file="$project_root/.rddf/state/iteration.json"
      [ -f "$iteration_file" ] || return 0
      local result
      result=$(python3 -c "
  import sys, json
  sys.path.insert(0, '$project_root/skills/_lib')
  from iteration.auto_advance import detect_unblocked
  unblocked = detect_unblocked('$iteration_file', '$archived_name')
  if unblocked:
      print('📋 bloker 已解除: ' + ', '.join(unblocked) + ' 可以执行')
  " 2>/dev/null)
      [ -n "$result" ] && echo "$result"
  }
  ```
  Call `detect_unblocked_changes "$name" "$main_root" || true` at the end of `archive_change()`.
- [ ] 4.4 **Verify pass**: Re-run — confirm it passes
- [ ] 4.5 **N/A** (no commit per MUST NOT DO)

## 5. 添加 no-op 测试：归档孤立 change 不输出建议 (T5)

- [ ] 5.1 **Write failing test**: Add bats test in `tests/integration/test_archive_hook.bats` — archive an isolated change (no dependents), assert no "bloker 已解除" output
- [ ] 5.2 **Verify fail**: Run the test — confirm it fails
- [ ] 5.3 **N/A** (logic already handles isolated case — no suggestions when no dependents)
- [ ] 5.4 **Verify pass**: Run — confirm it passes
- [ ] 5.5 **N/A** (no commit per MUST NOT DO)