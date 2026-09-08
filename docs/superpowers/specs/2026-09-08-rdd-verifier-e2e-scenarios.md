# rdd-verifier e2e 测试场景 spec

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` v1
> **覆盖 skill**: `rdd-verifier`（per ADR-0034 5 阶段架构验证回环、ADR-0045 inline-ac-verifier 自包含 LLM 验证、ADR-0035 verifier-archive-gate 双轨边界）
> **scenario 数**: 8（V-E1..V-E8）

## 0. 通用约定

详见 `2026-09-08-rdd-quick-e2e-scenarios.md` §0 通用约定字段定义。本 spec 复用。

**rdd-verifier 专属约定**：
- 入口：`skill_use("rdd-verifier")` 调 `rdd-verifier/SKILL.md` prose 状态机（自包含 LLM 验证协议，per ADR-0045）
- 验证协议：执行 agent 自身即 LLM，无需 `AC_LLM_*` env vars
- verdict schema：6 字段 `ac_id` / `description` / `status` / `confidence` / `evidence` / `reasoning`（per VERDICT_ITEM_SCHEMA）
- 状态机：read ACs → verify against code → classify → route
- 分类器：heuristic（implementation_gap / proposal_drift）
- 失败回环：max 3 retry，P3 → P1 (proposal_drift) / P3 → P2 (implementation_gap)
- 产物：`.rddf/state/.ac-verdict-<name>.json`
- AC 来源：plan 文件 `## Acceptance` 段（per rdd-quick P3 / rdd-builder P1 协同）
- verdict 缓存：`.rddf/state/.verifier-cache/<name>.json` v2

## V-E1: 读 plan ## Acceptance → 提取 AC

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt：`请读 .rddf/plans/<name>.md 的 ## Acceptance 段，提取所有 AC 并输出 JSON 列表` |
| 预期产物 | stdout JSON 数组，每项含 `ac_id` + `description`；与 plan 文件 checkbox 一一对应 |
| 必清状态 | 提取数 == plan `## Acceptance` 段 `- [ ]` 数；不读 `proposal.md`（per rdd-quick spec 锁） |
| AC 断言 | 数组长度与 plan 一致；每项 2 字段非空；`ac_id` 格式 `^AC-\d+$` |
| 隔离规则 | `setup_fake_project` 含 `.rddf/plans/<name>.md` fixture（3-5 AC） |
| 备注 | 验证 rdd-verifier 协议"AC source = plan ## Acceptance"契约 |

## V-E2: 读代码 → 6 字段 verdict JSON 构造

| 字段 | 内容 |
|------|------|
| 入口 | 接 V-E1；agent prompt：`请对每个 AC 验证：读对应代码，输出 VERDICT_ITEM_SCHEMA 6 字段` |
| 预期产物 | `.rddf/state/.ac-verdict-<name>.json` 存在；items 数组 6 字段齐全 |
| 必清状态 | verdict JSON 合 schema；`status ∈ {pass, fail, partial}`；`confidence ∈ [0.0, 1.0]`；`evidence` 是 ≥1 tool call 列表 |
| AC 断言 | `ac_id` / `description` / `status` / `confidence` / `evidence` / `reasoning` 6 字段 100% 齐全 |
| 隔离规则 | `setup_fake_project` 含真实代码 fixture（含部分实现、部分 stub） |
| 备注 | per `skills/rdd-verifier/SKILL.md` P3 verdict contract；与现有 8 unit tests 互补 |

## V-E3: pass 分类 → 升 archive 路径

| 字段 | 内容 |
|------|------|
| 入口 | 接 V-E2 全 pass；agent prompt：`AC 全部 pass，请走完成路径` |
| 预期产物 | stdout 含 `✓ All ACs passed` 段；verdict JSON `summary.pass=N/total`；下游 archive 路径可达 |
| 必清状态 | change 状态转入 archive-ready；iteration.json `status="verifying"` → `"archive-ready"` |
| AC 断言 | stdout 含 completed 段；summary 字段 N/N pass；status transition 正确 |
| 隔离规则 | 同 V-E2 |
| 备注 | 与 rdd-builder P3 / rdd-quick P4 completed 分支协同 |

## V-E4: fail → implementation_gap → 回 P2

| 字段 | 内容 |
|------|------|
| 入口 | 接 V-E2；故意让 AC 1 fail（plan 写"AC-1: function returns 42 for empty"但 impl 返回 false） |
| 预期产物 | verdict JSON `status=fail`；`reasoning` 字段含 gap 关键词（"not implement" / "missing" / "absent" / "todo: implement"）；路由信号 "implementation_gap" |
| 必清状态 | iteration.json `routing_target="phase-2"`；retry_count=1 |
| AC 断言 | status=fail；reasoning 含 gap keyword；routing_target 非空 |
| 隔离规则 | 同 V-E2 |
| 备注 | per `VERDICT_ITEM_SCHEMA` 路由层分类逻辑；routing layer 必须能正确分流 |

## V-E5: fail → proposal_drift → 回 P1

