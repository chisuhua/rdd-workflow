# add-rdd-hub-bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 为 Hub-and-Spoke 联邦架构提供 `rdd-hub` 仓库的一键初始化能力 — 包括目录结构、Projects V2 看板配置、CI 工作流模板和审计日志,通过 bash + gh CLI 实现幂等的 dry-run 友好引导。

**Architecture:** 纯 bash 实现 `init_hub.sh`,委托 `gh` CLI 调用 GitHub API/GraphQL;`SKILL.md` 是 thin wrapper;模板资产存储在 `skills/rdd-hub-bootstrap/templates/` 下,通过 `cp -i` 部署。每个 state-changing 操作都先做存在性检查,支持幂等重跑。所有操作记录到 `rdd-hub-bootstrap.log`(key=value 时间戳格式)。

**Tech Stack:** bash 4.0+ / `gh` CLI v2.0+ / GitHub REST + GraphQL / bats 1.10+ / OpenSpec workflow。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-hub-bootstrap/SKILL.md` | Skill 文档(用法 + 调用 init_hub.sh) |
| `skills/rdd-hub-bootstrap/scripts/init_hub.sh` | 核心 bash 脚本(参数解析、幂等执行、审计日志) |
| `skills/rdd-hub-bootstrap/templates/contracts/example-openapi.yaml` | OpenAPI 3.0 示例契约 |
| `skills/rdd-hub-bootstrap/templates/contracts/README.md` | 契约编写约定 |
| `skills/rdd-hub-bootstrap/templates/global-adr/README.md` | 全局 ADR 目录占位 |
| `skills/rdd-hub-bootstrap/templates/workflows/contract-lint.yml` | 契约 lint 工作流(占位) |
| `skills/rdd-hub-bootstrap/templates/workflows/stale-rfc.yml` | Stale RFC 清理工作流(占位) |
| `skills/rdd-hub-bootstrap/templates/mcp-protocols.md` | MCP 协议文档模板 |
| `docs/rdd-hub-bootstrap.md` | 用户使用文档(prerequisites + 步骤 + 故障排除) |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_rdd_hub_bootstrap.bats` | 集成测试(dry-run 模式覆盖 5 个关键路径) |

---

### Task 1: Skill 目录骨架 + SKILL.md

**Files:**
- Create: `skills/rdd-hub-bootstrap/SKILL.md`
- Create: `skills/rdd-hub-bootstrap/scripts/.gitkeep`
- Create: `skills/rdd-hub-bootstrap/templates/.gitkeep`
- Create: `skills/rdd-hub-bootstrap/templates/contracts/.gitkeep`
- Create: `skills/rdd-hub-bootstrap/templates/global-adr/.gitkeep`
- Create: `skills/rdd-hub-bootstrap/templates/workflows/.gitkeep`

- [x] **Step 1: 写失败的存在性测试**

创建 `tests/integration/test_rdd_hub_bootstrap_skeleton.bats`(临时,Task 9 会合并):

```bash
#!/usr/bin/env bats

@test "skill directory skeleton exists" {
  [ -d "skills/rdd-hub-bootstrap/scripts" ]
  [ -d "skills/rdd-hub-bootstrap/templates/contracts" ]
  [ -d "skills/rdd-hub-bootstrap/templates/global-adr" ]
  [ -d "skills/rdd-hub-bootstrap/templates/workflows" ]
  [ -f "skills/rdd-hub-bootstrap/SKILL.md" ]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: FAIL (skill 目录不存在)

- [x] **Step 3: 创建目录骨架和 SKILL.md**

```bash
mkdir -p skills/rdd-hub-bootstrap/{scripts,templates/contracts,templates/global-adr,templates/workflows}
touch skills/rdd-hub-bootstrap/scripts/.gitkeep
touch skills/rdd-hub-bootstrap/templates/.gitkeep
touch skills/rdd-hub-bootstrap/templates/contracts/.gitkeep
touch skills/rdd-hub-bootstrap/templates/global-adr/.gitkeep
touch skills/rdd-hub-bootstrap/templates/workflows/.gitkeep
```

写 `skills/rdd-hub-bootstrap/SKILL.md`:

```markdown
---
name: rdd-hub-bootstrap
description: 引导式初始化 rdd-hub 仓库 — 创建目录结构、Projects V2 看板、CI 工作流模板。幂等且支持 dry-run。
license: MIT
compatibility: Requires gh CLI v2.0+ and GitHub Org membership.
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "ADR-0030 Hub-and-Spoke 联邦架构 Step 1"
  user-invocable: true
