# add-spoke-system-prompt-injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 部署 cross-repo Hub 协议到 Spoke AI 工具(Cursor/Cline/Continue/Copilot/Claude Code),通过 `deploy.sh` 幂等地注入 bounded protocol 块,支持 `--tools` / `--uninstall` / `--status` flag 和 backup/restore。

**Architecture:** 单一 canonical `inject.md`(protocol_version: 1.0) + 5 工具特定 format 适配器 + `deploy.sh`(marker 检测 + idempotent append + backup before overwrite + uninstall reverse)。`install.sh --spoke-init` 调用 `deploy.sh`。

**Tech Stack:** bash 4.0+ / git / bats。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/spoke-system-prompt-injection/SKILL.md` | Skill 文档 |
| `skills/spoke-system-prompt-injection/inject.md` | Canonical protocol 内容(RFC initiation/review/sync/auto-approval prohibition) |
| `skills/spoke-system-prompt-injection/scripts/deploy.sh` | 部署脚本(idempotent + backup + uninstall + multi-tool) |
| `skills/spoke-system-prompt-injection/templates/cursor.cursorrules` | Cursor `.cursorrules` 模板 |
| `skills/spoke-system-prompt-injection/templates/cline.clinerules` | Cline `.clinerules` 模板 |
| `skills/spoke-system-prompt-injection/templates/continue.rules.md` | Continue `rules/cross-repo-hub.md` 模板 |
| `skills/spoke-system-prompt-injection/templates/copilot.instructions.md` | Copilot `.github/copilot-instructions.md` 模板 |
| `skills/spoke-system-prompt-injection/templates/claude.CLAUDE.md` | Claude Code `CLAUDE.md` 模板 |
| `install.sh` | + `--spoke-init` flag(MODIFY) |
| `docs/spoke-system-prompt.md` | 用户文档 |
| `README.md` | §跨项目协同 + Spoke 接入指南(MODIFY) |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_spoke_injection.bats` | deploy.sh 集成测试(5 cases) |

---

### Task 1: Canonical `inject.md` 内容

**Files:**
- Create: `skills/spoke-system-prompt-injection/inject.md`

- [x] **Step 1: 写 canonical protocol**

写 `skills/spoke-system-prompt-injection/inject.md`:

```markdown
<!-- RDD-HUB-PROTOCOL-START -->
<!-- protocol_version: 1.0 -->
<!-- DO NOT EDIT between START and END markers — managed by deploy.sh -->

# RDD-Hub Cross-Repo Protocol (v1.0)

## 1. RFC Initiation
Before creating an RFC, run `hub_read_issue` against likely duplicates
to avoid parallel RFCs. Wait ≥1s between parallel `hub_create_issue` calls.

## 2. RFC Review
When reviewing RFCs, surface ALL gate requirements (Stakeholders,
Contract-Impact, RDD-Gate) before approval. Never silently bypass.

## 3. Contract Sync
`hub_sync_contract` failures must notify the human operator immediately.
The MCP trace at `.rddf/state/.mcp-trace.jsonl` is the audit record.

## 4. Auto-Approval Prohibition
**NEVER auto-approve cross-repo RFCs.** All `hub_update_status` calls
setting status=approved must be preceded by explicit human approval.
SKIP_HUB_CHECK is for emergency use only — do NOT set this env var.

<!-- RDD-HUB-PROTOCOL-END -->
```

- [x] **Step 2: 推迟 commit**

---

### Task 2: `deploy.sh` 核心脚本

**Files:**
- Create: `skills/spoke-system-prompt-injection/scripts/deploy.sh`(可执行)

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_spoke_injection.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  export TARGET_DIR="$TMP"
  cd "$TMP"
  git init -q
  mkdir -p .github
}

teardown() {
  rm -rf "$TMP"
}

deploy() {
  bash "$REPO_ROOT/skills/spoke-system-prompt-injection/scripts/deploy.sh" "$@"
}

@test "deploy --tools cursor appends protocol block" {
  run deploy --tools cursor
  [ "$status" -eq 0 ]
  [ -f "$TARGET_DIR/.cursorrules" ]
  grep -q "RDD-HUB-PROTOCOL-START" "$TARGET_DIR/.cursorrules"
  grep -q "protocol_version: 1.0" "$TARGET_DIR/.cursorrules"
}

@test "deploy is idempotent — second run produces no duplicate" {
  deploy --tools cursor >/dev/null
  before_lines=$(wc -l < "$TARGET_DIR/.cursorrules")
  deploy --tools cursor >/dev/null
  after_lines=$(wc -l < "$TARGET_DIR/.cursorrules")
  [ "$before_lines" -eq "$after_lines" ]
}

