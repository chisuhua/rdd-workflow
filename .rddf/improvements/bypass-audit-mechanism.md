# bypass-audit-mechanism

**优先级**: P2 | **来源**: 2026-08-26 文档与代码一致性审计 + 流程治理 review
**阶段**: default | **分类**: governance
**类型**: feature
**状态**: 已推迟

## 架构依据

rdd-workflow 设计了多条"紧急跳过"旁路以应对 hotfix / 网络故障 / 紧急 archive 场景：

| 旁路 | 触发 | 文档位置 |
|------|------|----------|
| `SKIP_RDD_VERIFIER=yes` + `RDDF_VERIFIER_BYPASS_REASON` | archive 前跳过 AC 验证 | ADR-0034 §3.1 |
| `SKIP_HUB_CHECK=true` | design-done 跳过 Hub 检查 | README §"跨项目协同" |
| `tools/archive_on_main.sh --confirm-main` | 在 main 分支直接 archive | USAGE.md §"On-main Mode Caveats" |
| `SKIP_*_GATE` 系列（`SKIP_DESIGN_GATE`, `SKIP_ARCH_GATE`, `SKIP_DEPS_GATE`, `SKIP_AC_GATE`, `SKIP_CONTRACT_GATE`, `SKIP_PROPOSAL_COVERAGE`） | 跳过对应门控 | 散落各 ADR |

设计意图是"紧急情况下可绕过，但留 audit trail"。**当前问题**：

1. **缺乏集中审计**：每个旁路单独 append log，跨旁路无法聚合（`SKIP_RDD_VERIFIER` 写 `verifier/<change>.audit.jsonl`；`SKIP_HUB_CHECK` 写 `.cross-repo-audit.jsonl`；`archive_on_main` 写 stdout；其他 SKIP_*_GATE 仅 stderr warning）
2. **缺使用频率统计**：rdd-doctor 无 `bypass-audit` category；开发者无法自检"本月绕过 5 次 archive 是常态"
3. **缺阈值告警**：每月 `tools/archive_on_main.sh` 用 10 次 vs 1 次应该有不同 severity

## 范围

**In Scope**:
- 新建 `.rddf/state/.bypass-audit.jsonl` 统一 audit log（append-only）
- 所有旁路入口（`_lib/archive.sh` / `skills/guide-design/scripts/approve_proposal.sh` / `tools/archive_on_main.sh` / `_lib/rdd_verifier/` 等）增加 1 行 audit append
- 新增 `bash skills/rdd-doctor/scripts/doctor.sh --category bypass-audit` 报告本月 / 本季使用次数 + 阈值告警
- 阈值规则（可由 `STRICT_BYPASS_AUDIT=yes` 升级为阻断）：
  - 每月 archive_on_main 次数 > 3 → WARNING
  - 每月 SKIP_RDD_VERIFIER 次数 > 5 → WARNING
  - 任意 SKIP_*_GATE 次数 > 10/月 → WARNING
  - 任意 bypass 次数 > 20/月 → CRITICAL

**Out of Scope**:
- 移除任何旁路（保持 hotfix 能力）
- 跨项目 bypass 聚合（属 ADR-0027 L2 上报通道）
- 自动阻止（仅 WARNING；阻断由 follow-up 提案处理）

## 设计

### 统一 audit log schema

`.rddf/state/.bypass-audit.jsonl`（每行一个事件）：

```json
{
  "ts": "2026-08-26T...",
  "env_var": "SKIP_RDD_VERIFIER",
  "change": "my-change-name",   // 可选
  "reason": "hotfix for prod incident #123",
  "actor": "sisyphus",          // git config user.name 或 CI bot
  "codebase_commit": "abc1234",
  "scope": "verifier|design-gate|archive-on-main|cross-repo|..."
}
```

### 旁路入口集成

`_lib/archive.sh`（`SKIP_RDD_VERIFIER` 旁路）：