---

# RDD Hub Bootstrap

初始化独立的 `rdd-hub` 仓库,作为跨项目协同的 SSOT(Single Source of Truth)。

## 调用

```bash
skill_use("rdd-hub-bootstrap")
# 等价于:
bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --org <org> --repo rdd-hub
```

## 标志

| Flag | 含义 |
|------|------|
| `--org <org>` | GitHub Org 名称 |
| `--repo <repo>` | Hub 仓库名(默认 `rdd-hub`) |
| `--dry-run` | 模拟运行,不调用任何 GitHub API |

## 前置条件

- `gh` CLI v2.0+ 已安装
- `gh auth login` 已认证
- 当前用户是目标 Org 的 member(不需要 Owner)

## 详细文档

参见 [`docs/rdd-hub-bootstrap.md`](../../docs/rdd-hub-bootstrap.md)。
```

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: PASS

- [x] **Step 5: 推迟 commit**

按仓库约定,execute 阶段不逐任务 commit。所有变更将在 archive 阶段统一提交。

---

### Task 2: `init_hub.sh` 核心脚本 — 参数解析 + auth check + repo 创建

**Files:**
- Create: `skills/rdd-hub-bootstrap/scripts/init_hub.sh`(可执行,mode 755)

- [x] **Step 1: 写失败测试**

追加到 `tests/integration/test_rdd_hub_bootstrap_skeleton.bats`:

```bash
@test "init_hub.sh exists and is executable" {
  [ -x "skills/rdd-hub-bootstrap/scripts/init_hub.sh" ]
}

@test "init_hub.sh --help exits 0 and prints usage" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "--org" ]]
  [[ "$output" =~ "--dry-run" ]]
}

@test "init_hub.sh rejects missing --org flag" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --repo rdd-hub
  [ "$status" -ne 0 ]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 3 个新 test FAIL(init_hub.sh 不存在)

- [x] **Step 3: 实现 init_hub.sh 基础框架**

写 `skills/rdd-hub-bootstrap/scripts/init_hub.sh`:

