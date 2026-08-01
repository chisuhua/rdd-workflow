# refine-plan-openspec-integration — Tasks

## 1. 版本约束与降级路径

- [ ] 1.1 写失败测试：CLI 版本解析（1.4.1 → 降级；1.7.0 → DAG 可用）
- [ ] 1.2 `package.json` engines.openspec-cli 升级 `>=1.7.0`；AGENTS.md / README 同步
- [ ] 1.3 guide-plan intake 增加版本检测 + `OPENSPEC_DAG_AVAILABLE` 标记 + 升级 warning

## 2. DAG 驱动的 fill

- [ ] 2.1 写失败测试：`compute_required_artifacts(status_json)` 传递闭包（applyRequires 根 + requires 边递归；注入伪 status JSON）
- [ ] 2.2 新增 `skills/guide-plan/scripts/artifact_dag.{sh,py}`：闭包计算 + ready/blocked 感知 + 拓扑序
- [ ] 2.3 `skills/guide-plan/SKILL.md` Phase 2.5 fill 改为 DAG 驱动循环（status → ready artifact → instructions → 写入 → 重查）；`OPENSPEC_DAG_AVAILABLE=false` 时回退硬编码路径
- [ ] 2.4 bats 集成测试：注入伪 status 验证 fill 顺序 + blocked 工件等待依赖

## 3. propose instructions 循环实装

- [ ] 3.1 移除 `skills/propose/SKILL.md` 548-563 行 HALF-IMPLEMENTED 伪代码
- [ ] 3.2 `skills/propose/scripts/propose_change.{sh,py}` 实装全 artifact instructions 循环（复用 `artifact_dag` 模块）

## 4. plan-done 增强与 skip_specs

- [ ] 4.1 写失败测试：`status --json isComplete=false` 时 plan-done 输出 warning
- [ ] 4.2 `skills/guide-plan/scripts/plan_done_gate.sh` 在 ADR-0015 validate 循环内追加 isComplete 校验（warning 级）
- [ ] 4.3 `skills/propose/scripts/infer_change_type.py` 下游接入：doc-only/test-only → `.openspec.yaml` 写 `skip_specs: true`
- [ ] 4.4 e2e：doc-only change 从创建到 `openspec validate --strict` 通过

## 5. 回归与文档

- [ ] 5.1 deps skill / manual_deps / ADR-0024 相关测试无回归
- [ ] 5.2 deps 文档备注上游 add-change-stacking-awareness（未来 manual_deps 迁移候选）
- [ ] 5.3 全量测试：pytest tests/unit + tests/integration + bats tests/ 全绿（含恒真断言门控）