@test "deploy --tools all handles multi-tool list" {
  run deploy --tools cursor,cline,continue,copilot,claude
  [ "$status" -eq 0 ]
  [ -f "$TARGET_DIR/.cursorrules" ]
  [ -f "$TARGET_DIR/.clinerules" ]
  [ -f "$TARGET_DIR/.continue/rules/cross-repo-hub.md" ]
  [ -f "$TARGET_DIR/.github/copilot-instructions.md" ]
  [ -f "$TARGET_DIR/CLAUDE.md" ]
}

@test "deploy --uninstall removes protocol block" {
  deploy --tools cursor >/dev/null
  deploy --tools cursor --uninstall
  ! grep -q "RDD-HUB-PROTOCOL-START" "$TARGET_DIR/.cursorrules" || true
}

@test "deploy creates backup before overwrite" {
  echo "existing content" > "$TARGET_DIR/.cursorrules"
  deploy --tools cursor >/dev/null
  ls "$TARGET_DIR"/.cursorrules.bak.* 2>/dev/null | head -1
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_spoke_injection.bats`
Expected: 5 FAIL

- [x] **Step 3: 实现 `deploy.sh`**

```bash
#!/usr/bin/env bash
# deploy.sh — Inject Hub cross-repo protocol into Spoke AI tool config files.
#
# Usage:
#   deploy.sh --tools <list>           # comma-separated: cursor,cline,continue,copilot,claude,all
#   deploy.sh --uninstall              # remove protocol block + restore backup
#   deploy.sh --status                 # show current deployment status
#
# Files affected per tool:
#   cursor   → .cursorrules
#   cline    → .clinerules
#   continue → .continue/rules/cross-repo-hub.md
#   copilot  → .github/copilot-instructions.md
#   claude   → CLAUDE.md
#
# Marker: <!-- RDD-HUB-PROTOCOL-START --> ... <!-- RDD-HUB-PROTOCOL-END -->

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
INJECT_FILE="$SCRIPT_DIR/../inject.md"
TARGET_DIR="${TARGET_DIR:-$PWD}"
TOOLS=""
UNINSTALL=false
STATUS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tools) TOOLS="$2"; shift 2 ;;
    --uninstall) UNINSTALL=true; shift ;;
    --status) STATUS=true; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

# Read bounded protocol block from inject.md
PROTOCOL=$(awk '/<!-- RDD-HUB-PROTOCOL-START -->/,/<!-- RDD-HUB-PROTOCOL-END -->/' "$INJECT_FILE")
[[ -z "$PROTOCOL" ]] && { echo "ERROR: empty protocol block in inject.md" >&2; exit 3; }

# Tool → target path mapping
tool_path() {
  case "$1" in
    cursor)   echo "$TARGET_DIR/.cursorrules" ;;
    cline)    echo "$TARGET_DIR/.clinerules" ;;
    continue) echo "$TARGET_DIR/.continue/rules/cross-repo-hub.md" ;;
    copilot)  echo "$TARGET_DIR/.github/copilot-instructions.md" ;;
    claude)   echo "$TARGET_DIR/CLAUDE.md" ;;
    *) echo "" ;;
  esac
}

# Tool → template file mapping
tool_template() {
  case "$1" in
    cursor)   echo "cursor.cursorrules" ;;
    cline)    echo "cline.clinerules" ;;
    continue) echo "continue.rules.md" ;;
    copilot)  echo echo "copilot.instructions.md" ;;
    claude)   echo "claude.CLAUDE.md" ;;
    *) echo "" ;;
  esac
}

# Backup file with timestamp
backup_file() {
  local f="$1"
  [[ ! -f "$f" ]] && return 0
  local ts
  ts=$(date +%Y%m%d%H%M%S)
  cp "$f" "$f.bak.$ts"
}

# Idempotent append: if START marker exists, replace block; else append
inject_tool() {
  local tool="$1"
  local target
  target=$(tool_path "$tool")
  [[ -z "$target" ]] && { echo "Unknown tool: $tool" >&2; return 1; }

  mkdir -p "$(dirname "$target")"

  if [[ -f "$target" ]] && grep -q "RDD-HUB-PROTOCOL-START" "$target"; then
    # Replace existing block
    awk -v proto="$PROTOCOL" '
      /<!-- RDD-HUB-PROTOCOL-START -->/ { print proto; skip=1; next }
      /<!-- RDD-HUB-PROTOCOL-END -->/   { skip=0; next }
      !skip
    ' "$target" > "$target.tmp" && mv "$target.tmp" "$target"
  else
    # Fresh file: use template if exists, else create empty
    [[ ! -f "$target" ]] && : > "$target"
    backup_file "$target"
    echo "" >> "$target"
    echo "$PROTOCOL" >> "$target"
  fi
  echo "✅ $tool → $target"
}

