# ADR-0026: rdd-workflow Internal Metadata Namespace Convention

> **状态**: 已采纳
> **日期**: 2026-08-11
> **来源**: skill-context-audit POC 2026-08-11
> **影响范围**: 所有 rdd-workflow internal metadata 路径
> **关联提案**: `migrate-improvements-to-rddf-namespace`

## Context

`improvements/*.md` 目录存放 134 个 rdd-workflow 提案（每个独立 .md 文件）。这些文件被 opencode-skillfull 插件自动索引为 slash commands，注入到 system prompt 的 `<available_skills>` 块，静态消耗 **~4,887 tokens**（133 entries × ~147 chars ÷ 4）。

2026-08-11 的 POC 验证了以下事实：
- opencode-skillfull 插件不读取文件 frontmatter 元数据（`user-invocable: false` 无效）
- 插件过滤 dot-prefix 目录（`.poc-test-skillignore/probe` 实测不在 available_skills）
- 现有 `.rddf/plans/` 已是 "dot-prefix tracked exception" 先例

未来若添加新 metadata 类别（如 `.rddf/notes/`、`.rddf/experiments/`），若不约定 dot-prefix 路径，将重蹈覆辙。

## Decision

**rdd-workflow 项目的 internal metadata 必须使用 `.rddf/<category>/` 路径，符合 dot-prefix 命名约定。**

### 路径分类规则

| 类别 | 类型 | 例子 | .gitignore |
|------|------|------|------------|
| runtime-only | 临时状态，per-machine | `.rddf/state/`, `.rddf/wt/`, `.rddf/detectors/`, `.rddf/actions/` | gitignored |
| committed artifacts | 跨机器共享的元数据 | `.rddf/plans/`, `.rddf/improvements/` | tracked (默认靠"不写进 gitignore"实现) |

### 已存在实例

- **`.rddf/plans/`** (v2.0+) — TDD 5 步执行计划，git tracked
- **`.rddf/improvements/`** (本次迁移) — 134 个提案，git tracked
- **`.rddf/state/`** — runtime 状态，gitignored
- **`.rddf/wt/`** — git worktree 隔离目录，gitignored

### 添加新 metadata 类别的指引

1. **路径**: 必须 `.rddf/<category>/`
2. **类型决策**: 评估是 runtime-only 还是 committed artifacts
3. **gitignore**: 
   - runtime-only 默认加到 `.gitignore`（`.rddf/state/`, `.rddf/wt/` 等已存在）
   - committed artifacts 不写进 gitignore（靠"不写"实现 tracked）
4. **新提案**: 添加新 metadata 类别需走 add-improve → guide-design 流程，作为单独提案追踪

## Consequences

### 正面

- ✅ opencode-skillfull 插件自动过滤 dot-prefix 目录 → system prompt 节省 ~4,887 tokens
- ✅ 所有 rdd-workflow internal metadata 统一在 `.rddf/` 下，命名一致
- ✅ 与现有 `.rddf/plans/` 先例完全对齐
- ✅ 未来添加新 metadata 类别有明确路径规则

### 负面

- ❌ 改动现有 `improvements/` → `.rddf/improvements/` 需要更新 134 个 markdown 链接 + 37 个 skills/_lib/ 路径 + 11 个测试 fixture
- ❌ 一次性迁移成本（已完成）
- ❌ 任何未来添加的非-dot-prefix 目录需先评估是否符合本 ADR

### 风险

- opencode-skillfull 插件行为变更（dot-prefix 过滤）可能在新版本被破坏
  - **缓解**: 提案 migrate-improvements-to-rddf-namespace 的 AC-5 强制用户验证 available_skills 行为
- 外部引用（如果有）`.rddf/improvements/<name>` 链接可能在 plugin 升级后失效
  - **缓解**: 监控 plugin 升级 changelog

## Alternatives Considered

### A. 移动到 `openspec/changes/archive/_improvements/`
- ❌ 语义错误（这些是活跃提案池，不是归档）
- ❌ 与 OpenSpec 命名约定混淆

### B. 移动到 `.improvements/`（top-level dot-prefix）
- ❌ 破坏 rdd-workflow metadata 统一在 `.rddf/` 下的命名约定
- ❌ 与 `.rddf/plans/` 实践不一致

### C. 添加 symlink `improvements/` → `.rddf/improvements/`
- ❌ 引入新维护面
- ❌ N 版本后需清理

### D. 不迁移，仅文档化
- ❌ 不能解决 system prompt 浪费
- ❌ 未来 metadata 类别添加仍会出错

## References

- **ADR-0023** — v3 rename spec-workflow to rdd-workflow (解释了 `.rddf/` 命名起源)
- **ADR-0024** — deps-driven execution mode (提到 `.rddf/state/` 实践)
- **POC**: `/tmp/opencode-poc-B-verify.sh` 验证 dot-prefix 过滤机制
- **关联提案**: `migrate-improvements-to-rddf-namespace` (本次迁移的执行细节)

## Validation

执行迁移的验收标准（AC-7 已包含本 ADR）:
- [ ] 文件存在 `docs/adr/ADR-0026-internal-metadata-namespace-convention.md`
- [ ] 内容包含关键字 `.rddf/<category>` 和 `opencode-skillfull`
- [ ] PR merge 后用户验证 opencode available_skills 不再含 improvements/* 条目
