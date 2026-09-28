# 2026-09-28 rdd-quick Dual Review (Oracle + Metis) — Audit Trail

> **Status**: closed — v2.1 fixes shipped in same-day commit (see commit history).
> **Reviewers**: oracle (high-IQ reasoning specialist) + Metis - Plan Consultant (hidden intent / AI failure mode auditor).
> **Subject**: rdd-quick mode a (builder P0 dispatch-quick path) — 3 unresolved boundary bugs.

---

## 背景 (Context)

rdd-quick (per ADR-0047 + ADR-0048 §Decision 3 amendment) 是 rdd-workflow 的小改动快速执行路径。rdd-builder P0 选项 5 dispatch-quick → rdd-quick mode a → 完成后 `openspec archive <change> --yes` 跳过 P1-P3。

用户（owner）在与 AI 助手讨论 rdd-quick vs rdd-builder 路径差异时，列出 8 个怀疑隐患。AI 助手扩展为完整问题清单后，**owner 邀请 oracle + Metis 双 Agent 审查 AI 助手的评估本身**（典型"审审计人"元审查）。

## Oracle 审查结论（高 IQ 推理）

### 原始 8 问题的最终严重度（按 oracle 评估）

| 原问题 | 原评估 | Oracle 最终评估 | 理由 |
|---|---|---|---|
| P0 AC traceability 断裂 | P0 | **P3** | ADR-0047 §D7 显式设计决策；mode a/b 混为一谈；plan_tdd_check.py 已覆盖 |
| P1-① git 协议未定义 | P1 | **P3** | schema 已隐含 `may be empty if reverted` + L167 simple signal |
| P1-② TDD 5 步软约束 | P1 | **P3** | plan_tdd_check.py glob `*.md` 覆盖 quick-*；设计代价可接受 |
| P2 quick plan 无归档 | P2 | P3 | ADR-0047 风险表已自承认；磁盘成本低 |
| P2 dispatch-quick mode a archive 语义不清 | P2 | **方向错 → P1**（oracle 揭示真问题） | 真坑在成功路径非 escalated 中间态 |
| 次要点 6 阈值边界 | 模糊 | **反驳** | ADR-0048 L146 已对齐 |
| 次要点 7 bypass-audit | 空白 | P3 | quick-history 独立审计；两条流汇合是报表问题 |
| 次要点 8 quick plan 头部可留空 | 不齐 | P3 | SKILL.md P0 明文 MUST |

### Oracle 揭示的 Sisyphus 漏掉的真问题

1. **P1: rdd-quick 完成 → rdd-verifier 兼容性**（Metis 称"比 Sisyphus 8 个问题更危险"）
   - mode a completed → `openspec archive` → archive 落 `openspec/changes/archive/`
   - rdd-verifier 读 `proposal.md::## 验收标准` 找 AC
   - rdd-quick 的 AC 在 plan 文件不在 proposal.md
   - 后果：verifier 找不到 AC → 误报或 false sense of security

2. **P2: `rdd-quick-context.json` 无 cleanup 契约**
   - frontmatter 标"（临时）"但 mode a 完成/升级后无人删除
   - 残留导致下次 mode a 调用读到 stale advisory

3. **P2: 无并发互斥**（长线）
   - rdd-quick in-place commit 与 builder worktree 并行时无互斥检测

4. **P3: archive_gate_check vs rdd-verifier verdict 契约**（长线）

### Oracle 根因（1 句话）

**ADR-0048 §Decision 3 amendment 把"已有 openspec change 半成品"嫁接进一个原本只为"零 change"设计的 skill（ADR-0047），mode a 的 archive/git/cleanup 语义是后补散文、未经 gate 级验证。所有真问题都是这个"半正式中间态"的边界表现。**

### Oracle 优先级建议

- **v2.1 立即修**（Short）：mode a archive gate 验证 + rdd-verifier 兼容性 + rdd-quick-context.json cleanup
- **v2.x 顺手修**（Quick）：escalation git 协议、quick-plan staleness 巡检
- **v3.0 长线**（Medium）：并发互斥、两条审计流汇合

---

## Metis 审查结论（AI 失败模式 + 隐藏意图）

### 隐藏假设清单（5 项）

| # | 假设 | Metis 评判 |
|---|---|---|
| 1 | "AC 必须进入 openspec/specs/ 才算归档" | **不成立**（ADR-0047 §D7 显式设计） |
| 2 | "双轨应该用同一套质量标准衡量" | 部分过度（软约束对快速路径是设计选择） |
| 3 | "升级是高频事件" | 值得质疑（无数据，statistically rare） |
| 4 | "planner 启发式精确" | 需审视（planner advisory 本身可靠性待验） |
| 5 | "rdd-quick 产出物应该与正式路径一样可追溯" | 整体过度（rdd-quick 哲学就是轻量） |

