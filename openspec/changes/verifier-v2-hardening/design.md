## Context

`rdd-verifier` v2.0（ADR-0045，2026-09-07 归档于 `openspec/changes/archive/2026-09-07-inline-ac-verifier-into-rdd-verifier/`）把 LLM 验证协议从外部 `ac-verifier` 子技能内联到 `skills/rdd-verifier/SKILL.md`，让执行 skill 的 AI agent 自身作为 LLM。归档后由独立 oracle session（`ses_f8610cbf6ffeVLcEjlRw3s2COt`）做架构评估，按 SoC / 向后兼容 / 安全 / 可验证性 / 契约完整性五维度评分 **84/100**，并给出 5 个具体风险改进 + 5 个补测建议 + 3 个跨阶段 follow-up。

本次 `verifier-v2-hardening` change 是 v2.0 的闭环修复 + follow-up 调度，作为独立 OpenSpec change 而非 hotfix（不修改已归档 change 是工作流约定）。

**Oracle 审查的关键发现**：

1. **`verdict` 完整性无代码强制** 是 v2.0 当前最大破绽。SKILL.md Step 3 写明"verdict 数组长度等于 AC 数"是硬约束，但 `_lib/verifier/protocol.py::validate_verdict_items` 只校验单条 verdict 字段合法性，不感知 `ac_count`；`archive_gate_check` 消费 cache 时也没校验完整。实际后果：agent 对 5-AC 提案写 `[{"ac_id":"AC-1","status":"pass"}]`，`is_cache_fresh` 通过 → `archive_gate_check` 走 cache-hit 分支 → archive 通过。这是 **silent corruption 风险**：5 个 AC 只有 1 个被验证，其余 4 个根本没被 agent 看。

2. **协议漂移**：`VERDICT_ITEM_SCHEMA` 把 `evidence`/`reasoning` 标为 optional，但 SKILL.md Step 3 要求每条 AC 至少 1 条证据、fail 必须带 drift/gap 关键词。当前 jsonschema 容忍空数组证据 + 缺失 reasoning。

3. **shim 语义不一致**：`rddf ac-verify --skip` 与 proposal 缺失 → exit 2（良性 skip）；`rddf rdd-verify` 内部 `_stage_context_runner` exit 2 → run_one_change `route=halted` → aggregate_exit 把 `skipped` 映射为 4 挂整批。同一语义（"此 change 不需要 AC 验证"）两种 exit code。

4. **卫生债**：`rdd_verify_cmd.py:332` 仍用 `from skills._lib.verifier.discovery` 旧路由（违反 AGENTS.md 规则 25）；`_default_runner` 别名没标注弃用计划；`stage_verification_context` 用 `Path.write_text` 非原子写。

5. **可观测性**：单测覆盖率 64/1.25s 质量合格，但 v2.0 最核心新路径 `staged→pending`（mock runner 返回 `{"staged": True}` → `run_one_change` 写 loop state 为 pending + 不写 verdict cache）**竟无单测覆盖**。

6. **跨阶段可推广**：v2.0 的"SKILL.md § Protocol + `_lib/<phase>/protocol.py` 数据层 + staged context + agent writeback + SHA cache + fail-closed gate"模式适合 protocol-driven 推广。Oracle 建议首个落地点是 rdd-arch 的 gap analysis（把任何 LLM 邻近自动化换成 staged context）。

**架构依据**:
- ADR-0045（inline-ac-verifier-into-rdd-verifier）：v2.0 协议 + 数据层契约 + shim 窗口
- ADR-0034 §7.2：SHA-fingerprint verdict cache（保留不变）
- ADR-0028：role model per phase（rdd-arch/planner/builder/verifier 四阶段）
- ADR-0022：manual_deps 字段（用于本次调度 `remove-ac-verifier-completely`）
- `openspec/specs/verifier-lifecycle/spec.md` v2.0（7 Requirements / 23 Scenarios，oracle 验证）
- `openspec/specs/verifier-archive-gate/spec.md` v1.0（ADR-0035 双轨边界，需补 verdict 完整性场景）

## Goals / Non-Goals

**Goals**:

