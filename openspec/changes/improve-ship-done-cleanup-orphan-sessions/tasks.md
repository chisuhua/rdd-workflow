## 1. Implement read-only orphaned-session counter

- [ ] 1.1 Create the failing test `tests/integration/test_ship_done_orphan_prompt.bats` for the helper `count_orphaned_sessions`.

    ```bash
    # tests/integration/test_ship_done_orphan_prompt.bats
    #!/usr/bin/env bats
    # Matrix regression tests for ship-done orphan prompt.

    load ../test_helper

    _make_sessions_json() {
      local repo="$1"
      shift
      mkdir -p "$repo/.rddf/state"
      printf '%s' "$*" > "$repo/.rddf/state/sessions.json"
    }

    _run_check_remaining_work() {
      local repo="$1"
      bash -c '
        export RDD_WORKFLOW_SRC="$REPO_ROOT"
        source "$REPO_ROOT/skills/guide-ship/scripts/ship_done.sh"
        check_remaining_work "$1"
      ' _ "$repo"
    }

    setup() {
      repo=$(mktemp -d)
      git init -q "$repo"
      git -C "$repo" config user.email "t@t"
      git -C "$repo" config user.name "t"
      touch "$repo/init"
      git -C "$repo" add init && git -C "$repo" commit -q -m init
    }

    teardown() {
      rm -rf "$repo"
    }
    ```

    Add the helper tests first (corrupt/missing/zero cases):

    ```bash
    @test "count_orphaned_sessions: returns 0 when sessions.json is missing" {
      run bash -c '
        export RDD_WORKFLOW_SRC="$REPO_ROOT"
        source "$REPO_ROOT/skills/_lib/sessions_count.sh"
        count_orphaned_sessions "$1"
      ' _ "$repo"
      [ "$status" -eq 0 ]
      [ "$output" = "0" ]
    }

    @test "count_orphaned_sessions: returns 0 when sessions.json is corrupt" {
      _make_sessions_json "$repo" '{not valid}'
      run bash -c '
        export RDD_WORKFLOW_SRC="$REPO_ROOT"
        source "$REPO_ROOT/skills/_lib/sessions_count.sh"
        count_orphaned_sessions "$1"
      ' _ "$repo"
      [ "$status" -eq 0 ]
      [ "$output" = "0" ]
    }

    @test "count_orphaned_sessions: counts only orphaned sessions" {
      _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_000000000001","state":"orphaned"},{"session_id":"rds_000000000002","state":"active"},{"session_id":"rds_000000000003","state":"completed"}]}'
      run bash -c '
        export RDD_WORKFLOW_SRC="$REPO_ROOT"
        source "$REPO_ROOT/skills/_lib/sessions_count.sh"
        count_orphaned_sessions "$1"
      ' _ "$repo"
      [ "$status" -eq 0 ]
      [ "$output" = "1" ]
    }
    ```

    Verification: `bats tests/integration/test_ship_done_orphan_prompt.bats` (expected: FAIL, helper not implemented)

- [ ] 1.2 Implement `skills/_lib/sessions_count.sh`.

    ```bash
    #!/usr/bin/env bash
    # skills/_lib/sessions_count.sh — read-only orphaned rddf-session counter.

    count_orphaned_sessions() {
      local root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
      local file="$root/.rddf/state/sessions.json"
      [ -f "$file" ] || { echo 0; return 0; }
      if command -v jq >/dev/null 2>&1; then
        jq '[.sessions[]? | select(.state == "orphaned")] | length' "$file" 2>/dev/null || echo 0
      else
        python3 -c 'import json,sys; f=sys.argv[1]; print(len([s for s in json.load(open(f)).get("sessions",[]) if s.get("state")=="orphaned"]))' "$file" 2>/dev/null || echo 0
      fi
    }
    ```

    Verification: `wc -l skills/_lib/sessions_count.sh` ≤ 20, `grep -c 'count_orphaned_sessions' skills/_lib/sessions_count.sh` ≥ 1

- [ ] 1.3 Run the helper tests and confirm they pass.

    Verification: `bats tests/integration/test_ship_done_orphan_prompt.bats --filter count_orphaned_sessions` (expected: 3 PASS)

