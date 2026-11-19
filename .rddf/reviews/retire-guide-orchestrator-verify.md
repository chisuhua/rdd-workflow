# retire-guide-orchestrator 验收报告

- **change**: `openspec/changes/retire-guide-orchestrator/`
- **日期**: 2026-11-19
- **验收方式**: 本地验收（`rdd-verifier` skill 分流条件 2 不满足 —— 本 change 在 `.rddf/state/iteration.json` 中为 `in_worktree`，P3 archive gate 未触发）
- **已用轮次**: 1
- **依据 ADR**: ADR-0063（退役 Guide-as-Orchestrator，取代 ADR-0055 / ADR-0056，已采纳）

## 判据来源

`openspec/changes/retire-guide-orchestrator/proposal.md` 的 `## Acceptance` 段（AC-1 ~ AC-12）。

## 逐条判定

| AC | 判定 | 取证命令与结果 |
|---|---|---|
| AC-1 | **pass** | `test ! -d skills/guide` ⇒ 不存在；`docs/legacy/skills/guide/SKILL.md` ⇒ 存在；`grep -q '考古保留' docs/legacy/README.md` ⇒ 命中 |
| AC-2 | **pass** | `package.json::skills[]` ⇒ 28 项，`'guide' in skills[]` 为 False；`pyrightconfig.json` 无 `skills/guide` 匹配 |
| AC-3 | **pass** | `.rddf/state/.cross-repo-evidence.json` ⇒ `status="verified"`，3 个 item 全部 `observed=0`（`rdd-skills-no-guide` / `d7-revised` / `rdd-skills-available`）。**独立复跑**：`rdd-skills.sh --json` 的 `available[]` 28 项不含 `guide` |
| AC-4 | **pass** | `recommender.scan_state('.')` ⇒ `('rdd-builder', '变更生成已完成 → 进入变更执行', 'high')` |
| AC-5 | **pass** | `grep -rn 'stage_guide' skills/rddf-session/scripts/ _lib/` 的命中项经逐条核对，**全部**为 legacy enum 保留（`_types.py:32/41/55` 的 `_VALID_KINDS` / `_KIND_ALIAS` / `HEARTBEAT_TIMEOUT_BY_KIND`，`sessions_schema.json:14/47/48/69`）或文档字符串；**非注释、非 legacy 的代码路径命中 0**。与 `iteration_schema.json` / `verifier_loop_schema.json` 的既有政策一致 |
| AC-6 | **pass** | **实测**（非代码存在性推断）：fixture（`events.jsonl` 含 3 条 `phase_started`/`phase_completed`，`sessions.json` 一条 active `stage_builder`）下 `synthesize()` ⇒ `child_progress` 非空，含 `kind=stage_builder started=2 completed=1 detail='stage_builder 完成 1/2'` —— 含「完成」计数，不含 `child progress unavailable`。另：`grep -c 'phase_started' rddf_session_hooks.sh` ⇒ 2（hook 仍写事件）；`_read_events_for_children` 可导入 |
| AC-7 | **pass** | `bash tests/scripts/report_regression.sh` ⇒ **0 新增失败 / 11 已知失败 / 未评估 0**（评估 248/248 文件） |
| AC-8 | **pass** | `grep -c 'guide-orchestrator-flow' docs/architecture/README.md` ⇒ 0；`docs/legacy/guide-orchestrator-flow.md` 存在 |
| AC-9 | **pass** | ADR-0055 / ADR-0056 各含 1 处 `Superseded by ADR-0063`；ADR-0051 References 含 `ADR-0063` |
| AC-10 | **pass** | **跨仓人工验证**：`grep -c 'guide. skill 不删' ~/.config/opencode/.rddf/state/adr-front-agent-redesign.md` ⇒ 0；`grep -c 'front 吸收'` ⇒ 1（D7 的职责划分保留）。治理面改动已由 architect 实施并提交（opencode 仓 `82adaa6`，oracle + critic 双审通过） |
| AC-11 | **pass** | `install.sh:131-143` 含 broken symlink 清理（`-L` 真且 `-e` 假才删）；`docs/migration/v3-to-v4.md` 含 `rm -f ~/.agents/skills/guide` |
| AC-12 | **pass** | C 阶段全量门 `/tmp/opencode/c-full.log` ⇒ `✅ ALL PASSED`；B 阶段全量门（含 C 的全部改动 + B 的改动）`/tmp/opencode/b-full.log` ⇒ `rc=0` / `✅ ALL PASSED`（bats 回归门 0 新增失败；pytest unit 3433 passed；pytest integration 196 passed） |

## 失败项

无。

## 遗留清扫结果

| 项 | 结果 |
|---|---|
| TODO / FIXME / XXX / HACK | 0 |
| 调试日志 / `breakpoint()` | 0 |
| 注释掉的代码 | 0 |
| 被 skip 的测试 | 无新增 |
| 未替换的 mock | 0 |
| 临时 fallback 分支 | 0 |
| 恒假判据 | 已清：`orphan_gates_check.py`（检查目标 `skills/guide-design/` 早已不存在 ⇒ 恒返回空，假绿）+ `test_design_done_gate.sh`（被测函数全仓不存在） |
| 测试污染 | 已清：`improvement-suggestions.md` 末尾 2 行 `dirty e2e content` —— 来自本 change 删除的 `test_pre_checkout_warning.bats`（该测试直接往真实仓库文件追加内容）。已恢复 |
| 死代码 | 已清：4 个 `stage_guide` 代码路径（`guide_entry`/`guide_close`/`poll_events` hook、`update_last_seen_offset` API、`_reset_stage_guide_offsets`、`parent_kind_map` 两条映射、`_commands.py` 豁免分支、doctor 的 `last_seen_offset` 检查块） |

## 备注

1. **events 总线保留已实测**：AC-6 是本 ADR 最易被误删的资产（ADR-0063 Decision 7 专门划界）。实测确认 `phase_started` 事件仍被 hook 写入、`child_progress` 聚合仍产出「stage_builder 完成 1/2」。
2. **schema enum 保留是有意为之**：按 metis 修订后的政策，`sessions_schema.json` 保留 `stage_guide` / `guide-orchestrator` / `last_seen_offset` 的枚举值（与 `iteration_schema.json` / `verifier_loop_schema.json` 一致）—— 收窄会让全局安装用户的存量 `sessions.json` 立刻校验失败。
3. **治理面先行已满足**：ADR-0063 Decision 5 要求「治理面未合入前本仓不 archive」。治理面 5 处改动已于 2026-11-19 由 architect 角色实施（opencode 仓 `82adaa6`），oracle 判 `治理面判定: PASS-WITH-NOTES`、critic 判 `APPROVE_WITH_CONDITIONS`（BLOCKER 0，2 条 SHOULD_FIX 已闭合）。审稿报告见 `.rddf/reviews/adr-0063-cross-repo-governance-review.md`。
4. **本仓的 archive 门已满足**：`openspec archive` 对本 change 无阻塞项；`iteration.json` 中本 change 为 `in_worktree`，归档后由 `rddf archive-sync` 转为 `archived`。