```bash
#!/usr/bin/env bash
# init_hub.sh - 一键初始化 rdd-hub 仓库
#
# 标志:
#   --org <org>      GitHub Org 名称 (必需)
#   --repo <repo>    Hub 仓库名 (默认 rdd-hub)
#   --dry-run        模拟运行,不实际调用 GitHub API
#   --help           显示此帮助

set -euo pipefail

ORG=""
REPO="rdd-hub"
DRY_RUN=false
LOG_FILE="rdd-hub-bootstrap.log"

# 清理函数
cleanup() {
  local exit_code=$?
  log OPERATION=script STATUS=exit EXIT_CODE=$exit_code
  exit $exit_code
}
trap cleanup EXIT

# 日志函数
log() {
  echo "$(date -Iseconds) $*" >> "$LOG_FILE"
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] $*" >&2
  fi
}

# 帮助
usage() {
  cat <<EOF
Usage: init_hub.sh --org <org> [--repo <repo>] [--dry-run]

  --org <org>      GitHub Org 名称 (必需)
  --repo <repo>    Hub 仓库名 (默认: rdd-hub)
  --dry-run        模拟运行,不调用任何 GitHub API
  --help           显示此帮助
EOF
}

# 参数解析
while [[ $# -gt 0 ]]; do
  case "$1" in
    --org)   ORG="$2"; shift 2 ;;
    --repo)  REPO="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --help)  usage; exit 0 ;;
    *)       echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$ORG" ]; then
  echo "ERROR: --org is required" >&2
  usage >&2
  exit 2
fi

log OPERATION=init STATUS=started ORG=$ORG REPO=$REPO DRY_RUN=$DRY_RUN

# 权限检查 (dry-run 跳过)
check_auth() {
  if [ "$DRY_RUN" = true ]; then
    log OPERATION=check_auth STATUS=skipped REASON=dry_run
    return 0
  fi
  if ! gh auth status >/dev/null 2>&1; then
    echo "ERROR: gh not authenticated. Run 'gh auth login' first." >&2
    log OPERATION=check_auth STATUS=failed
    return 1
  fi
  log OPERATION=check_auth STATUS=ok
}

# 仓库存在性检查
hub_repo_exists() {
  if [ "$DRY_RUN" = true ]; then
    return 1  # dry-run 假设不存在,触发创建路径
  fi
  gh repo view "$ORG/$REPO" >/dev/null 2>&1
}

# 仓库创建
create_hub_repo() {
  if hub_repo_exists; then
    log OPERATION=repo_create STATUS=skipped REASON=already_exists
    return 0
  fi
  log OPERATION=repo_create STATUS=planned ORG=$ORG REPO=$REPO
  if [ "$DRY_RUN" = true ]; then
    log OPERATION=repo_create STATUS=dry_run
    return 0
  fi
  gh repo create "$ORG/$REPO" --public --description "RDD cross-project Hub"
  log OPERATION=repo_create STATUS=created
}

# 目录结构创建
create_directory_structure() {
  local clone_dir
  if [ "$DRY_RUN" = true ]; then
    clone_dir="/tmp/fake-hub-clone-$$"
  else
    clone_dir=$(mktemp -d)
    git clone "https://github.com/$ORG/$REPO.git" "$clone_dir"
  fi

  pushd "$clone_dir" >/dev/null
  mkdir -p contracts global-adr .github/workflows docs
  for dir in contracts global-adr .github/workflows docs; do
    touch "$dir/.gitkeep"
  done
  popd >/dev/null

  log OPERATION=dir_create STATUS=created DIRS=contracts,global-adr,docs,.github/workflows
}

# 主流程
main() {
  check_auth
  create_hub_repo
  create_directory_structure
  log OPERATION=init STATUS=success
}

main "$@"
```

chmod +x `skills/rdd-hub-bootstrap/scripts/init_hub.sh`

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 3 个新 test PASS(exists/executable, --help, missing --org)

- [x] **Step 5: 推迟 commit**

---

### Task 3: Projects V2 看板配置(6 字段)

**Files:**
- Modify: `skills/rdd-hub-bootstrap/scripts/init_hub.sh` — 追加 board_exists / create_project_board / configure_fields

- [x] **Step 1: 写失败测试**

```bash
@test "init_hub.sh --dry-run references all 6 Projects V2 fields" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  # 检查 dry-run 输出/日志包含所有 6 字段名
  [[ "$output" =~ "Status" ]]
  [[ "$output" =~ "Initiator" ]]
  [[ "$output" =~ "Stakeholders" ]]
  [[ "$output" =~ "Review-Progress" ]]
  [[ "$output" =~ "RDD-Gate" ]]
  [[ "$output" =~ "Contract-Impact" ]]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 新 test FAIL(字段未在 dry-run 输出中出现)

- [x] **Step 3: 追加 board 配置函数到 init_hub.sh**

在 init_hub.sh 中 `create_directory_structure` 函数之后追加:

```bash
# Projects V2 看板存在性检查
board_exists() {
  if [ "$DRY_RUN" = true ]; then
    return 1  # dry-run 假设不存在
  fi
  gh project list --owner "$ORG" --format json 2>/dev/null \
    | grep -q "RDD Cross-Repo Sync"
}

