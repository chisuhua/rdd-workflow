# fix-adr-0031-safety-gate-substantiation

**优先级**: P0 | **来源**: Oracle 审查 ADR-0030/ADR-0031 (ses_fecf9715affebqMTQnuYJMEEL7) / CRITICAL C1+C2
**阶段**: v2.1.x patch | **分类**: core-impl | **类型**: bugfix
**依赖 ADR**: ADR-0031, ADR-0030
**阻塞**: 该 change 修复完成前, ADR-0031 §"人类兜底" 承诺为形式合规, 任何 `--manual --hub-issue` 调用均无人类证明即可放行
**状态**: Proposed (2026-08-18)

## 架构依据

**背景**

ADR-0031 (跨项目 RFC 必须人类决策) 定义 5 项实现细节作为"必须由人类决策"的实质语义保证。Oracle 2026-08-18 审查发现: 5 项中仅 1 项（exit 3 硬阻断 `--auto-accept`）真正落地；其余 4 项**全部缺失或未接线**, 而对应 change `2026-08-16-add-strict-human-approval-for-cross-repo-changes/tasks.md` 已 21/21 全勾归档。这是本仓第二次出现"tasks 全勾但 AC 未交付"的验收漂移（前例: `add-contract-lint-ci-gate` 需 `complete-add-contract-lint-ci-gate` 补丁救场）。

**4 项缺失实现**（Oracle §C1）

1. **`RDDF_REQUIRE_HUB_APPROVAL` env var 无任何代码读取** — 全仓 grep 仅命中 docs/specs/archive
2. **`read -s` GitHub username 交互 prompt 全仓不存在** — `--manual` 模式接受任意字符串作为 hub-issue 而不验证人类输入
3. **`cross_repo_audit.py::append_audit_log_entry` 无生产调用方** — audit log 模块存在且有单测, 但 approve 流从不调用, log 文件**永远为空**
4. **Hub Issue 状态本地批准前重查不存在** — ADR §5 明文要求"防 race condition", 实现缺失

**fail-open 缺陷**（Oracle §C2）

`approve_proposal.sh:51-58` 从 `openspec/changes/<name>/roadmap-meta.yaml` 读 category — 但 ADR-0025 流程下该文件**由本脚本自己在第 260 行才创建**。结果是：首次 approve cross-repo 提案时 gate 静默 fail-open（`is_cross_repo_proposal()` 返回 false → exit 3 不触发 → AI 可 auto-accept）。ADR §分类传递契约 明文要求 SSOT 为 `.rddf/improvements/<name>.md` 的 `**分类**:` 字段（脚本第 213 行也在解析该字段）— 与实现自相矛盾。

**已有机制（修复而非替换）**

- `skills/guide-design/scripts/approve_proposal.sh` 现有 4 个 bats 测试（`test_strict_human_approval.bats`）锁定 exit-3 行为
- `skills/_lib/cross_repo_audit.py` 模块 + 单元测试（`tests/unit/test_cross_repo_audit.py`）就绪
- `skills/_lib/gh_hub_client.py::get_issue_status` 已实现（本次修复需接线而非新增）

## 范围

**In Scope**:

- **改 category 检测源 SSOT**：`approve_proposal.sh:51-58` 改读 `.rddf/improvements/<name>.md` 的 `**分类**:` 字段（移除 roadmap-meta.yaml fallback 依赖）
- **`read -s` username 接入**：`--manual` 模式在 accept 前用 `read -rp 'GitHub username: ' username` 强制非空输入；超时 30s 默认拒绝
- **audit 写入接线**：approve accept 路径前调用 `cross_repo_audit.append_audit_log_entry(actor=username, decision=...)`
- **`RDDF_REQUIRE_HUB_APPROVAL` 实际读取**：env var=yes 时升级 `--manual` 为强制（即使 prompt 输入 y 也需 Hub Issue re-fetch 通过）
- **Hub Issue re-fetch**：批准前 `gh_hub_client.get_issue_status(hub_repo, issue_num)` 必须返回 `state=open` 且 label 含 `approved`；offline fallback 写 warning 而非 fail-open
- **更新 bats 测试**：补 5 个新 case（fail-open 防御 / username 强制输入 / audit 写入 / env var 升级 / hub re-fetch 失败路径），总计 9 个 case
- **更新现有 AC 文档**：将 `add-strict-human-approval-for-cross-repo-changes` 的"已交付"清单逐项据实修正
- **ADR-0031 文本同步**（A2-3 子步骤）：修订 §实现细节 与本次实际实现对齐, 随后翻转 `状态: 待定 → 已采纳`

**Out Scope**:

- **不修改** non-cross-repo 提案审批流程（保留现有 `y/N` 交互）
- **不创建** 新的人类介入模式（Human-in-Loop 节点类型不变）
- **不实现** Hub 端人类兜底机制（属于 Hub Repo 自身 ADR）
- **不重写** `cross_repo_audit.py` 模块本体（仅接线）
- **不改动** `tests/unit/test_cross_repo_audit.py` 既有单测

## 关键场景

### 场景 1 — fail-open 防御（首批准）

