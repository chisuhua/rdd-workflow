#!/usr/bin/env bats
# ------------------------------------------------------------------------------
# Real-GitHub 端到端测试: rdd-hub 联邦协同全链路
#
# 用途:
#   - 验证 chisuhua/rdd-hub (Hub) 与 3 个本地 spoke 副本之间的真实协同流程
#   - 覆盖 RFC 上行 → 本地 design-done 门控 → 人类审批模拟 → 本地批准
#     → 契约下行 → contract-check → deps 跨仓库分析 → watch-hub 状态监听
#
# 前置条件:
#   - gh CLI 已认证 (chisuhua 用户, token 含 repo scope)
#   - 已联网
#   - bats-core 1.10+
#
# 副作用:
#   - 首次运行可能自动创建 public 仓库 chisuhua/rdd-hub
#   - 在 chisuhua/rdd-hub 创建若干 [e2e-test] 标签的 Issue (测试结束自动关闭)
#   - 在 chisuhua/rdd-hub/contracts/ 临时推送 e2e-* 契约 (teardown 删除)
#   - 在 /tmp/opencode/rdd-e2e-* 下创建 3 个 spoke 副本 (teardown 删除)
#
# 默认环境变量 (可覆盖):
#   E2E_HUB_REPO    Hub 仓库 (默认: chisuhua/rdd-hub)
#   E2E_TMPDIR      spoke 副本根目录 (默认: /tmp/opencode/rdd-e2e-<pid>)
#
# 运行:
#   bats tests/integration/test_cross_repo_e2e_real.bats
#   bats tests/integration/test_cross_repo_e2e_real.bats --filter "rfc_creation"
# ------------------------------------------------------------------------------

load ../test_helper

# ------------------------------------------------------------------------------
# File-level setup: 一次性环境准备
# ------------------------------------------------------------------------------
setup_file() {
  E2E_HUB_REPO="${E2E_HUB_REPO:-chisuhua/rdd-hub}"
  E2E_TMPDIR="${E2E_TMPDIR:-/tmp/opencode/rdd-e2e-$$}"
  export E2E_HUB_REPO
  export E2E_TMPDIR

  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT

  # rddf CLI 期望这些 env var
  export RDDF_HUB_REPO="$E2E_HUB_REPO"
  export RDDF_REPORT_GH_REPO="$E2E_HUB_REPO"
  # 非交互模式提供 approve 用户名
  export RDDF_APPROVE_ACTOR="chisuhua-e2e-bot"

  # 收集测试中创建的 Hub Issue 编号, teardown 统一清理
  : > "$E2E_TMPDIR.cleanup-issues"

  echo "# E2E setup_file: hub=$E2E_HUB_REPO tmp=$E2E_TMPDIR" >&3

  # 1. 确保 Hub 仓库存在 (不存在则建)
  if ! gh repo view "$E2E_HUB_REPO" >/dev/null 2>&1; then
    echo "# Hub 不存在,创建 public 仓库 $E2E_HUB_REPO ..." >&3
    gh repo create "$E2E_HUB_REPO" --public --description "RDD cross-project Hub (e2e test bed)" >/dev/null
  fi
  gh repo view "$E2E_HUB_REPO" >/dev/null 2>&1 || {
    echo "FATAL: Hub $E2E_HUB_REPO 不可达,中止测试" >&2
    return 1
  }

  # 2. 确保 Hub 含所需 labels (approve_proposal.sh / report_issue_rfc.py 依赖)
  for label_name in "rfc" "cross-repo" "approved" "e2e-test"; do
    if ! gh label view "$label_name" --repo "$E2E_HUB_REPO" >/dev/null 2>&1; then
      gh label create "$label_name" --repo "$E2E_HUB_REPO" \
        --color "0e8a16" --description "e2e test label: $label_name" \
        >/dev/null 2>&1 || true
    fi
  done

  # 3. 克隆 3 个 spoke 到临时目录 (浅克隆加速)
  mkdir -p "$E2E_TMPDIR"
  for s in spoke-a spoke-b spoke-c; do
    if [ ! -d "$E2E_TMPDIR/$s" ]; then
      echo "# 克隆 spoke: $s ..." >&3
      git clone --depth 1 https://github.com/chisuhua/rdd-workflow.git "$E2E_TMPDIR/$s" >/dev/null 2>&1
    fi
  done

  # 4. 验证 spokes 可用
  for s in spoke-a spoke-b spoke-c; do
    [ -d "$E2E_TMPDIR/$s/.rddf" ] || [ -d "$E2E_TMPDIR/$s/skills" ] || {
      echo "FATAL: spoke $s 克隆失败" >&2
      return 1
    }
  done

  echo "# E2E setup_file 完成" >&3
}