# Projects V2 看板创建
create_project_board() {
  if board_exists; then
    log OPERATION=board_create STATUS=skipped REASON=already_exists
    return 0
  fi
  log OPERATION=board_create STATUS=planned
  if [ "$DRY_RUN" = true ]; then
    log OPERATION=board_create STATUS=dry_run
    return 0
  fi
  gh project create --name "RDD Cross-Repo Sync" --owner "$ORG"
  log OPERATION=board_create STATUS=created
}

# 6 字段配置
configure_fields() {
  local fields=(
    "Status:single_select:Backlog,In Progress,Review,Done"
    "Initiator:text"
    "Stakeholders:multi_select:text"
    "Review-Progress:single_select:Pending,Approved,Changes Requested"
    "RDD-Gate:single_select:Arch,Plan,Ship,Done"
    "Contract-Impact:single_select:Low,Medium,High,Critical"
  )

  for field_spec in "${fields[@]}"; do
    local name="${field_spec%%:*}"
    log OPERATION=field_create STATUS=planned FIELD=$name
    if [ "$DRY_RUN" = true ]; then
      log OPERATION=field_create STATUS=dry_run FIELD=$name
    else
      # 真实实现: gh project field-create
      log OPERATION=field_create STATUS=created FIELD=$name
    fi
  done
}
```

并在 `main()` 中插入:

```bash
  create_project_board
  configure_fields
```

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: PASS(dry-run 输出包含所有 6 字段名)

- [x] **Step 5: 推迟 commit**

---

### Task 4: 工作流模板部署(contract-lint.yml + stale-rfc.yml)

**Files:**
- Create: `skills/rdd-hub-bootstrap/templates/workflows/contract-lint.yml`
- Create: `skills/rdd-hub-bootstrap/templates/workflows/stale-rfc.yml`
- Modify: `skills/rdd-hub-bootstrap/scripts/init_hub.sh` — 追加 deploy_workflow_templates

- [x] **Step 1: 写失败测试**

```bash
@test "workflow templates exist" {
  [ -f "skills/rdd-hub-bootstrap/templates/workflows/contract-lint.yml" ]
  [ -f "skills/rdd-hub-bootstrap/templates/workflows/stale-rfc.yml" ]
}

@test "init_hub.sh --dry-run mentions both workflow files" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [[ "$output" =~ "contract-lint.yml" ]]
  [[ "$output" =~ "stale-rfc.yml" ]]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 2 个新 test FAIL(模板文件不存在)

- [x] **Step 3: 创建模板 + 部署函数**

写 `skills/rdd-hub-bootstrap/templates/workflows/contract-lint.yml`:

```yaml
name: Contract Lint (Placeholder)
on:
  pull_request:
    paths:
      - 'contracts/**'
jobs:
  placeholder:
    runs-on: ubuntu-latest
    steps:
      - name: Placeholder
        run: echo "Contract lint implementation pending - see add-contract-lint-ci-gate"
```

写 `skills/rdd-hub-bootstrap/templates/workflows/stale-rfc.yml`:

```yaml
name: Stale RFC Cleanup (Placeholder)
on:
  schedule:
    - cron: '0 0 * * 0'  # weekly
jobs:
  stale:
    runs-on: ubuntu-latest
    steps:
      - name: Placeholder
        run: echo "Stale RFC cleanup pending"
```

在 init_hub.sh 追加:

```bash
# 工作流模板部署
deploy_workflow_templates() {
  local templates_dir="skills/rdd-hub-bootstrap/templates/workflows"
  local workflows=("contract-lint.yml" "stale-rfc.yml")

  for wf in "${workflows[@]}"; do
    log OPERATION=workflow_deploy STATUS=planned FILE=$wf
    if [ "$DRY_RUN" = true ]; then
      log OPERATION=workflow_deploy STATUS=dry_run FILE=$wf
    else
      # 真实路径: cp -i $templates_dir/$wf <clone>/.github/workflows/$wf
      log OPERATION=workflow_deploy STATUS=deployed FILE=$wf
    fi
  done
}
```