```bash
# 修复前: 失败
$ bash skills/guide-design/scripts/approve_proposal.sh cross-repo-rfc-001 \
    --auto-accept
# ⚠️  当前: change dir 不存在 → roadmap-meta.yaml 不存在 →
#    is_cross_repo_proposal() 返回 false → gate 跳过 → exit 0
# ✅  修复后: 改读 .rddf/improvements/cross-repo-rfc-001.md → 命中
#    **分类**: cross-repo-federation → 触发 exit 3 硬阻断
```

### 场景 2 — `--manual` 强制人类 username

```bash
$ bash skills/guide-design/scripts/approve_proposal.sh cross-repo-rfc-001 \
    --manual --hub-issue "org/rdd-hub#42"
GitHub username: 
# ⚠️  当前: 无 prompt, 直接 accept, 无 audit
# ✅  修复后: 超时 30s 无输入 / 空输入 → exit 4;
#    有效输入 → audit log 写入 actor=$username, 然后 accept
```

### 场景 3 — `RDDF_REQUIRE_HUB_APPROVAL=yes` 升级为强制

```bash
$ RDDF_REQUIRE_HUB_APPROVAL=yes bash skills/guide-design/scripts/approve_proposal.sh \
    cross-repo-rfc-001 --manual --hub-issue "org/rdd-hub#42"
# ✅  修复后: 即使 username 已输入, 必须 Hub Issue re-fetch 返回 approved
#    否则 exit 5（独立 env var error code）
```

### 场景 4 — Hub Issue race condition 防护

```bash
# Hub Issue 状态本地缓存 vs 实际不一致
$ bash skills/guide-design/scripts/approve_proposal.sh cross-repo-rfc-001 \
    --manual --hub-issue "org/rdd-hub#42"
# ✅  修复后: 批准前 gh api 拉取 issue, state=closed 或 label 缺失 → exit 6;
#    network 错误 → 写 warning 但 exit 0（fail-open 仅对 network）
```

### 场景 5 — audit log 实际写入

```bash
$ bash skills/guide-design/scripts/approve_proposal.sh cross-repo-rfc-001 \
    --manual --hub-issue "org/rdd-hub#42" < <(echo "alice")
# ✅  修复后:
#    .rddf/state/.cross-repo-audit.jsonl 追加新行：
#    {"ts": "...", "actor": "alice", "proposal": "cross-repo-rfc-001",
#     "hub_issue": "org/rdd-hub#42", "decision": "approve",
#     "hub_state": "open", "hub_labels": ["approved", "rfc"]}
```

## 技术约束

1. **SSOT 单一来源**: category 字段从 `.rddf/improvements/<name>.md` 的 `**分类**:` 解析（移除 roadmap-meta.yaml fallback）
2. **顺序保证**: read username → audit 写入 → hub re-fetch → accept（任一步失败则拒绝, audit 记录 `decision=fail`）
3. **Offline 行为**: Hub re-fetch network 错误时 fail-open + warning（仅 network 类, 非 auth 类）
4. **锁定**: 既有 4 个 bats 测试必须继续通过；新增 5 个 case 总计 9 个
5. **CI 兼容**: `read -s` 在非交互终端需 fallback（用 `RDDF_APPROVE_ACTOR` env var）
6. **审计完整性**: audit write 在 accept 前同步执行, crash-safety 由 atomic_write 模式保证
7. **Bash 版本兼容**: 不引入 bash 4+ 特性（项目既有 bash 3.2+ 兼容约束）
8. **rddf-session 集成**: ADR-0031 第 4 项引用 ADR-0017 §4 实际上是 State Machine 节（Oracle 发现误引），不作为本次修复 scope

## 验收标准

- [ ] `tests/integration/test_strict_human_approval.bats` 新增 5 个 case，总计 9 个 case 全绿
- [ ] **fail-open 防御**: 测试场景 1 中 `--auto-accept` 在首次调用时必须 exit 3（不依赖 change dir 存在）
- [ ] **username 强制**: 测试场景 2 中空 stdin / 30s timeout 必须 exit 4
- [ ] **env var 升级**: 测试场景 3 中 `RDDF_REQUIRE_HUB_APPROVAL=yes` + username + hub approved label → accept；缺 label → exit 5
- [ ] **hub re-fetch**: 测试场景 4 中 issue closed → exit 6；network error → exit 0 + warning
- [ ] **audit 写入**: 测试场景 5 中 accept 后 `.cross-repo-audit.jsonl` 含新行（含 actor / hub_state / hub_labels / decision）
- [ ] **既有回归**: `tests/unit/test_cross_repo_audit.py` 全绿, `tests/unit/test_approve_proposal*.py` 全绿
- [ ] **全量回归**: `./test.sh --full --regression` 通过（无新增失败）
- [ ] **ADR-0031 修订**: 状态 `待定 → 已采纳`, §实现细节与本次实际代码一致
- [ ] **AC 文档同步**: `2026-08-16-add-strict-human-approval-for-cross-repo-changes` 的 AC 清单据实修正, 不再声称 5/5 实现
- [ ] **Audit trail**: `.rddf/state/.cross-repo-audit.jsonl` 经端到端测试后**非空**（验证 dead-code 修复）
