# add-full-regression-gate

**优先级**: P0 | **来源**: UsrLinuxEmu 回归复盘 2026-07-27 — ctest 全量回归门缺失
**阶段**: v2.1 | **分类**: quality
**类型**: fix

## 架构依据
- **ADR-0003 三阶段架构** (已采纳): plan → ship 衔接前的全量回归门是 ship 阶段必须满足的质量门
- **ADR-0007 门控机制** (已采纳): `guide-ship` Phase 2.5 当前是可跳过扫描，应升级为 MANDATORY gate（与 `gate.py::register_gate_check()` 接口对齐）
- **ADR-0024 deps-driven execution mode** (已采纳): execute 流程上下文 — Step 5 全量回归是 deps 决策落地后的最终一致性验证
- **复盘事件 `e01632f`**: `compat/io.cpp` + `compat/dma-mapping.cpp` 编入 `libkernel.so`，但这两个文件引用 GPU 插件符号（`g_dma_pool`、`sim_bar_ioremap`），导致 71/117 个链接 `libkernel.so` 的测试崩溃。提交 message 仅验证 3 个新测试（30/30 bar_ioremap, dma_coherent, vram_store）→ 全量测试未跑
- **现状缺陷**: `execute` skill 验证标准是"ctest 相关测试通过"，缺少完成后的全量回归门；`guide-ship` Phase 2.5 回归检测是可选（默认跳过），不是 gate；pre-commit hook 仅跑 docs-audit，不跑测试

## 范围
- **挂载点**（3 个，分属不同层）:
  - **plan-ship 衔接层**: `execute/SKILL.md` 新增 **Step 5: Full Regression Gate** — 强制运行全量 `ctest --test-dir build --output-on-failure`，失败时 STOP 并修复后才能继续
  - **ship 阶段层**: `guide-ship/SKILL.md` Phase 2.5 改为 **MANDATORY gate** — 全量 ctest 零失败才可进入 Phase 3 archive；失败时提供 3 选项：返回 execute 修复 / 创建 debt change 跟踪 / 显式 `SKIP_REGRESSION=1` 强制跳过
  - **仓库层（预防）**: `scripts/hooks/pre-commit` 新增 build 文件变更触发规则 — `src/CMakeLists.txt`、`src/kernel/*.cpp` 被 stage 时自动运行 `scripts/regression-test.sh quick`，失败阻塞提交
- **In Scope**:
  - `execute/SKILL.md` Step 4 区分"单 WU 验证阶段"（`ctest -R <regex>` cover 当前 WU）和"全量验证阶段"（Step 5），防止措辞模糊导致仅验证新测试
  - `guide-ship/scripts/ship_review.sh` 现有 regression check 模块升级为 MANDATORY gate（hook into `gate.py::register_gate_check("ship_done", gate_check_full_regression)`，warning 级硬拦截）
  - `scripts/regression-test.sh` 添加 `quick` 子命令（已有完整回归 + 新增 quick 子集）
  - pre-commit hook 串联：docs-audit → openspec-gate → regression-quick（按 cheap→expensive 顺序，与 add-openspec-gate 提案联动）
  - `USAGE.md` 增加 "Full Regression Gate" 节，含安装、配置、跳过方法
- **Out Scope**:
  - 不修改 rdd-workflow 核心引擎的状态/事件模块（`_lib/state.py` / `_lib/event_log.py`）
  - 不修改 `regression-test.sh` 完整回归逻辑本身（仅新增 quick 子命令）
  - 不修改 `rdd-workflow-writing-plans` skill
  - 不实现 CI/Push 层 gate（属于另一个改进议题）
  - 不与 `add-openspec-gate` 提案的 pre-commit 段重叠 — 它管"代码路径 ↔ change 联动"，本提案管"build → ctest"

## 关键场景
- **GIVEN** 开发者修改 `src/CMakeLists.txt` 新增源文件到 `libkernel.so`，**WHEN** 触发 pre-commit hook，**THEN** 串联执行 docs-audit → openspec-gate（~50ms）→ regression-quick（~30s），任一失败阻塞 commit
- **GIVEN** `guide-ship` 准备 archive change A，**WHEN** Phase 2.5 全量回归发现 ctest 失败，**THEN** 提供 3 选项：返回 execute 修复 / 创建 debt change 跟踪 / 显式 `SKIP_REGRESSION=1` 强制跳过
- **GIVEN** `execute` Step 5 全量回归发现新引入的 compat 文件与 GPU 插件符号未解析（复现 `e01632f`），**WHEN** Step 4 单 WU 验证已通过，**THEN** Step 5 应在 worktree 完成前捕获并 STOP 防止问题代码提交
- **GIVEN** 紧急 hotfix 需要绕过回归门，**WHEN** 用户显式设置 `SKIP_REGRESSION=1`，**THEN** 强制跳过但要求在输出中记录"⚠️  已跳过回归门"警告，便于后续审计
- **GIVEN** pre-commit quick 回归耗时过长影响开发节奏，**WHEN** 用户设置 `SKIP_QUICK_REGRESSION=1`，**THEN** 跳过 quick 子集但完整回归门（execute Step 5 / guide-ship Phase 2.5）仍必须

## 技术约束
- **MUST** Step 5 全量回归是 MANDATORY（不可跳过），失败时明确 STOP，不允许 silently pass
- **MUST** Phase 2.5 regression gate 失败时需显式 `SKIP_REGRESSION=1` 才能强制跳过（防误操作）
- **MUST** pre-commit quick 回归与完整回归使用同一份 `regression-test.sh`（不重复实现）
- **MUST** ship_done gate 失败 warning 级不阻断 ship_done（与 ADR-0007 gate 哲学一致：warning 级 + 可跳过）
- **MUST** 不修改 rdd-workflow 核心引擎的状态/事件模块（已在 Out Scope 强调）
- **SHOULD** pre-commit quick 回归执行时间 ≤ 30s，超时则降级为软警告
- **SHOULD** `SKIP_REGRESSION=1` / `SKIP_QUICK_REGRESSION=1` 触发时在 git reflog 或 handoff 记录一笔审计日志
- **SHOULD** 与 `add-openspec-gate` 提案共用同一份 pre-commit hook 文件（避免各自 cp 一份导致漂移）

## 验收标准
- `execute/SKILL.md` 包含 Step 5: Full Regression Gate，描述清楚全量 ctest 要求
- `execute/SKILL.md` Step 4 明确区分"单 WU 验证"和"全量验证"
- `guide-ship/SKILL.md` Phase 2.5 不再是可跳过的扫描，而是必过 gate
- `guide-ship/scripts/ship_review.sh` 注册 `gate_check_full_regression` 到 `ship_done` gate
- `scripts/regression-test.sh quick` 子命令可用
- pre-commit hook 在 build 文件变更时触发 quick 回归（与 add-openspec-gate 串联）
- `USAGE.md` 增加 "Full Regression Gate" 节
- 所有现有测试通过
- 能在上一次回归场景中复现拦截效果：修改 `src/CMakeLists.txt` 引入未解析符号 → pre-commit 或 execute 全量回归门应捕获