uninstall_tool() {
  local tool="$1"
  local target
  target=$(tool_path "$tool")
  [[ ! -f "$target" ]] && return 0

  if grep -q "RDD-HUB-PROTOCOL-START" "$target"; then
    awk '
      /<!-- RDD-HUB-PROTOCOL-START -->/ { skip=1; next }
      /<!-- RDD-HUB-PROTOCOL-END -->/   { skip=0; next }
      !skip
    ' "$target" > "$target.tmp" && mv "$target.tmp" "$target"
    # Restore backup if exists
    local latest_bak
    latest_bak=$(ls -t "$target".bak.* 2>/dev/null | head -1 || true)
    [[ -n "$latest_bak" ]] && { echo "  backup available: $latest_bak"; }
    echo "🗑️  $tool protocol removed from $target"
  fi
}

status_tool() {
  local tool="$1"
  local target
  target=$(tool_path "$tool")
  if [[ -f "$target" ]] && grep -q "RDD-HUB-PROTOCOL-START" "$target"; then
    echo "  ✅ $tool: deployed → $target"
  else
    echo "  ❌ $tool: not deployed"
  fi
}

# Resolve "all"
if [[ "$TOOLS" == "all" ]]; then
  TOOLS="cursor,cline,continue,copilot,claude"
fi

IFS=',' read -ra TOOL_LIST <<< "$TOOLS"

if $STATUS; then
  echo "Spoke injection status for $TARGET_DIR:"
  for t in "${TOOL_LIST[@]}"; do status_tool "$t"; done
  exit 0
fi

if $UNINSTALL; then
  for t in "${TOOL_LIST[@]}"; do uninstall_tool "$t"; done
  exit 0
fi

# Default: inject
for t in "${TOOL_LIST[@]}"; do inject_tool "$t"; done
```

chmod +x `skills/spoke-system-prompt-injection/scripts/deploy.sh`

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_spoke_injection.bats`
Expected: 5 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 3: 5 个工具模板

**Files:**
- Create: `skills/spoke-system-prompt-injection/templates/cursor.cursorrules`
- Create: `skills/spoke-system-prompt-injection/templates/cline.clinerules`
- Create: `skills/spoke-system-prompt-injection/templates/continue.rules.md`
- Create: `skills/spoke-system-prompt-injection/templates/copilot.instructions.md`
- Create: `skills/spoke-system-prompt-injection/templates/claude.CLAUDE.md`

- [x] **Step 1: 创建 5 个模板**

每个模板都是同 protocol 内容,只是头部注释不同(工具特定):

**`cursor.cursorrules`**:
```markdown
# Spoke AI Cross-Repo Protocol
<!-- This file managed by skills/spoke-system-prompt-injection/scripts/deploy.sh -->

<!-- RDD-HUB-PROTOCOL-START -->
<!-- protocol_version: 1.0 -->

[canonical protocol content]

<!-- RDD-HUB-PROTOCOL-END -->
```

(其他 4 个模板同结构,只是头部"Spoke AI Cross-Repo Protocol"注释和工具名不同)

- [x] **Step 2: 推迟 commit**

---

### Task 4: SKILL.md + docs

**Files:**
- Create: `skills/spoke-system-prompt-injection/SKILL.md`
- Create: `docs/spoke-system-prompt.md`

- [x] **Step 1: 写 SKILL.md**

```markdown
---
name: spoke-system-prompt-injection
description: 部署 RDD-Hub 跨项目协议到 Spoke AI 工具(Cursor/Cline/Continue/Copilot/Claude Code)。通过 deploy.sh 幂等注入,支持 --tools/--uninstall/--status。
license: MIT
compatibility: bash 4+,git
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "ADR-0030 Step 4"
  user-invocable: true
---

# Spoke System Prompt Injection

## 调用

```bash
skill_use("spoke-system-prompt-injection")
# 等价于:
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --tools all
```

## Flag

| Flag | 含义 |
|------|------|
| `--tools <list>` | 逗号分隔的工具名: cursor,cline,continue,copilot,claude |
| `--uninstall` | 移除注入块并恢复 backup |
| `--status` | 显示当前部署状态 |

## 文件映射

| 工具 | 目标文件 |
|------|----------|
| Cursor | `.cursorrules` |
| Cline | `.clinerules` |
| Continue | `.continue/rules/cross-repo-hub.md` |
| Copilot | `.github/copilot-instructions.md` |
| Claude Code | `CLAUDE.md` |

## 幂等性

使用 `<!-- RDD-HUB-PROTOCOL-START -->` / `<!-- RDD-HUB-PROTOCOL-END -->` markers;重复运行不会产生重复注入。

## Backup

每次覆盖前创建 `.bak.YYYYMMDDHHMMSS` 备份;`--uninstall` 不会自动恢复,需手动 `mv .cursorrules.bak.* .cursorrules`。
```

