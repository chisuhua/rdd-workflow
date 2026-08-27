# verifier-archive-gate-clarification

**优先级**: P2 | **来源**: 2026-08-26 流程设计 review
**阶段**: default | **分类**: governance
**类型**: improvement
**状态**: 已推迟

## 架构依据

ADR-0034 §3 把 rdd-verifier 定义为"条件必经"（默认必走，`SKIP_RDD_VERIFIER=yes` 跳过）。同时 §5 让 `archive_gate_check` 接受 archive 的唯一条件：`verification.state ∈ (passed, bypassed) AND archive_ready == true`。

但 ADR-0034 §"中立"段保留 archive_gate_check 内嵌 ac-verifier 调用作为"fallback"——"用户绕过 rdd-verifier 直接 archive 时仍守门，且 fallback 写结构化 cache"。

这是**双轨设计**：
- **正常路径**：`rdd-verifier` → cache → `archive_gate_check` 读 cache 接受
- **fallback 路径**：跳过 verifier → `archive_gate_check` 内嵌 `ac-verifier` → 写 cache（`ran_by=archive_gate_check`） → 接受

双轨设计的潜在问题：

1. **"绕过 verifier"被鼓励**：只要 `archive_gate_check` 内嵌 fallback 仍能完成 AC 验证，用户有 incentive 跳过 rdd-verifier（节省批量阶段的 token）
2. **fallback 仅单 change**：archive_gate_check 内嵌调用是 atomic，不支持批量，与 rdd-verifier 能力不对等
3. **状态机不明确**：当前 `verification.state = bypassed` 与 `verification.state = passed` 都允许 archive，但 bypass 没有"被 ac-verifier 实际校验过"的语义

需要新增 ADR 明确两条路径的边界。

## 范围

**In Scope**:
- 新建 `docs/adr/ADR-0035-verifier-archive-gate-boundary.md`（或补到 ADR-0034 §5）
- 明确以下场景：
  - **场景 1（标准）**：change 走 rdd-verifier 验证 → cache hit → archive 通过
  - **场景 2（fallback）**：change 跳过 rdd-verifier → archive_gate 内嵌 ac-verifier → cache 写 `ran_by=archive_gate_check` → archive 通过
  - **场景 3（halted）**：change 在 rdd-verifier 中触发 max_loops → archive 阻断（exit 4）
  - **场景 4（deprecated?）**：change 走 `tools/archive_on_main.sh --confirm-main`（与 verifier 无关，USAGE §"On-main Mode"）
- 文档化"绕过 verifier 的 token 节省" vs "失去失败回环能力"的权衡
- 提议：把 `SKIP_RDD_VERIFIER` 与 `STRICT_AC_GATE` 关联（`STRICT_AC_GATE=yes` 时 SKIP 失效）

**Out of Scope**:
- 移除 `tools/archive_on_main.sh` 旁路（保持 hotfix 能力）
- 修改 ADR-0034 既有 §1-§10 条款
- 重新设计 `ac-verifier` 子技能

## 设计

### ADR-0035 草案（核心条款）

```markdown
# ADR-0035: rdd-verifier ↔ archive_gate_check 边界澄清

## 状态: 待定

## Context

ADR-0034 §3 把 rdd-verifier 定义为条件必经 + 保留 archive_gate_check 内嵌 fallback。
该双轨设计在三个场景下导致语义不一致：

1. fallback 路径不享受失败回环（无 max_loops 概念）
2. fallback 路径仅支持单 change 验证（不支持批量）
3. "绕过 verifier"与"严肃验证"在 archive gate 视角无法区分（都标记 verification.state=passed）

## Decision

### 1. 路径分类（4 类）

| 路径 | 触发 | cache 来源 | 失败回环 | 批量支持 | archive 接受条件 |
|------|------|-----------|----------|---------|-----------------|
| **P1 标准** | `rddf rdd-verify` 走完后 archive | cache `ran_by=rdd-verifier` | ✅ | ✅（串行） | `state == passed` |
| **P2 fallback** | `archive_gate_check` 内嵌 `ac-verifier` | cache `ran_by=archive_gate_check` | ❌ | ❌（atomic） | `state == passed` |
| **P3 bypass** | `SKIP_RDD_VERIFIER=yes` + reason | cache `ran_by=bypass` | ❌ | ❌ | `state == bypassed` |
| **P4 on-main** | `tools/archive_on_main.sh --confirm-main` | 不写 cache | ❌ | ❌ | 无 verification 字段（legacy） |

### 2. STRICT_AC_GATE 行为

- 默认 `STRICT_AC_GATE=no`：仅 WARNING（fallback 路径 P2 可接受）
- `STRICT_AC_GATE=yes`：升级为硬阻断 + P3 bypass 失效（必须 P1 路径）

### 3. on-main 旁路限制

- 每月 `tools/archive_on_main.sh` 次数 > 3 → WARNING（rdd-doctor bypass-audit 报告）
- 长期目标：v3.1+ 完全弃用 on-main，所有 archive 走 guide-ship Phase 3

## Consequences

### 正面
- 边界明确：4 类路径有清晰语义
- Token 节省路径（P2 fallback）保留，但与严肃验证路径（P1）有区分
- STRICT 升级为 CI 可选模式（与 STRICT_DESIGN_GATE / STRICT_DEPS_GATE 一致）

### 负面
- 文档复杂度增加（开发者需理解 4 类路径）
- on-main 旁路仍在，需 bypass-audit-mechanism 提案配合治理
```

### 代码改动（小）

`_lib/archive.sh::archive_gate_check` 注释增强：

```bash
# Per ADR-0035 §1 (待采纳) P2 fallback:
# - 仅在 rdd-verifier 跳过或不可用时触发
# - 单 change atomic, 不支持批量
# - cache 写 ran_by=archive_gate_check 区分 P1 路径
# - 失败无回环 (仅写 cache + 返回非零), 由调用方决定 archive 重试
```

## 影响

- **正向**：消除双轨设计的语义模糊
- **正向**：STRICT_AC_GATE=yes 是 CI 可选升级（与现有 STRICT_*_GATE 一致）
- **正向**：on-main 旁路通过 bypass-audit-mechanism 提案治理
- **风险**：P3 bypass 失效后，`SKIP_RDD_VERIFIER` 用例会增加 → bypass audit 需监控
- **兼容性**：纯文档 + ADR；无破坏性代码改动

## 验收

- [ ] `docs/adr/ADR-0035-verifier-archive-gate-boundary.md` 创建并 status=已采纳
- [ ] `_lib/archive.sh::archive_gate_check` 顶部注释引用 ADR-0035 §1
- [ ] STRICT_AC_GATE=yes 行为写进 README.md "紧急跳过" 章节
- [ ] docs/adr/README.md ADR 列表更新（依赖 adr-index-auto-sync 提案）
- [ ] 后续：完全弃用 on-main 的 v3.1 提案