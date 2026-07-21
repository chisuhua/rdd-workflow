# preship-dirty-check

**Priority**: P2
**Phase**: v2.1
**Status**: proposed

## Why

## 架构依据
- 复盘发现：主仓库有预存脏文件（dashboard/__init__.py, renderer.py）未提交，导致 guide-plan-noninteractive 的 git merge 失败
- 根因：archive 流程未检查主仓库 working tree 清洁度

## 范围
- **In Scope**:
  - guide-ship Phase 3 (archive) 前增加 `check_main_repo_clean()` 检查
  - 如果有脏文件且不涉及当前 change → 警告 + 建议 stash/commit
  - 如果有脏文件且涉及当前 change → 阻止归档，要求先 commit
  - 1 个 bats 测试：脏文件检测
- **Out Scope**:
  - 不自动 stash（避免意外数据丢失）

## 验收标准
- 有脏文件时归档被阻止并给出建议
- 1 个 bats 测试通过
