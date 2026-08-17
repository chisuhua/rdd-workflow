# complete-add-cross-repo-deps-orchestration — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [ ] 1.1 创建 `_lib/cross_repo_gate.py`(新文件,避免污染 `cross_repo_deps.py` 纯算法模块)
  - 主函数: `check_cross_repo_deps_blocked(project_root: str, spokes_key: str) -> List[str]`
  - 内部步骤:
    1. `from skills._lib.cross_repo_deps_cache import load_cache, save_cache, is_cache_valid`
    2. 若 `is_cache_valid(<project_root>/.rddf/state/.cross-repo-deps-cache.json, spokes_key)` → `load_cache()` 返回
    3. 否则 → 调 `kahn_topological_sort(build_cross_repo_graph(spokes_data))` 重算 + `save_cache()` 写盘
  - 输出格式: 返回 `List[str]`,每条形如 `"<change-name>: blocked by <spoke-repo>"`(空列表 = 无 blocker)
  - 不读 env var(env var 由 `plan_done_gate.sh` 消费,本函数只输出 blocker 列表)
- [ ] 1.2 在 `skills/guide-plan/scripts/plan_done_gate.sh` 实现 `STRICT_DEPS_GATE` 接线
  - 位置: line 146 之后(`STRICT_CHANGE_GATE` 检查 + `STRICT_CONTRACT_GATE` 调用之后)
  - 函数体(默认 warning):
    ```bash
    if [ "${SKIP_DEPS_GATE:-no}" = "yes" ]; then
      echo "[SKIP] cross-repo deps gate skipped"
      return 0
    fi
    blockers=$(python3 -c "
    import os, sys
    sys.path.insert(0, '$PROJECT_ROOT')
    from skills._lib.cross_repo_gate import check_cross_repo_deps_blocked
    blockers = check_cross_repo_deps_blocked('$PROJECT_ROOT', spokes_key='default')
    sys.exit(0 if not blockers else 1)
    " 2>&1) || blockers_rc=$?
    if [ "${blockers_rc:-0}" -ne 0 ]; then
      if [ "${STRICT_DEPS_GATE:-no}" = "yes" ]; then
        echo "❌ STRICT_DEPS_GATE: cross-repo deps blocker detected" >&2
        echo "$blockers" >&2
        return 1
      fi
      echo "⚠️ cross-repo deps blocker: $blockers" >&2
    fi
    ```
  - 现有 plan quality checks 不受影响
- [ ] 1.3 新增 `tests/unit/test_cross_repo_gate.py`(5 个关键路径)
  - Case 1 (无 blocker): mock `load_cache` 返回 `{"blockers": []}` → `check_cross_repo_deps_blocked()` 返回 `[]`
  - Case 2 (单 blocker): mock `load_cache` 返回 `{"blockers": [{"change": "change1", "spoke": "org/foo"}]}` → 返回 `["change1: blocked by org/foo"]`
  - Case 3 (跨仓库 chain): mock 3 change 跨仓库依赖链 A→B→C → 返回所有 chain 节点
  - Case 4 (cycle-detect): mock 循环依赖 A↔B → 返回 `["⚠️ cycle detected: A -> B -> A"]` + cycle 路径字符串
  - Case 5 (cache-hit): mock `is_cache_valid` 返回 True → 第二次调用不调 `kahn_topological_sort`(用 `unittest.mock.patch` 验证)
- [ ] 1.4 新增 `tests/integration/test_strict_deps_gate_wiring.bats`(≥3 用例)
  - Case 1: 默认 warning — mock blocker + 无 `STRICT_DEPS_GATE` → `plan_done_gate` exit 0 + stderr warning
  - Case 2: STRICT 升级 — `STRICT_DEPS_GATE=yes` + blocker → exit 1 + stderr "❌ STRICT_DEPS_GATE"
  - Case 3: SKIP 跳过 — `SKIP_DEPS_GATE=yes` + blocker → exit 0,无任何输出
- [ ] 1.5 README.md §跨项目协同 章节末尾新增 `### 跨仓库依赖示例` 子节(≥15 行)
  - 命令示例: `rddf deps cross-repo --spokes org/foo,org/bar`
  - Mermaid 图示例(独立 change 用 `subgraph`, 依赖用 `-->`, 冲突用 `-.->|冲突|`)
  - 推荐顺序表格(name / status / parallel_group / blocker)
  - `STRICT_DEPS_GATE=yes` 启用示例:
    ```bash
    export STRICT_DEPS_GATE=yes
    skill_use("guide-plan")  # 触发 plan_done_gate
    # 遇到跨仓库 blocker 时 plan-done 被阻断,stderr 输出 ❌ STRICT_DEPS_GATE
    ```
  - 紧急跳过: `export SKIP_DEPS_GATE=yes` 后 plan-done bypass cross-repo gate
- [ ] 1.6 验证现有 cross-repo deps 测试保持 pass(无 regression)
  - `tests/unit/test_cross_repo_deps.py` 14 个测试保持 pass
  - `tests/unit/test_cross_repo_deps_cache.py`(若有)测试保持 pass
  - 验证 `cross_repo_deps.py::kahn_topological_sort` 算法本身未被本提案修改
- [ ] 1.7 手工验证
  - 设置 `STRICT_DEPS_GATE=yes` 后跑 `guide-plan` plan-done 阶段,遇到跨仓库 blocker 时退出码非零
  - 未设置 `STRICT_DEPS_GATE` 时 exit 0 + warning
  - `SKIP_DEPS_GATE=yes` 时 exit 0,无 warning
  - 缓存命中验证: 第一次 plan-done 触发计算 → 第三次 plan-done 命中缓存(可通过 mock 验证或 timing test)
  - README 示例验证: 复制示例 `rddf deps cross-repo --spokes X,Y` 命令可在任意第三方项目目录运行