- **堵 P1 安全洞**：实现 `validate_verdict_completeness` 并强制 `run_one_change` + `archive_gate_check` 调用，agent 写不完整 verdict 必须重跑
- **强化协议契约**：`VERDICT_ITEM_SCHEMA` 严格化（evidence minItems=1、fail reasoning 必须含 drift/gap 关键词）；`validate_verdict_items` 升级拒绝无效 verdict
- **统一 exit-2 语义**：`run_one_change` exit-2 改 `pending`（与 ac-verify shim 一致）
- **补 5 个 v2.0 关键单测**：staged→pending、validate_verdict_items 强化、validate_verdict_completeness、schema_version 兼容、零 AC context
- **修复卫生债**：`rdd_verify_cmd.py:332` import 修正、`_default_runner` alias 弃用计划、`stage_verification_context` 原子写、`schema_version` fail-closed
- **调度 follow-up  change**：`remove-ac-verifier-completely`（roadmap-meta 标 `manual_deps: [inline-ac-verifier-into-rdd-verifier, verifier-v2-hardening]`）；`deprecation-aware-planner-scaffolding` 在 rdd-planner 内的 helper 暴露
- **spec 化 verifier-protocol 模板**：在 `docs/superpowers/specs/verifier-protocol-template.md` 记录共享模式（**只 spec 不实现**，首个落地点 rdd-arch gap analysis 留待下个 release 决策）

**Non-Goals**:

- 不删除 `skills/ac-verifier/` 或 `ac-verifier/scripts/`（属于 `remove-ac-verifier-completely` change）
- 不删除 `_default_runner` 别名（仍用于测试；标注弃用计划，下个 minor 由 `remove-ac-verifier-completely` 删除）
- 不实施 rdd-arch gap analysis 协议化（仅 spec 化模板）
- 不修改 `_lib/verifier/{cache,classify,branch,discovery,loop_state,archive_gate,hook_runner}.py` 的核心契约（除 `cache.py::read_verdict_cache` 加 schema_version fail-closed 行为）
- 不动 iteration schema v7
- 不修改已归档的 `inline-ac-verifier-into-rdd-verifier`（开闭原则）

## Decisions

### 1. verdict 完整性校验的位置

`validate_verdict_completeness` 放在 `_lib/verifier/protocol.py` 而非 `_lib/verifier/cache.py`。理由：cache 只负责"什么时候 cache 是新鲜的"（SHA 比对），完整性是协议语义（verdict 长度 vs AC 数），归 protocol 层更准确。调用方：`run_one_change` 在 cache 命中路径与 fresh verify 路径都校验；`archive_gate_check` 通过 `_lib/cli/rdd_verify_cmd.py` 暴露的 Python helper 校验（避免 shell-to-Python interpolation 复辟）。

**Alternatives rejected**:
- 放在 `_lib/verifier/cache.py::verdict_cache` writer 处 —— 拒绝：writer 不知道 ac_count，需要额外参数
- 放在 `_lib/verifier/audit.py` —— 拒绝：audit 是 append-only log，不应承载语义校验

### 2. VERDICT_ITEM_SCHEMA 严格化的边界

`evidence` 强制非空（minItems=1）是硬约束；`reasoning` 强制非空字符串（minLength=1）；`status` 在 `pass` 时不强制 reasoning 含关键词（pass 路径只要求 evidence），`status` 在 `fail` 时强制 reasoning 含 drift/gap 关键词（用 regex 或额外断言）。`partial` 与 `pass` 相同。

理由：pass 路径 agent 写"看到了，已检查"即可；fail 路径必须给分类器可路由的关键词（`_lib/verifier/classify.py` 依赖 drift/gap 关键词二分类）。

**Alternatives rejected**:
- 所有 status 都强制 reasoning 含关键词 —— 拒绝：pass 路径的关键词是 heuristic 路由用的，pass 不需要路由
- 完全保持 optional —— 拒绝：oracle 评级 P2，是契约漂移

### 3. exit-2 改 pending 的传播路径

`run_one_change` 把 exit_code=2 从 `skipped/halted` 改为 `pending`：
- `vstate = "pending"`
- `route = "pending-agent"`（语义：等 agent 补做 / 等 proposal 出现）
- **不写 verdict cache**（与 staged 路径一致：cache 还没写完）
- **写 loop state** 为 `pending`，写 audit event `pending`
- `aggregate_exit` 把 `pending` 保持 0（不阻断 batch，与现有 staged 行为一致）

**Alternatives rejected**:
- exit-2 保持 halted 但跳过 aggregate —— 拒绝：行为不一致，调用方困惑
- exit-2 抛出异常让调用方捕获 —— 拒绝：与 batch 模式冲突

### 4. stage_verification_context 原子写

```python
# temp file + atomic rename 模式
tmp = out.with_suffix(out.suffix + ".tmp")
tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
tmp.replace(out)  # POSIX atomic
```

**Alternatives rejected**:
- 加文件锁（`fcntl.flock`）—— 拒绝：跨平台问题，atomic rename 是 POSIX 标准答案
- `os.rename` + 异常恢复 —— 拒绝：atomic rename 已经是原子，无需异常恢复

### 5. schema_version fail-closed 的判定

`read_verdict_cache`：
- `schema_version == 2` → 正常返回（v2.0 当前）
- `schema_version == 1` 或缺失 → 返回 None + 在 `_lib/verifier/cache.py` 文档注释里说明"v1 was deprecated by ADR-0034 + superseded by ADR-0045; reading returns None to fail closed"
- 未知版本（如 `3`） → 返回 None + 文档说明

