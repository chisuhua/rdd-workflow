# add-progressive-linting

**优先级**: P2 | **来源**: Oracle 代码审查 2026-07-19 #3
**阶段**: default | **分类**: general
**类型**: feature

## 架构依据
- Oracle 建议：48 处 Any 用法，7,382 LOC Python 无类型检查。重构时类型回归无保护。Round A/B/C 提取 ~1,500 行 bash 后，下一步若提取 Python，缺类型检查会放大回归风险。

## 范围
- **In Scope**:
  - CI 加入 `ruff check skills/_lib/`（快，1 分钟接 CI）
  - CI 加入 `mypy --strict skills/_lib/core/`（仅 6 个内核文件）
  - requirements.txt 加入 ruff + mypy
  - 修复 ruff 发现的明显问题（未用 import、显然 bug）
- **Out Scope**:
  - 不对 loop/ 子目录强制类型（动态性高，性价比低）
  - 不修复所有 48 处 Any
  - 不引入 bandit/semgrep

## 关键场景
（无）

## 技术约束
- MUST 渐进式：新增的 lint 步骤不得因为既有问题而阻塞 CI
- MUST 使用 `--ignore` 或 per-file 配置来处理遗留问题
- SHOULD 优先修复 ruff 捕获的未用 import 等安全级问题

## 验收标准
- CI 包含 ruff 检查步骤
- CI 包含 mypy core/ 检查步骤
- ruff 零错误（通过忽略或修复）
- mypy strict 模式在 core/ 下零错误
- 所有现有测试通过
