---
SCOPE: shared
STATUS: PROPOSED
---

## Context

`rdd-workflow` 通过 3 个入口 skill 管理 OpenSpec change lifecycle：

| Skill | 入口 | 现有验证 |
|---|---|---|
| `propose` | 创建新 change | `openspec new change` + 写 artifacts，**不验证 baseline 真实性** |
| `guide-plan` | plan-done gate | 检查 artifacts 完整 + 已 commit，**不验证 baseline 真实性、不验证 delta target 存在** |
| `guide-ship` | archive 前置 | 直接调 `openspec archive`，**不预检 delta target**，等 openspec CLI 报 abort |

现有 `skills/_lib/gate.py` 提供 `Check` 抽象（name + condition lambda + message + severity），但**没有针对 spec 内容的预检 check**——所有 check 都是关于"流程状态"而非"内容真实性"。

`g-gpu-client-default-stub-init` v1 (2026-07-11) 和 `g-gpu-client-meyers-singleton-fallback` v2 (2026-07-11) 两个 incident 都暴露：
1. **Baseline 虚构**无人察觉（v1 spec 的 `CudaStub g_cuda_stub; exists` 声明）
2. **MODIFIED target 不存在**到 archive 才被发现（v2 spec 的 `shim-default-init-fallback` capability）

这两次都浪费 10+ 分钟人工调研 + 6+ 步额外修复。

## Goals / Non-Goals

**Goals:**
- 在 commit/archive 前**自动验证** baseline 段声明的真实性（文件存在、符号存在、git history 存在）
- 在 archive 前**自动验证** delta 段的 MODIFIED/RENAMED target 存在
- validator 是 CLI 工具，可独立调用（`python3 validate_baseline.py <change-name>`）
- validator 输出明确的错误信息和退出码（0=pass, 1=hard fail, 2=soft warn）
- validator 在 CI 中可调用，集成到现有 CI workflow
- 既有 skill 流程通过路径行为不变（仅在失败时阻断）

**Non-Goals:**
- 修改 openspec CLI 本身（外部 npm 包，out of scope）
- 自动修复无效声明（detection-only，人类修正）
- 验证 proposal.md / design.md 的自由文本（仅验证可结构化字段）
- 旧 archived changes 的回溯验证（仅新 change 触发）
- 非 spec 文件的验证（如 CHANGELOG、ADR 内容）

## Decisions

### Decision 1: 独立 CLI 工具 + 在 skills 中调用（chosen）

每个 validator 是独立的 Python 脚本，可独立运行：

```bash
# 独立使用
python3 skills/_lib/validate_baseline.py g-gpu-client-default-stub-init
# exit 0 = pass, exit 1 = hard fail, exit 2 = soft warn

# 在 skill 中调用
if ! python3 skills/_lib/validate_baseline.py "$CHANGE_NAME" 2>/dev/null; then
    echo "❌ Baseline validation failed. See error above."
    exit 1
fi
```

**Rationale**: 独立工具便于：
- CI 直接调用（无需额外依赖）
- 人类手动验证（`bash$ python3 validate_baseline.py <change>` 即可）
- 单元测试隔离（每个工具独立测试）
- 未来如需推到 openspec CLI 上游，独立工具易移植

### Decision 2: Baseline claim 解析采用结构化前缀

`.openspec.yaml` 的 `baseline:` 段是 YAML 嵌套结构（key: value），但 value 是自由文本。我们定义约定：

- `value` 以结构化前缀开头 → 触发对应验证
  - `file-exists:<path>` → 路径必须存在
  - `symbol-exists:<file>:<regex>` → 文件 grep 必须匹配
  - `git-history:<symbol>` → `git log -S` 必须 ≥1 个非 spec commit
- `value` 无前缀 → 视为描述性文本，通过（但记录为 unverifiable）

**Rationale**: 渐进式增强。现有 baseline 段的自由文本不会被破坏，只有显式声明前缀的才被严格验证。

**示例**：
```yaml
baseline:
  # 结构化（被验证）
  g_cuda_stub static instance: "file-exists:src/test_fixture/cuda_stub.cpp"
  g_cuda_stub symbol: "git-history:CudaStub g_cuda_stub"
  cuStreamSynchronize error: "symbol-exists:src/umd/libcuda_shim/cu_stream.cpp:NOT_INITIALIZED"
  
  # 描述性（通过，不验证）
  shim null guard: "cuStreamSynchronize returns NOT_INITIALIZED when g_gpu_client == nullptr"
  test setup pattern: "TU-local static MockGpuDriver g_mock; + explicit g_gpu_client = &g_mock;"
```

### Decision 3: Delta target 验证扫描 `## MODIFIED` 和 `## RENAMED` 段

`spec.md` 的格式约定（参考 `openspec/specs/gate-mechanism/spec.md`）：

```markdown
## ADDED Requirements
### Requirement: <title>  ← 新能力
[body]

## MODIFIED Requirements
### Requirement: <title>
[body describing change to EXISTING capability]

## RENAMED Requirements
### Requirement: <old-name> → <new-name>
[body]

## REMOVED Requirements
(none)
```

validator 解析 spec.md：
1. 找到 `## MODIFIED Requirements` 段
2. 从每个 `### Requirement:` 的 body 推断 target capability（默认是 change 自己的 capability name，但 MODIFIED 可能 target 其他 capability）
3. 检查 `openspec/specs/<target>/spec.md` 存在
4. 同理处理 `## RENAMED Requirements` 段

**简化方案（v1）**：仅校验 MODIFIED 段要求每个 Requirement 在 body 第一行包含 "target:" 或 "modifies: <capability>" 指令。若无，validator 默认假设 MODIFIED 改的是 change 自己的 capability（合理 default 因为大多数 change 改自己）。

