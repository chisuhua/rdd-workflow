# fix-bootstrap-fallback-paths

**优先级**: P1 | **来源**: 隔离 playground 全流程验证 — 第三方项目 global install fallback
**阶段**: v2.1 | **分类**: integration
**类型**: fix

## 架构依据

全局安装的共享库位于 `~/.agents/skills/_lib/`。当前多个运行时脚本和 `SKILL.md` 示例仍 fallback 到不存在的 `~/.agents/_lib/skill_root.sh`，导致外部项目在 arch、design、plan、ship 等阶段触发错误路径；在 Bats ERR trap 环境下会直接阻断 helper。

## 范围

- **In Scope**:
  - 将所有运行时脚本中的 `$HOME/.agents/_lib/skill_root.sh` 修正为 `$HOME/.agents/skills/_lib/skill_root.sh`。
  - 同步修正扫描发现的 `SKILL.md` 文档示例。
  - 保留本地项目路径优先、全局路径 fallback 的现有顺序和其余行为。
  - 增加外部项目回归测试，覆盖全局安装且无本地 `_lib` 的场景。
- **Out of Scope**:
  - 不改变 `resolve_rdd_lib_dir` 的优先级。
  - 不改变全局安装目录布局。
  - 不重构无关 shell helper。

## 关键场景

### 场景 1：第三方项目进入阶段 helper

- GIVEN 项目没有 `.opencode/_lib/skill_root.sh`
- AND 全局安装提供 `~/.agents/skills/_lib/skill_root.sh`
- WHEN arch/design/plan/ship 相关 helper 执行 fallback
- THEN helper 从正确的全局路径加载共享 resolver
- AND 不输出错误路径或因 ERR trap 失败

### 场景 2：文档 bootstrap 示例

- GIVEN 用户复制任一 `SKILL.md` 中的 bootstrap 示例
- WHEN 项目没有本地 skill root
- THEN 示例尝试正确的 `~/.agents/skills/_lib/skill_root.sh`

## 技术约束

- 只替换错误路径字面量，不改变调用顺序、函数签名和状态协议。
- 回归测试必须运行于 `$BATS_TMPDIR` 外部项目，不能写入源仓库 `.rddf/state/`。

## 验收标准

- `skills/` 运行时脚本和文档中不再出现 `$HOME/.agents/_lib/skill_root.sh`。
- 外部项目全局安装回归测试通过。
- 现有测试通过，且不引入新的 Bats/Python 失败。
