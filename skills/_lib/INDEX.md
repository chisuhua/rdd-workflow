# skills/_lib — 一页速查表

> 只列**怎么用**；模块清单与两层结构见 `skills/_lib/README.md`。
> 逻辑实现在仓库根 `_lib/`，`skills/_lib/` 是转发面（详见 README §1）。

## project_root 解析

| Helper | 导入 / 调用 | 用途 |
|---|---|---|
| `_resolve_project_root` | `source _lib/orchestrator_entry.sh` 后调用 | bash 侧项目根 |
| `resolve_project_root` | `from skills._lib._python_resolve_project_root import resolve_project_root` | skill 侧项目根 |
| `resolve_project_root` | `from _lib.cli.__main__ import resolve_project_root` | CLI 侧项目根 |
| `skill_root.sh` | `source _lib/skill_root.sh` | skill 双根路径解析 |

契约：`_lib/_resolve_project_root_contract.yaml`（返回 canonical root，非裸 git toplevel）。

## 状态 / 迭代

| Helper | 导入 / 调用 | 用途 |
|---|---|---|
| `state.sh` | `source _lib/state.sh` | 安全 JSON / YAML 读写 |
| `state_reader.py` | `from _lib.state_reader import ...` | CLI 子命令共享只读读层 |
| `iteration/` | `from _lib.iteration import ...` | iteration 视图 / 渲染 / 归档后处理 |
| `parse_approved.py` | `from _lib.parse_approved import ...` | `improvement-approved.md` 解析 |
| `tasks_count.py` | `from _lib.tasks_count import ...` | tasks.md checkbox 计数 |

## 门 / 校验

| Helper | 导入 / 调用 | 用途 |
|---|---|---|
| `gate.py` | `from _lib.gate import ...` | 阶段门判定（ADR-0007） |
| `arch_quality_gate.py` | `from _lib.arch_quality_gate import ...` | ADR 形态检查（ADR-0060） |
| `change_alignment.py` | `from _lib.change_alignment import ...` | plan_done 对齐门 |
| `validate_report.py` | `from _lib.validate_report import ...` | 结构化 `openspec validate`（ADR-0015） |
| `plan_quality.py` | `from _lib.plan_quality import ...` | 计划质量校验 |
| `docs_consistency.py` | `from _lib.docs_consistency import ...` | 文档一致性分类 |

## 跨仓 / Hub

| Helper | 导入 / 调用 | 用途 |
|---|---|---|
| `cross_repo_deps.py` | `from _lib.cross_repo_deps import ...` | 跨仓依赖编排（ADR-0030） |
| `cross_repo_state.py` | `from _lib.cross_repo_state import ...` | pending RFC 状态（CRUD + schema 校验） |
| `gh_hub_client.py` | `from _lib.gh_hub_client import ...` | GitHub Hub 客户端（REST + GraphQL） |
| `hub_issue.py` | `from _lib.hub_issue import ...` | Hub Issue CRUD |
| `contract_diff.py` | `from _lib.contract_diff import ...` | Hub OpenAPI ↔ Spoke 实现差异 |

## 会话 / 编排 / 循环

| Helper | 导入 / 调用 | 用途 |
|---|---|---|
| `session_manager.py` | `from _lib.session_manager import ...` | 并行会话管理（ADR-0010） |
| `session_stats.py` | `from _lib.session_stats import ...` | 会话统计 |
| `recommender.py` | `from _lib.recommender import ...` | 阶段推荐阶梯唯一实现（ADR-0062） |
| `loop_engine.py` | `from _lib.loop_engine import ...` | Loop Engine（ADR-0003） |
| `trigger_engine.py` / `trigger_registry.py` | `from _lib.trigger_engine import ...` | flow.yaml 触发判定（ADR-0012） |
| `dependency_scheduler.py` / `wave_compute.py` | `from _lib.dependency_scheduler import ...` | 依赖图 / 波次计算（ADR-0024） |
| `subagent_strategy.py` | `from _lib.subagent_strategy import ...` | subagent 编排策略 |

## 归档 / worktree

| Helper | 导入 / 调用 | 用途 |
|---|---|---|
| `archive.sh` | `source _lib/archive.sh` | 归档编排（merge → openspec archive → cleanup） |
| `check_worktree_commits` | `source _lib/archive.sh` | 归档前门禁：worktree 分支须有新 commit（ADR-0061） |
| `worktree.sh` | `source _lib/worktree.sh` | git worktree helper |
| `post_archive_cleanup.sh` | `source _lib/post_archive_cleanup.sh` | 归档后清理（plan 文件 / 状态） |
| `bypass_audit.sh` | `source _lib/bypass_audit.sh` | SKIP_* 旁路统一审计 |

## CLI 入口

| 入口 | 调用 | 用途 |
|---|---|---|
| `rddf` CLI | `rddf <subcommand>` / `python3 -m _lib.cli` | dispatcher（实现见 `_lib/cli/`） |
| `env_checks.sh` | `source _lib/env_checks.sh` | 共享环境健康检查 |
| `resolve_skill_name.sh` | `source _lib/resolve_skill_name.sh` | 短 skill 名 → 全名 |

## 约定

1. 逻辑写在仓库根 `_lib/`；`skills/_lib/` 只做转发 —— 不要在 shim 层写业务逻辑。
2. 跨层同名 helper 行为必须一致，由 `tests/unit/test_resolve_project_root_contract_bash.sh`
   与 `tests/unit/test_resolve_project_root_contract_python.py` 盯住。
3. 新增 helper 走 README §5 的六步；登记回 README §2 对应层的表格。
