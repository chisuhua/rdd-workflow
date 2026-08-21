## Implementation Tasks

> 任务编号沿用 `proposal.md` §范围 A-F + 测试场景 T1-T18 编号。**checkboxes 是契约**：执行者按序勾选，全部勾完才能进 archive 阶段。

### A. 共享扫描层 ADR 元数据

- [ ] A1. 创建 `skills/_lib/adr_catalog.py` 文件骨架，含 `AdrMeta` dataclass（fields: `adr_id`, `file_path`, `file_hash`, `title`, `status`, `phase`, `category`）
- [ ] A2. 实现 `scan_adr_catalog(project_root: Path) -> dict[str, AdrMeta]`，扫 `docs/adr/ADR-*.md`，sha256 file_hash，解析 frontmatter + 状态段
- [ ] A3. 修改 `skills/populate-roadmap-from-arch/scripts/populate_lib.py::catalog_sources()` 改为 wrapper：保留原签名（向后兼容），内部 `from _lib.adr_catalog import scan_adr_catalog`
- [ ] A4. 验证现有 4 个 v1.1 unit tests + 5 个 bats tests 仍通过（catalog_sources 行为不变）

### B. State schema v2

- [ ] B1. 创建 `skills/_lib/schemas/populate_state_schema.json`，顶层 `{version: {const: 2}}`，字段：`generated_at`, `codebase_commit`, `codegraph_fingerprint` (optional), `adrs[adr_id]`, `reverse_index`, `phases[phase_id]`
- [ ] B2. 更新 `tests/unit/test_schema_version_field.py` 列表加入 populate_state_schema（20 → 21 schemas）
- [ ] B3. 验证 schema JSON 合法（`python3 -c 'import json; json.load(open(...))'`）且顶层 version const=2

### C. populate_lib.py 7 个新函数

- [ ] C1. `load_populate_state_or_default(project_root)`：读 `.rddf/state/.populate-state.json`，schema 校验失败返回 None
- [ ] C2. `save_populate_state(state, project_root, codebase_commit)`：atomic write（tempfile + os.replace）
- [ ] C3. `detect_adr_changes(state, project_root, scan_adr_catalog_fn)`：返回 `(changed: list[adr_id], new: list, deleted: list)`，基于 file_hash 对比
- [ ] C4. `detect_code_changes(state, project_root)`：返回 `(changed_symbols: set, changed_files: list, status: str)`，调 git diff + rg 扫符号；codegraph signal 只读 env var `RDDF_CODEGRAPH_FINGERPRINT`，不调 MCP
- [ ] C5. `decide_update_mode(adr_changes, code_changes)`：返回 `(mode: str, reason: str, extra: Any)`，mode ∈ {skip, adr_only, code_only, full}
- [ ] C6. `select_adrs_for_incremental_verify(adrs, state, mode, extra)`：返回 `(to_verify: list, to_reuse: dict)`
- [ ] C7. `should_rewrite_phase_fragment(phase_id, prev_state, new_state, mode)`：返回 bool
- [ ] C8. 把 7 个新函数加入 `__all__`
- [ ] C9. 验证现有 25 + 12 = 37 个 v1.1 unit tests 仍通过（不破坏 v1.1 行为）

### D. guide-arch 集成脚本（3 文件 split，Oracle C1 env-var 模式）

- [ ] D1. 创建 `skills/guide-arch/scripts/roadmap_incremental_update.sh`（sh wrapper）：env var 装填 + Python 调用 + stderr 重定向
- [ ] D2. 创建 `skills/guide-arch/scripts/roadmap_incremental_update.env.py`：env var 校验（Oracle C1：消除 bash `$VAR` 字符串注入）
- [ ] D3. 创建 `skills/guide-arch/scripts/roadmap_incremental_update.py`：主模块，调 populate_lib.py 的 7 个新函数，实现四模式算法
- [ ] D4. sh wrapper 调用顺序固定：`save_supplementary` → `save_populate_state`（crash 安全）
- [ ] D5. 验证 bats 测试 `tests/integration/test_roadmap_incremental_update.bats` 通过

### E. guide-arch SKILL.md 修改

- [ ] E1. Phase 6 (arch-done exit) 内部新增 Step: Roadmap Sync，位置在写 handoff 之前
- [ ] E2. frontmatter `role.boundaries.owns` 加入 `.rddf/state/.populate-state.json` 和 `.rddf/roadmap/phases/*.md`（ADR-0028 边界修正）
- [ ] E3. 不修改 Phase 5 双重门控（ADR ≥ 1 + roadmap.md 存在）；roadmap-up-to-date 仅作为 warning 写入 `.arch-quality-report.json`
- [ ] E4. 验证现有 `tests/integration/test_guide_arch_skill.bats` 仍通过

### F. populate-roadmap-from-arch 重构

