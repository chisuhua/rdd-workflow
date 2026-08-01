# refine-plan-openspec-integration — Design

## Context

openspec v1.7.0 原生提供工件级 DAG（`status --json` 的 `artifacts[].requires`/`missingDeps`/`applyRequires`，Kahn 拓扑）、逐 artifact 的 `instructions --json` 模板、`validate --strict --json`（14 项 delta 校验）、`skip_specs: true` 零 delta 支持。guide-plan 目前硬编码 fill 顺序、propose 的 instructions 循环是伪代码、doc-only/test-only 用自建规避。change 级 DAG 上游未发布，deps skill/manual_deps/ADR-0022/ADR-0024 全部保留自建。

## Goals / Non-Goals

**Goals:**
- fill 由 `openspec status --json` 工件 DAG 驱动（applyRequires 传递闭包 + 拓扑序 + ready/blocked 感知）
- propose instructions 循环实装（伪代码清零）
- plan-done 增加 `status --json isComplete` 校验（不重复 ADR-0015 的 strict validate）
- doc-only/test-only change 使用 `skip_specs: true`
- CLI ≥1.7.0 版本约束 + <1.7.0 graceful degradation

**Non-Goals:**
- 不动 deps skill 输入输出 / manual_deps / ADR-0024 execution_mode
- 不 fork openspec schema；不实装上游 add-change-stacking-awareness
- 不改 guide-design / guide-ship 的 openspec 调用

## Decisions

- **D1 — 传递闭包计算**：从 `status --json` 的 `applyRequires` 出发，沿每个 artifact 的 `requires` 边递归展开得到必需集合（v1.7.0 changelog 明确修复过只查根节点导致无 delta specs 时错误进入 apply 的问题）。实现为一个纯函数 `compute_required_artifacts(status_json)`，可注入伪 status JSON 单测。
- **D2 — fill 执行模型**：循环 `status --json` → 取 status=ready 且未完成的 artifact（按返回数组拓扑序）→ 调 `instructions <artifact> --json` → 写入 → 重查 status。blocked 工件自然在其依赖完成后变 ready，无需手工排序。custom schema 天然兼容。
- **D3 — 版本检测与降级**：intake 时解析 `openspec --version`；<1.7.0 输出升级 warning 并设置 `OPENSPEC_DAG_AVAILABLE=false`，fill 回退现行硬编码 design→tasks 路径。不硬失败。
- **D4 — skip_specs 判定**：复用 `roadmap-meta.yaml` 的 `change_type`（doc-only / test-only → 写 `skip_specs: true` 到 `.openspec.yaml`），逻辑挂 `infer_change_type.py` 既有判定之后，单一事实源。
- **D5 — isComplete 校验位置**：`plan_done_gate.sh` 在既有 ADR-0015 validate 持久化循环内追加 `status --json` 调用，`isComplete=false` 记 warning（初版不阻断，避免与 skeleton/planned 语义冲突；strict 化另议）。

## Risks / Trade-offs

- **openspec CLI 版本碎片化**：用户环境 <1.7.0 时行为分裂 → D3 降级路径 + warning 显式告知；测试覆盖两条路径。
- **status --json 解析脆弱性**：只消费 `--json`（硬约束），字段缺失时按"无 DAG 信息"降级，不猜测。
- **与 move-proposal-creation-to-design 的交互**：①预建的完整 proposal 在 DAG 中显示 done，fill 自然跳过——两 change 顺序执行（①→②）避免同文件并发修改。

## Migration Plan

1. 版本约束升级 + 降级路径（行为不变的安全第一步）
2. `compute_required_artifacts` + DAG-driven fill（注入式单测先行）
3. propose instructions 循环实装（删伪代码）
4. isComplete 校验 + skip_specs 接入
5. 文档同步（AGENTS.md / README）

## Open Questions

- isComplete 是否应升级为 plan-done 阻断项？（初版 warning；待实战观察 skeleton/planned 语义冲突后另议）
- 上游 add-change-stacking-awareness 发布后，manual_deps 迁移策略？（仅文档备注，本 change 不实施）
