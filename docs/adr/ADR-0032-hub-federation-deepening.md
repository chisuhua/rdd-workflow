# ADR-0032: Hub 联邦深化 (Hub Federation Deepening)

> **状态**: 待定
> **日期**: 2026-08-19
> **决策者**: 待确认
> **父 ADR**: ADR-0030 (Hub-and-Spoke 联邦架构), ADR-0031 (跨项目 RFC 人类决策), ADR-0029 (Issue 驱动提案创建)
> **落地提案**: 4 个 P0 change（见 roadmap v2.2 Phase 1-3）+ 后续 P1-P3

## Context

ADR-0030/0031 奠定了 Hub 联邦的**基础通信通道**（RFC 上行 / 契约下行 / 状态轮询 / 人类审批门控）。2026-08-19 上线 e2e 测试 `tests/integration/test_cross_repo_e2e_real.bats` (13 cases) 时，发现并修复了 4 处 gh CLI 兼容层生产 bug（见 `2026-08-19-fix-federation-gh-cli-integration`）。

修复后，**流程可用**但仍存在 3 个**结构性体验缺陷**：

1. **提案生成盲区**: 当前 `add-improve` 仅生成 head 字段（阶段/分类/类型/特性），不分析提案是否触碰 Hub 契约。开发者需手动判断"这是不是跨仓变更"，容易遗漏 → 在 `guide-design` 中后期才补 RFC，重复劳动。
2. **审批与 RFC 脱节**: `approve_proposal.sh --manual --hub-issue` 要求人工先提供 Hub Issue URL，但创建 RFC 的步骤（`rddf report-issue --category=rfc`）独立。审批流程没有引导式交互，让人类在多个工具间跳转。
3. **design-done 与 RFC 草稿无关联**: 当前 `design_done_gate.py` 仅检查 pending 和 audit log，**不检查**本地是否已生成 RFC 草稿（即"准备发什么 RFC"）。这意味着开发者可以 approve 一个跨仓 proposal 但**没有准备任何 RFC 内容**，Hub 端无信息。

**架构依据**:
- ADR-0029 §3: Issue 驱动提案创建（已在单项目层面验证 `add-improve --from-issue`）→ 本 ADR 扩展为**Hub 端 Issue 驱动**
- ADR-0031 §实现细节 4: 审计 trail 写 `decision=fail` before refuse → 本 ADR 复用此模式，让"草稿-审批-发 RFC"全程有审计
- ADR-0025 §D1: design 阶段两层内容审查 → 本 ADR 增加第三层"Hub 影响审查"
- ADR-0018 (cross-repo deps gate) → 本 ADR 引入 RFC 草稿门控，与 deps gate 并列

## Decision

**确立"提案生成含跨仓分析 → 审批交互定 RFC 内容 → approve 后自动发 RFC"三阶段闭环**：

### 三阶段核心设计

#### 阶段 A: 提案生成含跨仓分析 (Phase 1)

- **A1**: 提案模板 5 段正文（动机 / 契约草案 / 利益相关方 / 兼容策略 / 回滚方案），覆盖跨仓变更完整生命周期
- **A2**: `add-cross-repo-impact-detection` 自动扫描提案正文，匹配 Hub `contracts/*.yaml` 文件，提示"建议发起 RFC"
- **A3**: 自动建议 `stakeholders` 列表（基于 Hub 契约 ownership 注释或元数据）

#### 阶段 B: 审批交互定 RFC 内容 (Phase 2)

- **B1**: `add-rfc-interview-flow` 引导式对话（title / stakeholders / gate / contract-impact / Hub Issue 占位），生成 `.rddf/state/.rfc-draft-<name>.json`
- **B3**: `rddf rfc-draft <name>` 与 `rddf rfc-create --from-draft <name>` 两阶段拆分，先有草稿再创建 Issue
- **B5**: Hub Issue Body 自动内联契约草案 base64 内容

