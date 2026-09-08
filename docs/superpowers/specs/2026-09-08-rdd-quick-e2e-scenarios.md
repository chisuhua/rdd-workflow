# rdd-quick e2e 测试场景 spec

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` v1
> **覆盖 skill**: `rdd-quick`（per ADR-0047）
> **scenario 数**: 8（Q-E1..Q-E8）

## 0. 通用约定

每 scenario 含：name / phase / 入口 / 预期产物 / 必清状态 / AC 断言 / 隔离规则 / 备注。

| 字段 | 含义 |
|------|------|
| 入口 | 调用的脚本/agent prompt/状态机启动命令 |
| 预期产物 | scenario 成功后必须存在的文件 / git ref / stdout 段 |
| 必清状态 | scenario 结束后必须还原的状态（sha256 锁） |
| AC 断言 | 验收项（含 golden output 关键字段） |
| 隔离规则 | 用 BATS_TEST_TMPDIR + fake project；不写 `$REPO_ROOT/.rddf/` |
| 备注 | 与现有 `test_rdd_quick.bats` 14 cases 的覆盖关系（互补 vs 替代） |

## Q-E1: P0 简单提案 → 脚手架 plan

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt：`scaffold_plan.sh --name "add-helper-fn" --proposal "Add a helper function that returns true for non-empty strings"` |
| 预期产物 | `.rddf/plans/quick-add-helper-fn.md` 存在；含 5 TDD marker + `## Acceptance` ≥1 AC |
| 必清状态 | `$FAKE_ROOT/.rddf/` 整体 sha256 在 setup 前 = teardown 后；`$REPO_ROOT/.rddf/` 不变 |
| AC 断言 | plan 含 `Step 1: Write the failing test` + `Step 5: Defer commit`；至少 1 个 `- [ ] AC-N: ...`；文件名 `quick-` 前缀 |
| 隔离规则 | `BATS_TEST_TMPDIR` + `setup_fake_project "$FAKE_ROOT"`；teardown `rm -rf "$FAKE_ROOT"` |
| 备注 | 现有 `test_rdd_quick.bats` 测脚本输出 contract；本 case 测 agent 能否真调脚本 + 输入传递正确 |

## Q-E2: P1 复杂提案触发 Metis/Oracle 评审

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt：`scaffold_plan.sh --name "migrate-pg-v15" --proposal "<含 migration + refactor + 多文件改动的 200+ token 提案>"` |
| 预期产物 | 计划文件中 `**Metadata**` 段含 `reviewed_by: metis+oracle`；stdout 含 `[Metis]` 和 `[Oracle]` 调用记录 |
| 必清状态 | 同 Q-E1 |
| AC 断言 | plan frontmatter 或 metadata 段含 `reviewed_by: metis+oracle`；scenario JSON 中 `expected.reviewed_by == "metis+oracle"` |
| 隔离规则 | 同 Q-E1 |
| 备注 | 验证复杂度分诊真触发；阈值由 SKILL.md prose 定义，agent 必须正确识别 |

## Q-E3: P1 简单提案直入 P2（跳过 review）

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt：`scaffold_plan.sh --name "fix-typo" --proposal "Fix typo in README"` |
| 预期产物 | plan 中 `reviewed_by` 字段缺失或为 `null`；stdout 无 Metis/Oracle 调用 |
| 必清状态 | 同 Q-E1 |
| AC 断言 | plan `reviewed_by` 不含 "metis" 也不含 "oracle"；plan size < 阈值 |
| 隔离规则 | 同 Q-E1 |
| 备注 | 与 Q-E2 互补：验证阈值边界 |

## Q-E4: P2 TDD 5 步就地执行

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt：`请按 .rddf/plans/quick-add-helper-fn.md 的 TDD 5 步执行，记录每个 step 结果` |
| 预期产物 | `$FAKE_ROOT/` 含新 test 文件 + impl 文件 + 1 git commit；commit message 含 "rdd-quick:" 前缀 |
| 必清状态 | `$REPO_ROOT/.rddf/` 不变；`$FAKE_ROOT/.rddf/state/.quick-history.jsonl` 含本次 entry |
| AC 断言 | 5 个 step checkbox 全部 `- [x]`；`git log -1` 含 commit；`history.jsonl` 最后一行 `name=add-helper-fn` + `outcome=completed` |
| 隔离规则 | `setup_fake_project` 含 git init + `tests/e2e/fixtures/sample_helper.py`；teardown 全清 |
| 备注 | A 层 `script/test_rdd_quick_smoke.bats` 测 scaffold 本身；本 case 测 agent 真跑 TDD 循环 |

