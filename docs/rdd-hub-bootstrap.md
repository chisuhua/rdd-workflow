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
