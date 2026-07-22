---
SCOPE: shared
STATUS: PROPOSED
---

## Why

OpenSpec 工作流在 `g-gpu-client-default-stub-init` ship 流程中暴露了两个 spec 验证盲点，导致返工：

**盲点 1: Baseline claim 无自动验证**（2026-07-11 v1 incident）

`g-gpu-client-default-stub-init` 的 `.openspec.yaml` `baseline:` 段声称：

> `g_cuda_stub static instance: already exists in src/test_fixture/cuda_stub.cpp`

但 `git log -S "CudaStub g_cuda_stub" --all` 仅返回该 spec 自身的提交——静态实例**从未存在**。Oracle bg_afcc8f4b 调查花费 10+ 分钟才发现。最终导致：
- v1 change 被 supersede 为 v2（`g-gpu-client-meyers-singleton-fallback`）
- 30+ 步骤的返工（重新规划 worktree、新建 change、重写 5 个 artifacts）

**盲点 2: MODIFIED/RENAMED target 在 archive 阶段才检查**（2026-07-11 v2 incident）

`g-gpu-client-meyers-singleton-fallback` 的 `specs/shim-default-init-fallback/spec.md` 在 `## MODIFIED Requirements` 段写了行为变更需求，但 `shim-default-init-fallback` 是新 capability（target spec 不存在）。结果：

- `openspec validate` ✅ 通过（不检查 target spec 存在性）
- `openspec archive` ❌ abort: `target spec does not exist; only ADDED requirements are allowed for new specs`

需要额外 6 步修复：编辑 spec → commit → push TaskRunner → bump submodule → push UsrLinuxEmu → 重试 archive。

**根本原因**：rdd-workflow 的验证逻辑分散在 `skills/propose.md` / `guide-plan.md` / `guide-ship.md` 三处，都只检查**结构完整性**（artifacts 存在、commit 存在），不检查**声明真实性**（baseline 是否成立、delta target 是否存在）。

## What Changes

新增 2 个验证工具 + 在 3 个 skill 入口接入：

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `skills/_lib/validate_baseline.py` | **新增** | 验证 `.openspec.yaml` `baseline:` 段的文件路径、符号、commit 历史声明 |
| `skills/_lib/validate_delta_targets.py` | **新增** | 验证 `spec.md` delta 段的 MODIFIED/RENAMED target capability 已在 main `openspec/specs/` 存在 |
| `skills/propose.md` | 修改 | 在 `openspec new change` 提交前调用 `validate_baseline.py`，exit 1 阻断 |
| `skills/guide-plan.md` | 修改 | Phase 4 plan-done gate 增加 `validate_baseline.py` + `validate_delta_targets.py` 调用 |
| `skills/guide-ship.md` | 修改 | Phase 3 archive 前置调用 `validate_delta_targets.py`，避免 archive abort |
| `tests/unit/test_validate_baseline.py` | **新增** | 单元测试覆盖所有 baseline claim 模式 |
| `tests/unit/test_validate_delta_targets.py` | **新增** | 单元测试覆盖所有 delta 场景 |

### Capabilities

#### New Capabilities

- **`spec-baseline-verification`**: 验证 `.openspec.yaml` 的 `baseline:` 段每条声明。支持的声明类型：
  - `file-exists:<path>` — 路径必须在文件系统存在
  - `symbol-exists:<file>:<symbol>` — 文件中必须 `grep` 到 `<symbol>`
  - `git-history:<symbol>` — `git log -S "<symbol>" --all` 必须返回 ≥1 个非 spec 自身的 commit
  - 自由文本（不可验证的描述）— 通过但记录

- **`spec-delta-target-validation`**: 验证 `spec.md` 中 `## MODIFIED Requirements` 和 `## RENAMED Requirements` 段的 target capability。规则：
  - `MODIFIED` target capability 必须在 `openspec/specs/<target>/spec.md` 已存在
  - `RENAMED` target capability 必须在 `openspec/specs/<source>/spec.md` 已存在（source 是被 rename 的旧 spec）
  - `ADDED` 不需要检查（新 capability 自然不存在）

#### Modified Capabilities

- `gate-mechanism.plan_done` 默认 checks 增加 1 项：`spec_baseline_verified` (error severity)
- `gate-mechanism.ship_done` 默认 checks 增加 1 项：`spec_delta_targets_verified` (error severity)

## Impact

- **影响文件**:
  - `skills/_lib/` 新增 2 个 ~150 LOC Python 模块
  - `skills/_lib/` 已有 `gate.py` 增加 2 个 check 函数（~20 LOC）
  - `skills/propose.md`、`skills/guide-plan.md`、`skills/guide-ship.md` 各插入 ~10 LOC 验证调用
  - `tests/unit/` 新增 2 个测试文件 ~200 LOC
- **破坏性变更**: 无。失败时仅阻断（exit 1），不影响通过路径。
- **API 变更**: 无。新工具仅 CLI 调用（`python3 validate_baseline.py <change-name>`）。
- **外部依赖**: 无新增。纯 Python 标准库（`subprocess`、`pathlib`、`re`、`json`）。
- **跨仓影响**: 无。rdd-workflow 是元仓，不影响 TaskRunner / UsrLinuxEmu。

## Acceptance Criteria

- [ ] `validate_baseline.py <change>` 对 `g-gpu-client-default-stub-init` v1 baseline 报错（exit 1，错误信息含"`CudaStub g_cuda_stub` symbol not found in git history"）
- [ ] `validate_delta_targets.py <change>` 对带 `MODIFIED` 段的非存在 target spec 报错
- [ ] `skills/propose.md` 在 `openspec new change` 提交前 exit 1 时中断流程
- [ ] `skills/guide-plan.md` plan-done gate 在 active change 任一未通过验证时阻断
- [ ] `skills/guide-ship.md` archive 前置验证避免 `openspec archive` abort
- [ ] 所有现有 skills（propose/guide-plan/guide-ship）通过路径行为不变
- [ ] `pytest tests/unit/` 全套通过（28 既有 + 2 新文件）
- [ ] `bats tests/smoke.bats` 通过
- [ ] CI assertion quality gate 不被破坏

## Risk

- **误报风险**（低）：baseline 段含大量自由文本描述。validator 必须只验证可结构化检查的声明（路径、符号、commit），自由文本通过但记录警告。
- **路径相对性**（低）：baseline 声明相对路径或绝对路径？validator 应基于 change 目录解析，相对路径相对 `<change-root>`。
- **git history 性能**（低）：大仓库 `git log -S` 可能慢。validator 必须有 timeout（默认 10s）并允许 `--no-git-history` 模式跳过。
- **CI 兼容性**（低）：CI 环境可能 git history 受限。validator 必须有 graceful degradation。
- **修改既有 skill 引入回归**（中）：在 propose.md/guide-plan.md/guide-ship.md 插入新调用可能破坏既有流程。tasks.md 必须包含"既有测试通过"验证步骤。

## Supersession / Dependencies

- **不 supersede** 任何现有 change
- **依赖** `gate-mechanism`（已存在的 gate 框架提供 `Check` API）
- **解锁**：未来可创建 `harden-openspec-validate-cli` change，将这些验证器逻辑推到 openspec CLI 上游