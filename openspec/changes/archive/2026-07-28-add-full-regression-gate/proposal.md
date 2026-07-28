# add-full-regression-gate

**优先级**: P0
**阶段**: v2.1
**分类**: quality

## Why

复盘事件 `e01632f` 显示：ci/io.cpp + compat/dma-mapping.cpp 编入 libkernel.so 后引用 GPU 插件符号，导致 71/117 个测试崩溃。提交仅验证了 3 个新测试——全量回归缺失。

当前问题：
- execute 的验证标准仅为"ctest 相关测试通过"，缺少完成后的全量回归门
- guide-ship Phase 2.5 回归检测是可选（默认跳过），不是强制 gate
- pre-commit hook 仅跑 docs-audit，不跑测试

## What Changes

在 3 层增加全量回归门：
1. **execute** Step 5: 强制 `ctest --test-dir build --output-on-failure`
2. **guide-ship** Phase 2.5: 升级为 MANDATORY gate，提供 3 选项（修复/跟踪/跳过）
3. **pre-commit**: 新增 build 文件变更触发规则

## Architecture

- 3 层挂载点：execute Step 5 最底层（阻止问题代码提交）、guide-ship Phase 2.5 中间层（归档前最终验证）、pre-commit 最外层（预防）
- `SKIP_REGRESSION=1` 用于紧急绕过
- `scripts/regression-test.sh quick` 用于 pre-commit 快速子集