**Alternatives rejected**:
- 自动升级 v1 → v2 —— 拒绝：cache v1 是 ac-verifier 时代产物，schema 不完全兼容（无 schema_version 字段），升级风险大
- 警告后照常使用 —— 拒绝：oracle 评级 P2/契约完整性，违背 fail-closed 原则

### 6. deprecation-aware planner scaffolding 的实现路径

`_lib/planner_*.py` 新增 `scan_deprecated_skills(skills_dir: Path) -> list[dict]`：
- 读取 `skills/<name>/SKILL.md` frontmatter
- 提取 `metadata.deprecated` 或 `user-invocable: false`
- 返回 `[{name, reason, removal_target, migration}]` 列表

proposal 阶段（`_lib/planner_propose.py` 或 propose skill）：扫一遍，把过期 skill 列表作为 suggestion 输出（不阻断生成）。

**Alternatives rejected**:
- 集成到 `_lib/quality_check.py` Plan B 模式 —— 拒绝：扫 skills frontmatter 是 planner 阶段职责，quality_check 是 plan-done gate
- 强制 deprecation 时阻断 propose —— 拒绝：propose 阶段允许引用 deprecated skill（如迁移指南），不阻断

### 7. remove-ac-verifier-completely 调度而非本 change 实施

本 change 在 `proposal-approved.md`（或 openspec/changes 下）注册 `remove-ac-verifier-completely` 的骨架（仅 `roadmap-meta.yaml` 的 manual_deps 标注 + 1 段提议文本），但**不实施**删除。删除属于下个 minor release 的独立 change，因为：
- 删除是不可逆操作，必须独立独立评审
- 下个 minor release 的窗口更适合做破坏性变更
- 用户社区可能有最后一次反馈窗口

**Alternatives rejected**:
- 本 change 直接删除 —— 拒绝：scope 过大，与"v2.0 closure 修复"性质不符
- 完全不调度，留给下一次 propose skill 扫描发现 —— 拒绝：oracle 明确建议"把移除排入下个 minor"，需要显式调度

### 8. verifier-protocol 模板 spec 化（不实现）

在 `docs/superpowers/specs/verifier-protocol-template.md` 记录"SKILL.md § Protocol + `_lib/<phase>/protocol.py` 数据层 + staged context + agent writeback + SHA cache + fail-closed gate"的 5 段通用模板。要求：
- `< Phase >` 的 staged context 文件命名约定（`rdd-<phase>-context-<change>.json`）
- cache schema 跨阶段一致（`schema_version: 2`、`codebase_commit`、`verification_state`、`failed_acs`、`implementation_ref`）
- fail-closed gate 一致（cache 缺失时阻断 + audited bypass）

**Alternatives rejected**:
- 同步在 rdd-arch/rdd-planner/rdd-builder 实施第一个落地点 —— 拒绝：scope 蔓延到 3 个 phase，超出 v2.0 closure
- 留作口头约定不写 spec —— 拒绝：spec 是 rdd-workflow 核心契约载体，跨阶段模式必须有 spec 化

## Risks / Trade-offs

1. **verdict_completeness 是契约收紧，可能拒绝历史 cache**。已部署的 v2.0 cache 若 agent 当时写了不完整 verdict（违反 SKILL.md 但未代码强制），本次升级后会立即 fail-closed 触发重跑。**缓解**：本次 change 在 commit message 标注 "breaking behavior for v2.0 caches with incomplete verdicts; safe migration via re-running `rddf rdd-verify`"。

2. **planner deprecation-aware scaffolding 是纯读取增强**。扫 skills frontmatter 是 O(N) 解析，propose 阶段 +N 文件 N<30 影响可忽略。

3. **schema_version fail-closed 拒绝 v1 cache**。v1 是 ac-verifier 时代产物，已被 ADR-0045 替换，本次只是把"读了也没用"显式化。**缓解**：cache v2 writer 是唯一合法 writer，v1 cache 实际不存在。

4. **stage_verification_context 原子写有微秒级开销**。temp + replace 涉及 2 次 syscall（write + rename），原 write_text 1 次。30 次/phase 调用 频率忽略。

5. **`verify_protocol-template` spec 化不实现**。风险是"写了不落地"。**缓解**：本次只 spec 化；下个 release decision 时作为 ADR 议题。

6. **Oracle 推荐的"审计 propose_quality_check.py 与 arch_quality_gate.py"未实施**。这是 follow-up advice，本 change 不实施（避免 scope 蔓延）。记入 `_lib/cli/AGENTS.md` 或 proposal-approved.md 作为下个 change 候选。