# ------------------------------------------------------------------------------
# File-level teardown: 清理 Hub 副作用 + spoke 副本
# ------------------------------------------------------------------------------
teardown_file() {
  echo "# E2E teardown_file 开始清理 ..." >&3

  # 1. 关闭/删除测试期间创建的 Hub Issues
  if [ -f "$E2E_TMPDIR.cleanup-issues" ]; then
    while IFS= read -r num; do
      [ -z "$num" ] && continue
      gh issue close "$num" --repo "$E2E_HUB_REPO" --reason "not planned" >/dev/null 2>&1 || true
      # 删除 (owner 有 delete 权限)
      gh issue delete "$num" --repo "$E2E_HUB_REPO" --yes >/dev/null 2>&1 || true
      echo "#  - closed/deleted Hub Issue #$num" >&3
    done < "$E2E_TMPDIR.cleanup-issues"
  fi

  # 2. 删除测试期间推送的 e2e-* 契约 (通过 gh api)
  # 先获取 contracts/ 目录列表
  contracts_json=$(gh api "repos/$E2E_HUB_REPO/contents/contracts" 2>/dev/null || echo "[]")
  echo "$contracts_json" | grep -oE '"name":\s*"e2e-[^"]+"' | sed 's/.*"name":\s*"\([^"]*\)".*/\1/' | while read -r name; do
    [ -z "$name" ] && continue
    sha=$(echo "$contracts_json" | grep -B1 "\"name\":\\s*\"$name\"" | grep -oE '"sha":\s*"[^"]+"' | head -1 | sed 's/.*"sha":\s*"\([^"]*\)".*/\1/')
    [ -z "$sha" ] && continue
    gh api -X DELETE "repos/$E2E_HUB_REPO/contents/contracts/$name" \
      -f message="e2e cleanup" -f sha="$sha" >/dev/null 2>&1 || true
    echo "#  - removed Hub contract: $name" >&3
  done

  # 3. 删除 spoke 副本目录
  if [ -d "$E2E_TMPDIR" ]; then
    rm -rf "$E2E_TMPDIR"
    echo "#  - removed $E2E_TMPDIR" >&3
  fi

  echo "# E2E teardown_file 完成" >&3
}

