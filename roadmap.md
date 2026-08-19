# 项目路线图

## 元信息
- **版本**: 3
- **创建时间**: 2026-06-07T09:16:26+08:00
- **最后更新**: 2026-08-19 (v2.2 规划: Hub 联邦深化, ADR-0032)
- **当前阶段**: v2.1 (多会话/编排), v2.2 规划中

## v2.0 已完成 (2026-06-26)

v2.0.0-beta 已发布。包含 5 个 Phase，8 个 ADR (ADR-0002~0008) 已全部实施。

详见 `docs/v2-implementation-plan.md`。

## v2.1 规划

### Phase 1: 完整多会话支持
**目标**: 完成 ADR-0010 的完整实现（并行会话、依赖调度）
**状态**: 📋 待启动
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v2-multi-session` | P0 | 2-3w | 1 | — | 多会话协调 + 依赖图调度器 (ADR-0010 §4) |
| `add-review-phase-debt-reflow` | P1 | 1-2w | 1 | — | Review 阶段债务回流机制 (ADR-0014) |
| `add-openspec-validate-critic` | P1 | 2-3h | 2 | `add-review-phase-debt-reflow` | openspec validate 集成为 plan-critic (ADR-0015) |
| `add-arch-artifact-discovery` | P1 | 1-2w | 1 | — | Arch 工件发现契约 (ADR-0016) |
| `add-incremental-skeleton-planning` | P2 | 1w | 2 | `add-arch-artifact-discovery` | 增量 skeleton planning (ADR-0020) |
| `add-manual-deps-field` | P1 | 1-2d | 1 | — | manual_deps 人工依赖声明 (ADR-0022) ✅ |
| **预计总计** | | **6-10w** | | | |

### Phase 2: 编排能力完善
**目标**: 补齐人工编排意图表达 + roadmap 格式升级 (ADR-0022)
**状态**: ✅ 部分完成
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `add-manual-deps-field` | P1 | 1-2d | 1 | — | manual_deps 字段 + iteration_schema v4 + deps 合并 (ADR-0022) ✅ |
| **预计总计** | | **1-2d** | | | |

## v2.2 规划: Hub 联邦深化 (ADR-0032)

**目标**: 巩固 Hub 联邦实战可用性 — 从"能跑通"到"提案生成含跨仓分析 + 审批交互定 RFC + approve 后自动发 RFC"三阶段闭环。
**父 ADR**: ADR-0030 (Hub-and-Spoke), ADR-0031 (跨项目 RFC 人类决策), ADR-0029 (Issue 驱动提案创建)
**前置依赖**: `2026-08-19-fix-federation-gh-cli-integration` (gh CLI 兼容层修复) ✅ 已 archive
**3 个月复核窗口**: 2026-11-15 — 4 个 P0 change 全部 archive + e2e 测试扩展 + 至少 2 个 Spoke 仓库实际使用 `--auto-issue`

### Phase 1: 提案生成阶段 — 自动跨仓分析 (A1/A2/A3)
**目标**: 让开发者在提案阶段就识别跨仓影响，无需事后补救
**状态**: 📋 待启动
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `add-cross-repo-impact-detection` | P0 | 2-3d | 1 | — | A2/A3: 扫描提案正文匹配 Hub `contracts/*.yaml`，自动建议 stakeholders + 检测 category=cross-repo-federation |
| `add-rfc-draft-template` | P0 | 1d | 1 | — | A1: 5 段正文模板（动机 / 契约草案 / 利益相关方 / 兼容策略 / 回滚）+ 自动 base64 内联契约草案 (B5) |
| **预计总计** | | **3-4d** | | | |

### Phase 2: 审批交互阶段 — 引导式 RFC 内容确认 (B1/B3/D2)
**目标**: 让审批流程与 RFC 起草合二为一，人类在 approve 前看到"准备发什么"
**状态**: 📋 待启动 (依赖 Phase 1)
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `add-rfc-interview-flow` | P0 | 3-4d | 2 | `add-cross-repo-impact-detection`, `add-rfc-draft-template` | B1/B3: 引导式对话生成 `.rfc-draft-<name>.json`，两阶段 RFC（draft → create） |
| `add-rfc-draft-gate` | P0 | 1d | 2 | `add-rfc-interview-flow` | D2: `design_done_gate.py::check_rfc_draft` 校验草稿存在性 + schema v1 |
| **预计总计** | | **4-5d** | | | |

### Phase 3: 审批后自动发 RFC (C1/C2)
**目标**: approve 后无需人重跑 `report-issue`，减少工具跳转
**状态**: 📋 待启动 (依赖 Phase 2)
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `add-auto-rfc-from-approve` | P0 | 2d | 3 | `add-rfc-draft-gate` | C1/C2: `approve_proposal.sh --manual --auto-issue` 选项，自动调 `report_issue_rfc.py` 并回填 URL |
| **预计总计** | | **2d** | | | |

### Phase 4: 多方对称 + 回归 (P1-P3, 后续)
**目标**: 完成 Stakeholder 端对称流程 + 双向同步 + 测试覆盖
**状态**: 📋 待规划 (依赖 Phase 3)
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `add-rfc-issue-bidirectional-link` | P1 | 1d | 4 | `add-auto-rfc-from-approve` | C3: proposal.md 头部 `**Hub RFC**:` 字段 + 反写 |
| `add-stakeholder-rfc-bootstrap` | P2 | 2d | 4 | `add-rfc-issue-bidirectional-link` | D6: Stakeholder 端 watch-hub 增强，发现新 RFC 自动创建本地 pending |
| `add-rfc-state-sync-watch` | P2 | 2d | 4 | `add-stakeholder-rfc-bootstrap` | C4/C5: watch-hub 检测 RFC reject → 本地 proposal 自动 reject；CONDITIONAL → 触发草稿重新生成 |
| `add-rfc-proposal-e2e-test` | P3 | 1d | 4 | `add-rfc-state-sync-watch` | D7: 新增 5 个 e2e case 覆盖"提案含跨仓分析 → 审批交互 → 自动发 RFC"全链路 |
| **预计总计** | | **6d** | | | |

### v2.2 总览

| 维度 | 数量 |
|---|---|
| Phase 1-4 总 Changes | 9 |
| P0 (含 4 个本轮必做) | 5 |
| P1 | 1 |
| P2 | 2 |
| P3 | 1 |
| 总估算工时 | 15-17d (Phase 1-4 全做) |

### v2.2 落地门槛

- ADR-0030 必须从"待定"转"已采纳"（单列 `transition-adr-0030-status` change）
- 4 个 P0 change 必须按 Wave 1→2→3 顺序，每个走完整 `guide-design → guide-plan → guide-ship` 流程
- 每个 P0 change 的 `tasks.md` 13 个 checklist 项 (同 `fix-federation-gh-cli-integration` 标准)
- 每个 P0 change 必须有 ≥1 个新增 bats test
- e2e 测试基线 `test_cross_repo_e2e_real.bats` 必须全绿，且新增 case ≥ 5

## v3.0 规划

## v3.0 规划

### Phase 1: 定时循环与事件触发
**目标**: 实现 ADR-0009 定时触发器
**状态**: 📋 待规划
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v3-scheduled-triggers` | P1 | 1-2w | 1 | — | 定时循环 + 事件触发 (ADR-0009) |
| **预计总计** | | **1-2w** | | | |

### Phase 2: 阶段步骤化执行
**目标**: 实现 ADR-0011 步骤化执行模型
**状态**: 📋 待规划
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v3-step-pipeline` | P1 | 3-4w | 1 | — | 阶段步骤化执行模型 (ADR-0011) |
| **预计总计** | | **3-4w** | | | |

### Phase 3: 流程定制层
**目标**: 实现 ADR-0012 自定义流程
**状态**: 📋 待规划
**依赖**: Phase 2 (步骤化执行模型为基础)
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v3-flow-customization` | P1 | 3-4w | 1 | - | 流程定制层 (ADR-0012) |
| **预计总计** | | **3-4w** | | | |

## v2.1 质量改进计划

> 来源: `.omo/plans/improve-change-quality-index.md` (Plan A/B/C/D)
> 执行顺序: Wave 1 (C ∥ A) -> Wave 2 (B) -> Wave 3 (D)
> 不引入新 ADR 引用，仅在现有架构上提升 change 质量与可观测性。

| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `refresh-input-sources` | P0 | 1-2h | 1 | - | Plan C: 扩展 roadmap + gap-analysis + TODO 扫描 |
| `refine-adr-0015-wiring` | P0 | 2-3h | 1 | - | Plan A: 补完 ADR-0015 plan-critic 链路 (状态 待定 -> 已采纳) |
| `add-propose-output-validation` | P1 | 6-8h | 2 | `refine-adr-0015-wiring` | Plan B: iteration_schema v3->v4 + 5 个 check + STRICT_PROPOSE_GATE |
| `add-change-quality-guide` | P1 | 2-3h | 3 | `add-propose-output-validation` | Plan D: docs/change-quality-guide.md + AGENTS.md/propose.md 引用 |
| **预计总计** | | **11-16h** | | | |
