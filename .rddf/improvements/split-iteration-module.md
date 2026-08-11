# split-iteration-module

**优先级**: P1 | **来源**: Oracle 代码审查 2026-07-19 #7
**阶段**: default | **分类**: general
**类型**: refactor-only

## 架构依据
- Oracle 验证：iteration.py 739 行，是最大单 Python 文件，混合 schema 定义 + CRUD + CLI 渲染 + merge 逻辑 4 类职责。每次新增 hook 需通读全文。
- ADR-0004 §3: 模块单一职责原则

## 范围
- **In Scope**:
  - skills/_lib/iteration/ 子目录创建
  - iteration/schema.py — schema 定义 + validation
  - iteration/store.py — CRUD + atomic write + merge
  - iteration/render.py — CLI/status 渲染
  - iteration/__init__.py — 兼容 re-export
  - 迁移现有 4-5 个 iteration 相关 unit 测试
- **Out Scope**:
  - 不修改 iteration.json schema
  - 不修改现有 6 个 hooks 的行为
  - 不引入新功能

## 关键场景
（无）

## 技术约束
- MUST 保持 __init__.py re-export 兼容现有 `from skills._lib.iteration import X`
- MUST NOT 改变公有 API 签名
- MUST 将拆分与 iteration schema bump 同步（如有）

## 验收标准
- iteration.py 消失，iteration/ 子目录 3 文件 + __init__.py
- 所有现有 import 正常工作
- 所有现有测试通过
- 无功能变化
