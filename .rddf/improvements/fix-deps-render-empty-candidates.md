# fix-deps-render-empty-candidates

**优先级**: P2 | **来源**: 2026-07-27 会话复盘
**阶段**: default | **分类**: core-impl
**类型**: bug

## 架构依据

- `deps_render_report.sh` 的契约：通过 env var `$CANDIDATES` 接收变更候选列表（第 33 行）
- `deps.md` Step 0 用 `mapfile -t CANDIDATES` 生成 bash 数组，但该变量通过 skill_use 加载时不受 export 保护
- `deps-candidates.json` 是权威数据源（已由 Step 0 写入），但渲染函数未使用它作为回退
- 参照 ADR-0016 的回退模式（handoff 缺失时回退默认值）

## 范围

- **In Scope**:
  - `deps_render_report.sh` 第 35-37 行的回退逻辑改为优先 env var CANDIDATES，空时回退读取 `.rddf/state/.deps-candidates.json`

- **Out Scope**:
  - 不修改 `deps.md` 的数组生成逻辑
  - 不改变 env var 传递契约（改渲染侧不改调用侧）
  - 不修改 `deps_output.py` 的 Python 渲染逻辑

## 关键场景

- GIVEN `.rddf/state/.deps-candidates.json` 含 1 个候选 change
  WHEN `render_deps_report` 被调用但 CANDIDATES env var 为空
  THEN 回退读取 JSON 文件，输出 `候选 changes: 1`

- GIVEN CANDIDATES env var 已正确设置
  WHEN `render_deps_report` 被调用
  THEN 优先使用 env var（保持向后兼容，不引入竞态）

- GIVEN 既无 env var 也无 deps-candidates.json
  WHEN 渲染函数被调用
  THEN 输出 `候选 changes: 0`（与当前空列表行为一致，不误报）

- GIVEN deps-candidates.json 内容损坏（非合法 JSON）
  WHEN 回退读取
  THEN 静默降级为 []（不中断渲染流程）

## 技术约束

- **MUST**：env var 优先于 JSON 文件（向后兼容，不改变正常路径行为）
- **MUST**：JSON 读取失败不中断渲染（降级为空列表）
- **MUST**：仅修改 `deps_render_report.sh`，不触碰 `deps_output.py`
- **MUST NOT**：不修改 `deps.md` Step 0 的 `mapfile` 逻辑

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | CANDIDATES 为空时从 deps-candidates.json 读取候选列表 | bats 集成测试：预置 JSON 含 2 个候选，断言输出含 "候选 changes: 2" |
| 2 | CANDIDATES env var 非空时保持不变（优先 env var） | bats：设置 CANDIDATES env var，断言输出与 env var 一致 |
| 3 | deps-candidates.json 缺失或 corrupt 时降级为 [] | bats：删除 JSON 或写入非法内容，断言输出 "候选 changes: 0" |
| 4 | 现有 deps 测试全部通过 | `bats tests/integration/ -f deps` |
