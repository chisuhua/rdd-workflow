# AGENT Tool Usage — 工具选用决策表

> rdd-workflow dogfood 实测 (ses_fb4e3770dffeCYhR7xxAAQdI9l, 492 tool calls, 7 errors/1.4%)。
> 修 3 类可避免摩擦。**本文件是 Agent 工具调用的决策依据 — 每次 edit/write/read 前先看对应决策树。**

## Edit 决策树

- 目标文件已存在 且 需要局部修改 → **edit**（用精确 oldString）
- 目标文件不存在 → **write**
- 上一次 Read/Edit 该文件 > 10 分钟前 → **先 Read 全文再 edit**（防 stale oldString）
- edit 报 "Could not find oldString" → 立即 **Read 全文 → 重试 edit 或降级 write**

## Write 决策树

- 目标文件已存在 → **禁止 write**（改走 edit；整文件重写也用 edit 带完整 oldString）
- 目标文件不存在 → write 可
- write 报 "File already exists" → **改 edit** 或 **Read 后 write**

## Read Offset 决策树

- 读某行号 → **先 Read 文件头确认总行数**，再带 offset
- 行号来自脚本硬编码 → **改用动态 offset**（`python3 -c "print(len(open(p).readlines()))"` 先取行数）
- read 报 "Offset out of range" → **重读文件头**，用实际行数