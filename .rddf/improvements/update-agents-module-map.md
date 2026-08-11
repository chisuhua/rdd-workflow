# update-agents-module-map

**优先级**: P1 | **来源**: Oracle 代码审查 2026-07-19 遗漏 #3
**阶段**: default | **分类**: general
**类型**: feature

## 架构依据
- Oracle 发现：AGENTS.md 的关键目录章节中，"skills/_lib/" 列表缺少 `core/` / `loop/` / `schedulers/` 子目录标注。审查者因此误以为 loop_state.py/event_queue.py 等文件不存在。AGENTS.md 是项目主要文档入口，模块地图过时影响所有下游开发者和 AI 审查者。

## 范围
- **In Scope**:
  - AGENTS.md "关键目录"章节中 _lib/ 部分更新：标注 core/（6 文件）、loop/（15 文件）、schedulers/ 子目录
  - 更新 Python 模块描述列表，标注每个模块的子目录归属
- **Out Scope**:
  - 不更新 ADR 文档
  - 不更新 skill 文件
  - 不更新测试文档

## 关键场景
（无）

## 技术约束
- MUST 保持 AGENTS.md 的现有格式和风格
- MUST 更新文件计数以反映实际文件数
- SHOULD 添加简单树形结构展示子目录层次

## 验收标准
- AGENTS.md 中 _lib/ 目录树包含 core/、loop/、schedulers/、schemas/、plugins/ 子目录
- Python 模块列表清晰标注每个文件在子目录中的位置
- 文件计数准确
