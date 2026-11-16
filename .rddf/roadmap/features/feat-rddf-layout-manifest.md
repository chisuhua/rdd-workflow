---
id: feat-rddf-layout-manifest
kind: feature
status: done
phase_refs: [phase-4]
主题: rddf 布局单一真源 —— .rddf/ 机读清单 + layout 子命令 + doctor layout category + 散文由清单派生
---

## 概述

`.rddf/` 的布局（有哪些条目、谁读谁写、按模式是否必需、是否入库）此前没有单点真源：ADR-0026 定了 `runtime-only` / `committed` 两分类但无机器可执行形态；路径常量只有 `_lib/core/defaults.py:24-32` 的 2 条 DEFAULTS + `:67-71` 的 5 个模块常量；散文只覆盖 handoff 三文件与 `detectors/` `actions/`；doctor 24 个 category 无布局类（`rdd-doctor/SKILL.md:4` 仍写「13 file categories」）。

本 feature 把 ADR-0026 落地为工具：`_lib/core/rddf_layout.py` 单一清单（`path` / `kind` / `read_by` / `write_by` / `required_when` / `transient` / `class` / `severity`）+ 只读子命令 `rddf layout --json`（**清单出口**）+ doctor `layout` category（**诊断出口**，三支判据）+ `docs/architecture/rddf-layout.md`（表格 + 新增条目三步 + 文件级一节）。

动机来自消费方提问：第三方项目与 e2e 测试床无从判断「必须建什么」以及「我加的 `.rddf/config/` 文件会不会被覆盖」。

对应 improvement：`.rddf/improvements/rddf-layout-manifest.md`（已批准 2026-11-16，rdd-planner）。
审稿记录：`.rddf/reviews/rddf-layout-manifest-planner-review.md`（metis 1 轮，13 条 finding 全部采纳）+ `.rddf/reviews/rddf-layout-manifest-builder-review.md`（build 侧证据核对，4 BLOCKER + 9 SHOULD_FIX 全部处置）。

## 跨阶段拆分

### phase-4

单一 change：`rddf-layout-manifest`（improvement → openspec change 由 rdd-builder P0 生成）。

| 子项 | 内容 | 落点 |
|---|---|---|
| 1 | 单一清单 + `as_dicts()` | `_lib/core/rddf_layout.py`（新） |
| 2 | 清单出口（只读子命令，`schema_version`/`tool_version`，无时间戳 ⇒ 字节确定） | `_lib/cli/layout_cmd.py`（新）+ `_lib/cli/__init__.py` + `_lib/cli/__main__.py` |
| 3 | 诊断出口（三支判据；只扫一层；永不 CRITICAL；`.rddf/` 不存在 ⇒ 0 finding） | `skills/rdd-doctor/scripts/checks/layout_check.py`（新）+ `doctor_main.py` |
| 4 | 人读契约页（表格 + 新增条目三步 + 文件级一节，**以代码为源**） | `docs/architecture/rddf-layout.md`（新）+ `docs/architecture/README.md` |
| 5 | 散文补链与修正（`state-and-events.md` 修 v3 遗留 handoff 表 + 补链；`extension-points.md` 补链；`ADR-0026` 加描述性链接） | `docs/architecture/`、`docs/adr/ADR-0026-*.md` |
| 6 | skill 描述去漂移（description 去固定数字 + usage 行 category 枚举同步 + category 说明表加行） | `skills/rdd-doctor/SKILL.md` |
| 7 | 测试（unit: 清单不变量 + 断言 A/B + CLI 确定性；integration: doctor layout 三支判据 + 本仓 0 finding） | `tests/unit/test_rddf_layout.py`、`tests/unit/test_layout_cmd.py`、`tests/integration/test_doctor_layout.bats`（均新） |

## 验收标准

设计/plan 阶段消费；源 = `.rddf/improvements/rddf-layout-manifest.md` 的 `## Acceptance` 段。

- [ ] `_lib/core/rddf_layout.py` 导出 `RDFF_LAYOUT`；每条含 8 个字段；取值域闭合；`path` 唯一且按字典序输出
- [ ] `rddf layout --json` 输出 `entries`（首版 14 条）+ `schema_version: 1` + `tool_version`
- [ ] 同仓连续两次 `rddf layout --json` **字节一致**；共享 `skills/rdd-doctor/scripts/doctor_render.py` 未被修改
- [ ] `rddf doctor --category layout` 在本仓输出 **0 finding**（含两个 `.roadmap-migrate-backup-*` 目录，由 `transient` 放行）
- [ ] 三支判据可复现：缺失 `always` 条目 ⇒ WARNING；未登记顶层条目 ⇒ INFO；`class` 与 `.gitignore` 不符 ⇒ WARNING
- [ ] 本 category 永不产生 CRITICAL（exit code 1 而非 2）；`.rddf/` 不存在 ⇒ 0 finding
- [ ] 最小第三方 fixture 上：WARNING 集合**恰好等于** `required_when=always` 集合
- [ ] `wt/` 仅在 worktree 模式下要求存在
- [ ] 断言 A（`defaults` + 5 个模块常量被清单覆盖）与断言 B（`class` 与 ignore 实况一致，含含 tracked 文件的 `.rddf/state/` 目录）通过
- [ ] `schema_version` 演进策略成文（增字段/增 entry 不升版；改语义或删 entry 升版；消费方忽略未知字段、按 `path` 集合比较）
- [ ] `docs/architecture/rddf-layout.md` 含「真源 = `_lib/core/rddf_layout.py`」「对外出口 = `rddf layout --json`」「新增顶层条目三步」「文件级」四节
- [ ] `state-and-events.md` 的 handoff 表与 mermaid 图修成 v4 命名（不再残留 `guide-design`/`guide-plan`/`guide-ship`/`.design-handoff.json`/`.plan-handoff.json`）
- [ ] 三处散文补链到位 + `docs/architecture/README.md` Doc Map 索引已更新
- [ ] `rdd-doctor/SKILL.md` description 不含固定 category 数目；usage 行 category 枚举与 `_CHECKERS` 实况一致；category 表含 `layout` 一行
- [ ] 边界声明成文：`RDDF_STATE_DIR` 重定向不在契约内
- [ ] 回归：`./test.sh --quick` 不新增失败；`git diff --stat` 不含「把现有路径引用改成读常量」的改动，且不含 `doctor_render.py`

## 验收与归档

- **验收**：18/18 AC pass（报告 `.rddf/reviews/rddf-layout-manifest-verify.md`，verdict cache `.rddf/state/verifier/.ac-verdict-rddf-layout-manifest.json`，`codebase_commit=d173f791`）
- **critic 审稿**：APPROVE_WITH_CONDITIONS / mergeable: yes / 0 BLOCKER（报告 `.rddf/reviews/rddf-layout-manifest-arch-review.md`）
- **归档**：`openspec/changes/archive/2026-11-16-rddf-layout-manifest`（+25 Requirements 合流进 `openspec/specs/rddf-layout-manifest/spec.md`）