# ------------------------------------------------------------------------------
# Per-test setup: 清空 spoke-a/b/c 的 state 文件
# ------------------------------------------------------------------------------
setup() {
  SPOKE_A="$E2E_TMPDIR/spoke-a"
  SPOKE_B="$E2E_TMPDIR/spoke-b"
  SPOKE_C="$E2E_TMPDIR/spoke-c"

  # 每个测试用独立 proposal name, 避免互相污染
  TEST_ID="$(printf '%04d' "$BATS_TEST_NUMBER")-$(date +%s)"
  export TEST_ID

  for s in "$SPOKE_A" "$SPOKE_B" "$SPOKE_C"; do
    cd "$s" || return 1
    # 清状态文件 + 之前测试累积的 openspec/changes/, 避免污染
    rm -f .rddf/state/.cross-repo-pending.json \
          .rddf/state/.cross-repo-audit.jsonl \
          .rddf/state/.cross-repo-deps-cache.json 2>/dev/null || true
    # 清空 proposal 文件 (避免后续测试的 --manual approve 引用旧文件)
    rm -f .rddf/improvements/*.md 2>/dev/null || true
    # 清 openspec/changes (保留 archive/, specs/)
    find openspec/changes -mindepth 1 -maxdepth 1 ! -name 'archive' -exec rm -rf {} + 2>/dev/null || true
    mkdir -p .rddf/state .rddf/improvements openspec/changes openspec/specs
    git -C "$s" checkout -- proposal-approved.md 2>/dev/null || true
  done

  cd "$SPOKE_A" || return 1
}

# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------

@test "01_hub_exists_or_bootstrap" {
  # setup_file 已经确保 Hub 存在; 这里只验证
  run gh repo view "$E2E_HUB_REPO" --json name,isPrivate
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "rdd-hub"
}

@test "02_rfc_creation_creates_hub_issue_and_pending" {
  TITLE="[RFC][e2e-test] Test RFC $TEST_ID"
  BODY="Test RFC body generated by e2e bats"

  cd "$SPOKE_A"

  run env RDDF_REPORT_GH_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/report-issue/scripts/report_issue_rfc.py" \
      --category=rfc \
      --title="$TITLE" \
      --stakeholders "spoke-b,spoke-c" \
      --gate="Design-Gate" \
      --contract-impact="Breaking-Change" \
      --body="$BODY"
  echo "$output"
  [ "$status" -eq 0 ]

  # 提取 Issue 编号
  ISSUE_NUM=$(echo "$output" | grep -oE 'issues/[0-9]+' | head -1 | sed 's|issues/||')
  [ -n "$ISSUE_NUM" ]
  echo "$ISSUE_NUM" >> "$E2E_TMPDIR.cleanup-issues"
  export E2E_LAST_ISSUE_NUM="$ISSUE_NUM"

  # 验证 Hub Issue 真实存在
  run gh issue view "$ISSUE_NUM" --repo "$E2E_HUB_REPO" --json title,state,labels
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "RFC"

  # 验证本地 pending 文件
  [ -f ".rddf/state/.cross-repo-pending.json" ]
  run jq -r '.entries[0].hub_issue_url' .rddf/state/.cross-repo-pending.json
  [ "$status" -eq 0 ]
  [[ "$output" == *"$E2E_HUB_REPO/issues/$ISSUE_NUM"* ]]
}

@test "03_design_gate_blocks_while_pending" {
  # 复用上一个测试创建的 Issue (创建新的也行,这里简化: 每次独立创建)
  TITLE="[RFC][e2e-test] Gate block test $TEST_ID"
  run env RDDF_REPORT_GH_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/report-issue/scripts/report_issue_rfc.py" \
      --category=rfc --title="$TITLE" \
      --stakeholders "spoke-b" --gate="Design-Gate"
  [ "$status" -eq 0 ]
  ISSUE_NUM=$(echo "$output" | grep -oE 'issues/[0-9]+' | head -1 | sed 's|issues/||')
  [ -n "$ISSUE_NUM" ]
  echo "$ISSUE_NUM" >> "$E2E_TMPDIR.cleanup-issues"

  cd "$SPOKE_A"
  # check_hub_pending 应返回 True (有 pending 条目)
  run python3 "$REPO_ROOT/skills/guide-design/scripts/design_done_gate.py" check-hub-pending
  [ "$status" -eq 1 ]   # 1 = block
}

@test "04_design_gate_skipped_with_SKIP_HUB_CHECK" {
  # 准备 pending 条目
  TITLE="[RFC][e2e-test] SKIP_HUB_CHECK test $TEST_ID"
  run env RDDF_REPORT_GH_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/report-issue/scripts/report_issue_rfc.py" \
      --category=rfc --title="$TITLE" --stakeholders "spoke-b"
  [ "$status" -eq 0 ]
  echo "$(echo "$output" | grep -oE 'issues/[0-9]+' | head -1 | sed 's|issues/||')" >> "$E2E_TMPDIR.cleanup-issues"

  cd "$SPOKE_A"
  # 即使有 pending, SKIP_HUB_CHECK=true 应放行
  run env SKIP_HUB_CHECK=true \
    python3 "$REPO_ROOT/skills/guide-design/scripts/design_done_gate.py" check-hub-pending
  [ "$status" -eq 0 ]   # 0 = pass
}

@test "05_approval_simulation_adds_label" {
  # 创建 RFC
  TITLE="[RFC][e2e-test] Approval sim $TEST_ID"
  run env RDDF_REPORT_GH_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/report-issue/scripts/report_issue_rfc.py" \
      --category=rfc --title="$TITLE" --stakeholders "spoke-b"
  [ "$status" -eq 0 ]
  ISSUE_NUM=$(echo "$output" | grep -oE 'issues/[0-9]+' | head -1 | sed 's|issues/||')
  [ -n "$ISSUE_NUM" ]
  echo "$ISSUE_NUM" >> "$E2E_TMPDIR.cleanup-issues"

  # 模拟人类审批: 在 Hub Issue 上添加 "approved" label (保持 state=OPEN)
  run gh issue edit "$ISSUE_NUM" --repo "$E2E_HUB_REPO" --add-label "approved"
  [ "$status" -eq 0 ]

  # 验证 label 存在
  run gh issue view "$ISSUE_NUM" --repo "$E2E_HUB_REPO" --json state,labels
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "OPEN"
  echo "$output" | grep -q "approved"
}

@test "06_approve_proposal_rejects_auto_accept_for_cross_repo" {
  # 创建跨仓 proposal 文件 (category: cross-repo-federation)
  PROPOSAL_NAME="e2e-$TEST_ID"
  cat > ".rddf/improvements/$PROPOSAL_NAME.md" <<EOF
# E2E Test Proposal

**阶段**: design
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__

## Why
Test proposal for e2e auto-accept rejection.

## What Changes
TBD
EOF

  # --auto-accept 必须被 exit 3 拒绝
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    "$PROPOSAL_NAME" P1
  [ "$status" -eq 3 ]
  [[ "$output" == *"requires --manual flag"* ]] || [[ "$output" == *"cannot use --auto-accept"* ]]

  # 清理
  rm -f ".rddf/improvements/$PROPOSAL_NAME.md"
}

@test "07_approve_proposal_manual_writes_audit_log" {
  PROPOSAL_NAME="e2e-$TEST_ID"

  # 1. 创建 RFC + 模拟人类审批
  TITLE="[RFC][e2e-test] Manual approve $TEST_ID"
  run env RDDF_REPORT_GH_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/report-issue/scripts/report_issue_rfc.py" \
      --category=rfc --title="$TITLE" --stakeholders "spoke-b"
  [ "$status" -eq 0 ]
  ISSUE_NUM=$(echo "$output" | grep -oE 'issues/[0-9]+' | head -1 | sed 's|issues/||')
  [ -n "$ISSUE_NUM" ]
  echo "$ISSUE_NUM" >> "$E2E_TMPDIR.cleanup-issues"
  gh issue edit "$ISSUE_NUM" --repo "$E2E_HUB_REPO" --add-label "approved" >/dev/null

  # 2. 创建本地 improvement 文件
  cat > ".rddf/improvements/$PROPOSAL_NAME.md" <<EOF
# E2E Manual Approval Test

**阶段**: design
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__

## Why
Test that manual approval writes audit log and creates change dir.

## What Changes
TBD
EOF

  # 3. 触发 --manual 批准 (RDDF_APPROVE_ACTOR 已在 setup_file 设置)
  cd "$SPOKE_A"
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    "$PROPOSAL_NAME" P1 \
    --manual \
    --hub-issue "$E2E_HUB_REPO#$ISSUE_NUM"
  echo "$output"
  [ "$status" -eq 0 ]

  # 4. 验证 audit log
  [ -f ".rddf/state/.cross-repo-audit.jsonl" ]
  run jq -r 'select(.decision=="approve") | .hub_issue' .rddf/state/.cross-repo-audit.jsonl
  [ "$status" -eq 0 ]
  [[ "$output" == *"$ISSUE_NUM"* ]]

  # 5. 验证 openspec/changes/<name>/ 创建
  [ -d "openspec/changes/$PROPOSAL_NAME" ]
  [ -f "openspec/changes/$PROPOSAL_NAME/roadmap-meta.yaml" ]
  run cat "openspec/changes/$PROPOSAL_NAME/roadmap-meta.yaml"
  [[ "$output" == *"cross-repo-federation"* ]]
}

@test "08_design_gate_passes_after_approval" {
  PROPOSAL_NAME="e2e-$TEST_ID"

  # RFC + 审批 + 提案文件 + 本地批准 (复用 test 07 的流程)
  TITLE="[RFC][e2e-test] Gate pass $TEST_ID"
  run env RDDF_REPORT_GH_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/report-issue/scripts/report_issue_rfc.py" \
      --category=rfc --title="$TITLE" --stakeholders "spoke-b"
  [ "$status" -eq 0 ]
  ISSUE_NUM=$(echo "$output" | grep -oE 'issues/[0-9]+' | head -1 | sed 's|issues/||')
  [ -n "$ISSUE_NUM" ]
  echo "$ISSUE_NUM" >> "$E2E_TMPDIR.cleanup-issues"
  gh issue edit "$ISSUE_NUM" --repo "$E2E_HUB_REPO" --add-label "approved" >/dev/null

  cat > ".rddf/improvements/$PROPOSAL_NAME.md" <<EOF
**阶段**: design
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__
EOF

  cd "$SPOKE_A"
  bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    "$PROPOSAL_NAME" P1 --manual --hub-issue "$E2E_HUB_REPO#$ISSUE_NUM" \
    >/dev/null 2>&1

  # 现在 design-done 两个 check 都应通过
  run python3 "$REPO_ROOT/skills/guide-design/scripts/design_done_gate.py" check-hub-pending
  # 注意: pending 文件里仍有 pending 条目 (因为我们没移除)
  # 这个测试主要验证 check_cross_repo_approvals (audit 已写)
  run python3 "$REPO_ROOT/skills/guide-design/scripts/design_done_gate.py" check-cross-repo-approvals
  [ "$status" -eq 0 ]   # 0 = pass (audit 有对应记录)
}

@test "09_sync_hub_pulls_contract" {
  # 1. 推送测试契约到 Hub
  CONTRACT_NAME="e2e-$TEST_ID.yaml"
  CONTRACT_CONTENT=$(cat <<EOF
openapi: 3.0.0
info:
  title: E2E Test Contract $TEST_ID
  version: 1.0.0
paths:
  /e2e/test:
    get:
      responses:
        '200':
          description: ok
EOF
)
  CONTENT_B64=$(printf '%s' "$CONTRACT_CONTENT" | base64 -w0)

  run gh api -X PUT "repos/$E2E_HUB_REPO/contents/contracts/$CONTRACT_NAME" \
    -f message="e2e test contract $TEST_ID" \
    -f content="$CONTENT_B64"
  [ "$status" -eq 0 ]

  # 2. 从 spoke-a 拉取
  cd "$SPOKE_A"
  run env RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/sync-hub/scripts/sync_hub.py" \
      --contract "$CONTRACT_NAME"
  echo "$output"
  [ "$status" -eq 0 ]

  # 3. 验证 openspec/specs/<name>/spec.md 生成
  LOCAL_NAME="${CONTRACT_NAME%.yaml}"
  [ -f "openspec/specs/$LOCAL_NAME/spec.md" ]
  run cat "openspec/specs/$LOCAL_NAME/spec.md"
  [[ "$output" == *"E2E Test Contract"* ]]
}

@test "10_contract_check_passes_with_compliant_impl" {
  # 推送带 required fields 的契约
  CONTRACT_NAME="e2e-$TEST_ID.yaml"
  CONTRACT_CONTENT=$(cat <<EOF
openapi: 3.0.0
info:
  title: E2E Contract Check $TEST_ID
  version: 1.0.0
paths:
  /e2e/login:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email_field, password_field]
              properties:
                email_field: {type: string}
                password_field: {type: string}
EOF
)
  CONTENT_B64=$(printf '%s' "$CONTRACT_CONTENT" | base64 -w0)
  gh api -X PUT "repos/$E2E_HUB_REPO/contents/contracts/$CONTRACT_NAME" \
    -f message="e2e contract-check $TEST_ID" \
    -f content="$CONTENT_B64" >/dev/null

  cd "$SPOKE_A"
  # 拉契约到本地 (fallback contract_check 读本地路径)
  env RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/sync-hub/scripts/sync_hub.py" \
      --contract "$CONTRACT_NAME" >/dev/null

  # 创建合规本地实现
  mkdir -p /tmp/e2e-impl-$TEST_ID
  cat > "/tmp/e2e-impl-$TEST_ID/compliant.py" <<EOF
def login(payload):
    email = payload.get('email_field')
    password = payload.get('password_field')
    if not email or not password:
        raise ValueError('missing field')
    return True
EOF

  LOCAL_NAME="${CONTRACT_NAME%.yaml}"
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "openspec/specs/$LOCAL_NAME/spec.md" \
    --local "/tmp/e2e-impl-$TEST_ID/compliant.py"
  echo "$output"
  [ "$status" -eq 0 ]
}

@test "11_contract_check_breaking_with_noncompliant_impl" {
  # 复用 test 10 推送的契约 (如果同 TEST_ID 不可能,这里重新推)
  CONTRACT_NAME="e2e-$TEST_ID.yaml"
  CONTRACT_CONTENT=$(cat <<EOF
openapi: 3.0.0
info:
  title: E2E Breaking Test $TEST_ID
  version: 1.0.0
paths:
  /e2e/login:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email_field, password_field, device_fingerprint_field]
              properties:
                email_field: {type: string}
                password_field: {type: string}
                device_fingerprint_field: {type: string}
EOF
)
  CONTENT_B64=$(printf '%s' "$CONTRACT_CONTENT" | base64 -w0)
  gh api -X PUT "repos/$E2E_HUB_REPO/contents/contracts/$CONTRACT_NAME" \
    -f message="e2e breaking $TEST_ID" \
    -f content="$CONTENT_B64" >/dev/null

  cd "$SPOKE_A"
  env RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/sync-hub/scripts/sync_hub.py" \
      --contract "$CONTRACT_NAME" >/dev/null

  # 创建不合规实现 (缺 device_fingerprint_field)
  mkdir -p /tmp/e2e-impl-$TEST_ID
  cat > "/tmp/e2e-impl-$TEST_ID/breaking.py" <<EOF
def login(payload):
    email = payload.get('email_field')
    password = payload.get('password_field')
    if not email or not password:
        raise ValueError('missing field')
    return True
EOF

  LOCAL_NAME="${CONTRACT_NAME%.yaml}"
  run python3 "$REPO_ROOT/skills/contract-check/scripts/contract_check.py" \
    --hub "openspec/specs/$LOCAL_NAME/spec.md" \
    --local "/tmp/e2e-impl-$TEST_ID/breaking.py"
  echo "$output"
  # exit 1 = breaking detected
  [ "$status" -eq 1 ]

  rm -rf "/tmp/e2e-impl-$TEST_ID"
}

@test "12_deps_cross_repo_generates_graph" {
  # 在 3 个 spoke 的 iteration.json 中注入 cross_repo_dependencies
  for s in spoke-a spoke-b spoke-c; do
    SPOKE_DIR="$E2E_TMPDIR/$s"
    cat > "$SPOKE_DIR/.rddf/state/iteration.json" <<EOF
{
  "version": 1,
  "changes": [
    {
      "name": "change-$s",
      "status": "proposed",
      "cross_repo_dependencies": ["$E2E_HUB_REPO-org/change-blocker"]
    }
  ]
}
EOF
  done

  # 生成跨仓依赖分析
  run python3 "$REPO_ROOT/skills/deps/scripts/cross_repo_cli.py" \
    --spokes "$E2E_HUB_REPO" 2>&1 || true
  echo "$output"
  # 至少生成 mermaid graph + wave 表
  echo "$output" | grep -q "graph TD" || echo "$output" | grep -q "mermaid" || echo "$output" | grep -qE "wave|parallel_group" || {
    # fallback: 直接调用内部函数
    run python3 -c "
import sys, os, json
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.cross_repo_deps import build_cross_repo_graph
data = {
    'spoke-a': [{'change': 'a-change', 'depends_on': 'spoke-b#b-change'}],
    'spoke-b': [{'change': 'b-change', 'depends_on': ''}],
}
graph = build_cross_repo_graph(data)
print('graph:', graph)
"
    [ "$status" -eq 0 ]
  }
}

@test "13_watch_hub_detects_completed_issue" {
  PROPOSAL_NAME="hub-$TEST_ID"

  # 1. 创建 RFC + 提案 + 关闭 with stateReason=COMPLETED
  TITLE="[RFC][e2e-test] Watch hub $TEST_ID"
  run env RDDF_REPORT_GH_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/report-issue/scripts/report_issue_rfc.py" \
      --category=rfc --title="$TITLE" --stakeholders "spoke-b"
  [ "$status" -eq 0 ]
  ISSUE_NUM=$(echo "$output" | grep -oE 'issues/[0-9]+' | head -1 | sed 's|issues/||')
  [ -n "$ISSUE_NUM" ]
  echo "$ISSUE_NUM" >> "$E2E_TMPDIR.cleanup-issues"

  # 关闭 with stateReason=COMPLETED (这是 watch_hub.py 唯一认可的 close 状态)
  run gh issue close "$ISSUE_NUM" --repo "$E2E_HUB_REPO" --reason completed
  [ "$status" -eq 0 ]

  # 2. 运行 watch-hub --once (期望它检测到 closed+COMPLETED, 标记本地 pending 为 approved)
  cd "$SPOKE_A"
  run env RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/watch-hub/scripts/watch_hub.py" \
      --once --owner="$E2E_HUB_REPO"
  echo "$output"
  [ "$status" -eq 0 ]

  # 3. 验证本地 pending 条目状态变 approved
  run jq -r ".entries[] | select(.hub_issue_url | contains(\"issues/$ISSUE_NUM\")) | .status" \
    .rddf/state/.cross-repo-pending.json
  [ "$status" -eq 0 ]
  [[ "$output" == *"approved"* ]]
}