# ADR-0034: rdd-verifier 验证回环阶段架构

> **状态**: 已采纳
> **日期**: 2026-08-26
> **决策者**: sisyphus

## 问题

rdd-workflow v2.1+ 4 阶段架构缺独立的验证回环阶段。`_lib/archive.sh::archive_gate_check` 已自动调用 ac-verifier 技能（v1.0，2026-08-17），但默认 `STRICT_AC_GATE=no`（warning-only），且：
1. AC 验证仅是 archive 内嵌步骤，无用户可见阶段菜单
2. 缺失败回环机制（AC fail 后用户需手动判断去 plan 还是 ship）
3. 缺批量能力（一次只能验证一个 change）
4. 缺 SHA 指纹缓存（archive_gate_check 与外部 LLM 调用可能重复）

## 决策

新增第 5 阶段 `rdd-verifier`（arch → design → plan → ship → **verify** → archive），采用 **Approach C 混合形态**：

- **位置**: ship 完成后、archive 前的独立验证步骤
- **属性**: 条件必经（默认必走，`SKIP_RDD_VERIFIER=yes` 跳过）；非线性必经节点
- **人工介入**: high（AI 分类 + 用户确认 + 失败回环决策）
- **失败回环**: 启发式分类（implementation_gap / proposal_drift）+ 用户确认 + 跳回 plan 或 ship，最多重试 3 次
- **与 ac-verifier 关系**: 复用 sub-skill，不重写 LLM
- **默认严格**: 与 `STRICT_AC_GATE=yes` 共享同一开关语义
- **SHA 指纹 verdict 缓存**: `.rddf/state/.ac-verdict-<name>.json` 带 `codebase_commit` 字段，避免 archive_gate_check 与 rdd-verifier 双跑 LLM
- **角色模型（ADR-0028 扩展）**:
  - `role.owns`: `.rddf/state/.verifier-loop.json`, `.rddf/state/.ac-verdict-<name>.json`, `.rddf/state/.ac-verifier-blocked.jsonl`
  - `role.not_owns`: `openspec/changes/<name>/`, `docs/adr/`
  - `role.human_involvement`: `high`

## 退出码扩展（兼容 ac-verifier 的 0/1/2/3）

| Code | Meaning |
|------|---------|
| 0 | 全部 pass，archive 可继续 |
| 1 | AC fail（implementation_gap / proposal_drift），触发回环 |
| 2 | SKIP_RDD_VERIFIER=yes 跳过 |
| 3 | ac-verifier 内部错误（LLM 失败、API key 缺失等） |
| **4 (new)** | **max_loops 触发，archive halted，需人工** |

## 后果

**正面**:
- AC 验证成为用户可见阶段而非内嵌步骤
- 失败自动回环避免人工跟踪
- SHA 指纹缓存避免 LLM 双跑（省钱 + 省时间）
- 启发式分类无需额外 LLM 调用（Oracle §E 评审建议）

**负面**:
- 5 阶段架构文档更新成本（AGENTS.md / guide 推荐器菜单）
- 启发式分类误判需用户确认兜底（ambiguous 默认 implementation_gap）

**中立**:
- 不修改现有 4 阶段职责边界（verify 属 ship 后、archive 前的回环，不属新增设计/规划阶段）
- 不并发跑 LLM（v1 串行，避免 token 峰值 + 输出交错难审计）
- 保留 archive_gate_check 内的 ac-verifier 调用作为兜底（用户绕过 rdd-verifier 直接 archive 时仍守门）

## 参考

- ADR-0003: 三阶段架构
- ADR-0025: design 阶段独立化（四阶段）
- ADR-0028: role model per phase
- ADR-0017: rddf-session
- ADR-0024: deps-driven execution mode（execution_mode_decisions 复用）
- Spec: `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md`
- Oracle 评审: 82/100 分，6 个 actionable 建议全部吸收

## 设计文档

- Spec: `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md`
- Plan: `docs/superpowers/plans/2026-08-26-rdd-verifier-implementation.md`