# improve-from-roadmap-naming-flexibility

**优先级**: P2 | **来源**: 2026-08-27 Hybrid path reflection (调用 `from_roadmap.sh` 时遇到命名约束 `from-roadmap-<phase>-<category>`, 只能创建 1 个固定命名的 scaffold, 9 个多 proposal batch 创建不适用)
**阶段**: phase-2 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-27 Hybrid path reflection (流程改进)

## 架构依据

`skills/add-improve/scripts/from_roadmap.sh` 的命名逻辑是:

```bash
proposal_name = f"from-roadmap-{phase_id}-{category_id}".replace("/", "-")
```

后果:
- 2026-08-27 Hybrid path 试图用 `from_roadmap.sh` 一次性创建 9 个 proposal,但每次调用只能生成 1 个 `from-roadmap-phase-1-governance.md`,名称冲突(重复调用会覆盖前一次)。
- AI agent 遇到约束后只能放弃走直接 `write` 路径,绕过标准流程。
- Hybrid path 中最终放弃了 `from_roadmap.sh`,改为直接 `write` 9 个文件,虽然格式正确但失去了 `from_roadmap.sh` 应有的 scaffold 优势。

期望行为: `from_roadmap.sh` 支持 `--name <proposal_name>` 参数,允许 AI agent 或 user 指定 proposal 名称,从而支持多 proposal batch 创建。

## 范围

**In Scope**:

- `from_roadmap.sh` 增加 `--name <proposal_name>` 参数,可选
- `from_roadmap.py` (Python 主逻辑) 接受 `ADD_IMPROVE_NAME` env var (Oracle C1 pattern)
- 不指定 `--name` 时,行为保持向后兼容(默认 `from-roadmap-<phase>-<category>`)
- `proposal_name` 唯一性校验: 若同名文件已存在,返回 exit 1 + 明确错误

**Out of Scope**:

- 改变 scaffold 模板内容
- 修改 `from_issue.sh` 命名(独立提案)
- 批量调用 API(单次调用足够)

## 关键场景

- GIVEN AI agent 调用 `from_roadmap.sh --name fix-iteration-archive-sync --from-roadmap phase-1/governance --theme ...`
  WHEN scaffold 创建
  THEN 文件名是 `.rddf/improvements/fix-iteration-archive-sync.md` (而非 `from-roadmap-...`)

- GIVEN AI agent 调用 `from_roadmap.sh --name fix-existing-thing --from-roadmap ...` 但 `fix-existing-thing.md` 已存在
  WHEN scaffold 创建
  THEN 返回 exit 1,stderr 输出 "❌ proposal already exists: fix-existing-thing.md"

- GIVEN AI agent 不指定 `--name`,调用 `from_roadmap.sh --from-roadmap phase-1/...`
  WHEN scaffold 创建
  THEN 文件名仍是默认 `from-roadmap-phase-1-...` (向后兼容)

## 技术约束

- MUST: `--name` 通过 env-var `ADD_IMPROVE_NAME` 传递(Oracle C1)
- MUST: 唯一性校验,防止 overwrite 已存在的 proposal
- MUST: 命名合法性校验(kebab-case,符合 `proposal_name` schema)
- MUST NOT: 改变 scaffold 模板内容
- SHOULD: 错误信息清晰,提供修复建议
- SHOULD: 历史 scaffold 文件名保持不变(无 rename)

## 验收标准

- [ ] `from_roadmap.sh --name <proposal_name>` 参数支持
- [ ] `from_roadmap.py` 接受 `ADD_IMPROVE_NAME` env var
- [ ] 默认行为保持向后兼容(不指定 `--name` 时使用旧命名)
- [ ] 唯一性校验:同名已存在返回 exit 1
- [ ] 命名合法性校验:kebab-case,不能含特殊字符
- [ ] 新增 unit test 覆盖 scenarios:
  - `--name fix-x` → 生成 `fix-x.md`
  - 不指定 `--name` → 生成 `from-roadmap-<phase>-<category>.md`
  - 同名已存在 → exit 1
  - 非法命名(空格/大写) → exit 1
- [ ] 文档: `add-improve/SKILL.md` from-roadmap 章节更新
- [ ] `add-improve/scripts/from_roadmap.sh --help` 输出新参数说明

## 相关

- 关联: `from_roadmap.sh` (本次修改目标)
- 关联: `add-improve/SKILL.md` from-roadmap 模式文档
- 来源: 2026-08-27 Hybrid path reflection (本次会话)
- 文件: `skills/add-improve/scripts/{from_roadmap.sh, from_roadmap.py}`