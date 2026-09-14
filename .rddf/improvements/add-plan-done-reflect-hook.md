# add-plan-done-reflect-hook

**优先级**: P1 | **来源**: 反思工作流 e2e 覆盖分析（rdd-workflow-e2e 集成验证）
**阶段**: default | **分类**: core-impl
**类型**: feature
**关联 ADR**: ADR-0027 §1.0 双平面架构, ADR-0029 issue-driven proposal, ADR-0048 §Decision 2
**关联变更**: add-workflow-reflect-engine (原提案，遗漏 plan-done hook)

## Why

`add-workflow-reflect-engine` 原提案（2026-08-12, ADR-0027）声明 3 个 gate hook 点全部接入：

> guide-plan: Phase 4 gate → plan-done pass → reflect_engine(plan)

实际落地状态（2026-09-14 audit）：
- ✅ arch-done hook: `skills/rdd-arch/scripts/write_arch_handoff.sh:48-66` 已 wired
- ❌ plan-done hook: **未实现** — `skills/rdd-planner/scripts/planner_stage_exit.sh` 无 reflect 调用
- ✅ archive hook: `_lib/archive.sh:642-670` 已 wired

后果：
1. **planner 阶段失败无反思**：proposal 反复被同一质量门拒、跨多 phase 的 plan-done 阻塞，无 fingerprint 冷却、无 dedup 命中反馈
2. **dedup matcher 实际只在 plan/ship 阶段使用**：arch 是 log-only 永不 propose；plan 未挂 hook 等于 dedup matcher 永远 idle
3. **ADR-0027 §10 数据流图不闭合**：`rdd-planner` Phase 0/4 → box 缺失
4. **e2e 覆盖测试明确指出缺口**：`tests/integration/test_full_workflow_e2e.bats` 与 `tests/e2e/_lib/reflect_invoke.py` 都把 plan phase 作为直调引擎 API 的测试入口，绕过了生产 wiring；`rdd-workflow-e2e` 外部 testbed 也确认 0 case 覆盖 plan-done 集成

修复目的：把 plan-done hook 补全，与 arch/ship 对齐；保持 ADR-0027 双平面架构一致（Script 平面 inline hook + Agent 平面 SKILL.md 指令）。

## What Changes

新增 1 个 inline hook 调用 + 1 个 SKILL.md 段：

**1. Script 平面** — `skills/rdd-planner/scripts/planner_stage_exit.sh` 末尾追加：
- 与 `write_arch_handoff.sh:48-66` / `_lib/archive.sh:642-670` 完全同款模式
- 守卫：`SKIP_WORKFLOW_REFLECTION != 1`
- Phase: `plan`
- failures: 从 `.rddf/state/event_log.json` 末 20 条过滤 `unrecovered_failure` / `execute_error`
- Non-blocking: `2>/dev/null || true`

**2. Agent 平面** — `skills/rdd-planner/SKILL.md` 末尾新增：
- 标题："Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)"
- 与 `skills/rdd-arch/SKILL.md:712-730` 完全对齐的 checklist + 触发清单
- 替换词：phase 名 `rdd-arch` → `rdd-planner`

**3. 集成测试** — 3 个新 e2e case：
- A 层 `tests/e2e/script/test_reflect_smoke.bats`：
  - R-E10: plan-done hook 在 planner_stage_exit.sh 成功路径上触发且不阻塞（harness 跑真实脚本）
  - R-E11: SKIP_WORKFLOW_REFLECTION=1 + planner_stage_exit 仍成功（skip guard non-blocking）
- testbed `rdd-workflow-e2e/tests/integration/test_reflect_plan_hook_e2e.bats`：第三方项目视角 2 case
  - plan hook in third-party install
  - SKIP_WORKFLOW_REFLECTION 在第三方项目生效

## Impact

### In Scope

