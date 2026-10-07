---
id: feat-rdd-doctor-coverage-completion
kind: feature
status: done
phase_refs: [phase-2]
主题: rdd-doctor coverage completion — lazy-import refactor + CI 护送 14/22 + review-debt/roadmap-backup 新 category
---

## 概述

Closes 4 rdd-doctor usability gaps discovered 2026-10-07 (per `openspec/changes/archive/2026-10-07-add-rdd-doctor-coverage-completion/`):

| # | 项 | 来源 | 实现 |
|---|---|---|---|
| 1 | **Lazy-import check modules** — `doctor_main._CHECKERS` 改为 `name -> import_path` string map；`aggregate_findings` lazy-resolve。根因修 #2 | 2026-10-07 user research | commit `4499840` |
| 2 | **`test_rdd_doctor_proposal_section.bats` 5/5 pre-existing** — eager `from checks import ...` 在 temp-fixture 缺 `_lib` 时崩 | 2026-10-07 user research | lazy-import 修复（与 #1 同一 commit）|
| 3 | **`review-debt` category (21st)** — 扫 unticketed TODO/FIXME/HACK | 已存在的 `_lib/review_debt_checker._TODO_PATTERN` 复用 | commit `0f9a3e0` (impl) + `8962d66` (wire) |
| 4 | **`roadmap-backup` category (22nd)** — `.rddf/roadmap/.backup/` staleness 检查 | 新功能 | commit `21a5b4e` (impl) + `8962d66` (wire) |
| 5 | **CI 护送矩阵** — `.github/workflows/test.yml` 10 structural + 4 advisory | `.github/workflows/test.yml` 之前只跑 `docs-consistency` | commit `ed96464` |

## Acceptance

| AC | 状态 |
|----|--------|
| AC-1 doctor_main 无 top-level `from checks import` | ✅ commit `4499840` |
| AC-2 _CHECKERS lazy-import + `_resolve_check` memoize | ✅ commit `4499840` |
| AC-3 test_rdd_doctor_proposal_section.bats 5/5 PASS（was 0/5）| ✅ |
| AC-4 review_debt_check.py exists | ✅ commit `0f9a3e0` |
| AC-5 roadmap_backup_check.py exists | ✅ commit `21a5b4e` |
| AC-6 _CHECKERS len == 22 | ✅ commit `8962d66` |
| AC-7 _CATEGORY_NAMES 22 entries | ✅ commit `8962d66` |
| AC-8 skills_md_sync bats 6/6 PASS（auto-detect 22）| ✅ |
| AC-9 CI structural gate (10 categories) | ✅ commit `ed96464` |
| AC-10 CI advisory gate (4 categories) | ✅ commit `ed96464` |
| AC-11 pytest unit ≥ 3147 PASS（excl monitor_watch pre-existing 2）| ✅ |
| AC-12 test_review_debt_check 4/4 | ✅ |
| AC-13 test_roadmap_backup_check 6/6 | ✅ |
| AC-14 doctor --category roadmap-backup exit ≤ 1 | ✅ |
| AC-15 doctor --category review-debt exit ≤ 1 | ✅ |
| AC-16 git diff ≤ 10 files / ≤ +400 LOC | ✅ 9 files, ~ +400 LOC（含 4 commits）|

## Test Plan

- `pytest tests/unit/` 3147+ PASS (excl 2 pre-existing monitor_watch)
- `bats tests/integration/test_rdd_doctor*.bats` 41/41 PASS（was 36/41 with 5 proposal-section pre-existing failures）
- `bats tests/integration/test_rdd_doctor_skills_md_sync.bats` 6/6 PASS (auto-locks 22 categories)
- `./test.sh --full --regression` 0 new failures vs baseline

## Bonus

CI 矩阵首次运行即 surface 了一个先前未被发现的 pre-existing drift：`.rddf/state/.cross-repo-deps-cache.json` schema 不兼容（旧 `save_cache()` 实现写错格式）。该文件 gitignored；本地删除让下次 cross-repo-deps 工具重新生成。根因与本 PR 无关（git stash baseline 验证）。

## Side Benefits (out-of-spec)

- Lazy-import 重构对未来 `_lib`-依赖的 check 模块同样友好（不再需要每个 contributor 重蹈 ModuleNotFoundError 陷阱）
- CI 矩阵显式分 structural / advisory 两组，避免一刀切 fail-all-or-nothing 阻塞 PR

## References

- `.rddf/improvements/add-rdd-doctor-coverage-completion.md` (proposal)
- `docs/superpowers/specs/2026-10-07-rdd-doctor-coverage-completion-design.md` (design)
- `docs/superpowers/plans/2026-10-07-rdd-doctor-coverage-completion.md` (implementation plan)
- `openspec/changes/archive/2026-10-07-add-rdd-doctor-coverage-completion/` (archive)