- [ ] 1.4 Commit the helper.

    ```bash
    git add skills/_lib/sessions_count.sh tests/integration/test_ship_done_orphan_prompt.bats
    git commit -m "feat(ship-done): read-only orphaned rddf-session counter"
    ```

## 2. Integrate orphan prompt into ship-done menu

- [ ] 2.1 Add the ship-done integration tests to `tests/integration/test_ship_done_orphan_prompt.bats`.

    Append the matrix tests after the helper tests created in 1.1:

    ```bash
    @test "ship-done: 3 orphans + 0 changes shows option 5 and lists ids" {
      _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_a1b5","state":"orphaned"},{"session_id":"rds_1221","state":"orphaned"},{"session_id":"rds_0569","state":"orphaned"}]}'
      run _run_check_remaining_work "$repo"
      [ "$status" -eq 0 ]
      [[ "$output" == *"✅ 所有 changes 已处理完毕"* ]]
      [[ "$output" == *"⚠️ 发现 3 个 orphaned rddf-sessions (rds_a1b5, rds_1221, rds_0569)"* ]]
      [[ "$output" == *"5. 🧹 清理 3 个 orphaned sessions"* ]]
      [[ "$output" == *"1. 继续处理"* ]]
      [[ "$output" == *"2. 回到 spec 端"* ]]
      [[ "$output" == *"3. 本次 session 结束"* ]]
      [[ "$output" == *"4. 项目完成"* ]]
      [[ "$output" == *"i. 其他输入"* ]]
    }

    @test "ship-done: 0 orphans + 0 changes matches baseline output" {
      run _run_check_remaining_work "$repo"
      [ "$status" -eq 0 ]
      [[ "$output" != *"orphaned"* ]]
      [[ "$output" != *"5."* ]]
      [[ "$output" == *"1. 继续处理"* ]]
      [[ "$output" == *"2. 回到 spec 端"* ]]
      [[ "$output" == *"3. 本次 session 结束"* ]]
      [[ "$output" == *"4. 项目完成"* ]]
      [[ "$output" == *"i. 其他输入"* ]]
    }

    @test "ship-done: 1 orphan + 1 change shows 还有 header and option 5" {
      mkdir -p "$repo/openspec/changes/example-change"
      _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_9999","state":"orphaned"}]}'
      run _run_check_remaining_work "$repo"
      [ "$status" -eq 0 ]
      [[ "$output" == *"📋 还有"* ]]
      [[ "$output" == *"⚠️ 发现 1 个 orphaned rddf-sessions (rds_9999)"* ]]
      [[ "$output" == *"5. 🧹 清理 1 个 orphaned sessions"* ]]
      [[ "$output" == *"1. 继续处理"* ]]
      [[ "$output" == *"2. 回到 spec 端"* ]]
      [[ "$output" == *"3. 本次 session 结束"* ]]
      [[ "$output" == *"4. 项目完成"* ]]
      [[ "$output" == *"i. 其他输入"* ]]
    }

    @test "ship-done: more than 3 orphans truncates list with +N more" {
      _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_0001","state":"orphaned"},{"session_id":"rds_0002","state":"orphaned"},{"session_id":"rds_0003","state":"orphaned"},{"session_id":"rds_0004","state":"orphaned"},{"session_id":"rds_0005","state":"orphaned"}]}'
      run _run_check_remaining_work "$repo"
      [ "$status" -eq 0 ]
      [[ "$output" == *"rds_0001, rds_0002, rds_0003 ... +2 more"* ]]
      [[ "$output" != *"rds_0004"* ]]
      [[ "$output" != *"rds_0005"* ]]
    }
    ```

    Verification: `bats tests/integration/test_ship_done_orphan_prompt.bats` (expected: 4 new FAILs, menu not implemented)

