# add-e2e-test-skip-on-missing-hub-auth

## Why

**症状 (2026-08-31 ship 阶段, 2 个 P1 change 触发)**:

- 回归门跑 `bats tests/ --recursive` 包含 `test_cross_repo_e2e_real.bats`
- 该测试 setup_file 需：gh 认证 + 网络 + 真实 `chisuhua/rdd-hub` 仓库
- 某轮回归门（第4 轮）中 setup_file 偶发失败，报告脚本报 `新增失败: 1`（description = `setup_file failed`）
- 手动验证 setup_file 的各步骤（gh repo view / label create / git clone spoke）都能成功（网络 OK）
- 判断为 flaky（网络抖动 / 时序），非代码 regression
- 修复：把 `setup_file failed` 加 KNOWN_FAILURES.txt，第5 轮回归门 `✅ 0 新增失败`

**根因分析**:

`tests/integration/test_cross_repo_e2e_real.bats` 是真实 GitHub E2E 测试（`bats tests/integration/test_cross_repo_e2e_real.bats` 单独跑 OK）。但它没有任何「环境依赖检查」：

1. 无 `gh auth status` 前置检查
2. 无 Hub 仓库可达性检查（首次自动创建，但创建失败直接 return 1）
3. 无网络检查
4. setup_file 中 git clone 3 个 spoke（spoke-a/b/c）无超时/重试/降级
5. CI 环境若无 Hub 访问（私有网络 / gh 未认证）时，测试必然 fail 而非 skip

**Skip-not-fail 的既有先例**：

`tests/integration/test_global_install_external_project.bats` 已有 Skip-not-fail 策略（`~/.agents/skills/_lib/skill_root.sh` 不存在时自动 skip），是仓库内已接受的模式。`test_cross_repo_e2e_real.bats` 应采用同样策略。

**影响范围**:

- 所有真实 E2E 测试（`test_cross_repo_e2e_real.bats` + `test_cross_repo_impact_detection.bats` 也依赖 gh + Hub）在无 Hub 环境（CI / 无认证 / 私有网络）下必然失败
- 失败触发回归门"新增失败"，阻塞 archive
- 当前通过 KNOWN_FAILURES 标记为已知，但每次失败都需人工判断「是否是 regression」——磨耗信任

## What Changes

**In Scope**:

- setup_file 开头加环境检查：
- Hub 可达性检查（`gh repo view`）失败 → skip（而非 return 1）
- git clone spoke 失败 → 尝试重试 1 次，仍失败 → skip 该测试文件（或该 test 单独 skip）
- skip 时 stdout 输出原因（可追溯）
- 该测试依赖 gh + Hub 仓库（E2E_HUB_REPO=chisuhua/rdd-hub）
- 加同样的 `gh auth` / `gh repo view` 前置检查 + skip
- 本提案 ship 后，`setup_file failed` 不再作为已知失败（真实失败会由 skip 机制避免）
- 删除 `tests/KNOWN_FAILURES.txt` 中的 `setup_file failed # pre-existing WIP: ...` 条目（commit b5fa42c 加的）
- `docs/change-quality-guide.md` 加"真实 E2E 测试 Skip-not-fail"段
- `tests/integration/README.md`（如有）说明 E2E 测试前置条件
- **不修改** `test_cross_repo_e2e_real.bats` 的核心测试逻辑（RFC 上行 / contract-check / watch-hub 流程）
- **不实现** mock Hub（真实 E2E 保留，CI 需要时用 `E2E_HUB_REPO` 指向测试仓库）
- **不修改** CI workflow（`.github/workflows/test.yml` 中的 E2E 步骤）
- **不修改** gh / git 行为

### 关键场景

### 场景 1: 无 gh CLI 的环境

- **GIVEN** 环境无 `gh` 命令
- **WHEN** 回归门跑 `test_cross_repo_e2e_real.bats`
- **THEN** setup_file 检测到 gh 缺失 → `skip "gh CLI not available; skipping E2E"`
- **AND** 报告不把该测试算失败