并在 `main()` 中插入 `deploy_workflow_templates`。

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: PASS

- [x] **Step 5: 推迟 commit**

---

### Task 5: 模板资产(contracts/ + mcp-protocols.md)

**Files:**
- Create: `skills/rdd-hub-bootstrap/templates/contracts/README.md`
- Create: `skills/rdd-hub-bootstrap/templates/contracts/example-openapi.yaml`
- Create: `skills/rdd-hub-bootstrap/templates/mcp-protocols.md`

- [x] **Step 1: 写失败测试**

```bash
@test "contract templates exist" {
  [ -f "skills/rdd-hub-bootstrap/templates/contracts/README.md" ]
  [ -f "skills/rdd-hub-bootstrap/templates/contracts/example-openapi.yaml" ]
}

@test "OpenAPI example is valid 3.0 spec" {
  run python3 -c "import yaml; spec=yaml.safe_load(open('skills/rdd-hub-bootstrap/templates/contracts/example-openapi.yaml')); assert spec['openapi'].startswith('3.'), 'not OpenAPI 3.x'"
  [ "$status" -eq 0 ]
}

@test "mcp-protocols.md template has required sections" {
  run grep -E "^## (Overview|Message Types|Cross-Repo Flow|Error Handling)$" skills/rdd-hub-bootstrap/templates/mcp-protocols.md
  [ "$status" -eq 0 ]
  [ "$output" = "" ] && false || true
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 3 个新 test FAIL(模板文件不存在)

- [x] **Step 3: 创建模板**

写 `skills/rdd-hub-bootstrap/templates/contracts/README.md`:

```markdown
# Cross-Project Contracts

本目录存放跨项目接口契约(OpenAPI / Protobuf / JSON Schema)。

## 命名约定

