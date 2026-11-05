# 收尾报告 — 2026-11-05 归档 + planner 遗留项清理

- **日期**：2026-11-05
- **触发**：用户批准「按建议路径实施」（盘点 → P0 验收/归档 → P1 planner 收尾 → 追加 roadmap-md-integrity）
- **涉及角色**：verifier → builder → planner → builder（切换记录见 `.rddf/state/role.json` history）
- **commit**：`0bcf04c`（parse_acs 表格式 AC 修复）+ 本轮 3 个 commit（见文末）

## 一、P0：验收并归档 4 个 change

### 起点状态

4 个 change 的 tasks 全部 100% 完成，但**全部未归档**，且都缺 `iteration.json` 条目 —— `discover_eligible()` 因此返回空队列，`rddf rdd-verify` 报 `No eligible changes to verify`。

### 关键发现：`parse_acs` 不认表格式 AC（产品缺口）

4 个 change 的 `## 验收标准` 全部是**表格式**（`| AC-1 | 描述 |`），而 `_lib/verifier/protocol.py::parse_acs` 只识别 `- ` bullet → 提取结果为 **0 条** → verdict cache 完整性校验（长度必须等于 AC 数）必然 fail-closed → 归档门报 `no valid verdict cache`。

走 `SKIP_RDD_VERIFIER=yes` 旁路可以绕过，但旁路会写 `.rddf/state/.bypass-audit.jsonl`（doctor 月度阈值告警）。**改为修提取器**：

- `parse_acs` 新增表格式支持：首列为显式 `AC-N` 的行才计入，id **按原文取**（不重编号，避免与 proposal 和验收报告里的编号错位）；bullet 形式行为不变
- 7 个新单测（表格式、混合格式、重复 id、多余列、非 AC 表）

commit `0bcf04c`。

### 验收与归档链路

```
补 iteration.json 条目 (status=completed, tasks_done == tasks_total)
  → discover_eligible() 发现 4 个 change
  → 建 openspec/<name> 分支（tip == HEAD）
  → rddf rdd-verify（第一次）→ stage context，state=pending
  → 按 LLM Verification Protocol 逐条取证 → 写 verdict cache v2
  → rddf rdd-verify（第二次）→ cache hit → state=passed / archive_ready=true
  → 归档门 4/4 exit=0（verifier_contract_check + archive_gate_check）
  → rddf archive ×4 → openspec archive + worktree/分支清理 + iteration 标记 archived
```

**零旁路**：全程未使用 `SKIP_RDD_VERIFIER` / `SKIP_*_GATE` / `tools/archive_on_main.sh --confirm-main`。

### 验收结果

| change | AC 数 | 判定 | 验收报告 |
|---|---|---|---|
| fix-agent-interface-contracts | 20 | 20 ✅ | `.rddf/reviews/fix-agent-interface-contracts-verify.md`（本轮新建） |
| fix-test-isolation-and-hygiene | 19 | 19 ✅ | `.rddf/reviews/fix-test-isolation-and-hygiene-verify.md`（2026-11-04） |
| fix-v4-residue-contract | 15 | 15 ✅ | `.rddf/reviews/fix-v4-residue-contract-verify.md`（2026-11-04） |
| remove-dead-dup-layer | 18 | 18 ✅ | `.rddf/reviews/remove-dead-dup-layer-verify.md`（2026-11-04） |

全局回归：pytest unit 3475 passed / integration 201 passed；bats 全量 `report_regression.sh` → 已知失败 11 / **新增失败 0** / zombie 0。

## 二、P1：planner 遗留项收尾

| # | 项 | 处理 | 结果 |
|---|---|---|---|
| 1 | 4 个 feature fragment 状态停留在 `in-progress` / `proposed` | 推进到 `done` + 验收标准按实际取证勾选 + 补 ship 记录（commit / 验收报告 / 归档名） | `rddf roadmap validate-fragments` ✅；AGENTS.md AUTO 段已刷新 |
| 2 | `improvement-suggestions.md` 3 条 finding（1 幽灵链接 + 2 列数不符） | 幽灵行 `add-objective-evidence-v02-llm-synthesis` 全仓从未存在 → 删行；列数不符源于内容里的转义竖线 `\|` → 改写为 `/` | `doctor --category proposal-table` ✅ |
| 3 | 9 个 improvement 缺 YAML frontmatter | 逐个从文件自身内容提取真实元数据（状态/日期/来源行、元数据表、归档指针）补全；`migrate_improvement_frontmatter` 对这 9 个报 `no metadata found` 无法自动迁移 | `doctor --category improvement-frontmatter-consistency` ✅ |
| 4 | v3 legacy handoff 残留（`.plan-handoff.json` / `.design-handoff.json`） | 删除（保留在 `/tmp/opencode/legacy-backup/`）。代码仍把它们当 v3 fallback 读，但本仓 `.planner-handoff.json` 有效，判定不变 | `rddf guide` 推荐仍是 `rdd-builder`；legacy 警告消失；`doctor --category state` ✅ |
| 5 | ADR-0060 已实施但未走 change 流程 → 「关联 change」指针缺失 | 建 `.rddf/improvements/adr-0060-shape-contract-implementation.md` 作登记载体（ADR 元数据回填属 architect 职责，未代改） | ADR-0060 的 8 条 Verification 已实跑全通过 |
| 6 | 6 条已知失败无活跃归属（备注指向从未创建的 `feat-doc-drift-cleanup`） | 建 `.rddf/improvements/fix-agents-md-worktree-commit-flow.md`（P1），含可直接通过既有断言的完整示例段（已实测 6/6） | 待实施 |
| 7 | `add-scope-bootstrap-agent.md` 提案评审 | Hard 6/6 ✅、Soft 1/4；In Scope 与提案本体重叠 → 收窄（已完成项移出，净交付 = 2 处文档编辑 + 1 份 mock）；Meta 状态判据改为可机检形式 → **批准**，从 suggestions 移入 approved | 索引双向一致（交集 0） |

