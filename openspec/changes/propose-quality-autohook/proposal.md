# propose-quality-autohook

**Priority**: P0
**Phase**: v2.1
**Status**: skeleton

## Why

## 架构依据
- Oracle 审查结论: propose_quality_check.py 是 dead asset (5 项结构性检查存在但从未接入 propose 流程)
- 当前 propose 没有任何审查环节，低质量 proposal 直接进入 change pipeline
- 接入 plan_done gate 作为 warning 级 (STRICT_PROPOSE_GATE=yes 升级为 error)

## 范围
- **In Scope**:
  - propose.md Phase 4 末尾调用 propose_quality_check.py --change <name>
  - gate.py plan_done 注册 propose_quality_checks Check (warning 级)
  - 输出 warnings 不阻断流程
  - 对应 unit test
- **Out Scope**:
  - 不修改 propose_quality_check.py 的 5 项检查逻辑
  - 不引入新的检查项
  - 不做 content review (另见 add-propose-content-review)

## 关键场景
- GIVEN propose Phase 4 创建完 change artifacts, WHEN 自动触发 quality check, THEN 输出 5 项检查结果 (不阻断)
- GIVEN plan_done 阶段, WHEN STRICT_PROPOSE_GATE=yes, THEN quality check 失败时返回 error 阻断

## 技术约束
- MUST NOT 阻断默认流程 (warning 级)
- MUST 复用现有 propose_quality_check.py 的 run_all_checks()
- SHOULD 遵循 ADR-0007 gate 哲学: warning 不阻断, error 才阻断

## 验收标准
- propose 执行后终端输出 quality check 结果
- plan_done gate 含 propose_quality_checks Check
- STRICT_PROPOSE_GATE=yes 时检查失败返回非零
- 所有现有测试通过

## What Changes

- TODO: define specific changes during fill phase

## Impact

- Affected specs: TBD
- Affected code: TBD