| 字段 | 内容 |
|------|------|
| 入口 | 接 V-E2；故意让 AC 1 fail 但代码实现正确（proposal 写错 AC） |
| 预期产物 | verdict JSON `status=fail`；`reasoning` 字段含 drift 关键词（"exists but" / "discrepan" / "mismatch" / "differs from ac"）；路由信号 "proposal_drift" |
| 必清状态 | iteration.json `routing_target="phase-1"`；retry_count=1 |
| AC 断言 | status=fail；reasoning 含 drift keyword；routing_target="phase-1" |
| 隔离规则 | 同 V-E2 |
| 备注 | V-E4 vs V-E5 是核心分类器测试；routing layer 决定下游 |

## V-E6: partial 分类 — 部分通过

| 字段 | 内容 |
|------|------|
| 入口 | 接 V-E2；3 AC 中 2 pass + 1 fail |
| 预期产物 | verdict JSON 含 3 item：2 pass / 1 fail；`summary.pass=2/3, fail=1/3` |
| 必清状态 | partial 状态正确识别；下游按"已通过部分存档"或"全部重测"二选一（per rdd-verifier SKILL.md P3 决策） |
| AC 断言 | 数组长度 3；2 个 status=pass，1 个 status=fail；summary 字段正确 |
| 隔离规则 | 同 V-E2 |
| 备注 | 验证 verdict 多 item 正确分类；与现有单 AC 测试互补 |

## V-E7: 3 次重试上限 → escal

| 字段 | 内容 |
|------|------|
| 入口 | 接 V-E4 fail 路径；3 次连续重试（retry 1, 2, 3） |
| 预期产物 | 第 3 次重试后 escal；iteration.json `routing_target="escal"`；stdout 含升级摘要 |
| 必清状态 | `retry_count=3 == RDDF_VERIFIER_MAX_RETRIES=3`；不再循环 |
| AC 断言 | 第 3 次后不再 retry；escal 状态正确；升级摘要 4 元素（per rdd-quick P4 模板） |
| 隔离规则 | 同 V-E2 |
| 备注 | per spec §3.4 P3 max 3 retry；与 rdd-builder B-E11 互锁 |

## V-E8: 离线 / 无 LLM 凭据时 graceful skip

| 字段 | 内容 |
|------|------|
| 入口 | 故意 unset `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / 本地 agent 凭据 |
| 预期产物 | rdd-verifier SKILL.md prose 给出 skip 路径；不 crash；stderr 含明确 skip 原因 |
| 必清状态 | verdict JSON 不写（因 skip）；iteration.json 不变 |
| AC 断言 | exit code ∈ {0, 125}（125 = bats skip 约定）；stderr 含 "skip" 关键词；无 exception traceback |
| 隔离规则 | env 隔离用 `env -i` 子进程 |
| 备注 | C 层 nightly 在无凭据环境 graceful skip；与 A 层 smoke（无 LLM 依赖）分离 |

## 覆盖矩阵

| verifier 内部 phase | 覆盖 scenarios |
|---------------------|----------------|
| AC 提取 | V-E1 |
| 验证 + verdict 构造 | V-E2 |
| Pass 路径 | V-E3 |
| Fail 分类（gap） | V-E4 |
| Fail 分类（drift） | V-E5 |
| Partial 分类 | V-E6 |
| 重试上限 | V-E7 |
| 凭据缺失 skip | V-E8 |

## 与现有 8 cases 的关系

- `tests/unit/test_rdd_verifier_protocol.py`（5）+ `test_verifier_cache_v2.py`（3）：保留，单元层
- `tests/integration/test_ac_verifier_archive_gate.bats`（已 deprecated per ADR-0045）+ `test_ac_verify_removed.bats`：保留为历史契约锁
- `tests/integration/test_archive_gate_no_ac_fallback.bats`：保留，archive gate fallback 契约
- `tests/e2e/agent/test_rdd_verifier_e2e.bats`（8，本 spec）：新增，prose UX 真 e2e

总计 16+ cases 覆盖 rdd-verifier（8 旧 + 8 新），分层无重叠。

## 关键协同

| 协同 skill | 协同点 |
|------------|--------|
| rdd-quick P3 | verdict 协议复用（Q-E5 / Q-E6 路径走 V-E2 schema） |
| rdd-builder P3 | verdict 输出驱动 archive 决策（V-E3 → B-E9；V-E4 → B-E11） |
| ac-verifier（deprecated） | ADR-0045 完成后 v2.0 移除，本 spec 取代其 e2e 覆盖 |

## ⚠️ 关键约束

per ADR-0035（verifier-archive-gate 双轨边界）：
- `STRICT_AC_GATE=yes` 时 verifier fail 必须阻断 archive
- `SKIP_AC_VERIFY=yes` 时 archive 跳过 verifier（仅 hotfix）
- `SKIP_RDD_VERIFIER=yes` 时整个 rdd-verifier 阶段跳过

本 spec V-E1..V-E7 默认 `STRICT_AC_GATE=yes`；V-E8 显式 unset env vars。
