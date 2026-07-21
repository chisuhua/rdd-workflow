# Tasks: add-parent-feature-param

## Task 1: Python - create_skeleton_change 加 parent_feature 参数
- [x] 1.1 修改 `skills/propose/scripts/propose_change.py::create_skeleton_change` 签名加 `parent_feature: Optional[str] = None`
- [x] 1.2 在函数入口校验 `parent_feature != "__ungrouped__"`，否则抛 `ValueError`
- [x] 1.3 roadmap-meta.yaml 写入时加 `parent_feature:` 字段（None 写 null，非 None 写字符串）
- [x] 1.4 `it_mod.add_or_update_change` 调用时传入 `parent_feature=parent_feature`（仅当非 None 时）
- [x] 1.5 单元测试 `test_create_skeleton_change_with_parent_feature` + `test_create_skeleton_change_rejects_ungrouped`

## Task 2: Python - update_roadmap_meta 加 parent_feature 参数
- [x] 2.1 修改 `skills/propose/scripts/propose_change.py::update_roadmap_meta` 签名加 `parent_feature: Optional[str] = None`
- [x] 2.2 roadmap-meta.yaml 写入时加 `parent_feature:` 字段
- [x] 2.3 单元测试 `test_update_roadmap_meta_with_parent_feature`

## Task 3: Python - update_iteration_proposed 加 parent_feature 参数
- [x] 3.1 修改 `skills/propose/scripts/propose_change.py::update_iteration_proposed` 签名加 `parent_feature: Optional[str] = None`
- [x] 3.2 入口校验 `parent_feature != "__ungrouped__"`
- [x] 3.3 `it_mod.add_or_update_change` 调用传入 `parent_feature`（仅当非 None 时）
- [x] 3.4 单元测试 `test_update_iteration_proposed_with_parent_feature` + `test_update_iteration_proposed_rejects_ungrouped`

## Task 4: bash wrapper - propose_change.sh 传递 PARENT_FEATURE
- [x] 4.1 `propose_create_change` 读取 `PARENT_FEATURE` env var，通过 `os.environ.get` 传给 Python
- [x] 4.2 `propose_finalize_change` 读取 `PARENT_FEATURE` env var，传给 `update_roadmap_meta` 和 `update_iteration_proposed`
- [x] 4.3 bats 集成测试 `test_propose_create_change_with_parent_feature_env`
- [x] 4.4 bats 集成测试 `test_propose_finalize_change_with_parent_feature_env`

## Task 5: 端到端 feature 分组验证
- [x] 5.1 单元测试 `test_parent_feature_groups_into_feature` - 两个 change 同 `parent_feature`，`list_feature_groups` 归入同一组

## Task 6: propose.md 文档更新
- [x] 6.1 Phase 4 `propose_create_change` 调用前加可选 `PARENT_FEATURE` 设置说明
- [x] 6.2 Phase 4 `propose_finalize_change` 调用前加可选 `PARENT_FEATURE` 设置说明

## Task 7: 回归验证
- [x] 7.1 `python3 -m pytest tests/unit/test_propose_change.py tests/unit/test_iteration.py tests/unit/test_feature_view.py -v`
- [x] 7.2 `python3 -m pytest tests/unit/ -q --tb=short` (唯一失败为无关的 `test_all_builtin_detectors_run_sequentially_under_500ms`，环境性能波动)
- [x] 7.3 `bats tests/integration/test_propose_skill.bats` + `bats tests/integration/test_propose_parent_feature.bats`
- [x] 7.4 `lsp_diagnostics` 干净 (propose_change.py 无 diagnostics)