| 项目 | 改动量 |
|------|--------|
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | +19 行 inline hook（与 write_arch_handoff.sh L48-66 镜像） |
| `skills/rdd-planner/SKILL.md` | +20 行 "Phase Exit" 段 |
| `tests/e2e/script/test_reflect_smoke.bats` | +2 个 @test case |
| `rdd-workflow-e2e/tests/integration/test_reflect_plan_hook_e2e.bats` | +2 个 @test case（新文件） |
| ADR-0027 §1.0 数据流图 | 不需改（graph 已含 plan box，只是 implementation 缺失） |
| AGENTS.md "已 wired 生产 hook" 列表 | +1 行更新 |

### Out Scope

| 项目 | 原因 |
|------|------|
| 改 _lib/reflect_engine.py 引擎逻辑 | 引擎本身已支持 phase=plan（unit tests 已覆盖 R-E3/R-E4/R-E5/R-E6） |
| 改 dedup matcher 或 cooldown | 行为契约已稳定，引擎 API 直调测试 9/9 pass |
| 引入新的 SKILL.md "Phase Exit" 模板 | 复用 rdd-arch L712-730 现有模板 |
| 加 rdd-builder / rdd-verifier 的 Phase Exit 段 | builder/verifier 当前无对应反思触发点（builder 失败归 ship phase 的 archive hook；verifier 是判定者无 fail-by-itself） |
| 修 `_scan_suggestions` 的 json.load 死路径 | 单独 improvement（已被 R-E5 规避：测试种子走 `.rddf/improvements/*.md`） |
| 引入 C 层 scenario JSON | 单独 follow-up（mock 模式零行为信号，需 maintainer 决定） |

### Backward Compatibility

- ✅ 无破坏：现有 planner_stage_exit 行为不变（hook 末尾追加，失败被 `|| true` 吞）
- ✅ 无新依赖：复用 _lib/reflect_engine.py 既有 import path
- ✅ 无 schema 变更：planner-handoff-v1 不动
- ✅ 无 CLI 变化：rddf planner 不增子命令
- ⚠️ fixture 调整：现有 `tests/integration/test_full_workflow_e2e.bats` teardown 第 33 行已 `unset SKIP_WORKFLOW_REFLECTION`，无需改；现有 `invoke_planner_stage`（fixture L188）暂不挂 reflect（仍 export SKIP_WORKFLOW_REFLECTION=1 抑制副作用），未来若需 e2e 验证 plan hook 走集成通道，须扩展 fixture 新增 `invoke_planner_stage_with_reflect`（参考 `invoke_arch_stage_with_reflect` 模式）

## Capabilities

### MUST

- `planner_stage_exit.sh` 成功完成 `.planner-handoff.json` 写入后，**总是**触发 `ReflectEngine(phase='plan').analyze()`，除非 `SKIP_WORKFLOW_REFLECTION=1`
- `ReflectEngine(phase='plan')` 的 failures 输入从 `.rddf/state/event_log.json` 末 20 条过滤 `unrecovered_failure` / `execute_error` 事件（与 ship hook 一致）
- Reflect 异常/超时被 `2>/dev/null || true` 吞掉，不影响 planner_stage_exit 退出码
- `SKIP_WORKFLOW_REFLECTION=1` 时：bash hook 不执行；SKILL.md "Phase Exit" 段仍生效（agent 平面独立于 bash hook）
- rdd-planner SKILL.md 新增段必须**逐字对齐** rdd-arch L712-730 模板（除 phase 名 `rdd-arch` → `rdd-planner` 外）

### MUST NOT

