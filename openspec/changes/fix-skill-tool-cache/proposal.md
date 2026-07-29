## Why

`skill()` 工具加载 `guide-arch` 和 `guide-plan` 时，每次显示旧版本（无 Phase 5.5）。文件已通过 `git commit` 提交，但 skill 工具从 base directory 读取的内容不同步，导致每次需手动绕过交互菜单。

## What Changes

- 调查 skill 工具的文件加载路径（base directory）与实际工作目录的关系
- 若从 `~/.agents/skills/` 加载，增加文件修改时间检测或同步机制
- 在 guide/scan-state.sh 中增加检测：若 skill 版本号与文件系统不一致则提示

## Capabilities

### New Capabilities
- `skill-version-check`: 检测 skill 加载内容是否过期

### Modified Capabilities
- `guide-scan`: 在 scan-state.sh 中增加版本一致性检测

## Impact

- 修改文件：skills/guide/scripts/scan-state.sh
- 影响流程：guide 推荐器入口
- 检测方式：文件 mtime 对比或 git log 对比
