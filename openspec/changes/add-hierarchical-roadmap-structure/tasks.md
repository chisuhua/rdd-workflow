## Implementation Tasks

### Change 1（hierarchical-roadmap-foundation）

- [ ] **T1**: 创建 `.rddf/roadmap/{phases,features,archive}/` 目录结构（`gitkeep` 占位）
- [ ] **T2**: bump ADR-0016 schema v2（`_lib/schemas/arch_handoff_schema.json` 加 `roadmap_fragments_dir: string` 字段）
- [ ] **T3**: 更新 `_lib/discover-arch-artifacts.sh` 默认候选（`.rddf/roadmap.md` 优先）+ 新增 `SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR` env var
- [ ] **T4**: 实现 `Fragment` dataclass in `_lib/roadmap_state.py`（8 字段：id, kind, status, phase_refs, theme, file_path, frontmatter, body）
- [ ] **T5**: 实现 `load_fragments`、`get_fragment`、`list_active_fragments` 三个聚合函数（读 `.rddf/roadmap/{phases,features}/`）
- [ ] **T6**: 实现 `render_fragment_index`（写 `<!-- AUTO-INDEX -->` sentinel 到主文档底部，原子化 tmp + rename）
- [ ] **T7**: 实现 `aggregate_phase_progress`（聚合主文档 + phase fragment 完成度）
- [ ] **T8**: 实现 `roadmap migrate` 子命令 9 步流程（preflight → parse main → plan slice → dry-run → backup → execute → validate → archive hint → rollback hint）
- [ ] **T9**: 单元测试：Fragment dataclass + 6 个新函数（≥ 15 个 case，每个函数 ≥ 2 个）
- [ ] **T10**: bats 集成测试：`roadmap migrate` 9 步流程（≥ 5 个 case：dry-run / execute / rollback / 失败恢复 / 备份保留）
- [ ] **T11**: bats 集成测试：discover-arch-artifacts.sh 新增 env var（≥ 2 个 case）
- [ ] **T12**: 自家仓库执行 `roadmap migrate --execute` + 验证所有现有 test 仍 pass
- [ ] **T13**: 更新 `skills/roadmap/SKILL.md` migrate 子命令章节 + 嵌套阶段语法更新

### Change 2（hierarchical-roadmap-validation）

- [ ] **T14**: 实现 `validate_fragment_refs`（8 条规则 R1-R8：phase_refs 完整性、id 唯一性、kind 枚举、phase id 命名、feature 必须有 phase_refs、引用主文档未定义 phase、auto-index 陈旧、fragments_dir 缺失）
- [ ] **T15**: `roadmap validate-fragments` 子命令 + `STRICT_ROADMAP_REFS_GATE` / `SKIP_ROADMAP_REFS_GATE` env var（exit code 0/1/2/3 对齐 openspec validate）
- [ ] **T16**: `rdd-doctor` 新增 `roadmap-refs` category（仅报告不修复，调用同一 `validate_fragment_refs`）
- [ ] **T17**: `guide-plan` plan-done gate 集成 `validate_fragment_refs`（默认 WARNING level 不阻断；STRICT 升级）
- [ ] **T18**: 单元测试：8 条规则判定边界（≥ 10 个 case，每条规则 ≥ 1 个，含正常 + 异常）
- [ ] **T19**: bats 集成测试：`roadmap validate-fragments` + `rdd-doctor roadmap-refs` 双入口（≥ 3 个 case）
- [ ] **T20**: bats 集成测试：plan-done gate STRICT 阻断（模拟 R1 违反）
- [ ] **T21**: bats 集成测试：rdd-doctor 只读原则（运行后无任何 tracked/gitignored 文件修改）

### 验证 & 治理

- [ ] **T22**: 全量回归 `./test.sh --full --regression` 通过（无新增 failure）
- [ ] **T23**: 更新 `openspec/specs/roadmap-hierarchy/spec.md` Purpose 字段（archive 后）
- [ ] **T24**: 提交 worktree commits + archive change（`guide-ship` Phase 3）