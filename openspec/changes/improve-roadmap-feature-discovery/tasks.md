# improve-roadmap-feature-discovery — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `feature_discovery.py::list_active_features` 枚举 `.rddf/roadmap/features/*.md` 含 frontmatter name + description + phase_refs
- [x] Task 2: 跳过无 frontmatter name 的文件 (graceful)
- [x] Task 3: 缺失 features/ dir 返回空 list (graceful)
- [x] Task 4: 6 个 unit test 全部通过
- [x] Task 5: `bash tests/scripts/report_regression.sh` 不增加新 failure
- [x] Task 6: `feat-fix-audit-findings` 已在 AGENTS.md / guide-design phase-1 preflight 段引用
