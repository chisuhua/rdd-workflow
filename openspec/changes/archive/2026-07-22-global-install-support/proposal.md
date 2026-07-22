# global-install-support

**Priority**: P2
**Phase**: v2.1
**Status**: proposed

## Why

Spec-workflow 安装流程只支持项目内安装（.opencode/skills/rdd-workflow/）。
需要跨项目共享技能的能力，减少重复安装。

## 范围

- **In Scope**:
  - install.sh 增加 `--global` 参数安装到 `~/.agents/skills/`
  - 全局安装自动安装 Python 依赖 + .pth 文件 + rddf CLI symlink
  - README.md 和 INSTALL.md 更新全局安装文档
  - 1 个 bats 测试
- **Out Scope**:
  - 不修改子技能逻辑本身

## 验收标准
- `bash install.sh --global` 安装完成
- `rddf` CLI 在 PATH 中可用
- 测试通过