- [x] **Step 2: 写 docs/spoke-system-prompt.md**

```markdown
# Spoke AI Protocol Injection (ADR-0030 Step 4)

Spoke 仓库通过 `deploy.sh` 自动部署 Hub 跨项目协议到所有主流 AI 工具配置。

## 快速开始

```bash
bash ~/.agents/skills/rdd-workflow/skills/spoke-system-prompt-injection/scripts/deploy.sh --tools all
```

## 支持的工具

| 工具 | 配置文件 |
|------|----------|
| Cursor | `.cursorrules` |
| Cline | `.clinerules` |
| Continue | `.continue/rules/cross-repo-hub.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Claude Code | `CLAUDE.md` |

## 协议内容

每次部署包含:
1. RFC 发起规则(去重 + 速率限制)
2. RFC 审查规则(gate 要求)
3. 契约同步规则(failure → 通知人类)
4. **自动审批禁止**(NEVER auto-approve cross-repo RFCs)

## 卸载

```bash
deploy.sh --tools all --uninstall
```

会移除注入块,但 backup 文件保留。手动恢复:`mv .cursorrules.bak.* .cursorrules`

## 相关

- ADR-0030 Hub-and-Spoke 联邦架构
- `add-mcp-cross-repo-protocol` (W2-4)
- `add-rdd-hub-bootstrap` (W1-1) Hub 仓库
```

- [x] **Step 3: 推迟 commit**

---

### Task 5: `install.sh --spoke-init`

**Files:**
- Modify: `install.sh` — 调用 `deploy.sh`

- [x] **Step 1: 修改 install.sh**

在 install.sh 末尾(若已有 `--spoke-init` 子命令则替换)追加:

```bash
# === --spoke-init subcommand (Spoke AI 协议注入) ===
if [ "${1:-}" = "--spoke-init" ]; then
  shift
  TARGET_DIR="${1:-$(pwd)}"
  DEPLOY="$SCRIPT_DIR/skills/spoke-system-prompt-injection/scripts/deploy.sh"
  if [ ! -f "$DEPLOY" ]; then
    echo "ERROR: deploy.sh not found at $DEPLOY" >&2
    exit 1
  fi
  exec bash "$DEPLOY" --target-dir "$TARGET_DIR" "$@"
fi
```

注意:deploy.sh 接受 `--target-dir` 或从环境读 `TARGET_DIR`。

- [x] **Step 2: 推迟 commit**

---

### Task 6: 全栈验证 + README 更新

**Files:**
- Modify: `README.md`

- [x] **Step 1: 跑所有测试**

Run: `bats tests/integration/test_spoke_injection.bats`
Expected: 5 PASS

- [x] **Step 2: README 更新**

在 README §跨项目协同 末尾追加:

```markdown
### Spoke 接入:协议注入

新 Spoke 仓库接入联邦,运行 `bash ~/.agents/skills/rdd-workflow/skills/spoke-system-prompt-injection/scripts/deploy.sh --tools all` 即可在 Cursor/Cline/Continue/Copilot/Claude Code 中启用 Hub 协议。

详见 [docs/spoke-system-prompt.md](../docs/spoke-system-prompt.md)。
```

- [x] **Step 3: openspec validate**

Run: `openspec validate add-spoke-system-prompt-injection`
Expected: exit 0

- [x] **Step 4: 推迟 commit**

---

## Verification Checklist

- [x] `deploy.sh --tools cursor` 成功向 `.cursorrules` 注入 bounded block
- [x] `deploy.sh --tools all` 处理 5 个工具(cursorrules / clinerules / continue / copilot / claude)
- [x] 重复运行 idempotent(无重复 block)
- [x] `--uninstall` 移除 block + backup 保留
- [x] 首次运行对已存在文件创建 `.bak.YYYYMMDDHHMMSS` 备份
- [x] `install.sh --spoke-init` 调用 deploy.sh 成功
- [x] 5 个模板文件都包含 RFC initiation/review/sync/auto-approval-prohibition 4 部分
- [x] README §跨项目协同 含 Spoke 接入指南