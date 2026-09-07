## Why

`rdd-verifier` v2.0（ADR-0045，已归档）将 LLM 验证协议内联到 `skills/rdd-verifier/SKILL.md`，把执行验证的 AI agent 自身作为 LLM，消除了 `AC_LLM_*` 环境变量与外部 Python 进程桥接。归档后由 oracle（独立 review session）按 SoC / 向后兼容 / 安全 / 可验证性 / 契约完整性五维度打分，综合 **84/100**，并列出 5 个具体风险/改进：

1. **[P1 完整性] verdict 完整性无代码强制** —— SKILL.md Step 3 硬约束（verdict 数组长度等于 AC 数、每条 AC 至少 1 条证据、fail 必须含 drift/gap 关键词）只在协议文档里，没有代码层 enforce。`validate_verdict_items` 不感知 `ac_count`，`archive_gate_check` 消费 cache 时也不校验。**最严重破绽：agent 对 5-AC 提案写 `[AC-1 pass]` 会被 `is_cache_fresh` 命中并放行归档**。
2. **[P2 契约漂移] `VERDICT_ITEM_SCHEMA` 比 SKILL.md 宽松** —— `evidence`/`reasoning` 都是 optional（jsonschema required 只有 `ac_id`/`status`/`confidence`），而 SKILL.md 要求 evidence 非空、fail 必须 reasoning 嵌入关键词。
4. **[P2 卫生] `rdd_verify_cmd.py:332` 仍用 `from skills._lib.verifier.discovery import discover_archived`** —— 违反 AGENTS.md 规则 25（新代码必须 `import _lib.X`）；同文件其他 import 全部是 `_lib.verifier.*`。`_default_runner` 别名应在 shim 窗口关闭时删除，避免与 `_stage_context_runner` 漂移。
5. **[P2 语义] exit-2 映射误杀整批** —— `run_one_change` 把 exit 2（proposal.md 缺失）映射为 `route=halted`、`vstate=skipped`，而 `aggregate_exit` 把 `skipped` 映射为 4。单 change 缺 proposal 会让整批 batch `halted`；但 ac-verify shim 的 exit 2 是良性 skip。语义不一致。
7. **[P3 健壮性] 三处小洞** —— `stage_verification_context` 用非原子 `write_text`（并发可交错）；无 `schema_version` 前向兼容测试（读到 v1/未知版本 cache 时行为未定义未锁定）；jsonschema 缺失时静默降级为 structural-only 校验，弱化协议保证。

Oracle 同时指出 5 个缺失的关键单测（v2.0 最核心新路径 `staged→pending` 竟无单测覆盖；`verdict_completeness` 函数与未实现；schema_version 兼容未锁定；零 AC pass-through 未锁定）。

最后，Oracle 对四阶段后续工作的统一建议可拆为 **3 个独立工作流动作**：

- **rdd-planner**：加 deprecation-aware scaffolding（proposal 阶段扫描 `user-invocable: false` / `deprecated-relation` frontmatter 提示"该 skill 已排期移除"）。
- **rdd-builder**：把"移除 ac-verifier"排入下个 minor 的独立 change，roadmap-meta 标 `manual_deps: [inline-ac-verifier-into-rdd-verifier]` 保证顺序。
- **rdd-verifier**：v2.0 模式（SKILL.md 内联协议 + 数据层抽离 + staged context + SHA cache + fail-closed gate）可推广，但 protocol-driven 而非 copy-paste；首选目标 rdd-arch 的 gap analysis。

本次 change 将以上 **v2.0 closure 修复 + oracle 推荐的 5 个补测 + 跨阶段 follow-up 调度**作为一个独立 OpenSpec change 推进，避免在已归档的 `inline-ac-verifier-into-rdd-verifier` 上 hotfix（违反"不修改已归档 change"的约定）。

## What Changes

### v2.0 closure 修复（P0-P2，per oracle 评分项）

