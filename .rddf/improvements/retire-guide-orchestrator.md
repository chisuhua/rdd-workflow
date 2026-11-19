---
优先级: P1
来源: ADR-0063（退役 Guide-as-Orchestrator，取代 ADR-0055 / ADR-0056）
阶段: v4
分类: core-impl
类型: debt
主题: 架构退役
---

## 架构依据

ADR-0063（2026-11-19 已采纳，oracle + critic 双审）。`stage_guide` 长会话架构自 2026-09 落地起零真实使用：

| 数据源 | 总量 | stage_guide |
|---|---|---|
| `.rddf/state/sessions.json` | 21 | 1（completed，2026-09-23，POC owner） |
| `.rddf/state/sessions.archive.json` | 43 | 0 |
| `.rddf/state/events.jsonl` | 20 | 0 条含 guide |
| `~/.config/opencode/.rddf/state/` | — | 0 |

同时 opencode 侧 front agent 已接管「唯一交互入口」职责。**events 总线保留**（服务所有 stage，见 ADR-0063 Decision 7）。

**metis 修订（2026-11-19）**：
- **schema 政策改为「保留 legacy enum + 只删代码路径」** —— 与 `iteration_schema.json` / `verifier_loop_schema.json` 的既有政策一致（它们明确「legacy 值保留只为存量校验」）。收窄 `sessions_schema.json` 的 enum 会让全局安装用户的老项目 doctor 立刻红（`state_schema_check.py` 无 schema_version 门），而本仓无法证明外部无活跃数据。
- **补用户可见文档同步** —— `AGENTS.md` 会被注入所有 agent 上下文，归档后不删会让 agent 继续 `skill_use("guide")`，比 ADR 正文更重要。
- **补全局安装 broken symlink** —— `install.sh` 只对现存 skill 做 `ln -sf`，从不清理已移除项。

## 范围

### In Scope

1. `skills/guide/` 整体归档 → `docs/legacy/skills/guide/`；**新建** `docs/legacy/README.md`（当前不存在）说明「考古保留，不参与 install / pyright」。
2. `package.json::skills[]` 移除 `guide`；`pyrightconfig.json` 移除 `skills/guide` root。
3. **`stage_guide` 代码路径退役（schema enum 保留）**：
   - 原子步 A：`rddf_session_hooks.sh` 的 `parent_kind_map` 两条映射、`guide-entry` / `guide-close`、`rddf_session_hook_poll_events`、`RDDF_GUIDE_SESSION_ENABLED`
   - 原子步 B：`rddf_session.py::update_last_seen_offset`、`events_log.py::_reset_stage_guide_offsets`、`rddf_session_pkg/_commands.py` 的 stage_guide 豁免
   - 原子步 C：`rdd-doctor` 的 `last_seen_offset` 检查块
   - **不改** `_lib/schemas/sessions_schema.json` 的 enum 值（保留 `stage_guide` / `guide-orchestrator` / `last_seen_offset`，只在 description 标注 legacy）
4. `docs/architecture/guide-orchestrator-flow.md` → `docs/legacy/`；`docs/architecture/README.md` 索引同步。
5. **用户可见文档同步**：`skills/INSTALL.md`（3 处 `guide`）、`docs/ONBOARDING.md`（3 处，顺带修 `guide.md` → 归档路径）、`AGENTS.md`（关键目录列表 + skill 计数 −1）。
6. **ADR-0051 指针回填**：`docs/adr/ADR-0051-skill-description-convention.md` 的 References 加一行指向 ADR-0063（Decision 8 要求）。
7. **全局安装残留清理**：`install.sh` 增加「清理 `AGENTS_DIR` 下目标不存在的 symlink」；migration 文档加一行 `rm -f ~/.agents/skills/guide`。
8. **跨仓证据工件**：产出 `.rddf/state/.cross-repo-evidence.json`，覆盖两件事（`rdd-skills.sh --json` 不含 guide；D7 已修订），字段 `{path, command, executed_at, exit_code, stdout_sha256, status}`。
9. 测试：28 个引用 `skills/guide` 的文件 = 14 删除 + 11 改造 + 3 fixture/断言调整（`test_global_install_external_project.bats:195-197` 的 `expected_skills` 硬编码了 `guide`，必须点名）。

