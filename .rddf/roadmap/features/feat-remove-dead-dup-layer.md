---
id: feat-remove-dead-dup-layer
kind: feature
status: proposed
phase_refs: [phase-4]
主题: 删除 skills/_lib 陈旧重复层 — iteration 副本 + 20 个 schema 副本 + 3 个失效代理 + 8 条死 dash 注册 + 修 populate 路径恢复被静默跳过的校验
---

## 概述

P1-1b（commit c3a90fe）把实现从 `skills/_lib/` 扁平化到仓库根 `_lib/`，`skills/_lib/` 留作
向后兼容 shim。绝大多数 shim 正确（`sys.modules[__name__] = _lib.X` identity-merge），
但**两棵子树没被 shim 化，而是留了完整副本**。

| # | 残留 | 性质 | 证据 |
|---|---|---|---|
| 1 | `skills/_lib/iteration/` 下 7 个陈旧完整副本（1524 行 vs canonical 1762 行） | 死代码 | 运行时不可达（`__init__.py` 已把 `_lib/iteration` 前插进 `__path__`）但肉眼可见，改错文件会静默无效 |
| 2 | `skills/_lib/schemas/` 下 20 个陈旧 JSON 副本（18 个与 canonical 不同） | 死代码 | JSON 无法 identity-merge → 一旦分叉就静默生效 |
| 3 | `_lib/populate_lib.py` 的 schema 路径算术 `parents[2]` | **真 bug** | 解析到**仓库的父目录** → `exists()==False` → populate 的 jsonschema 校验一直被静默跳过 |
| 4 | 3 个失效代理 + 8 条指向不存在目录的 dash-bridge 注册 | 死注册 | `guide-arch` / `guide-plan` / `guide-ship` / `guide-design` / `ac-verifier` 目录均不存在 |

## 实施中最有价值的发现

**canonical `iteration_schema.json` 缺 `cross_repo_dependencies`**（该字段只有陈旧副本里有），
而该 schema 是 `additionalProperties: false`，且运行时 `_lib/iteration/__init__.py:174`
（v6→v7 迁移）**每个 change 都写这个字段** → **运行时写出的 iteration.json 校验必失败**。
这是「删副本 + 测试改指 canonical」暴露出来的 latent bug，也是保留副本的**唯一**理由。

## 跨阶段拆分

### phase-4

| Task | 内容 | commit |
|---|---|---|
| Task 1 | 删 `skills/_lib/iteration/` 7 个副本 + 修 canonical docstring + 守卫测试 | 1 |
| Task 2 | 搬 3 个活契约进 canonical + 删 `skills/_lib/schemas/` + README 索引同步 | 1 |
| Task 3 | 修 `populate_lib.py` 路径（3 处）→ 恢复被静默跳过的校验 | 2 |
| Task 4 | 删 3 个失效代理 + 修 `skills/__init__.py` | 3 |
| Task 5 | 清理 8 条失效 dash-bridge 注册 | 3 |
| Task 6 | 修 `verifier_audit_schema.json` 非法 JSON（必须先于 Task 7） | 3 |
| Task 7 | 5 个 schema 测试改指 canonical + 29 个 schema 补 `version` 注解 + 修 5 处同名冲突 + 补 `cross_repo_dependencies` | 3 |
| Task 8/9 | 守卫收尾 + `docs/schemas/README.md` 索引同步（34 个） | 3 |

## 验收标准

- [ ] `skills/_lib/` 下无 `.json`；超过 50 行的 `.py` 全部命中显式豁免清单（清单规模 ≤ 3）
- [ ] `skills/_lib/iteration/` 只剩 path-widening shim
- [ ] 3 个活契约在 `_lib/schemas/` 下且与副本逐字节一致
- [ ] `populate` 的 schema 路径解析到仓库内真实文件；jsonschema 分支**真的执行**
- [ ] 无指向不存在目录的代理 / dash 注册
- [ ] 34 个 canonical schema 全部合法 JSON、带 ADR-0016 `version` 元数据、无重复键
- [ ] `docs/schemas/README.md` 索引与磁盘双向一致

## 跨阶段拆分

### phase-4
<TBD - 此阶段内的子任务清单>


## 验收标准
<TBD - markdown checkbox 列表, design/plan 阶段消费>