**metis 审查**：新建的 2 个 improvement 经 metis gap 分析，报 4 个 BLOCKER + 8 个 quality/nice-to-have，**全部处理**：

- 2 个 BLOCKER 是草稿文本与既有测试语义不符 —— 「后 2 行内」应为「所在行本身」（测试是无 `-A` 的 grep）、「一级标题 `###`」措辞矛盾 → 已改，并用临时 AGENTS.md **实测 6/6 断言通过**
- 1 个 BLOCKER 是 A-2 判据恒真 —— `arch_audit_check.py` 只有 3 项检查，确无「关联 change 缺失」检查 → 改为「记录现状」而非断言
- 1 个 BLOCKER 是 A-1 与 archive gate 的交互未说明 → 补「跨角色收口，不阻塞归档」
- 另有：V-1..V-8 拆成「已实施证据」/「本提案待办」两组、V-6 补可粘贴命令、两个未决外溢写明、refresh 洁净度判据与执行顺序、位置约束（AUTO 哨兵段）、`trap #6` 历史命名说明、A-0 双向指针

## 三、追加：roadmap-md-integrity（builder）

doctor 要求 AUTO-INDEX 有 Phases / Features / **Objectives** 三段，但 `render_fragment_index` 只渲染前两段 → 每个项目都报假缺口。

修复：`_lib/roadmap_state.py` 新增 `load_objectives()`（objective 不是 fragment，frontmatter schema 不同，用 `_lib.objective.parse_objective` 解析；archived 与不可解析文件跳过）+ renderer 渲染 `### Objectives` 段（**始终输出**，无 objective 时写 `- _(none)_`，避免「没有 objective 反而报缺段」）。6 个新单测。

验证：`doctor --category roadmap-md-integrity` ✅；roadmap/doctor/objective 相关 351 个测试全过。

## 四、遗留清单（交用户裁决，本轮按「只修 roadmap-md-integrity，其余记录」执行）

| # | 遗留 | 现状 | 处置 |
|---|---|---|---|
| 1 | 52 条 `review-debt.unticketed-marker` | 历史代码里的 TODO/FIXME/HACK 无 ticket 关联 | 记录，未修 |
| 2 | 8 条 `arch-audit` | 存量 ADR 的 status 字段非终态（如「待定」） | 记录，未修（存量不追溯） |
| 3 | 1 条 `ai-context-bootstrap` | AGENTS.md 无 Layer 0 块，需 `rddf setup ai-context` 部署 | 记录，未修 |
| 4 | 5 条已知失败无活跃归属 | env-bootstrap `--help` flags / `mark_approved_completed` 幂等 / `phase0_approval.sh --auto-approve` 5 段 / 2 条 SKILL.md description —— 各自指向另一个 TBD 占位 fragment | 记录，未修（另有 6 条 AGENTS.md 类已建 improvement 覆盖） |
| 5 | ADR-0060 元数据指针回填（A-1） | architect 职责 | 未做，跨角色收口不阻塞 |
| 6 | `tests/unit/test_guide_close_local_var.py::test_guide_close_can_read_project_root_in_trap_context` 偶发 30s 超时 | **既有 flaky，非本轮引入**：单独跑 3/3 通过（1.7–3.2s）；该测试只依赖 `guide_entry.sh` + `rddf_session_hooks.sh`（本轮未改），且 `guide_entry.sh` 不解析 AUTO-INDEX（`parse_auto_index_segments` 仅 doctor 使用） | 记录，未修（满载下的超时余量问题） |
| 7 | `rddf roadmap --refresh-fragments` 未在 CLI 子命令表里暴露 | 脚本 `skills/roadmap/scripts/roadmap_refresh_fragments.sh` 存在且可用，但 `rddf roadmap --refresh-fragments` 打印 help | 记录，未修（直接调脚本绕过） |

## 五、当前 doctor 全貌

`rddf doctor` → **0 CRITICAL · 58 WARNING · 5 INFO**（本轮开始时 74 WARNING）。剩余 WARNING 的构成：52 条 `review-debt.unticketed-marker`（历史 TODO/FIXME）+ 8 条 `arch-audit`（存量 ADR 的 status 非终态）+ 1 条 `ai-context-bootstrap`（AGENTS.md 无 Layer 0 块），以及少量与已知失败相关的归因记录。
