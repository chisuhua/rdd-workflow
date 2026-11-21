# session-lesson-mining

从**真实会话历史**挖教训，并把它们固化成 `rdd-workflow-e2e` 的机械判据。

流程与硬约束见 `SKILL.md`；这里只记**实现与验证事实**。

## 组成

| 文件 | 作用 |
|---|---|
| `scripts/session_export.py` | opencode 会话库（sqlite）→ 归一化 JSONL。支持 V2（`session_v2`/`session_message`）与 V1（`session`/`message`/`part`）两套 schema；`--list` / `--session` / `--last` / `--since` / `--max-text` |
| `scripts/mine_lessons.py` | JSONL → 候选教训清单（7 个检测器，按「同类证据」聚合，`--top` / `--min-count` / `--detector` / `--format md\|json`） |
| `scripts/selftest.sh` | 判别力自测：7 个检测器各须被夹具触发；干净会话不误报；导出器保留 user 正文 / exit 码 / 中段内容 |

## 数据来源（实测）

- 本机会话库：`~/.local/share/opencode/opencode.db`（可用 `OPENCODE_DB` 覆盖）。
- **V2** 表：`session_v2` + `session_message`（当前在用）。
  - `session_message.type` = `user` / `assistant`；assistant 的正文在 `data.content[]`（`text` / `reasoning` / `tool`），**user 的正文在 `data.text`**（没有 content 数组）。
  - 工具结果：`data.content[].state` = `{status, input, content[], metadata{exit,…}}`。
- **V1** 表：`message` / `part`（更早的会话），工具状态在 `state.output` / `state.metadata.exit`。

## 验证记录（2026-11-19）

在**产生过错的那次会话**上实跑（`~/.config/opencode`，2026-11-19）：

| 步骤 | 结果 |
|---|---|
| 导出（`--max-text 0`） | **6024 行**（含 136 条 user 消息），JSONL 4.3 MB |
| 挖掘（`--top 15`） | **1718 条候选 → 78 类** |
| 抽检命中 | `printf: 'H': invalid format character`（判据夹具自身的格式串 bug）、`Permission denied: shell`（权限面）、`FileNotFoundError`（路径假设）、「**又踩了同一个坑**：bun 非 TTY 时把失败行写到 stderr」「我漏了一个 requirement」 |

**验证过程中发现并修掉的两个导出器 bug**（都不是"设计问题"，是实跑才暴露的）：

1. **user 正文全丢**：初版只遍历 `data.content[]`，而 V2 的 user 行把正文放在 `data.text` ⇒ 纠正类检测器恒为 0。修后 136 条 user 消息全部导出。
2. **`--max-text 0` 反而截断**：`len(s) <= 0` 为假 ⇒ 走进截断分支，产出「截断 -359 字」并丢掉开头。修后 `n <= 0` 明确表示"不截断"（挖掘默认用它，因为失败行常出现在长输出中段）。

自测：`bash scripts/selftest.sh` ⇒ 7 检测器全触发 + 干净会话零误报 + 导出器三条断言通过。

## 已知限制

- 检测器是**文本启发式**：换一种说法就漏（如把"我漏了"写成"这里少了一处"），引用错误原文又会多报。多报由 P3 人工收敛。
- 只看**产物/现象**，不判"agent 是否真的会这样想"；行为层要真实模型 + 额度。
- `--max-text` 默认 2000 时保留"头 + 尾"；挖掘请用 `0`。
- 导出的 JSONL 含绝对路径与完整命令：只写 `/tmp/opencode/`，**不要入库**。
