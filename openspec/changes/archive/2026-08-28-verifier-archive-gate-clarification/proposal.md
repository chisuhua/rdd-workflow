# verifier-archive-gate-clarification

## Why

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

## What Changes

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

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

- [ ] `docs/adr/ADR-0035-verifier-archive-gate-boundary.md` 创建并 status=已采纳
- [ ] `_lib/archive.sh::archive_gate_check` 顶部注释引用 ADR-0035 §1
- [ ] STRICT_AC_GATE=yes 行为写进 README.md "紧急跳过" 章节
- [ ] docs/adr/README.md ADR 列表更新（依赖 adr-index-auto-sync 提案）
- [ ] 后续：完全弃用 on-main 的 v3.1 提案

