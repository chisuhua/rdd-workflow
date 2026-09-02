# ADR-0036: .rddf/project.yaml 项目级配置源

> **状态**: 已采纳 (2026-09-02)
> **决策者**: rdd-workflow maintainers
> **关联**: [proposal rfc-rddf-project-yaml-config-i10](../proposal-approved.md) · [issue #10](https://github.com/chisuhua/rdd-workflow/issues/10)

## Context

rdd-workflow 当前 5 优先级配置链 `runtime > loop.yaml > .rddf.json > env vars > defaults` 缺少一个**项目级持久化层**，导致 4 类硬编码假设阻碍异构项目接入：

1. ADR 编号固定 4 位 (`_lib/adr_catalog.py:13`)
2. openspec/ 强制 git-tracked（worktree/archive 流程前提）
3. AC 验证强制 LLM（无 API key 或硬件项目无法复用）
4. 配置只支持 env var（每次 shell 手动 export，CI 注入繁琐）

首个受影响项目是 **ChipForge**（CppTLM+CppHDL 硬件验证平台），它使用 3 位 ADR 编号（`ADR-040`）且 commit 3e8fdbf 显式 untrack `openspec/`。

## Decision

引入 **`.rddf/project.yaml`** 作为单一权威项目级配置源，统一上述可配项。完整向后兼容（缺失时行为 = 现状）。

**优先级链扩展**：

```
runtime_overrides > project.yaml > loop.yaml > env vars > .rddf.json > defaults
```

**核心字段**：

| 字段 | 默认 | 作用 |
|------|------|------|
| `adr.pattern` | `^ADR-(\d{4})-.*\.md$` | ADR 编号正则（支持 3 位/4 位） |
| `adr.glob` | `ADR-*.md` | Shell glob（与 pattern 语义等价） |
| `git.openspec_tracked` | `true` | false → 强制轻量模式（branch-only） |
| `verification.provider` | `llm` | hook → 调外部 `tools/verify_change.sh` |

**加载机制**：

- Python 端：`ConfigParser.project_yaml` + `_load_project_yaml()` 集成到 `parse()` merge 链
- Bash 端：`_lib/project_config.sh::project_yaml_get` 通过 env-var 模式调用 Python subprocess（Oracle C1 防注入）
- Schema：`_lib/schemas/config_schema.json` 新增 `project` 节，jsonschema 强校验（fail-closed）

**防御式约束**：

- project.yaml 缺失时**零影响**（`_load_project_yaml` 返回 `{}`）
- 字段类型错误 raise `ConfigError`（不静默 fallback）
- 保留 env var 覆盖能力（CI 临时注入仍可用）
- 不强制现有项目迁移

## Consequences

**正面**：

- 异构项目（硬件验证、嵌入式、文档驱动）原生接入
- ADR 编号灵活（3 位/4 位/混合）
- 工作区可不被 git 追踪（轻量模式）
- 外部验证 hook 可与 CTest 等测试框架组合
- 配置可团队共享（git tracked，schema 校验）

**负面 / 风险**：

- `_lib/config.py` merge 顺序全局影响（M1 标为 🔴 高风险）— 需保留 17 个 schema 文件顶层 version const v1，破坏兼容性即触发全量回归门
- `archive.sh::archive_change()` 新增分支（`openspec_tracked=false` 跳过 git 操作）— 任何错误会破坏现有归档路径
- hook runner path-traversal 风险— 必须强制路径白名单 `{project_root}/tools/`
- 文档可能漂移（README/USAGE 与新字段同步）

## Implementation

按提案分 5 个里程碑实施（详见 `.rddf/plans/rfc-rddf-project-yaml-config-i10.md`）：

| M | 内容 | 状态 |
|---|------|------|
| M1 | 配置基础设施（project_config.sh + config.py merge + schema + defaults） | ✅ 已实施 |
| M2 | ADR 发现可配置（pattern 参数化） | ✅ 部分实施（2/6 task） |
| M3 | openspec_tracked / 轻量模式（archive.sh 分支） | ✅ 已实施 |
| M4 | verification hook（hook_runner.py） | ✅ 已实施 |
| M5 | 文档 + 全量测试 + ADR（本 ADR） | ✅ 已实施 |

## References

- ADR-0016 (发现契约) — `_lib/discover-arch-artifacts.sh` Path 1.5 接入 project.yaml
- ADR-0025 (design 阶段独立化) — 本提案从 arch 阶段迁移到 design 阶段审批
- ADR-0029 (issue-driven proposal) — 本提案通过 `add-improve --from-issue #10` 创建
- ADR-0030 (Hub-Spoke 联邦) — `verification.provider=hook` 不影响 Hub 上行通道
- ADR-0033 (submodule-aware) — `project.yaml` 在 submodule 内独立管理（per `_lib/skill_root.sh` 解析）
- ADR-0034 (rdd-verifier) — `verification.provider=hook` 是 LLM 的等价替代，verifier 仍走 `ac-verify` 框架
- ADR-0035 (verifier-archive-gate boundary) — archive gate 不区分 LLM/hook provider

## Compliance Notes

- 提案追踪：`openspec/changes/rfc-rddf-project-yaml-config-i10/`
- 实施计划：`.rddf/plans/rfc-rddf-project-yaml-config-i10.md`
- Branch：`openspec/rfc-rddf-project-yaml-config-i10`
- Approval: `proposal-approved.md` (2026-09-01, guide-design)
- 上游 RFC: https://github.com/chisuhua/rdd-workflow/issues/10

## Open Questions

- M2 剩余 4 个 task（populate 透传）延后到独立 PR，本提案仅实施 M2 核心（参数化 + discover）
- M5 全量回归门 `./test.sh --full --regression` 在 archive 前必须全绿（per AGENTS.md 硬性要求）
