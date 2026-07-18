# Design: skills-reorg-phase4-thin

## Decision 1: 现实目标 ≤450 行

提案原先声称 "≤300 行"，但当前前 7 个文件平均 ~601 行，4B 提取仅能移除 ~320 行，剩余 ~281 行差距。且 propose(686) 的 46% 和 deps(636) 的 59% 是纯 markdown 流程说明，无法提取。

修正后的现实目标：≤450 行（降低 ~25%），deps(636) 和 propose(686) 因 markdown 比重高可放宽至 ≤500。

## Decision 2: 提取优先级

1. `> 20 行` 且 `> 80% 代码` 的内联块 → 必提取
2. 重复 ≥3 次且 ≥5 行的模式 → 提取为共享 helper（如 case handler）
3. 纯 markdown 指令/表格/Mermaid 图 → 保留在 SKILL.md 中

## Decision 3: 共享 case handler 提取

6-8 个 SKILL.md 文件重复 `q|quit|exit|r|refresh|?|help|*` 交互菜单，提取为 `skills/guide-ship/scripts/_case_handler.sh` 的 `handle_common_cases()` 函数（因 guide-ship 是使用频率最高的文件），其他文件 source 此函数。

## Decision 4: state.sh 不是 STUB

AGENTS.md 的 "STUB (无 production 调用方)" 标签错误。`state.sh` 有 6 个活跃函数：
- `safe_python_json`, `safe_python_yaml` — 安全解析
- `read_suggestions`, `write_suggestions` — proposal suggestions 读写
- `count_pending_suggestions` — 待处理建议计数

消费者：propose、roadmap、status、plan_queue_overview。Phase 4 修正 AGENTS.md 标签为 `共享工具`。

## Decision 5: 不创建 references/ 目录

OpenCode skill 系统以 `SKILL.md` 为主文档，`references/` 无消费机制。LLM agent 阅读 SKILL.md 作为主要指令来源，不会自动加载 references/。删除原提案的 4B references/ 计划。

## Decision 6: $REPO_ROOT 统一化

Phase 3 后 guide-ship/SKILL.md 中 3 处 `$REPO_ROOT` 统一为 `$(dirname "${BASH_SOURCE[0]:-$0}")` 模式（与同一文件中其他 13 处 source 行一致）。

## 回滚方案

per-file `git checkout`。