## Q-E5: P3 全部 AC pass → completed

| 字段 | 内容 |
|------|------|
| 入口 | 接 Q-E4；agent prompt：`请按 quick-add-helper-fn.md ## Acceptance 段验证全部 AC，写 verdict JSON` |
| 预期产物 | `$FAKE_ROOT/.rddf/state/.ac-verdict-quick-add-helper-fn.json` 存在；history.jsonl `outcome=completed` |
| 必清状态 | 同 Q-E4 |
| AC 断言 | verdict JSON 6 字段齐全：`ac_id` / `description` / `status` / `confidence` / `evidence` / `reasoning`；所有 AC `status="pass"`；history `verdict_summary` 含 "N/N pass" |
| 隔离规则 | 同 Q-E4 |
| 备注 | 验证 rdd-verifier 协议（per ADR-0045）真被复用 |

## Q-E6: P3-P4 部分 AC fail → retry 1/3

| 字段 | 内容 |
|------|------|
| 入口 | 接 Q-E4 变体；plan 含故意写错的 AC（如 "AC-2: function returns 42 for empty string" 但 impl 返回 false） |
| 预期产物 | history.jsonl 含 2 条 entry（retry 1 + final）；retry_count=1；最终 `outcome=completed`（修复后） |
| 必清状态 | 同 Q-E4 |
| AC 断言 | history.jsonl 行数 ≥ 2；第一次 retry 时 `outcome="unverified"`，修复后 `outcome="completed"`；`retry_count` 字段递增 |
| 隔离规则 | 同 Q-E4 |
| 备注 | 验证重试回路真触发；与现有 `RDDF_QUICK_MAX_RETRIES=3` 默认对齐 |

## Q-E7: P4 retry 3/3 仍 fail → escalate

| 字段 | 内容 |
|------|------|
| 入口 | 故意写破坏性 plan（AC 互相矛盾，无解）；agent prompt 同 Q-E5 |
| 预期产物 | stdout 含升级摘要 4 元素（原始提案 / git diff --stat / 失败 ACs / `Run skill_use("rdd-planner")` 提示）；history.jsonl `outcome=escalated` |
| 必清状态 | `$FAKE_ROOT/openspec/changes/` 和 `$REPO_ROOT/openspec/changes/` **均不变**（关键零污染断言） |
| AC 断言 | stdout 含 `=== Escalation Summary ===` 4 段标题；history `outcome="escalated"` + `retry_count=3` + `upgraded_to_change=null` |
| 隔离规则 | 同 Q-E4 |
| 备注 | 验证升级路径 + 零污染升级（不自动落 openspec change） |

## Q-E8: 隔离契约 — 不污染四阶段路径

| 字段 | 内容 |
|------|------|
| 入口 | 真跑 Q-E1..Q-E7 全部 7 个 scenario 后，扫 `$REPO_ROOT/` 关键路径 |
| 预期产物 | 7 个 scenario 的 `isolation_audit.json`（每个 case 一份），含 baseline / after 两条 sha256 记录 |
| 必清状态 | `$REPO_ROOT/.rddf/` / `openspec/` / `.rddf/wt/` / `iteration.json` / `sessions.json` / `roadmap-state.json` 全部 sha256 == setup 前 |
| AC 断言 | `isolation.bash::verify_zero_pollution` exit 0；6 个锁定文件全部 unchanged |
| 隔离规则 | meta-测试，跨 7 case 汇总 |
| 备注 | per ADR-0047 零污染契约（spec Scenario 锁 hash）的真 e2e 验证 |

## 覆盖矩阵

| skill 内部 phase | 覆盖 scenarios |
|-------------------|----------------|
| P0 plan gen | Q-E1 |
| P1 complexity triage | Q-E2, Q-E3 |
| P2 in-place execution | Q-E4 |
| P3 AC verification | Q-E5, Q-E6 |
| P4 completion/retry/escalate | Q-E6, Q-E7 |
| 零污染契约 | Q-E8 |

## 与现有 27 cases 的关系

- `tests/unit/test_quick_history.py`（9）：保留，单元层
- `tests/integration/test_rdd_quick.bats`（14）：保留，契约/结构层
- `tests/integration/test_rdd_quick_isolation.bats`（4）：保留，hash 锁层
- `tests/e2e/agent/test_rdd_quick_e2e.bats`（8，本 spec）：新增，prose UX 真 e2e

总计 35 cases 覆盖 rdd-quick（27 旧 + 8 新），分层无重叠。