### 场景 2: gh 已装但未认证

- **GIVEN** gh 已安装，`gh auth status` 失败
- **WHEN** 回归门跑 E2E
- **THEN** setup_file skip（提示需 chisuhua 认证）
- **AND** 报告不失败

### 场景 3: Hub 仓库不可达（网络 / 仓库删除）

- **GIVEN** `gh repo view chisuhua/rdd-hub` 失败
- **WHEN** E2E setup_file 检查
- **THEN** skip（而非 return 1 导致 setup_file failed）
- **AND** stdout 输出 `Hub chisuhua/rdd-hub unreachable; skipping E2E`

### 场景 4: 有 gh + 认证 + Hub（正常 CI）

- **GIVEN** 完整 E2E 环境
- **WHEN** 回归门跑
- **THEN** setup_file 通过，13 个 E2E test 正常执行（不 skip）
- **AND** 回归门正常跑

### 场景 5: 网络抖动（git clone spoke 失败一次）

- **GIVEN** setup_file clone spoke-a 失败（网络抖动）
- **WHEN** 重试 1 次
- **THEN** 重试成功 → 继续；重试仍失败 → skip（留 audit 线索）
- **AND** 不误报 setup_file failed

**Out of Scope**:

- (no items specified)

## Capabilities

- **MUST NOT**: 改 gh CLI 行为（`gh auth` / `gh repo view` 是读取操作，无副作用）
- **MUST NOT**: 改 `test_cross_repo_e2e_real.bats` 的 13 个核心 test（仅 setup_file 加检查）
- **MUST NOT**: 在无 Hub 的 CI 上强制跑 E2E（skip 是目标）
- **MUST**: 与既有 Skip-not-fail 策略（`test_global_install_external_project.bats`）风格一致
- **MUST**: skip 时输出明确原因（audit trail）
- **SHOULD**: 重试逻辑简单（bash for 循环 1 次即可，不引入新依赖）

## Impact

- (no items specified)

## Acceptance

### 单元与集成测试

- [ ] `test_cross_repo_e2e_real.bats` setup_file 加 3 个前置检查（gh 存在 / gh auth / Hub 可达）
- [ ] `test_cross_repo_impact_detection.bats` 加同样前置检查
- [ ] 模拟无 gh 环境跑 `test_cross_repo_e2e_real.bats` → skip（非 fail）
- [ ] 模拟无认证跑 → skip
- [ ] 模拟 Hub 不可达跑 → skip
- [ ] 正常环境跑 → 13 test PASS（非 skip）

### 端到端验证

- [ ] `bats tests/integration/test_cross_repo_e2e_real.bats` 在无 Hub 环境输出 `ok`（skip）而非 `not ok`
- [ ] `./test.sh --full --regression` 在无 Hub 环境跑出 0 新增失败（不再依赖 KNOWN_FAILURES 标记 setup_file failed）
- [ ] KNOWN_FAILURES.txt 移除 `setup_file failed` 条目后回归门仍 pass

### 文档化

- [ ] `docs/change-quality-guide.md` 加"真实 E2E 测试 Skip-not-fail"段
- [ ] `tests/integration/README.md`（如有）补 E2E 前置条件说明
- [ ] `tests/KNOWN_FAILURES.txt` 头注释注明 `setup_file failed` 已由 skip 机制取代

### 兼容性验证

- [ ] 有 Hub 的 CI 环境 E2E 测试全部 PASS（不 skip）
- [ ] 与 `fix-report-regression-sed-double-hash-strip` (P0-2) 无交互
- [ ] 与 `add-known-failures-baseline` 提案无冲突

### 副作用监测

- [ ] ship 后 30 天观察期：E2E setup_file failed 不再出现（无 Hub 时 skip，有 Hub 时 pass）
- [ ] KNOWN_FAILURES.txt 规模不因本提案扩大（反而移除 1 条）