- [ ] 2.2 Modify `skills/guide-ship/scripts/ship_done.sh` to add the orphan prompt and option 5 while keeping the file ≤ 30 lines.

    ```bash
    #!/usr/bin/env bash
    # skills/guide-ship/scripts/ship_done.sh
    check_remaining_work() {
      local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
      source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
      source "$(resolve_rdd_lib_dir)/sessions_count.sh"
      local REMAINING REMAINING_WT ORPHANS
      REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]')
      REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l | tr -d '[:space:]')
      ORPHANS=$(count_orphaned_sessions "$PROJECT_ROOT")
      if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING" -gt 0 ]; then echo "📋 还有 $REMAINING_WT 个 worktree 在跑,$REMAINING 个未处理 change"; else echo "✅ 所有 changes 已处理完毕"; fi
      echo ""
      if [ "$ORPHANS" -gt 0 ]; then
        local IDS; IDS=$(PROJECT_ROOT="$PROJECT_ROOT" python3 -c 'import json, os; d=json.load(open(os.path.join(os.environ["PROJECT_ROOT"], ".rddf/state/sessions.json"))); ids=[s["session_id"] for s in d.get("sessions",[]) if s.get("state")=="orphaned"]; print(", ".join(ids[:3]) + (" ... +{} more".format(len(ids)-3) if len(ids)>3 else ""))' 2>/dev/null || echo "???")
        echo "⚠️ 发现 $ORPHANS 个 orphaned rddf-sessions ($IDS)"
        echo "   建议清理: skill_use(\"rddf-session\", \"abandon\", ...) 或 archive-history"
      fi
      echo "请选择:"
      echo "1. 继续处理 (skill_use(\"guide-ship\")) - 还有 worktree 要处理"
      echo "2. 回到 spec 端 (skill_use(\"guide-arch\") 或 skill_use(\"guide-plan\")) - 创建更多 changes"
      echo "3. 本次 session 结束 - 退出 ship-done,稍后继续"
      echo "4. 项目完成 - 不再做任何 change(此项目归档)"
      [ "$ORPHANS" -gt 0 ] && echo "5. 🧹 清理 $ORPHANS 个 orphaned sessions (skill_use(\"rddf-session\", \"abandon\", ...) 或 archive-history)"
      echo "i. 其他输入"
    }
    ```

    Verification: `wc -l skills/guide-ship/scripts/ship_done.sh` ≤ 30

- [ ] 2.3 Run the integration tests and confirm all six matrix cases pass.

    Verification: `bats tests/integration/test_ship_done_orphan_prompt.bats` (expected: 7 PASS)

- [ ] 2.4 Run the existing ship-done semantics tests to confirm no regression.

    Verification: `bats tests/integration/test_ship_done_semantics.bats` (expected: 2 PASS)

- [ ] 2.5 Commit the ship-done integration.

    ```bash
    git add skills/guide-ship/scripts/ship_done.sh tests/integration/test_ship_done_orphan_prompt.bats
    git commit -m "feat(ship-done): conditional orphan cleanup prompt in Phase 5 menu"
    ```

## 3. Document and validate

- [ ] 3.1 Add a short paragraph to `skills/guide-ship/SKILL.md` Phase 5 describing the orphan prompt.

    Insert after the `check_remaining_work` code block (around line 613) and before the **输入处理** section (line 616):

    ```markdown
    **Orphaned rddf-sessions prompt**: When `.rddf/state/sessions.json` contains orphaned sessions, `check_remaining_work` prints the first three IDs (with `+N more` if there are more) and adds option 5 to the ship-done menu. Choosing option 5 launches the rddf-session cleanup skill; no automatic cleanup occurs.
    ```

    Verification: `grep -c "orphaned rddf-sessions" skills/guide-ship/SKILL.md` = 1

- [ ] 3.2 Run the full ship-done bats suite.

    Verification: `bats tests/integration/test_ship_done_*.bats` (expected: 9 PASS)

- [ ] 3.3 Run strict OpenSpec validation for the change.

    Verification: `openspec validate --type change improve-ship-done-cleanup-orphan-sessions --strict --json` (expected: valid=true)

- [ ] 3.4 Commit the documentation update.

    ```bash
    git add skills/guide-ship/SKILL.md
    git commit -m "docs(ship-done): document orphaned rddf-session prompt in Phase 5"
    ```
