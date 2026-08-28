# ADR-0035: rdd-verifier ↔ archive_gate_check 双轨设计边界

> **状态**: 已采纳
> **日期**: 2026-08-28
> **决策者**: sisyphus
> **关联**: ADR-0034 (rdd-verifier 阶段架构), ADR-0027 (L2 上报)

## 背景

ADR-0034 §3 定义 rdd-verifier 为"条件必经"(默认必走,`SKIP_RDD_VERIFIER=yes` 跳过)。同时 §5 让 `archive_gate_check` 接受 archive 唯一条件:`verification.state ∈ (passed, bypassed) AND archive_ready == true`。

ADR-0034 §"中立"段保留 archive_gate_check 内嵌 ac-verifier 调用作为"fallback"——"用户绕过 rdd-verifier 直接 archive 时仍守门,且 fallback 写结构化 cache"。

这是**双轨设计**:

- **正常路径**: `rdd-verifier` → cache → `archive_gate_check` 读 cache 接受
- **fallback 路径**: 跳过 verifier → `archive_gate_check` 内嵌 `ac-verifier` → 写 cache (`ran_by=archive_gate_check`) → 接受

双轨设计的潜在问题:

1. **"绕过 verifier"被鼓励**:只要 `archive_gate_check` 内嵌 fallback 仍能完成 AC 验证,用户有 incentive 跳过 rdd-verifier(节省批量阶段的 token)
2. **fallback 仅单 change**:archive_gate_check 内嵌调用是 atomic,不支持批量,与 rdd-verifier 能力不对等
3. **状态机不明确**:当前 `verification.state = bypassed` 与 `verification.state = passed` 都允许 archive,但 bypass 没有"被 ac-verifier 实际校验过"的语义

## 4 个 Scenario 边界

### 场景 1(标准路径)

change 走 rdd-verifier 验证 → cache hit → archive 通过。

- `verification.state = passed`
- `verification.archive_ready = true`
- `verdict_sha` 绑定到当前 commit SHA

### 场景 2(fallback 路径)

change 跳过 rdd-verifier → archive_gate 内嵌 ac-verifier → cache 写 `ran_by=archive_gate_check` → archive 通过。

- `verification.state = bypassed`
- `verification.bypass_source = 'SKIP_RDD_VERIFIER'`
- `verification.archive_ready = true`

### 场景 3(halted)

change 在 rdd-verifier 中触发 max_loops → archive 阻断 (exit 4)。

- `verification.state = halted`
- `verification.archive_ready = false`
- `route = halted` → 人工 review

### 场景 4(on-main mode — 紧急 hotfix)

change 走 `tools/archive_on_main.sh --confirm-main`(与 verifier 无关, USAGE §"On-main Mode")。

- 跳过 verification 对象 (compat 模式)
- 仅 emergency, 不推荐

## 权衡:绕过 verifier

| 选项 | Token 节省 | 失败回环能力 |
|------|-----------|-------------|
| 走 rdd-verifier (场景 1) | 高 (批量 4+ change 时明显) | ✅ 完整 |
| 走 archive_gate fallback (场景 2) | 中 (省 rdd-verifier 阶段) | ⚠️ 单 change 失败回 plan/ship |
| 走 on-main mode (场景 4) | 最高 | ❌ 无 |

**建议**: 大型 release 走场景 1; 单 change hotfix 可走场景 2; 紧急 hotfix 走场景 4。

## STRICT_AC_GATE 升级

`STRICT_AC_GATE=yes` 强制 `SKIP_RDD_VERIFIER=yes` 失效 (fatal error, refuses to archive):

```
🚫 STRICT_AC_GATE active; SKIP_RDD_VERIFIER bypass refused
```

设置方法:

```bash
export STRICT_AC_GATE=yes   # CI / strict mode
unset STRICT_AC_GATE         # 默认 (warning only)
```

## 后续 follow-up

- 弃用 on-main mode (留作 v3.1 follow-up)
- rdd-verifier cache 加 SHA 指纹 (已有 per ADR-0034)

## 参考

- ADR-0034 §3 (rdd-verifier 阶段架构)
- ADR-0034 §5 (archive_gate_check acceptance 条件)
- ADR-0027 (L2 上报契约)
- docs/adr/ADR-0027-supersede.md (历史 ADR-0027 拆分)