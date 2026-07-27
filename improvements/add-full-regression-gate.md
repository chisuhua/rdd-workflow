# add-full-regression-gate

**优先级**: P0 | **来源**: UsrLinuxEmu 回归复盘 2026-07-27
**阶段**: v2.1 | **分类**: planning
**类型**: fix

## 架构依据
- `e01632f` 提交将 `compat/io.cpp` + `compat/dma-mapping.cpp` 编入 `libkernel.so`，但这两个文件引用 GPU 插件中的符号（`g_dma_pool`、`sim_bar_ioremap`），导致 71/117 个链接 `libkernel.so` 的测试崩溃
- 提交 message 显示仅验证了 3 个新测试（30/30 bar_ioremap, dma_coherent, vram_store）→ 全量测试未跑
- `execute` skill 的验证标准是 "ctest 相关测试通过"，缺少完成后的全量回归门
- `guide-ship` Phase 2.5 的回归检测是可选的（默认跳过），不是 gate
- pre-commit hook 仅跑 docs-audit，不跑测试

## 范围
- **In Scope**:
  - `execute/SKILL.md`：在所有 Work Unit 执行完毕后，新增 **Step 5: Full Regression Gate** — 强制运行全量 `ctest --test-dir build --output-on-failure`，失败时 STOP 并修复后才能继续
  - `execute/SKILL.md` Step 4：区分"单 WU 验证阶段"（`ctest -R <regex>` cover 当前 WU）和"全量验证阶段"（Step 5），防止措辞模糊导致仅验证新测试
  - `guide-ship/SKILL.md` Phase 2.5：测试回归检测改为 **MANDATORY gate** — 全量 ctest 零失败才可进入 Phase 3 archive；失败时提供 3 选项：返回 execute 修复 / 创建 debt change 跟踪 / 显式 `SKIP_REGRESSION=1` 强制跳过
  - `scripts/hooks/pre-commit`：新增 build 文件变更触发规则 — `src/CMakeLists.txt`、`src/kernel/*.cpp` 被 stage 时自动运行 `scripts/regression-test.sh quick`，失败阻塞提交
- **Out Scope**:
  - 不修改 rdd-workflow 核心引擎（Python `_lib/`）
  - 不修改 `regression-test.sh` 自身逻辑
  - 不修改 `rdd-workflow-writing-plans` skill

## 关键场景
1. **共享库修改引入回归**：修改 `libkernel.so` 的编译列表（`src/CMakeLists.txt`），新增源文件引用插件端符号 → 全量 ctest 应检测到所有链接 `libkernel.so` 的测试崩溃
2. **仅跑新测试的盲区**：开发者在 worktree 中完成 implementation，TDD 5-step 仅验证当前 group 测试 → Step 5 全量回归门应在此刻捕获
3. **pre-commit 快速拦截**：在 `git commit` 之前，build 文件变更触发 quick 回归 → 提交前就发现，不推到 CI 才报

## 技术约束
- Step 5 全量回归必须是 MANDATORY（不可跳过），失败时明确 STOP
- Phase 2.5 regression gate 失败时需要显式 `SKIP_REGRESSION=1` 才能强制跳过（防误操作）
- pre-commit 中的 quick 回归可能耗时 ~30s，用户可通过 `SKIP_QUICK_REGRESSION=1` 跳过
- 不引入新的外部依赖

## 验收标准
- `execute/SKILL.md` 包含 Step 5: Full Regression Gate，描述清楚全量 ctest 要求
- `execute/SKILL.md` Step 4 明确区分"单 WU 验证"和"全量验证"
- `guide-ship/SKILL.md` Phase 2.5 不再是可跳过的扫描，而是必过 gate
- pre-commit hook 在 build 文件变更时触发 quick 回归
- 所有现有测试通过
- 能在上一次回归场景中复现拦截效果：修改 `src/CMakeLists.txt` 引入未解析符号 → pre-commit 或 execute 全量回归门应捕获
