# relocate-loop-engine

**优先级**: P2 | **来源**: Oracle 代码审查 2026-07-19 遗漏 #2
**阶段**: default | **分类**: general
**类型**: feature

## 架构依据
- Oracle 发现：loop_engine.py 358 行是 v2.0 引擎入口，却放在 skills/ 根目录与其他 13 个 .md skill 文件并列。AGENTS.md 注明"在 skills/ 根, 不在 _lib/"，是历史遗留。

## 范围
- **In Scope**:
  - skills/loop_engine.py → skills/_lib/loop_engine.py 迁移
  - skills/loop_engine.py 保留为 re-export shim（from skills._lib.loop_engine import *）
  - 更新所有 import 路径
- **Out Scope**:
  - 不修改 loop_engine.py 内部逻辑
  - 不修改公有 API

## 关键场景
（无）

## 技术约束
- MUST 保留 skills/loop_engine.py 作为兼容 shim（删除原代码，单行 import）
- MUST 更新 skills/__init__.py 如有必要
- SHOULD 更新 AGENTS.md 和 README 中 loop_engine.py 的路径引用

## 验收标准
- skills/_lib/loop_engine.py 存在且与原文件内容一致
- skills/loop_engine.py 为单行 re-export
- 所有现有 import 正常工作
- 所有现有测试通过
