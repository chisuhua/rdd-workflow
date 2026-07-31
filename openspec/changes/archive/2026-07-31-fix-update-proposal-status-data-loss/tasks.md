## 1. 修复插入逻辑

- [x] 1.1 在 `update_proposal_status.py` 的 `## 已实施` 插入分支中，将 `break` 改为继续写剩余行（表头、分隔线、全部旧条目）
- [x] 1.2 验证单次归档：已实施表 N 条旧记录 + 1 条新条目 = N+1 条，旧条目全部保留

## 2. 数据保留验证

- [x] 2.1 连续归档 3 个 change，断言已实施表条目数 = 原始数 + 3（当前：每次归档后条目数递减）
- [x] 2.2 已实施表为空（仅表头）时归档，新条目插入表头之后（保持现有行为不变）

## 3. 测试

- [x] 3.1 新增 `tests/integration/test_archive_proposal_status.bats` 非空表场景用例：已实施表含 N 条历史记录时归档，断言旧记录全部保留
- [x] 3.2 运行 `bats tests/integration/test_archive_proposal_status.bats` 全部通过（含空表 + 非空表用例）
- [x] 3.3 运行 `python3 -m pytest tests/unit/ -q --tb=short` 全量回归通过
- [ ] 3.4 用修复后的脚本重跑恢复已损坏的 proposal-approved.md，验证条目数恢复