- 不修改 _lib/reflect_engine.py 任何业务逻辑
- 不修改 _lib/planner_handoff.py 任何 handoff schema
- 不阻塞 planner_stage_exit 的 exit code（即使 reflect 抛异常，planner 必须返回 0 或 planner-done 双门控自身的 2）
- 不引入新的 env var（仅复用既有的 SKIP_WORKFLOW_REFLECTION）
- 不创建 .rddf/issues/ 目录或 .rddf/state/.quick-history.jsonl（这些属于 rdd-quick / rddf issue 等其他子系统）
- 不修改 improvement-suggestions.md / improvement-approved.md / .rddf/improvements/*.md 内容

## Acceptance

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | `planner_stage_exit.sh` 末尾含 `ReflectEngine(phase='plan')` 调用 | `grep -n 'ReflectEngine(phase="plan"' skills/rdd-planner/scripts/planner_stage_exit.sh` |
| 2 | `planner_stage_exit.sh` 含 SKIP_WORKFLOW_REFLECTION 守卫 | `grep -n 'SKIP_WORKFLOW_REFLECTION' skills/rdd-planner/scripts/planner_stage_exit.sh` |
| 3 | `planner_stage_exit.sh` 含 `2>/dev/null \|\| true` non-blocking 后缀 | grep 验证 |
| 4 | `rdd-planner/SKILL.md` 末尾含 "Phase Exit — Post-Flow Analysis" 段 | `tail -30 skills/rdd-planner/SKILL.md \| grep "Phase Exit"` |
| 5 | `rdd-planner/SKILL.md` Phase Exit 段含 `rddf report-issue --phase rdd-planner` 模板 | grep 验证 |
| 6 | A 层 R-E10 pass：plan hook 集成 + handoff 正常写 | `bats tests/e2e/script/test_reflect_smoke.bats -f "R-E10"` |
| 7 | A 层 R-E11 pass：SKIP_WORKFLOW_REFLECTION=1 + planner_stage_exit 仍成功 | `bats tests/e2e/script/test_reflect_smoke.bats -f "R-E11"` |
| 8 | testbed 2/2 新增 case pass | `RDD_WORKFLOW_REPO=~/.agents/skills/rdd-workflow bats tests/integration/test_reflect_plan_hook_e2e.bats` |
| 9 | 本仓 pytest unit + integration 零失败 | `./test.sh --unit && ./test.sh --integration` |
| 10 | 现有 planner e2e 集成（test_full_workflow_e2e 2/7）零回归 | `bats tests/integration/test_full_workflow_e2e.bats` |
| 11 | 仓级零污染：`.rddf/` `openspec/changes/` 无新增 | `git status --short .rddf/ openspec/` |
| 12 | AGENTS.md "已 wired 生产 hook" 段更新 plan 阶段 | `grep "plan.*reflect\|planner_stage_exit.*reflect" AGENTS.md` |

## 实施 Plan（建议执行顺序）

1. **FU-3**（30 min）— Script 平面：在 planner_stage_exit.sh 加 inline hook（与 write_arch_handoff.sh L48-66 镜像）
2. **FU-4**（15 min）— Agent 平面：在 rdd-planner/SKILL.md 加 "Phase Exit" 段
3. **FU-5**（30 min）— A 层补 R-E10 + R-E11 case
4. **FU-6**（30 min）— testbed 新增 test_reflect_plan_hook_e2e.bats
5. **FU-7**（15 min）— 全量回归 + 零污染检查 + 更新 AGENTS.md

总工时 ~2h，CI 流水线 +~3s

## 风险

| 风险 | 缓解 |
|------|------|
| planner_stage_exit 当前 export `SKIP_AUTO_PLANNER_FEEDBACK=1` 之类的 gate 守卫，与 SKIP_WORKFLOW_REFLECTION 语义混淆 | reflect hook 不依赖任何现有 export；只读 `SKIP_WORKFLOW_REFLECTION` 单变量 |
| `.rddf/state/event_log.json` 不存在时，failures=[]，reflect 返回 action=none，无副作用（与 ship hook 同款） | 已验证（现有 inline bash 通过 `os.path.isfile` 守卫） |
| rdd-planner SKILL.md Phase Exit 段被 rdd-builder/rdd-verifier 误读 | 段标题明确 "Phase Exit — Post-Flow Analysis"，scope 限定本阶段 |
| 双平面间状态不一致（bash hook 跑了但 SKILL.md 没指令 agent，或反之） | 双平面**完全独立**：bash hook 在脚本退出时自动跑（Script 平面）；SKILL.md 指令 agent 在 turn 结束时主动调 rddf report-issue（Agent 平面）。两者互不阻塞，可同时触发 |
| testbed 全量回归出现新失败 | 先跑本仓 A 层 + integration；通过后再跑 testbed |
