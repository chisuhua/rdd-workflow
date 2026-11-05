---
id: feat-fix-v4-residue-contract
kind: feature
status: done
phase_refs: [phase-4]
主题: 契约面 v4 残留修复 — 失败路由统一 rdd-builder + feedback schema 对齐 + 用户可见文案 + v4-residue 守卫 + schema 路径扫描扩展到代码
---

## 概述

v3 → v4 重命名（ADR-0043 / ADR-0044 Wave 3 hard removal）覆盖了**主路径**，但**契约面**仍停留在旧名，会把 agent / 用户指向不存在的 skill。本 feature 只修契约面 + 补守卫，**不改阶段语义、不删文件**。

| # | 残留 | 性质 | 影响 |
|---|---|---|---|
| 1 | `route_loop.sh:66,68` 与 `rdd_verify_cmd._classify_route` 写 `guide-ship` / `guide-plan` | 路由写入方 | 失败路由指向已删除 skill，且进 `.rddf/state/verifier/<change>.json` 被 dashboard 展示 |
| 2 | `feedback_entry_schema.json` 的 source enum 缺 `rdd-arch` / `rdd-planner` / `rdd-builder` | 对外契约过期 | 按 `rddf feedback show-schema` 校验的外部消费者会拒掉合法写入 |
| 3 | 10+ 处用户可见文案指向旧 skill（`rddf --help`、错误提示、示例命令） | 误导用户 | `rddf --help` 是第一入口，误导面最大 |
| 4 | **无守卫**能发现同类残留 | 缺失防复发 | doctor 的 22 个 check 无一扫 v4 重命名残留 |
| 5 | `check_schema_path_canonical` 只扫 `AGENTS.md` / `README.md` | 扫描面过窄 | 代码 docstring 里指向旧路径同样误导人 |

### 路由语义的关键决策

`implementation_gap` 与 `proposal_drift` **统一回 `rdd-builder`**（不是 drift → `rdd-planner`）。依据：

- `skills/rdd-verifier/SKILL.md:126,128` 的状态机已 v4 化，写的是 `route="rdd-builder P2"` / `route="rdd-builder P1"`；
- `docs/adr/ADR-0025:91` restore note：**rdd-planner does NOT own proposal.md authoring; rdd-builder P0 owns it**；
- P1 / P2 的差异由 `classification_history` + 打印行承载，state 的 `route` 只表达「去哪个阶段」。

### schema enum 只增不减

`verifier_loop_schema.json::route` 在 `loop_state.py` save 时**强制** `jsonschema.validate` → 删掉 legacy 值会让存量 state **加载失败**。因此 enum 加入 `rdd-builder`，**保留** `guide-ship` / `guide-plan`。

## 跨阶段拆分

### phase-4

| Task | 内容 | commit |
|---|---|---|
| Task 1 | 失败路由统一到 `rdd-builder`（route_loop.sh / rdd_verify_cmd / 2 个 schema / SKILL.md 文本 / 5 处既有断言） | 1 |
| Task 2 | feedback schema source enum 对齐 + 漂移守卫 | 1 |
| Task 3 | 用户可见文案统一（12 处，含守卫发现的 2 处）+ 映射口径纠错 | 1 |
| Task 4 | doctor `v4-residue` 分类（R1/R2/R3 + 显式 allowlist） | 2 |
| Task 5 | `check_schema_path_canonical` 扫描面扩到代码目录（+ 自指豁免） | 2 |

## 验收标准

- [x] `route_loop.sh` 两种分类都写 `route="rdd-builder"`，输出不含 `guide-`
- [x] `_classify_route` 两种分类都返回 `rdd-builder`
- [x] 两个 schema 的 route enum 同时含 `rdd-builder` 与 legacy 值（存量 state 仍可加载）
- [x] `feedback` schema 的 source enum 与运行时 `VALID_SOURCES` 完全一致
- [x] `rddf --help` 的 `guide-` 计数为 0
- [x] doctor 新增 `v4-residue` 分类，且本仓输出 0 CRITICAL / 0 WARNING
- [x] `check_schema_path_canonical` 能发现代码 docstring 里的旧路径；不扫 `__pycache__`；不自报

## 备注

- ship：commit `da9035e`（`fix(v4-residue): point the contract surface at v4 skills, and guard it`）
- 验收：`.rddf/reviews/fix-v4-residue-contract-verify.md`（15/15 AC pass）
- 归档：`2026-11-05-fix-v4-residue-contract`，verdict cache `passed / archive-ready`
- **2026-11-05 收尾动作**：frontmatter `status: proposed → done` + 验收标准按实际取证勾选 + 补 ship 记录
