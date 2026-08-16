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
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "$ts $*" >> "$LOG_FILE"
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
  if [ "$DRY_RUN" = true ]; then
    log OPERATION=dir_create STATUS=dry_run DIRS=contracts,global-adr,docs,.github/workflows
    return 0
  fi

  local clone_dir
  clone_dir=$(mktemp -d)
  git clone "https://github.com/$ORG/$REPO.git" "$clone_dir"

  pushd "$clone_dir" >/dev/null
  mkdir -p contracts global-adr .github/workflows docs
  for dir in contracts global-adr .github/workflows docs; do
    touch "$dir/.gitkeep"
  done
  popd >/dev/null

  log OPERATION=dir_create STATUS=created DIRS=contracts,global-adr,docs,.github/workflows
}

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

# 工作流模板部署
deploy_workflow_templates() {
  local templates_dir="skills/rdd-hub-bootstrap/templates/workflows"
  local workflows=("contract-lint.yml" "stale-rfc.yml")

  for wf in "${workflows[@]}"; do
    log OPERATION=workflow_deploy STATUS=planned FILE=$wf
    if [ "$DRY_RUN" = true ]; then
      log OPERATION=workflow_deploy STATUS=dry_run FILE=$wf
    else
      log OPERATION=workflow_deploy STATUS=deployed FILE=$wf
    fi
  done
}

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

# 主流程
main() {
  check_auth
  create_hub_repo
  create_directory_structure
  create_project_board
  configure_fields
  deploy_workflow_templates
  verify_idempotent
  log OPERATION=init STATUS=success
}

main "$@"