#### 阶段 C: 审批后自动发 RFC (Phase 3)

- **C1**: `approve_proposal.sh --manual --auto-issue` 选项，approve 后自动调 `report_issue_rfc.py`
- **C2**: 本地 `--hub-issue` 占位 → 自动捕获新建的 Issue URL 并回填

#### 阶段 D: 门控与契约

- **D2**: `design_done_gate.py::check_rfc_draft` 新增门控：category=cross-repo-federation 必须存在 `.rfc-draft-<name>.json`，且内容 schema 校验通过
- **D3**: `rfc_draft_schema.json` v1，定义草稿必填字段
- **D5**: RFC 草稿的契约部分与现有 Hub 契约的兼容度自动检查（集成 `contract_check.py`）

### 影响范围

**In Scope (本 ADR 涵盖)**:

- `skills/add-improve/scripts/detect_cross_repo_impact.py` (新增)
- `skills/guide-design/scripts/rfc_interview.sh` (新增)
- `skills/guide-design/scripts/rfc_draft_gate.py` (新增)
- `skills/guide-design/scripts/approve_proposal.sh` 增加 `--auto-issue` 选项
- `skills/_lib/schemas/rfc_draft_schema.json` (新增 v1)
- `skills/report-issue/scripts/report_issue_rfc.py` 接受 `--contract-draft` 参数
- 4 个 P0 proposal（见 roadmap.md v2.2 Phase 1-3）
- 2 个 P1 / 2 个 P2 / 1 个 P3（见 roadmap.md v2.2 Phase 4）

**Out of Scope (后续 ADR 涵盖)**:

- Hub Projects V2 字段自动配置（已在 ADR-0030 §Out Scope 提及，由 `rdd-hub-bootstrap` 渐进完善）
- Stale RFC 自动清理（已在 ADR-0030 后续待办 11）
- MCP Server 真实传输（依赖 mcp SDK 升级）
- 跨仓库联合 Ship 编排（依赖 `cross-repo-deps` Phase 4 后续工作）
- Stakeholder 端自动发现新 RFC（由 P2 `add-stakeholder-rfc-bootstrap` 在 v2.2+ 渐进）

### 实现约束

1. **不破坏 ADR-0031**: 任何阶段都必须维持"人类强制审批"语义。AI 可分析、起草、推荐，但**不可代批**。
2. **草稿与执行解耦**: RFC 草稿是设计产物，Hub Issue 是执行产物。两阶段拆分让人类在"准备发什么"和"实际发"之间有清晰的检查点。
3. **审计 trail 完整**: 草稿生成、approve、auto-issue 三步骤各自写 `.cross-repo-audit.jsonl`，可追溯。
4. **schema 验证**: 草稿、Hub Issue body、approve 状态全部经 schema 校验，禁止字段缺失或类型错误。
5. **dry-run 支持**: 所有新工具默认支持 `--dry-run`，便于 CI 与排错。

### 与 ADR-0030 的关系

本 ADR **不替换** ADR-0030，而是其**深化子集**：

| 维度 | ADR-0030 (基础) | ADR-0032 (深化) |
|---|---|---|
| 通信通道 | RFC 上行 + 契约下行 + 状态轮询 | (复用，无新增) |
| 人类决策 | approve 强制人工 (ADR-0031) | 拓展为"草稿-审批-发 RFC"三阶段 |
| 提案生成 | 模板 + 分类 | + 跨仓影响自动分析 + RFC 草稿模板 |
| 门控 | pending + audit | + RFC 草稿存在性 + schema |
| 自动发 RFC | 无 | approve 后自动 `--auto-issue` |

ADR-0030 状态从"待定"转为"已采纳"作为本 ADR 采纳的前置条件（见 §后续步骤）。

### 与 ADR-0031 的关系

