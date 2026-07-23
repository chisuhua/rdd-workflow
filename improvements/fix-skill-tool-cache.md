# fix-skill-tool-cache

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — skill 工具加载过期内容
**阶段**: v2.1 | **分类**: developer-experience
**类型**: feature

## 架构依据

- `skill()` 工具加载 `guide-arch` 和 `guide-plan` 时，每次显示旧版本（无 Phase 5.5）
- 文件已通过 `git commit` 提交，但 skill 工具从 base directory 读取的内容不同步
- 导致每次需手动绕过交互菜单（因为菜单显示的是错误内容）

## 范围

- **In Scope**:
  - 调查 skill 工具的文件加载路径（base directory）与实际工作目录的关系
  - 若从 `~/.agents/skills/` 加载，增加文件修改时间检测或同步机制
  - 在 guide/scan-state.sh 中增加检测：若 skill 版本号与文件系统不一致则提示
- **Out Scope**:
  - 不修改 skill 工具本身（平台层）

## 关键场景

- GIVEN guide-arch SKILL.md 已修改并提交, WHEN 调用 skill("guide-arch"), THEN 加载最新内容
- GIVEN skill 版本滞后, WHEN 检测到不一致, THEN 提示用户刷新

## 技术约束

- MUST 检测方式轻量（文件 mtime 对比或 git log 对比）
- SHOULD 不影响正常加载速度

## 验收标准

- skill 加载内容与文件系统一致
- 或至少有明确的过期检测提示