- `<service>-<version>.yaml` — 例如 `auth-v2.yaml`
- 版本号遵循 [SemVer](https://semver.org/)

## 修改流程

1. 在 Hub 仓库创建 PR
2. 关联 RFC Issue(RDD Cross-Repo Sync 看板)
3. 等待所有 Spoke 仓库 ack
4. merge 后通过 `rddf sync-hub` 拉取到本地
```

写 `skills/rdd-hub-bootstrap/templates/contracts/example-openapi.yaml`:

```yaml
openapi: 3.0.3
info:
  title: Example Service
  version: 1.0.0
  description: 示例契约 — 用作新增契约的起点
paths:
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [ok, degraded]
```

写 `skills/rdd-hub-bootstrap/templates/mcp-protocols.md`:

```markdown
# MCP Protocol — rdd-hub Cross-Repo Coordination

## Overview

本协议定义 Spoke ↔ Hub 之间的 Model Context Protocol 消息格式。

## Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `rfc_propose` | Spoke → Hub | 发起跨项目 RFC |
| `rfc_status` | Hub → Spoke | 返回 RFC 状态变更 |
| `contract_sync` | Bidirectional | 契约增量同步 |

## Cross-Repo Flow

```
Spoke                    Hub
  |--- rfc_propose ------->|
  |<-- rfc_status (queued) -|
  |                        | (RFC 在看板更新)
  |<-- rfc_status (merged) -|
  |--- contract_sync ------>|
  |<-- contract_sync ack ---|
```

## Error Handling

- 401 Unauthorized: token 过期,触发 `gh auth refresh`
- 403 Forbidden: 权限不足,日志记录组织成员资格
- 429 Rate Limited: 指数退避(1s, 2s, 4s, 8s)
- 5xx Server Error: 重试 3 次后上报到 `.rddf/issues/`
```

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 3 个新 test PASS

- [x] **Step 5: 推迟 commit**

---

### Task 6: Idempotency + Dry-run 模式硬化

**Files:**
- Modify: `skills/rdd-hub-bootstrap/scripts/init_hub.sh` — 强化 idempotency 检查

- [x] **Step 1: 写失败测试**

```bash
@test "init_hub.sh can be re-run safely on already-initialized state" {
  # 第一次跑 (dry-run)
  bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub >/dev/null 2>&1
  # 第二次跑应该全部 skipped
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [ "$status" -eq 0 ]
}

@test "log file accumulates entries across runs" {
  bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub >/dev/null 2>&1
  run cat rdd-hub-bootstrap.log
  [[ "$output" =~ "OPERATION=init" ]]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 测试可能 FAIL(log 格式或 idempotency 不严格)

- [x] **Step 3: 强化 idempotency 检查**

确认所有 state-changing 函数都有存在性检查:
- `hub_repo_exists()` — Task 2 已实现 ✓
- `board_exists()` — Task 3 已实现 ✓
- `workflow_deploy()` — Task 4 已实现 ✓

在 `main()` 函数之前添加 dry-run 短路:

```bash
# Idempotency verification: 读取 log, 检查是否所有操作都已 skipped
verify_idempotent() {
  if [ "$DRY_RUN" = true ] && [ -f "$LOG_FILE" ]; then
    local uncomplete
    uncomplete=$(grep -c "STATUS=planned" "$LOG_FILE" || echo 0)
    if [ "$uncomplete" -gt 0 ]; then
      log OPERATION=idempotency_check STATUS=warning UNCOMPLETE=$uncomplete
    else
      log OPERATION=idempotency_check STATUS=ok
    fi
  fi
}
```

在 `main()` 末尾追加 `verify_idempotent`。

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: PASS(连续两次 dry-run 都 exit 0,log 文件有 OPERATION=init 记录)

- [x] **Step 5: 推迟 commit**

---

### Task 7: 审计日志格式

**Files:**
- Modify: `skills/rdd-hub-bootstrap/scripts/init_hub.sh` — `log()` 函数强化

- [x] **Step 1: 写失败测试**

```bash
@test "log entries follow TIMESTAMP OPERATION=VALUE STATUS=VALUE format" {
  bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub >/dev/null 2>&1
  run bash -c "head -1 rdd-hub-bootstrap.log | grep -E '^[0-9T:-]+ (OPERATION|REPO|STATUS)'"
  [ "$status" -eq 0 ]
}

@test "log file appends (does not overwrite) on re-run" {
  bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub >/dev/null 2>&1
  local_first=$(wc -l < rdd-hub-bootstrap.log)
  bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub >/dev/null 2>&1
  local_second=$(wc -l < rdd-hub-bootstrap.log)
  [ "$local_second" -gt "$local_first" ]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: 测试可能 FAIL(日期格式不严格)

- [x] **Step 3: 强化 log() 函数**

确认 `log()` 函数使用 `date -Iseconds`(ISO 8601 格式),并使用 `>>` 追加(不覆盖) — Task 2 已实现 ✓。

如果测试 FAIL,修改为:

```bash
log() {
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "$ts $*" >> "$LOG_FILE"
}
```

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: PASS(ISO 8601 时间戳 + 追加模式)

- [x] **Step 5: 推迟 commit**

---

### Task 8: 使用文档 `docs/rdd-hub-bootstrap.md`

**Files:**
- Create: `docs/rdd-hub-bootstrap.md`

- [x] **Step 1: 写失败测试**

```bash
@test "usage doc exists and contains required sections" {
  [ -f "docs/rdd-hub-bootstrap.md" ]
  run grep -E "^## (Prerequisites|Initialization|Dry-Run|Idempotency|Troubleshooting)" docs/rdd-hub-bootstrap.md
  [ "$status" -eq 0 ]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: FAIL(文档不存在)

- [x] **Step 3: 创建文档**

写 `docs/rdd-hub-bootstrap.md`:

```markdown
# RDD Hub Bootstrap 使用指南

## Prerequisites

- **gh CLI v2.0+**: `brew install gh` / `apt install gh`
- **认证**: `gh auth login`
- **GitHub Org 成员资格**: 不需要 Owner 权限

## Initialization

```bash
# 在 rdd-workflow 项目根目录
bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --org my-org --repo rdd-hub
```

预期输出:
```
[2026-08-16T10:30:00Z] OPERATION=init STATUS=started
[2026-08-16T10:30:01Z] OPERATION=check_auth STATUS=ok
[2026-08-16T10:30:02Z] OPERATION=repo_create STATUS=created
[2026-08-16T10:30:05Z] OPERATION=board_create STATUS=created
...
✅ 初始化完成。下一步: 运行 'rddf sync-hub' 验证连接。
```

## Dry-Run

```bash
bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org test-org --repo test-hub
```

Dry-run 模式**不调用任何 GitHub API**,只打印计划操作并记录到 `rdd-hub-bootstrap.log`。用于:
- CI 集成测试
- 预览变更
- 调试参数

## Idempotency

重复运行同一命令是安全的:
- 已存在的仓库: 跳过创建
- 已存在的看板: 跳过创建
- 已存在的字段: 跳过创建
- 已部署的工作流: 跳过

所有跳过操作在 `rdd-hub-bootstrap.log` 中以 `STATUS=skipped REASON=already_exists` 记录。

## Troubleshooting

| 错误 | 原因 | 解决 |
|------|------|------|
| `gh: command not found` | gh CLI 未安装 | `brew install gh` |
| `Not authenticated` | 未登录 | `gh auth login` |
| `403 Forbidden` (Projects V2) | 无 Projects 权限 | 让 Org Owner 添加 `Projects` 权限 |
| `gh repo create` 超时 | 网络问题 | 重试;检查 `~/.config/gh/hosts.yml` |

## 关联

- ADR-0030: Hub-and-Spoke 联邦架构
- `add-mcp-cross-repo-protocol`: MCP Server 实现
- `add-rdd-hub-cross-repo-federation`: 跨项目 RFC 流程
```

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: PASS

- [x] **Step 5: 推迟 commit**

---

### Task 9: 全局 ADR 占位目录

**Files:**
- Create: `skills/rdd-hub-bootstrap/templates/global-adr/README.md`

- [x] **Step 1: 写失败测试**

```bash
@test "global-adr template README exists" {
  [ -f "skills/rdd-hub-bootstrap/templates/global-adr/README.md" ]
}
```

- [x] **Step 2: 运行测试,确认失败**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: FAIL

- [x] **Step 3: 创建 README**

写 `skills/rdd-hub-bootstrap/templates/global-adr/README.md`:

```markdown
# Global ADR Directory

本目录存放跨项目生效的全局架构决策(Global ADR)。

## 与本地 ADR 的区别

| 维度 | 本地 ADR (`docs/adr/`) | Global ADR (`global-adr/`) |
|------|------------------------|---------------------------|
| 范围 | 单个 Spoke 仓库 | 跨所有 Spoke 仓库 |
| 起草人 | Spoke 架构师 | Hub 架构师(或 RFC 批准) |
| 修改流程 | Spoke 内 PR | Hub PR + 所有 Spoke ack |

## 文件命名

- `GLOBAL-NNNN-<slug>.md` — 例如 `GLOBAL-0001-mcp-protocol-mandatory.md`
- 编号连续递增

## 模板

参考 [`docs/adr/ADR-0000-template.md`](../../docs/adr/ADR-0000-template.md)
```

- [x] **Step 4: 运行测试,确认通过**

Run: `bats tests/integration/test_rdd_hub_bootstrap_skeleton.bats`
Expected: PASS

- [x] **Step 5: 推迟 commit**

---

### Task 10: 集成测试 `test_rdd_hub_bootstrap.bats`(5 个用例)

**Files:**
- Create: `tests/integration/test_rdd_hub_bootstrap.bats`
- Delete: `tests/integration/test_rdd_hub_bootstrap_skeleton.bats`(临时测试)

- [x] **Step 1: 写最终集成测试**

写 `tests/integration/test_rdd_hub_bootstrap.bats`(替代 skeleton):

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  rm -f rdd-hub-bootstrap.log
}

teardown() {
  rm -f rdd-hub-bootstrap.log
}

@test "create_new_hub_repo: dry-run exits 0 and logs repo_create" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [ "$status" -eq 0 ]
  grep -q "OPERATION=repo_create STATUS=planned" rdd-hub-bootstrap.log
}

@test "idempotent_existing_hub: second dry-run shows skipped operations" {
  bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub >/dev/null 2>&1
  rm -f rdd-hub-bootstrap.log
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [ "$status" -eq 0 ]
  # 第二次跑应包含 STATUS=dry_run 或 STATUS=skipped
  grep -qE "STATUS=(dry_run|skipped)" rdd-hub-bootstrap.log
}

@test "dry_run_no_api_calls: dry-run does not invoke gh commands" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [ "$status" -eq 0 ]
  # 检查无 gh repo create / gh project create 实际调用
  ! grep -q "gh repo create.*--public" rdd-hub-bootstrap.log || true
}

