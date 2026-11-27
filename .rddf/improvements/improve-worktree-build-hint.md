---
优先级: P2
来源: 2026-11-26 CppTLM 立项会话实测（worktree 首次全量构建 19 分钟 + 7 次 sleep 轮询）+ oracle 建议 13（文案指向项目侧，不在 rdd-workflow 造缓存机制）
阶段: phase-3
分类: developer-experience
类型: improvement
状态: 已归档（2026-11-27 · change `2026-11-27-improve-worktree-build-hint` · 5/5 AC pass · 验收报告 `.rddf/reviews/improve-worktree-build-hint-verify.md`）
主题: worktree 内的构建提示 —— 「build 目录缺失」时输出一行可机判的提示，不在 rdd-workflow 造缓存机制
---

**优先级**: P2 | **来源**: 2026-11-26 CppTLM 立项会话实测 | **阶段**: phase-3 | **分类**: developer-experience | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **输出通道与触发步骤未钉** ⇒ bats `run` 的断言面不定 ⇒ 钉 **stderr**（stdout 留给 P2 结构化输出）+ **worktree 建好之后、执行之前**。
- 已改：技术约束补通道与触发步骤；新增 AC4（通道断言）；AC4→AC5 顺延。


**主题**: worktree 内的构建提示 —— 「build 目录缺失」时输出一行可机判的提示

## 架构依据

`phase2_execute.sh` 建 worktree 后，该 worktree **没有** `build/` 目录（CppTLM 实测：worktree 内首次全量构建
**19 分钟**，4 核；会话里出现 **7 次** `sleep` 轮询等待产物）。
⇒ 这是**项目特性**（CMake 项目 + catch2 amalgamated 大 TU），不是 rdd-workflow 的缺陷。

因此本提案**不做缓存机制**（oracle 建议 13：在 rdd-workflow 造缓存 = 过度设计），只做**可机判的一行提示**：
worktree 内无 `build/` 目录时，P2 提示「本 worktree 无构建缓存 ⇒ 首次构建耗时可能较长（建议后台任务 + 等完成通知，勿 sleep 轮询）」，
并在**项目侧**给出加速建议的**引用**（ccache / 复用主仓 build 目录 / 只构建目标 target）——**由项目自己决定**。

## delta 载体（P0 生成输入）

**delta**: added worktree-build-hint
**语义要求**: Worktree creation SHALL announce a missing build directory | When Phase 2 creates a worktree that has no `build/` directory, it SHALL print one fixed-text hint line on stderr telling the agent that the first build may be slow and that it should run the build as a background task instead of polling with sleep. The hint SHALL NOT appear when a `build/` directory exists, the detection SHALL be read-only, and no execution behaviour SHALL change. | A worktree without a build directory gets the hint | Phase 2 created a worktree whose directory has no `build/` | the Phase 2 output is inspected | stderr contains the fixed hint line and stdout does not

## 范围

**In Scope**:

- `phase2_execute.sh`：worktree 内检测 `build/` 缺失 ⇒ 输出一行**固定文本**的提示（含「后台任务」「勿 sleep 轮询」两个关键词）；
- 该提示文案引用**项目侧**加速手段（ccache / 复用 build 目录 / `--target`），**不在本仓实现**任何缓存机制；
- 回归用例：bats 断言 P2 输出含该行（**存在即通过是弱判据** ⇒ 断言必须绑定「仅在 build 目录缺失时出现 / 存在时不出现」两种情形）。

**Out of Scope**:

- 不实现 ccache / sccache / 构建缓存 / 构建目录共享（**项目侧**决策）；
- 不改 P2 的执行模式判定（worktree vs 轻量）；
- 不改构建命令本身；
- 不为「构建慢」加超时或并发控制。

## 关键场景

1. worktree 内无 `build/` ⇒ P2 输出含提示行（含两个关键词）。
2. worktree 内已有 `build/` ⇒ **不**输出该提示行（避免噪音）。
3. 项目仓已用 ccache ⇒ 提示行仍出现（文案只做引用，不做检测分支）。

## 技术约束

- 提示是**一行**、文本固定 ⇒ 可机判（bats 断言字符串）；
- **输出通道 = stderr**（stdout 留给 P2 的结构化输出）；**触发步骤 = worktree 建好之后、执行之前**；
- 检测**只读**（`test -d`）；
- 不因提示而改变任何执行行为（不阻断、不自动构建）。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/integration/test_phase2_build_hint.bats`：worktree 无 `build/` ⇒ 输出含提示行
      ⇒ 修复前红 ⇒ 修复后绿；
- [ ] **AC2（红→绿）** 同文件用例：worktree 已有 `build/` ⇒ **不**含该提示行（防噪音）；
- [ ] **AC3（判别力）** 同文件用例：把提示的检测条件反相（存在时才打印）⇒ AC1 必须红；
- [ ] **AC4（通道）** 同文件用例：提示行出现在 **stderr**（stdout 不含该行）⇒ 防通道漂移；
- [ ] **AC5（门）** `./test.sh --gates` 与 `./test.sh --bats` 全绿。

## Capabilities

- MUST: worktree 无构建缓存时给出**一行**可机判的提示（含「后台任务」「勿 sleep 轮询」）。
- MUST NOT: 在 rdd-workflow 仓实现任何构建缓存机制。
- MUST NOT: 因提示改变执行行为。

## Impact

| 面 | 影响 |
|---|---|
| `skills/rdd-builder/scripts/phase2_execute.sh` | 一行提示（只读检测） |
| `tests/integration/` | 新增 1 个 bats 文件 |
| 项目侧 | 加速手段（ccache / 复用 build）由项目自决 |