- [ ] F1. SKILL.md frontmatter `version: 1.2`，加 `evolved-from: populate-roadmap-from-arch`
- [ ] F2. SKILL.md 顶部加 deprecation banner："本 skill 在 v2.3+ 将被 guide-arch 内置功能取代，新项目请直接调 guide-arch"
- [ ] F3. SKILL.md troubleshooting 节加一行 reset 命令 `rm .rddf/state/.populate-state.json`（无 baseline → 下次 full）
- [ ] F4. `scripts/populate.sh` 改为 thin wrapper：不写 Step 1.5 编排，直接 `source $RDDF_GUIDE_ARCH_SCRIPTS/roadmap_incremental_update.sh` 或调 Python 入口
- [ ] F5. 保留 CLI 兼容性：`--code-verify=off|on|strict` + 新增 `--incremental`（默认 on）+ `--standalone`（标记 deprecated path）
- [ ] F6. 验证现有 5 个 bats tests + 25 unit tests 仍通过（v1.1 行为保持）

### G. 测试覆盖（T1-T18）

- [ ] **T1**: 两方皆不变（state 存在，ADR 未改，HEAD 未变） → mode=skip → exit 0 + stderr "No changes"
- [ ] **T2**: 仅 ADR 改（改 ADR-0001 一行） → mode=adr_only → 仅重写 1 个 phase fragment
- [ ] **T3**: 仅代码改（改 skills/guide/SKILL.md） → mode=code_only → 仅重跑受影响 ADR
- [ ] **T4**: 两方都改 → mode=full
- [ ] **T5**: 新增 ADR-0099.md → mode=adr_only → 新 ADR 入 state + 对应 phase 重生成
- [ ] **T6**: 删除 ADR-0001.md → mode=adr_only → 对应 phase 重生成（移除引用）
- [ ] **T7**: 无 baseline（state.json 不存在） → mode=full
- [ ] **T8**: codegraph 不可用（`RDDF_CODEGRAPH_FINGERPRINT=stale`） → mode=full + stderr warning
- [ ] **T9**: v1 state 文件存在（schema 不匹配） → mode=full（自动 rebuild）
- [ ] **T10**: guide-arch Phase 6 自动调用链路 → arch-done 后 state.json 必更新
- [ ] **T11**: `--roadmap-update=off` 完全跳过 → populate 不写 state
- [ ] **T12**: `--roadmap-update=force` 跳过增量判定 → 总是 full mode
- [ ] **T13**: force-push 后 last_commit 不存在（`git_commit_exists=false`） → mode=full + stderr warning + exit 0
- [ ] **T14**: rebase 后 `last_commit..HEAD` range 仍有效 → 不 crash（mode 任意），exit 0
- [ ] **T15**: cherry-pick 后 → exit 0 + state 重写
- [ ] **T16**: merge commit 后续跑 → code_only 过度触发（保守正确），exit 0
- [ ] **T17**: worktree 内首跑（无 state） → mode=full，exit 0
- [ ] **T18**: 切 worktree 后 state mismatch → mode=full（自动 reset codebase_commit）

### H. 文档

- [ ] H1. `AGENTS.md` "常见陷阱" 节增 3 条：
  - "切分支/切 worktree 后第一次 arch-done 自动 fallback full（per-worktree state 隔离）"
  - "codegraph signal 必须由 agent 侧通过 RDDF_CODEGRAPH_FINGERPRINT env var 注入，Python 内部不能调 MCP"
  - "reset roadmap 增量 state：`rm .rddf/state/.populate-state.json`（无 baseline → 下次 full）"
- [ ] H2. `docs/proposal-suggestions-format.md` 加 v2 schema 示例
- [ ] H3. `README.md` "v2.2 新特性" 节加 roadmap incremental 节

### I. 测试基础设施

- [ ] I1. 创建 `tests/unit/test_populate_lib_incremental.py`，≥ 18 个测试覆盖 T1-T9 + T13-T16
- [ ] I2. 创建 `tests/integration/test_roadmap_incremental_update.bats`，≥ 12 个 @test（T10-T12 + T17-T18 + 跨调用链路）
- [ ] I3. 验证 `tests/unit/test_schema_version_field.py` 列表 21 个 schemas
- [ ] I4. 验证所有现有测试通过（baseline: 2018 passed / 4 pre-existing failures unrelated）

### J. Archive 前全量回归（MANDATORY）

- [ ] J1. 跑 `./test.sh --full --regression`，确认 0 新增失败（已知失败在 `tests/KNOWN_FAILURES.txt` baseline 中）
- [ ] J2. 性能实测：T1 < 0.1s / T2 < 1s / T3 < 1.5s / T13/T17/T18 < 4s（fallback full）
- [ ] J3. 手动验证：`rm .rddf/state/.populate-state.json` 后再跑 → mode=full，stderr warning
- [ ] J4. worktree 内 commit + archive（按 `AGENTS.md` "Worktree Commit Flow" 三段式：execute → worktree-internal commit → archive）