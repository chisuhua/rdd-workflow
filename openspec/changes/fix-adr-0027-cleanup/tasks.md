# Tasks: fix-adr-0027-cleanup

## 1. Apply R1 — §6.3 python skeleton fix

- [x] 1.1 Verify env-var assignments (RDDF_ISSUE_DATA / RDDF_CHANGE_NAME / RDDF_NEW_VERSION) are placed **before** `python3 -c` command, not after
- [x] 1.2 Add `import sys` to python imports (was missing — used `sys.stderr` without import)
- [x] 1.3 Remove `echo "$issue_refs" |` pipe (script reads from env, not stdin)
- [x] 1.4 Use `f-string` → regular `f"..."` for multi-line comment (f-string can't span multi-line literals)
- [x] 1.5 Strip `r.stderr` with `.strip()` (was leaking trailing newline)

## 2. Apply R2 — Stale path / string cleanup (9 occurrences)

- [x] 2.1 Line 31: `_lib/sanitizer.py` → `_lib/loop/sanitizer.py` (Context 段引用)
- [x] 2.2 Line 95: `.rddf/config.yaml` → 用 `_lib/config.py` namespace 描述（与 §8 一致）
- [x] 2.3 Line 108: 移除 `conflict-report: true`（触发点已删除，详见 M4）
- [x] 2.4 Line 111: `_lib/sanitizer.py` → `_lib/loop/sanitizer.py`（redact_patterns 注释）
- [x] 2.5 Line 119: banner 禁用路径从 `.rddf/config.yaml` 改为 `RDDF_REPORT_ENABLED=no` env
- [x] 2.6 Line 153: `_lib/sanitizer.py` → `_lib/loop/sanitizer.py`（issue body 示例）
- [x] 2.7 Line 530: "匿名化" → "假名化（pseudonymous，跨 issue 关联）"（与 line 119 banner 一致）
- [x] 2.8 Line 538: `~/.rddf/config.yaml` → `.rddf.json` 的 `reporting` namespace
- [x] 2.9 Line 541: `_lib/sanitizer.py` → `_lib/loop/sanitizer.py`（Consequences 段）

## 3. Apply R3 — References section dedup

- [x] 3.1 Remove duplicate `skills/_lib/archive.sh` Reference (line 603, 重复 line 598)
- [x] 3.2 Remove duplicate `skills/_lib/post_archive_cleanup.sh` Reference (line 604, 重复 line 600)
- [x] 3.3 Remove duplicate `ADR-0010 §3` Reference (line 606, 重复 line 602)
- [x] 3.4 Normalize ADR-0010 path to `docs/adr/ADR-0010-multi-session-management.md`
- [x] 3.5 Add `verified line 340/346` and `verified line 231/237` notes to archive hook references

## 4. Apply R4 — Triage label lifecycle fix

- [x] 4.1 Add `--remove-label needs-triage --add-label triage-in-progress` after `y` action
- [x] 4.2 Add `--remove-label needs-triage --add-label not-actionable` after `n` action
- [x] 4.3 Add `--remove-label needs-triage --add-label deferred` after `d` action
- [x] 4.4 Document `s` action preserves label (intentional — re-triage on next run)

## 5. Apply R5 — Env prefix unification

- [x] 5.1 `RDD_REPORT_AUTO_SUBMIT` → `RDDF_REPORT_AUTO_SUBMIT` (line 92)
- [x] 5.2 `RDD_REPORT_CLOSE_ON_ARCHIVE` → `RDDF_REPORT_CLOSE_ON_ARCHIVE` (line 313)
- [x] 5.3 `RDD_REPORT_*` → `RDDF_REPORT_*` in §8 loading order (line 396, 409)
- [x] 5.4 Confirm no remaining `RDD_REPORT_*` occurrences

## 6. Flip ADR-0027 status to 已采纳

- [x] 6.1 Update header `**状态**: 待定` → `**状态**: 已采纳`
- [x] 6.2 Add `> **Oracle 复核**: PASS-WITH-MINOR-FIXES (2026-08-12, 8/8/7 评分) — 详见 fix-adr-0027-cleanup change`
- [x] 6.3 Verify no other state references remain (e.g. "待修复" todos are still 待修复 in 后续待办 section, that's expected)

## 7. Update ADR index

- [x] 7.1 Add ADR-0027 row to `docs/adr/README.md` 表格
- [x] 7.2 Add ADR-0027 to "v2.1.x+ 实施状态" mapping
- [x] 7.3 Update "已实施 (v2.1.x+)" line if applicable
- [x] 7.4 Update "上次同步" date

## 8. Verification

- [ ] 8.1 Run `grep -n "_lib/sanitizer\.py\|RDD_REPORT_\|\\.rddf/config\\.yaml\|匿名化" docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` — expect 0 hits
- [ ] 8.2 Run `openspec validate fix-adr-0027-cleanup --type change --json` — expect 0 errors
- [ ] 8.3 Run `./test.sh --quick` — expect 0 regression (sanity check; docs-only change)
- [ ] 8.4 Manual review of `git diff docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` — confirm only Oracle-approved edits
- [ ] 8.5 Manual review of §6.3 python skeleton — confirm env-var placed correctly, no syntax errors

## 9. Commit & archive

- [ ] 9.1 `git add docs/adr/ADR-0027-continuous-evolution-feedback-loop.md docs/adr/README.md openspec/changes/fix-adr-0027-cleanup/`
- [ ] 9.2 `git commit -m "docs(adr): apply Oracle review cleanup to ADR-0027

Oracle 复核: PASS-WITH-MINOR-FIXES (Pattern 8/10, Privacy 8/10, Impl 7/10)
- R1: §6.3 python 骨架 env-var 位置 + import sys + 移除 stdin pipe
- R2: 9 处残留旧路径/字串
- R3: References 重复条目
- R4: triage 标签生命周期
- R5: env 前缀统一 RDDF_REPORT_*
- 翻转 ADR-0027 状态 待定 → 已采纳"`
- [ ] 9.3 `openspec archive fix-adr-0027-cleanup --yes` (lightweight mode, only doc changes)
- [ ] 9.4 Confirm archive moved `openspec/changes/fix-adr-0027-cleanup/` to `openspec/changes/archive/`