- **P1 verdict 完整性校验**：`_lib/verifier/protocol.py` 新增 `validate_verdict_completeness(verdict, acs, context_acs)` —— 校验长度等于 ac_count、ac_id 集合相等、无重复 ac_id。`run_one_change` 在 cache 命中路径与 fresh verify 路径都调用；`archive_gate_check` 消费 cache 时调用。
- **P2 schema 严格化**：`VERDICT_ITEM_SCHEMA` 改为强制 `evidence` 数组非空（minItems=1）、`status` 在 `pass`/`fail` 时 `reasoning` 必须含关键词。`validate_verdict_items` 同步升级（pass/fail 路径强制 evidence 非空 + fail 强制 reasoning 含 drift/gap 关键词）。
- **P2 卫生**：`_lib/cli/rdd_verify_cmd.py:332` 的 `skills._lib.verifier.discovery` 旧 import 改为 `_lib.verifier.discovery`；`_default_runner` 别名标注弃用计划（roadmap-m meta 标记 shim 关闭时移除）。
- **P2 exit-2 语义**：`run_one_change` 把 exit_code=2 映射从 `skipped/halted` 改为 `pending`（与 `rddf ac-verify` shim 的"良性 skip"语义一致）；`aggregate_exit` priority 把 `pending` 保持 0（不阻断 batch）。
- **P3 健壮性**：`stage_verification_context` 改为原子写（temp file + rename）；`read_verdict_cache` 在 schema_version 缺失/未知时记录 `warning` 并拒绝消费（fail-closed）；jsonschema 缺失时记录 `warning` 并拒绝验证（不再静默降级）。

### Oracle 推荐 5 个补测

- **`staged→pending` 映射单测**：mock runner 返回 `{"staged": True}`，断言 `state==pending`、`route==pending-agent`、**不写 verdict cache**。
- **`validate_verdict_items` 缺必填字段 + evidence 非空**：缺 `confidence`/`status`、evidence 空数组均触发 problem。
- **`validate_verdict_completeness` 三场景**：长度不匹配、未知 ac_id、重复 ac_id。
- **`schema_version` 兼容**：`read_verdict_cache` 读 `schema_version: 1`/未知/缺字段时返回 None + warning。
- **零 AC context**：AC 段存在但无 bullet → `ac_count==0`；`cmd_rdd_verify --stage` 与 `rddf ac-verify` 对零 AC 提案 exit 0 pass-through。

### 跨阶段 follow-up 调度（per oracle Q3）

- **rdd-planner**：`_lib/planner_*.py` 新增 `scan_deprecated_skills()` helper（读取 `skills/<name>/SKILL.md` frontmatter 的 `user-invocable: false` 与 `metadata.deprecated`），在 propose 阶段把"该 skill 已排期移除"作为 suggestion 浮出（本次就有 `ac-verifier` 命中）。
- **rdd-builder**：调度新 change `remove-ac-verifier-completely`（roadmap-meta 标 `manual_deps: [inline-ac-verifier-into-rdd-verifier, verifier-v2-hardening]`）。该 change 任务：删除 `skills/ac-verifier/` 全套（SKILL + scripts + 4 providers + mocks）、删除 `_default_runner` 别名、ac-verify CLI 路由改为友好报错、测试文件去掉 deprecation banner。加 post-removal 回归 bats：`rddf ac-verify` 移除后 exit ≠ 0 且提示清晰。
- **rdd-verifier 模式推广**：在 `docs/superpowers/specs/` 下创建 `verifier-protocol-template.md`，记录"SKILL.md § Protocol + `_lib/<phase>/protocol.py` 数据层 + staged context + agent writeback + SHA cache + fail-closed gate"的共享模板（**不实现**，仅 spec 化，待下个 release 决策后首个落地点是 rdd-arch gap analysis）。
- **跨阶段审计建议**：记录（不实施）`propose_quality_check.py` 与 `arch_quality_gate.py` 的同类外部 LLM/hook 耦合审计建议到下个 change。

## Capabilities

### New Capabilities

- **verdict_completeness 校验**：`validate_verdict_completeness(verdict, acs)` 作为 protocol.py 公共 API，`run_one_change` 与 `archive_gate_check` 都强制通过该校验才能消费 cache。
- **stage_context 原子写**：`stage_verification_context` 内部改为 temp file + rename 模式，避免并发交错。
- **schema_version fail-closed**：`read_verdict_cache` 在 schema_version 缺失或未知时返回 None 并触发 fail-closed（cache 被视为不可用）。
- **deprecation-aware planner scaffolding**：`_lib/planner_*.py` 暴露 `scan_deprecated_skills()` helper，proposal 阶段提示已排期移除的 skill。
- **verifier-protocol-template spec**：在 `docs/superpowers/specs/verifier-protocol-template.md` 记录可复用模板（文档化，不实现）。