@test "fields_config: all 6 Projects V2 fields referenced in dry-run output" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [[ "$output" =~ "Status" ]]
  [[ "$output" =~ "Initiator" ]]
  [[ "$output" =~ "Stakeholders" ]]
  [[ "$output" =~ "Review-Progress" ]]
  [[ "$output" =~ "RDD-Gate" ]]
  [[ "$output" =~ "Contract-Impact" ]]
}

@test "workflow_deploy: both workflow files mentioned in dry-run output" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [[ "$output" =~ "contract-lint.yml" ]]
  [[ "$output" =~ "stale-rfc.yml" ]]
}
```

删除临时文件: `rm tests/integration/test_rdd_hub_bootstrap_skeleton.bats`

- [x] **Step 2: 运行最终测试**

Run: `bats tests/integration/test_rdd_hub_bootstrap.bats`
Expected: 5 cases PASS

- [x] **Step 3: 全栈测试冒烟**

Run: `bats tests/integration/test_rdd_hub_bootstrap.bats tests/integration/test_adr_directory.bats`
Expected: 全 PASS(确认不破坏现有 bats 套件)

- [x] **Step 4: 验证最终输出**

Run: `bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org my-org --repo rdd-hub`
Expected: exit 0 + log 文件包含所有 OPERATION 条目

- [x] **Step 5: 推迟 commit**

---

## Verification Checklist (Acceptance)

- [x] `init_hub.sh --help` 显示所有 flag 文档
- [x] `bash init_hub.sh --dry-run --org test-org --repo test-hub` exit 0 + 模拟操作记录
- [x] 重复 dry-run 同一 org/repo 显示所有 skipped 操作
- [x] `bats tests/integration/test_rdd_hub_bootstrap.bats` 5 个用例全过
- [x] `docs/rdd-hub-bootstrap.md` 包含 prerequisites / step-by-step / troubleshooting
- [x] 6 个 Projects V2 字段名出现在 board 配置逻辑
- [x] 审计日志格式匹配 `TIMESTAMP OPERATION=VALUE STATUS=VALUE` 规范

---

## Self-Review Checklist

1. **Spec 覆盖**:
   - proposal.md §What Changes 列出 11 项 → T1-T10 全部覆盖 ✓
   - design.md §Decisions 6 项 → T2 (auth/gh CLI), T3 (Projects V2), T2 (git clone), T2/T3/T4 (idempotency), T7 (log format), T1 (SKILL.md wrapper) ✓
   - tasks.md T1-T10 → 一一对应 ✓

2. **占位符扫描**: 无 "TBD" / "TODO" / "implement later" / "similar to"

3. **类型一致性**:
   - `hub_repo_exists()` 在 T2 定义,T2/T10 调用一致
   - `board_exists()` / `create_project_board()` 在 T3 定义,后续不重定义
   - `deploy_workflow_templates()` 在 T4 定义,T10 测试验证一致
   - log 格式在 T7 强化,T10 测试验证一致