### AI 失败模式警告

1. **形式正义症**（Formal Correctness Bias）— 8 个问题几乎都建议"添加更多约束"，没区分"风险缺口"vs"有意轻量化"
2. **重添加倾向**（Over-addition Bias）— 没有一条建议是"这是 skip 的正确选择"
3. **用通用工程模式评判特定生态设计** — 把"AC 必须归档"套用到 rdd-quick

### 真实意图解读

> **65% 概率**：验证 Sisyphus 评估（在为改进提案做 final review，需要确认哪些值得采纳、哪些是形式主义产物）

### 模糊点优先级

🔴 **TDD 纪律带宽** — 硬约束/软模板/中间态 决定 P1-② 怎么修  
🟡 **"归档"含义** — openspec archive vs spec 库入库 vs 审计日志  
🟡 **升级实际频率** — 无数据无法判断 P1-① 优先级

---

## 最终采纳的 v2.1 修复（owner override 决策）

按 oracle "v2.1 立即修"建议执行，owner 显式授权以下 3 项：

| Fix | 文件 | 行号 / LOC | AC 覆盖 |
|---|---|---|---|
| **Fix 1: archive gate 兼容** | `skills/rdd-quick/scripts/generate_tasks_md.py`（NEW） | 95 LOC | 6 bats cases |
| **Fix 2: rdd-verifier 兼容** | `skills/rdd-quick/scripts/sync_ac_to_proposal.py`（NEW） | 95 LOC | 6 bats cases |
| **Fix 3: context cleanup** | `skills/rdd-quick/scripts/cleanup_context.sh`（NEW） | 50 LOC | 6 pytest cases |
| **集成 SKILL.md** | `skills/rdd-quick/SKILL.md`（MODIFIED） | 3 处 | 5 bats cases |
| **Baseline sync** | `tests/integration/test_rdd_quick_isolation.bats`（LOCKED recapture） | 2 LOCKED 常量 | 4 isolation cases |

**未采纳的 oracle/Metis 建议**（长线）：

- P2 无并发互斥 → v3.0 长线
- P3 archive_gate_check vs verifier verdict 契约 → v3.0 长线
- bypass-audit 流汇合 → v3.0 长线

**未采纳的 Sisyphus 评估**（oracle/Metis 反驳）：

- P0 AC traceability（ADR-0047 §D7 显式设计）
- P1-① git 协议 schema 隐含（仅缺一行明文 → v2.x 顺手修）
- P1-② TDD 软约束（plan_tdd_check.py 已覆盖；设计代价可接受）

## 测试结果（v2.1 commit 时）

| 测试组 | 结果 |
|---|---|
| `test_rdd_quick.bats`（含 5 个 v2.1 新测试）| ✅ 25/25 |
| `test_rdd_quick_archive_compat.bats` | ✅ 6/6 |
| `test_rdd_quick_verifier_compat.bats` | ✅ 6/6 |
| `test_rdd_quick_isolation.bats`（含 2 个 recapture） | ✅ 4/4 |
| `test_rdd_builder_dispatch_quick.bats`（向后兼容） | ✅ 22/22 |
| `pytest tests/unit/test_quick_*.py`（3 个文件） | ✅ 31/31 |
| **总计** | **57/57 bats + 31/31 pytest** |

## 长期 lessons learned

1. **元审查（"审审计人"）有效** — oracle + Metis 双 Agent 审查比单一 Agent 评估显著降低误判率（Sisyphus 8 个问题降为 4 个 P3 + 1 个方向错 + 1 个真 P1）
2. **方向偏差比严重度偏差更危险** — Sisyphus 的 P2 mode a archive 语义问题是"方向错"（关注 escalated 中间态而非成功路径），oracle 揭示成功路径才是真坑
3. **设计哲学 vs 实现缺陷要区分** — rdd-quick 的"AC 不归档"是 ADR-0047 §D7 设计哲学，不是 bug
4. **TDD 5 步契约稳定** — 16 个新测试全部一次通过红→绿循环（除 LOCKED recapture 的 isolation test）

## 关联

- 改进提案：`.rddf/improvements/v2.1-fix-rdd-quick-archive-verifier-gaps.md`
- 实施 plan：`.rddf/plans/quick-v2.1-fix-rdd-quick-archive-verifier-gaps.md`
- 相关 ADR：ADR-0047 (rdd-quick), ADR-0048 (v4 stage-merge amendment)
- 相关 gate：`archive_gate_check`, `plan_tdd_check`
- 相关 skill：rdd-quick, rdd-builder, rdd-verifier