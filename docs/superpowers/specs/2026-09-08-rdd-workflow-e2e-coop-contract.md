# rdd-workflow ↔ chisuhua/rdd-workflow-e2e 协同契约

> **日期**: 2026-09-08
> **状态**: v1
> **关联 spec**: `2026-09-08-e2e-test-plan-design.md` §6
> **本仓角色**: 单 skill 真 e2e（prose UX + 零污染契约）
> **外部 testbed 角色**: 4-5 stage 全流程集成（arch + planner + (quick|builder) + verifier）+ 36 rddf CLI 子命令 smoke

## 1. 职责边界

| 职责 | 本仓 `tests/e2e/` | 外部 `rdd-workflow-e2e` |
|------|-------------------|--------------------------|
| 单 skill prose UX 真 e2e | ✅ C 层 5 skill (44 scenarios) | — |
| Phase 脚本非交互 smoke | ✅ A 层 10 cases | — |
| 4-5 stage 全流程 e2e | — | ✅ 第三方项目视角 |
| 36 rddf CLI 子命令 smoke | — | ✅ |
| 第三方项目视角安装测试 | — | ✅ |
| 跨 stage 状态机集成 | — | ✅ |
| Prose 漂移检测（SKILL.md 改动） | ✅ C 层（per skill） | — |
| 零污染契约（sha256 锁 6 路径） | ✅ A 层 + C 层 | — |

**核心原则**：互补不重复。本仓 5 skill 内部状态机细粒度；外部 testbed 多 stage 集成粗粒度。

## 2. 数据交换格式

### 2.1 Scenario JSON (本仓 → 外部)

外部 testbed 启动 rdd-workflow skill 时，可读取本仓的 `tests/e2e/agent/scenarios/*.json` 作为 fixture 模板：

```json
{
  "scenario_id": "Q-E1",
  "skill": "rdd-quick",
  "input": { "command": "...", "args": [...] },
  "golden_output": { "files": [...], "stdout_contains": [...] },
  "isolation": { "locked_paths": [".rddf", "openspec"] }
}
```

**Schema 版本**: v1 (5 必填字段：scenario_id / skill / input / golden_output / isolation)

### 2.2 Verdict JSON (本仓 C 层 → 外部 testbed)

`.rddf/state/.ac-verdict-<name>.json` 6 字段 per `VERDICT_ITEM_SCHEMA`：

```json
{
  "ac_id": "AC-1",
  "description": "...",
  "status": "pass | fail | partial",
  "confidence": 0.0-1.0,
  "evidence": "...",
  "reasoning": "..."
}
```

**Schema 版本**: v1 (per ADR-0034 + ADR-0045)

### 2.3 Golden Output

`mock_output` 段用于 mock mode（CI 安全）：

```json
{
  "mock_output": {
    "files": {"relpath": "content"},
    "stdout": "..."
  }
}
```

外部 testbed 可选：若希望真跑 agent 验证 prose 漂移，调 `RDDF_AGENT_E2E=1` + `opencode --prompt <prompt>`。

## 3. 失败传播规则

| 失败位置 | 触发 | 响应 |
|----------|------|------|
| 外部 testbed nightly 全流程失败 | 4-5 stage 集成 | 本仓跑对应单 skill C 层 scenarios 定位故障域 |
| 本仓 A 层 smoke 失败 | phase 脚本回归 | 修脚本后通知外部 testbed 重跑 |
| 本仓 C 层 scenarios 失败 | prose drift | 修 SKILL.md 后通知外部 testbed 重跑 stage 集成 |

**双向通知机制**：通过 GitHub Issues 标签 `[rdd-workflow-e2e-coop]` 互通。

## 4. 版本兼容矩阵

| 组件 | 本仓要求 | 外部 testbed 要求 | 兼容性 |
|------|----------|-------------------|--------|
| openspec CLI | v1.3.1+ | v1.3.1+ | ✅ |
| bats-core | 1.10+ | 1.10+ | ✅ |
| Python | 3.11+ | 3.11+ | ✅ |
| git | 2.25+ | 2.25+ | ✅ |
| scenario JSON schema | v1 | v1 (read) | ✅ |
| verdict JSON schema | v1 | v1 (read) | ✅ |

**升级策略**：本仓主版本升 scenario JSON schema 时，外部 testbed 需同步支持新 schema；旧 schema 维护至少 1 release cycle。

## 5. 本仓新增的契约测试

`tests/e2e/integration/test_rdd_workflow_e2e_coop.bats`（3 cases）：

1. **scenario JSON 兼容** — 验证所有 `tests/e2e/agent/scenarios/*.json` 含 5 必填字段（外部 testbed reader 必读字段）
2. **verdict JSON 兼容** — 验证 `.rddf/state/.ac-verdict-*.json` mock_output 6 字段齐全
3. **workflow 触发合规** — 验证 `.github/workflows/e2e-nightly.yml` + test.yml 含 e2e 步骤且 `continue-on-error` 设置正确

## 6. 手动协同命令

```bash
# 外部 testbed 跑本仓 fixtures（第三方项目视角）
cd rdd-workflow-e2e
RDDF_WORKFLOW_REPO=~/.agents/skills/rdd-workflow bats tests/

# 本仓跑回放外部 testbed 报告（手动）
RDD_E2E_REPORT_PATH=/path/to/rdd-workflow-e2e/report.json \
    ./test.sh --regression-external
```

## 7. 升级到下一版契约

- 本 spec 升级时同步通知 chisuhua/rdd-workflow-e2e maintainer
- 双方 PR review 加 `[rdd-workflow-e2e-coop]` 标签
- 至少 1 release cycle 双 schema 并存
