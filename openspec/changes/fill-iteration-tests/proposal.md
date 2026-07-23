## P1: ## 架构依据
- test_iteration.py 941 行但零测试函数
- iteration/ 子目录管理 6 个模块（schema/store/re...

## 架构依据
- test_iteration.py 941 行但零测试函数
- iteration/ 子目录管理 6 个模块（schema/store/render/merge 等）的调度生命周期
- 是项目核心调度模块，无测试覆盖构成最大回归风险

## 范围
- **In Scope**:
  - 为 iteration/schema.py 添加 schema 验证测试（至少 5 个）
  - 为 iteration/store.py 添加 CRUD 操作测试（至少 5 个）
  - 为 iteration/render.py 添加渲染输出测试（至少 3 个）
  - 测试状态转换：planned→in_progress→completed 每步的 iteration.json 更新
- **Out Scope**:
  - 不修改 iteration/*.py 源码
  - 不修改 schema 定义

## 关键场景
- GIVEN iteration.json 含 planned change, WHEN 状态转 in_progress, THEN json 正确更新
- GIVEN 同时更新多个 change, WHEN 并发写入, THEN 原子性保证

## 技术约束
- MUST 使用 pytest + tmp_path fixture
- MUST 遵循现有 test_*.py 命名和风格
- SHOULD 与 test_iteration_concurrency.py 共享 fixture

## 验收标准
- 至少 13 个测试函数
- 所有测试通过
- 不修改现有 iteration 源码