#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  # canonical 项目根。linked worktree 下 resolver 按 ADR-0033 返回**主仓根**
  # （而非 worktree 目录），故此处必须问 resolver，不能用 $REPO_ROOT 顶替 ——
  # 否则用例在 worktree 模式既误判、又把缓存写进主仓 state。
  PROJECT_ROOT="$(python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib._python_resolve_project_root import resolve_project_root
print(resolve_project_root(start_dir='$REPO_ROOT'))
")"
  export PROJECT_ROOT
  cat > "$TMP/iteration.json" <<'EOF'
{"version": 7, "changes": {"x": {"name": "x", "cross_repo_dependencies": []}}}
EOF
}

teardown() { rm -rf "$TMP"; }

@test "rddf deps cross-repo --help" {
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" --help \
    --cache-file "$TMP/.cross-repo-deps-cache.json"
  [ "$status" -eq 0 ]
}

@test "rddf deps cross-repo --output-format json" {
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" \
    --spokes "fake-org/fake-repo" \
    --output-format json \
    --cache-file "$TMP/.cross-repo-deps-cache.json"
  [ "$status" -eq 0 ]
}

@test "rddf deps cross-repo --output-format mermaid" {
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" \
    --spokes "fake-org/fake-repo" \
    --output-format mermaid \
    --cache-file "$TMP/.cross-repo-deps-cache.json"
  [ "$status" -eq 0 ]
}

@test "cross-repo deps: default cache path lands under the project root, not the CWD" {
  # 红基线用例：默认路径当前是 CWD 相对 → 文件落在 $tmpcwd 而不是仓库根。
  # 本用例故意会往仓库根写一次文件，结束前自己清理（AC-2 要求跑完 bats 后仓库里没有它）。
  local real_cache="$PROJECT_ROOT/.rddf/state/.cross-repo-deps-cache.json"
  rm -f "$real_cache"

  local tmpcwd="$TMP/cwd"
  mkdir -p "$tmpcwd/.rddf/state"      # 让「落错位置」能真的写成功，断言才有区分度

  cd "$tmpcwd"
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" \
    --spokes "fake-org/fake-repo" --output-format json
  cd "$REPO_ROOT"

  [ "$status" -eq 0 ]
  [ -f "$real_cache" ]
  [ ! -f "$tmpcwd/.rddf/state/.cross-repo-deps-cache.json" ]

  rm -f "$real_cache"
}

@test "cross-repo deps: writes cache to the given path, not the real project state" {
  local real_cache="$PROJECT_ROOT/.rddf/state/.cross-repo-deps-cache.json"
  rm -f "$real_cache"

  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" \
    --spokes "fake-org/fake-repo" --output-format json \
    --cache-file "$TMP/.cross-repo-deps-cache.json"
  [ "$status" -eq 0 ]
  [ -f "$TMP/.cross-repo-deps-cache.json" ]
  [ ! -f "$real_cache" ]
}
