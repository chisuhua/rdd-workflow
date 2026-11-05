---
id: feat-fix-test-isolation-and-hygiene
kind: feature
status: done
phase_refs: [phase-4]
主题: 测试隔离与仓库卫生 — 测试零污染 + 根解析统一到 canonical resolver + 状态快照/worktree 垃圾清理 + doctor plan-tdd 降噪
---

## 概述

一次遗留审查发现 4 类问题，其中 2 个是**真 bug**（都不是「代码不好看」，是会真的写坏数据 / 写错位置）：

| # | 问题 | 性质 | 证据 |
|---|---|---|---|
| 1 | `tests/integration/test_rddf_cross_repo_cli.bats` 不给 `--cache-file` → 脚本默认值是 **CWD 相对**路径 → 在仓库根跑测试就把假数据写进真实 `.rddf/state/.cross-repo-deps-cache.json` | 测试污染真实状态 | `rddf doctor` 因此报 4 条 CRITICAL |
| 2 | `skills/rdd-quick/scripts/append_history.py` 用「向上走直到找到 `_lib/`」推项目根，而 `<repo>/skills/_lib/` **本身就是 `_lib` 目录** → 停在 `<repo>/skills` | 根解析 bug | 产出 `skills/.rddf/state/.quick-history.jsonl`，且该路径未被 gitignore |
| 3 | canonical resolver 的**实现**住在 shim 层（`skills/_lib/_python_resolve_project_root.py`），canonical `_lib/` 下没有 | 分层错位 | 5 个 skill 脚本按 shim 路径 import |
| 4 | 仓库卫生：48 个 `iteration.corrupt.*` 快照 + 2 个 `.before-*` + 14M 残留 `.rddf/wt/test-change/` + 根目录 2 个 0 字节文件 + doctor 96 条历史 plan 噪音 | 噪音 / 残留 | `rddf doctor` 167 WARNING |

另有一处**判据层事实**：canonical resolver 的 git 探测是 **CWD 基准**的（`cd /tmp` 调用返回 `/tmp`）。若脚本只做「无参调用 resolver」，从任意目录运行仍会把状态写进调用目录 —— 因此本 feature 给 resolver 增加**可选探针锚点** `start_dir`（默认 `None` = 原行为，向后兼容），脚本把自身仓库根作为锚点传入。

## 跨阶段拆分

### phase-4

| Task | 内容 | commit |
|---|---|---|
| Task 1 | resolver 探针锚点 + 测试隔离 + `--cache-file` 默认值 | 1 |
| Task 2 | `append_history.py` 根解析 + resolver 实现归位（identity-merge shim） | 2 |
| Task 3 | `.gitignore` 兜底 + 删 `skills/.rddf/` | 3 |
| Task 4 | 删状态快照 / 孤儿 worktree / 根目录 0 字节文件 | 3 |
| Task 5 | doctor `plan-tdd` 只查活跃 change + 近期 plan | 3 |

## 验收标准

- [x] `--cache-file` 默认值是绝对路径，落在解析出的项目根下（不是 CWD）
- [x] 跑完 `test_rddf_cross_repo_cli.bats` 后仓库内没有缓存文件
- [x] `append_history.py` 从任意目录执行，历史仍落在 `<项目根>/.rddf/state/`
- [x] 脚本不再出现「向上循环 + 探测特征目录」的根推导
- [x] `skills._lib._python_resolve_project_root is _lib._python_resolve_project_root`
- [x] `skills/.rddf/` 不存在且被 gitignore 覆盖
- [x] 状态快照 / 孤儿 worktree / 根目录 0 字节文件清零，`git worktree list` 不变
- [x] `rddf doctor` 的 `plan-tdd` WARNING 从 96 降到 0，state 类 CRITICAL 为 0

## 备注

- ship：commit `2de1ab5`（`fix(hygiene): stop tests from writing into real project state`）
- 验收：`.rddf/reviews/fix-test-isolation-and-hygiene-verify.md`（19/19 AC pass）
- 归档：`2026-11-05-fix-test-isolation-and-hygiene`，verdict cache `passed / archive-ready`
- **2026-11-05 收尾动作**：frontmatter `status: proposed → done` + 验收标准按实际取证勾选 + 补 ship 记录
