# add-plugin-loader-tests

**优先级**: P2 | **来源**: Oracle 代码审查 2026-07-19 #5 修正版
**阶段**: default | **分类**: general
**类型**: test-only

## 架构依据
- Oracle 验证：plugin_loader.py 114 行做动态插件加载，是 loop 引擎的可扩展性入口。现有 except 块无 logging。无 dedicated unit test 锁定预期行为。

## 范围
- **In Scope**:
  - 3 个 unit test：load 成功 / load 失败 / 重复 load
  - 测试文件：tests/unit/test_plugin_loader.py
- **Out Scope**:
  - 不改动 plugin_loader.py 源码
  - 不为 loop_state.py 或 event_queue.py 加测试（太小，integration 覆盖足够）

## 关键场景
（无）

## 技术约束
- MUST 使用 pytest 和 tmp_path fixture
- MUST 不依赖外部插件文件
- SHOULD 测试 `except Exception` 分支（确保失败不静默）
- SHOULD 遵循现有 test_*.py 命名和风格

## 验收标准
- tests/unit/test_plugin_loader.py 含 3 个测试函数
- 加载成功/失败/重复加载场景覆盖
- 所有现有测试通过