### Modified Capabilities

- **`rdd-verifier` protocol**：`VERDICT_ITEM_SCHEMA` 严格化（evidence minItems=1、fail 必须 reasoning 含关键词）；`run_one_change` exit-2 映射改 pending；`aggregate_exit` 移除 `skipped=4` 隐式阻断。
- **`ac-verify` shim**：`exit 2` 语义保持（良性 skip），与 v2.0 `rdd-verifier` 一致。
- **archive_gate_check**：`read_verdict_cache` 失败时不再 fallback；调用 `validate_verdict_completeness` 校验 cache verdict；fail-closed + audited bypass 语义不变。

## Impact

Affected code:
- `_lib/verifier/protocol.py` — 新增 `validate_verdict_completeness` + `validate_verdict_items` 强化 + `stage_verification_context` 原子写
- `_lib/cli/rdd_verify_cmd.py` — 修复 `skills._lib` 旧路由、exit-2 映射、alias 弃用计划
- `_lib/archive.sh` — 校验 cache verdict 完整性（调用 `_lib/verifier/protocol.py::validate_verdict_completeness` 经 `_lib/cli/__init__.py` 或新建的 Python helper，避免 shell-to-Python interpolation 复辟）
- `_lib/verifier/cache.py` — `read_verdict_cache` schema_version fail-closed
- `_lib/planner_*.py` — 新增 `scan_deprecated_skills()` helper
- `tests/unit/test_rdd_verifier_protocol.py` — 新增 5 类测试（staged→pending、validate_verdict_items 强化、validate_verdict_completeness、schema_version 兼容、零 AC context）
- `tests/integration/test_rdd_verifier_self_contained.bats` — 新增 case 覆盖 agent 写 1 条 verdict 的完整拒绝路径
- `tests/integration/test_archive_gate_no_ac_fallback.bats` — 新增 case 覆盖不完整 verdict 被 fail-closed 拒绝
- `openspec/specs/verifier-archive-gate/spec.md` — 更新 fail-closed 场景（verdict 完整性维度）
- `openspec/specs/verifier-lifecycle/spec.md` — 更新 verdict schema 严格化场景

Affected docs:
- `docs/superpowers/specs/verifier-protocol-template.md` (NEW)
- `docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md` — 追加"v2.0 closure fix addendum"
- `AGENTS.md` — `rdd-verifier` 行追加"shim 关闭时移除"标记
- `CHANGELOG.md` — 新条目
- `proposal-suggestions.md` 或 `proposal-approved.md` — `remove-ac-verifier-completely` 注册

Backward compatibility:
- 已存在的 v2 cache 文件（schema_version=2 且 verdict 完整）继续可读
- 不完整 verdict 的历史 cache 被视为不可用，会触发 rdd-verify 重跑（这是预期行为，避免静默错误）
- `_default_runner` 别名仍保留（用于测试），加 `__deprecated_to__` 标记
- `ac-verify` shim 继续工作 1-2 release cycle

Migration:
- 无用户面 CLI 变更
- 下个 minor release 由独立 `remove-ac-verifier-completely` change 删 `ac-verifier` 全套

## Reference

- Oracle session: `ses_f8610cbf6ffeVLcEjlRw3s2COt`
- Oracle Q1 5 维度评分：SoC 88 / 向后兼容 85 / 安全 80 / 可验证 84 / 契约 82，综合 **84/100**
- Oracle Q2 实际跑单测：64 passed (1.25s) + 5 推荐补测
- Oracle Q3 四阶段建议：rdd-arch 无需调整；rdd-planner 加 scaffolding；rdd-builder 调度 `remove-ac-verifier-completely`；rdd-verifier protocol 模式 protocol-driven 推广
- 上游 change：`openspec/changes/archive/2026-09-07-inline-ac-verifier-into-rdd-verifier/`（ADR-0045）
- 上游 review session：`session_id=ses_f8610cbf6ffeVLcEjlRw3s2COt`