- ADR-0031 规定"AI 不可自动批准" → 本 ADR 引入 `--auto-issue` 是审批**之后**自动调用 `report_issue_rfc.py`，**不违反** ADR-0031（人类已批准）
- ADR-0031 审计 trail (`decision=fail` before refuse) → 本 ADR 草稿门控失败同样写 `decision=fail`
- ADR-0031 `RDDF_APPROVE_ACTOR` env var → 本 ADR `--auto-issue` 复用同一 env var

### 与 ADR-0029 的关系

- ADR-0029 `add-improve --from-issue <N>` (单项目 GitHub Issue 驱动) → 本 ADR 扩展为 `add-improve --from-hub-issue <org/repo#N>` (跨项目 Hub Issue 驱动)
- 复用 `gh_repo` 参数解析逻辑，复用本地 pending 状态文件结构

### 失败模式与回滚

| 失败 | 当前行为 | 后续恢复 |
|---|---|---|
| 草稿 schema 校验失败 | design-done 阻断 + 写 audit fail | 人类编辑 `.rddf/improvements/<name>.md` + 重跑 add-rfc-interview-flow |
| `--auto-issue` 调 `report_issue_rfc.py` 失败 (rate limit / 网络) | approve 已成功，RFC 未发 | 人类手动跑 `rddf rfc-create --from-draft <name>` |
| Hub Issue 创建后未及时关联 proposal | proposal.md 缺 `**Hub RFC**:` 字段 | `add-rfc-issue-bidirectional-link` (P1) 补齐 |
| `report_issue_rfc.py` URL 解析失败 (gh v2.92.0 bug) | RFC 创建失败 | 人类手动复制 URL 回填 `--hub-issue` |

## 后续步骤

### ADR-0030 转正

- [ ] **前置**: 将 ADR-0030 状态从"待定"改为"已采纳"（包含 gh CLI 兼容性、e2e 测试现状、ADR-0032 引用）
- [ ] **联动**: 提交 `transition-adr-0030-status` change 单独完成此动作，不混入本 ADR

### 4 个 P0 change（按 roadmap v2.2 顺序实施）

1. `add-cross-repo-impact-detection` (Phase 1, P0)
2. `add-rfc-draft-template` (Phase 1, P0)
3. `add-rfc-interview-flow` (Phase 2, P0)
4. `add-auto-rfc-from-approve` (Phase 3, P0)

每个 change 完整走 `guide-design → guide-plan → guide-ship` 流程，含：
- improvement 文件 + proposal.md + design.md + tasks.md
- openspec/changes/<name>/ 目录 + specs/ delta
- worktree execute + 单元测试 + bats 集成测试
- archive

### 3 个月复核窗口

- [ ] **2026-11-15 复核**:
  - 4 个 P0 change 是否全部 archive
  - e2e 测试是否扩展到覆盖"草稿-审批-发 RFC"全链路（+5 cases 目标）
  - `--auto-issue` 是否在 ≥2 个 Spoke 仓库被实际使用（非 dogfood）
  - 审计 trail 是否完整（草稿 + approve + RFC 创建各自留痕）

## References

- ADR-0030: hub-and-spoke-federation (本 ADR 的父)
- ADR-0031: human-in-loop-cross-repo (本 ADR 的合规基线)
- ADR-0029: issue-driven-proposal-creation (本 ADR 扩展其 Issue-driven 模式)
- ADR-0025: design-proposal-creation (本 ADR 增加第三层 Hub 影响审查)
- ADR-0018: change-arch-alignment (cross-repo deps gate, 与本 ADR RFC 草稿门控并列)
- `2026-08-19-fix-federation-gh-cli-integration` (本 ADR 落地的前置 bug fix)
- `tests/integration/test_cross_repo_e2e_real.bats` (13 cases e2e baseline)
- `docs/proposal-suggestions-format.md`
- `docs/proposal-approved-format.md`
- `openspec/specs/cross-repo-federation/spec.md` (本 ADR 将扩展此 capability)