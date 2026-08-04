#!/usr/bin/env bats
# tests/integration/test_ship_submodule_share.bats
# Submodule + worktree: git keeps submodule gitdirs PER-WORKTREE
# (.git/worktrees/<wt>/modules/<name>; see submodule_name_to_gitdir() in git's
# submodule.c) and clone_submodule() only reuses an existing gitdir
# (`file_exists(sm_gitdir)`) — otherwise every new worktree re-downloads the
# submodule from the network. share_submodules_to_worktree() in ship_plan.sh
# hardlinks the main repo's shared store into the worktree's private gitdir
# (cp -al; pack/loose objects are immutable, so hardlinks are safe), making
# `git submodule update` take the reuse branch: local checkout, zero network.

load ../test_helper

# git >= 2.38 blocks the file transport for submodule clones spawned from
# config (protocol.file.allow default = user). This file's scratch repos use
# local-path submodule URLs, so allow the file transport for this test file.
export GIT_ALLOW_PROTOCOL=file

# setup_superproject <dir> <change> — bare superproject with one committed
# OpenSpec change (no submodule).
setup_superproject() {
  local dir="$1"
  local change="$2"
  git -C "$dir" init -q -b master
  git -C "$dir" config user.email "test@test"
  git -C "$dir" config user.name "test"
  echo "root" > "$dir/README.md"
  git -C "$dir" add README.md
  git -C "$dir" commit -qm "root"
  add_change "$dir" "$change"
}

# add_change <dir> <change> — create + commit one OpenSpec change (scoped to
# the change dir only, so .rddf/ worktree artifacts never get staged).
add_change() {
  local dir="$1"
  local change="$2"
  mkdir -p "$dir/openspec/changes/$change"
  echo "# design" > "$dir/openspec/changes/$change/design.md"
  echo "# tasks" > "$dir/openspec/changes/$change/tasks.md"
  echo '{"name":"'$change'"}' > "$dir/openspec/changes/$change/.openspec.yaml"
  git -C "$dir" add "openspec/changes/$change/"
  git -C "$dir" commit -qm "change $change"
}

# setup_submodule_src <dir> — scratch submodule "remote" repo at <dir>/src.
setup_submodule_src() {
  local dir="$1"
  mkdir -p "$dir/src"
  git -C "$dir/src" init -q
  git -C "$dir/src" config user.email "test@test"
  git -C "$dir/src" config user.name "test"
  echo "sub" > "$dir/src/file.txt"
  git -C "$dir/src" add file.txt
  git -C "$dir/src" commit -qm "init sub"
}

# setup_gitlink_submodule <dir> — register submodule via .gitmodules + gitlink
# WITHOUT cloning (simulates a clone without --recurse-submodules: the shared
# store .git/modules/ does not exist yet → bootstrap path).
setup_gitlink_submodule() {
  local dir="$1"
  git -C "$dir" config -f .gitmodules submodule.sub.path sub
  git -C "$dir" config -f .gitmodules submodule.sub.url "$dir/src"
  git -C "$dir" add .gitmodules
  git -C "$dir" update-index --add --cacheinfo 160000,"$(git -C "$dir/src" rev-parse HEAD)",sub
  git -C "$dir" commit -qm "add submodule gitlink"
}

# setup_added_submodule <dir> — register submodule via `git submodule add`
# (the shared store .git/modules/sub already exists → direct-share path).
setup_added_submodule() {
  local dir="$1"
  git -C "$dir" submodule add -q "$dir/src" sub
  git -C "$dir" commit -qm "add submodule"
}

@test "ship submodule share: share_submodules_to_worktree 已定义且被 setup_execution_workspace 调用" {
  [ -f "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh" ]
  grep -q "^share_submodules_to_worktree()" "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  grep -q 'share_submodules_to_worktree "\$project_root" "\$wt_path"' "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
}

@test "ship submodule share: 无 submodule 项目 worktree 创建不受影响且 stdout 纯净" {
  TEST_REPO=$(mktemp -d)
  setup_superproject "$TEST_REPO" "c1"
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  WT=$(setup_execution_workspace "$TEST_REPO" "c1" "worktree")
  # stdout 必须是纯路径 (git worktree add -q 修复: 防 "HEAD is now at" 泄漏)
  [ "$WT" = "$TEST_REPO/.rddf/wt/c1" ]
  [ -d "$WT" ]
  rm -rf "$TEST_REPO"
}

@test "ship submodule share: 未初始化 submodule 走 bootstrap, worktree 复用对象库零网络" {
  TEST_REPO=$(mktemp -d)
  setup_superproject "$TEST_REPO" "c1"
  setup_submodule_src "$TEST_REPO"
  setup_gitlink_submodule "$TEST_REPO"
  # bootstrap 前提: 共享存储尚不存在
  [ ! -d "$TEST_REPO/.git/modules/sub" ]
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  WT=$(setup_execution_workspace "$TEST_REPO" "c1" "worktree")
  [ "$WT" = "$TEST_REPO/.rddf/wt/c1" ]
  # 1. worktree 内 submodule 已物化
  [ -f "$WT/sub/file.txt" ]
  # 2. 对象库硬链接共享: 两侧相同相对路径文件 inode 相同
  local main_obj rel wt_obj
  main_obj=$(find "$TEST_REPO/.git/modules/sub/objects" -type f | head -1)
  rel=${main_obj#$TEST_REPO/.git/modules/sub/}
  wt_obj="$TEST_REPO/.git/worktrees/c1/modules/sub/$rel"
  [ -n "$main_obj" ]
  [ -f "$wt_obj" ]
  [ "$(stat -c %i "$main_obj")" = "$(stat -c %i "$wt_obj")" ]
  # 3. 删除 submodule 远程源后, worktree 内 update 仍成功 (零网络)
  rm -rf "$TEST_REPO/src"
  git -C "$WT" submodule update --init --recursive >/dev/null 2>&1
  [ -f "$WT/sub/file.txt" ]
  # 4. 主工作区 submodule 完好
  [ -f "$TEST_REPO/sub/file.txt" ]
  rm -rf "$TEST_REPO"
}

@test "ship submodule share: 已初始化 submodule 直接共享, 多 worktree 均零网络" {
  TEST_REPO=$(mktemp -d)
  setup_superproject "$TEST_REPO" "c1"
  setup_submodule_src "$TEST_REPO"
  setup_added_submodule "$TEST_REPO"
  # 已初始化前提: 共享存储已存在
  [ -d "$TEST_REPO/.git/modules/sub" ]
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  WT1=$(setup_execution_workspace "$TEST_REPO" "c1" "worktree")
  [ -f "$WT1/sub/file.txt" ]
  # 第二个 change → 第二个 worktree 同样共享
  add_change "$TEST_REPO" "c2"
  git -C "$TEST_REPO" branch "openspec/c2" HEAD
  WT2=$(setup_execution_workspace "$TEST_REPO" "c2" "worktree")
  [ -f "$WT2/sub/file.txt" ]
  # 删除远程源后, 两个 worktree 的 update 均零网络成功
  rm -rf "$TEST_REPO/src"
  git -C "$WT1" submodule update --init --recursive >/dev/null 2>&1
  git -C "$WT2" submodule update --init --recursive >/dev/null 2>&1
  [ -f "$WT1/sub/file.txt" ]
  [ -f "$WT2/sub/file.txt" ]
  rm -rf "$TEST_REPO"
}