**Rationale**: v1 简化方案覆盖 90% case。复杂的跨-capability MODIFIED 是 edge case，后续 iteration 处理。

### Decision 4: 错误信息格式统一

validator 失败时输出：

```
❌ [VALIDATOR] <change-name>: <category>
   Claim: <original-claim-text>
   Expected: <what-should-be-true>
   Actual: <what-is-true>
   Fix: <how-to-fix>
   
   See: docs/spec-validation-gates.md (if exists)
```

**Rationale**: 错误信息必须包含 actionable fix hint，否则用户面对"baseline claim false"会陷入 v1 incident 的困境——Oracle 调研 10 分钟才发现。

### Decision 5: 集成点策略——单点 hook，失败 fast-fail

3 个 skill 入口在关键决策点插入 validator：

| Skill | 插入点 | 失败行为 |
|---|---|---|
| `propose` | `openspec new change` 之后、写 artifacts 之前 | exit 1 阻断（baseline 必须先真实才能写） |
| `guide-plan` Phase 4 plan-done gate | 写入 `.rddf/state/.plan-handoff.json` 之前 | exit 1 阻断（不能交接未验证的 plan） |
| `guide-ship` Phase 3 archive | 调用 `openspec archive` 之前 | exit 1 阻断（避免 archive abort 浪费 6 步修复） |

**Rationale**: 失败 fast-fail 避免 archive abort 的 6 步修复链。validate 阶段捕获 → 1 步修正 → 重新 validate。

## Alternatives Considered

### Alt 1: 推到 openspec CLI 上游

修改 `@fission-ai/openspec` 包添加 validate hooks。

**Rejected**:
- 依赖外部项目 release cycle，无法快速迭代
- rdd-workflow 用户可能用旧版 openspec CLI
- 维护负担重（fork vs upstream PR）

### Alt 2: 在 CI 中独立运行 validators

CI workflow 调用 validators 作为独立 step，不在 skill 流程中。

**Rejected**:
- 反馈循环长（commit → push → CI 才发现 → 修复 → 重新 commit）
- 不阻断本地流程（用户可能 commit + push 后才发现）
- 与现有 gate mechanism 不一致

### Alt 3: 强制 baseline 段必须是结构化

要求所有 baseline claim 必须有前缀，否则报错。

**Rejected**:
- 破坏性变更（现有 baseline 都是自由文本）
- 一次性迁移成本高
- 与 Decision 2 的渐进式增强策略相反

## Risks / Trade-offs

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Validator 误报（结构化前缀 syntax 错误理解） | v1 只支持 3 种明确前缀（`file-exists:`, `symbol-exists:`, `git-history:`），其他视为描述性 |
| 2 | 大仓库 `git log -S` 慢 | 默认 timeout 10s，加 `--no-git-history` 标志跳过 |
| 3 | 路径相对性混淆（baseline 写绝对 vs 相对） | validator 默认相对 `<change-root>` 解析，允许绝对路径 |
| 4 | 修改 propose/guide-plan/guide-ship 引入回归 | tasks.md 包含完整既有测试套件验证步骤（pytest + bats） |
| 5 | validator 输出格式不友好 | Decision 4 统一错误格式，包含 actionable fix hint |
| 6 | SPEC.md MODIFIED target 推断错误 | v1 用保守 default（target = change 自己），edge case 留 TODO |
| 7 | 跨工作树（worktree）路径解析问题 | validator 调用时 cd 到 change root |

## Verification

```bash
# 单元测试
cd /workspace/project/rdd-workflow
pip install -r requirements.txt
python3 -m pytest tests/unit/test_validate_baseline.py -v
python3 -m pytest tests/unit/test_validate_delta_targets.py -v
python3 -m pytest tests/unit/ -q   # 全部 28+2 个测试文件

# 集成测试 (手动)
# 1. 创建一个故意 baseline 失败的 change
mkdir -p /tmp/test-change/openspec/changes/bad-baseline/{specs/cap}
cat > /tmp/test-change/openspec/changes/bad-baseline/.openspec.yaml <<EOF
schema: spec-driven
baseline:
  nonexistent-file: "file-exists:does/not/exist.cpp"
EOF
python3 skills/_lib/validate_baseline.py bad-baseline  # expect exit 1 + error

# 2. 创建一个故意 delta target 失败的 spec.md
cat > /tmp/test-change/openspec/changes/bad-delta/specs/cap/spec.md <<EOF
# cap Specification
## MODIFIED Requirements
### Requirement: x
Body targets nonexistent-cap which is not in main specs.
EOF
python3 skills/_lib/validate_delta_targets.py bad-delta  # expect exit 1 + error

# 3. CI 工作流集成
bats tests/smoke.bats  # 不破坏既有 smoke
```

## Open Questions

- **Q**: 是否在 baseline claim 验证中支持 glob 模式（`file-exists:src/**/*.cpp`）？
  **A**: v1 不支持。仅精确路径。glob 支持是 v2 enhancement。
- **Q**: MODIFIED target 推断是否需要 LLM 解析 body？
  **A**: v1 不需要。Default target = change 自己的 capability。LLM 解析留后续。
- **Q**: validator 是否要 ship 到 PyPI？
  **A**: 不在 v1 scope。rdd-workflow 是 git submodule + skills/_lib/ 模式，不是独立 Python package。
- **Q**: CI 何时调用 validator？
  **A**: PR trigger 时（`on: pull_request`），在现有 pytest + bats 之前或之后都可以，建议并列。