### Out of Scope

- 推荐逻辑收敛（`consolidate-recommender-implementation`）。
- ADR-0044 注释类残留（`cleanup-guide-star-residue`）。
- `sessions_schema.json` 的 enum 收窄（见上，保留 legacy 值）。
- `docs/adr/` 历史正文追溯改写。
- events 总线本体（保留）。

## 关键场景

- **GIVEN** `skills/guide` 已归档，**WHEN** 跑 `rddf-skills.sh --json`，**THEN** `available[]` 不含 `guide`。
- **GIVEN** schema enum 保留，**WHEN** `rdd-doctor` 校验存量 `sessions.json`（含 1 条 completed stage_guide），**THEN** 不报错（枚举合法，检查块已删）。
- **GIVEN** 全局安装过 guide 的机器，**WHEN** 跑更新后的 `install.sh`，**THEN** `~/.agents/skills/guide` 的 broken symlink 被清理。
- **GIVEN** 事件总线保留，**WHEN** 跑 `rddf monitor` 且存在 active stage_builder，**THEN** 输出含 `Child Progress` 与 `stage_builder`，且不含 `child progress unavailable`。

## 技术约束

- **原子步**：`_types._VALID_KINDS` 与 `sessions_schema.json` 枚举**都保留**（本次不改），所以无「运行时拒绝老记录」风险；但代码路径删除必须按上面的原子步分组，不能按文件顺序散落。
- **跨仓先行**：治理面未合入前，本 change 保持 in-progress、不 archive；证据工件 `status != verified` 时不得 archive。
- `stage_quick` 退役后的 parent 值在 `design.md` 定稿，并回填一条断言。

## 验收标准

- [ ] AC-1: `skills/guide` 不存在；`docs/legacy/skills/guide/SKILL.md` 存在；`[ -f docs/legacy/README.md ]` 为真且含「考古保留」
- [ ] AC-2: `package.json::skills[]` 不含 `guide`；`pyrightconfig.json` 不含 `skills/guide`
- [ ] AC-3: `.rddf/state/.cross-repo-evidence.json` 存在，`status=="verified"`，且含 `rdd-skills.sh` 与 D7 两个 item
- [ ] AC-4: `rddf guide` 仍可执行并输出 RECOMMEND
- [ ] AC-5: `grep -rn 'stage_guide' skills/rddf-session/scripts/ _lib/` 的**非注释代码行** = 0；`sessions_schema.json` 的 enum 保留 `stage_guide`（政策一致）
- [ ] AC-6: fixture 项目（events.jsonl 含 `phase_started` + sessions.json 一条 active `stage_builder`）下 `rddf monitor` 输出含 `stage_builder` 与 `完成`，且不含 `child progress unavailable`
- [ ] AC-7: `python3 -m pytest tests/unit/ -q` 与 `bats tests/ --recursive` 无新增失败
- [ ] AC-8: `docs/architecture/README.md` 不含 guide-orchestrator-flow；该文件存在于 `docs/legacy/`
- [ ] AC-9: ADR-0055 / ADR-0056 Status 含 `Superseded by ADR-0063`；ADR-0051 References 含 `ADR-0063`
- [ ] AC-10: `grep -c 'skill_use("guide")' skills/INSTALL.md` = 0；`grep -c 'guide/SKILL.md' AGENTS.md` = 0；`docs/ONBOARDING.md` 不含 `skills/guide.md`
- [ ] AC-11: `install.sh` 含清理不存在 symlink 的逻辑；migration 文档含 `rm -f ~/.agents/skills/guide`
- [ ] AC-12: 全量门 `./test.sh --full --regression` ⇒ 未评估 0 + 新增失败 0