```bash
if [ "${SKIP_RDD_VERIFIER:-no}" = "yes" ]; then
  if [ -z "${RDDF_VERIFIER_BYPASS_REASON:-}" ]; then
    echo "❌ SKIP_RDD_VERIFIER requires RDDF_VERIFIER_BYPASS_REASON" >&2
    exit 3
  fi
  # Append audit
  audit_bypass_log "SKIP_RDD_VERIFIER" "${RDDF_VERIFIER_BYPASS_REASON}" "$CHANGE_NAME"
  # ... 现有 bypass 逻辑
fi
```

`tools/archive_on_main.sh`：

```bash
audit_bypass_log "ARCHIVE_ON_MAIN" "用户显式 --confirm-main" "$1"
```

新增 `_lib/bypass_audit.sh` helper：

```bash
audit_bypass_log() {
  local env_var="$1"
  local reason="$2"
  local change="${3:-}"
  local scope="${4:-unknown}"
  local audit_file=".rddf/state/.bypass-audit.jsonl"
  
  mkdir -p "$(dirname "$audit_file")"
  jq -n -c \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg env_var "$env_var" \
    --arg reason "$reason" \
    --arg change "$change" \
    --arg actor "$(git config user.name 2>/dev/null || echo 'unknown')" \
    --arg commit "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
    --arg scope "$scope" \
    '{ts: $ts, env_var: $env_var, reason: $reason, change: $change, actor: $actor, codebase_commit: $commit, scope: $scope}' \
    >> "$audit_file"
}
```

### rdd-doctor bypass-audit category

```python
# _lib/bypass_audit_doctor.py
def run() -> list[dict]:
    issues = []
    audit = Path(".rddf/state/.bypass-audit.jsonl")
    if not audit.exists():
        return issues
    
    events = [json.loads(line) for line in audit.read_text().splitlines() if line]
    
    # 按 env_var 聚合本月
    month = datetime.now().strftime("%Y-%m")
    by_env = defaultdict(int)
    for e in events:
        if e["ts"].startswith(month):
            by_env[e["env_var"]] += 1
    
    thresholds = {
        "ARCHIVE_ON_MAIN": 3,
        "SKIP_RDD_VERIFIER": 5,
    }
    default_threshold = 10
    
    for env_var, count in by_env.items():
        limit = thresholds.get(env_var, default_threshold)
        if count > limit:
            severity = "CRITICAL" if count > limit * 2 else "WARNING"
            issues.append({
                "severity": severity,
                "name": f"bypass-{env_var}-freq",
                "detail": f"本月 {env_var} 旁路使用 {count} 次（阈值 {limit}）",
                "fix_command": "考虑是否应修复根本问题，去掉旁路",
            })
    return issues
```

CLI 集成：

```bash
bash skills/rdd-doctor/scripts/doctor.sh --category bypass-audit
# 输出：
# ⚠️  bypass-ARCHIVE_ON_MAIN-freq: 本月 ARCHIVE_ON_MAIN 旁路使用 4 次（阈值 3）
# ℹ️  bypass-SKIP_RDD_VERIFIER-freq: 本月 SKIP_RDD_VERIFIER 旁路使用 2 次（阈值 5）
```

## 影响

- **正向**：bypass 使用有"集中审计 + 月度统计 + 阈值告警"，防止旁路常态化
- **正向**：与 ADR-0027 continuous evolution 反馈环对齐（bypass 异常 → L2 上报）
- **风险**：每个旁路入口多 1 行 audit append，对 hotfix 路径增加 ~5ms 延迟（可接受）
- **兼容性**：纯增量，旁路仍可正常使用

## 验收

- [ ] `_lib/bypass_audit.sh::audit_bypass_log` 实现
- [ ] `.rddf/state/.bypass-audit.jsonl` 在 SKIP_RDD_VERIFIER / archive_on_main 触发后写入
- [ ] `_lib/bypass_audit_doctor.py` 实现月度统计
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category bypass-audit` 输出当前统计
- [ ] `tests/unit/test_bypass_audit.py` 5+ 个 unit test PASS
- [ ] `tests/integration/test_bypass_audit.bats` 3+ 个 integration test PASS
- [ ] AGENTS.md line 535-540 紧急跳过指引更新（指向 audit log）
- [ ] USAGE.md "On-main Mode Caveats" 章节末尾添加 audit 提醒
- [ ] STRICT_BYPASS_AUDIT=yes 升级为阻断的 follow-up 提案