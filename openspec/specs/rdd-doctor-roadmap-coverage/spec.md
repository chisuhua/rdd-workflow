# rdd-doctor-roadmap-coverage Specification

## Purpose
TBD - created by archiving change add-roadmap-phases-and-md-integrity-category.

rdd-doctor provides read-only diagnostic coverage for `.rddf/roadmap/` artifacts. As of 2026-10-07, rdd-doctor has 20 categories covering 6 distinct sub-domains of roadmap integrity: features, objectives, phases, main-doc table, AUTO-INDEX segments, and ADR links.

## Requirements

### Requirement: rdd-doctor-roadmap-coverage

The `rdd-doctor` skill MUST provide diagnostic coverage for all three `.rddf/roadmap/` artifact classes plus `.rddf/roadmap.md` main document integrity. The two new categories added by `add-roadmap-phases-and-md-integrity-category` MUST each satisfy all Acceptance checkboxes in `openspec/changes/archive/2026-10-07-add-roadmap-phases-and-md-integrity-category/proposal.md` ## Acceptance section.

#### Scenario: roadmap-phases covers phases artifacts

GIVEN `.rddf/roadmap/phases/*.md` files exist in the project
WHEN `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-phases` is run
THEN the check validates frontmatter completeness (id/kind/status/phase_refs/主题), AUTO-INDEX Phases segment sync, main doc Phase Skeleton consistency, and warns on phase_refs misuse
AND emits `Finding` objects with `category` field one of `roadmap-phases.{frontmatter,index-drift,main-doc-missing,ref-misuse}`.

#### Scenario: roadmap-md-integrity covers main document

GIVEN `.rddf/roadmap.md` exists in the project
WHEN `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity` is run
THEN the check validates `## Phase Skeleton` table schema (5 columns), AUTO-INDEX three-segment completeness (Phases/Features/Objectives), Phases-segment-to-disk sync, ADR link resolution to `docs/adr/`, and AUTO-SPRINT-START Current Sprint phase column drift (advisory)
AND emits `Finding` objects with `category` field one of `roadmap-md-integrity.{table-schema,index-segment,index-sync,adr-links,sprint-drift}`.

#### Scenario: doctor-main category count is 20

GIVEN the new categories are wired into `_CHECKERS` dict
WHEN `bash skills/rdd-doctor/scripts/doctor.sh --help` is run
THEN the `--category` choices list contains 20 entries including `roadmap-phases` and `roadmap-md-integrity`
AND `len(_CHECKERS) == 20` per `tests/unit/test_doctor_main.py::test_checkers_dict_has_20_entries`.

#### Scenario: SKILL.md sync invariant

GIVEN SKILL.md is updated to reflect the 20-category reality
WHEN `bats tests/integration/test_rdd_doctor_skills_md_sync.bats` is run
THEN all 6 sync tests pass (heading `20 类检查概览`, table has 20 rows, every documented category is wired in `_CHECKERS`, every wired category is documented, `.rddf/roadmap/` quick-reference section mentions roadmap-feature + roadmap-refs + objective-lifecycle).

#### Scenario: regression invariant preserved

GIVEN the new categories are added without modifying existing 18 categories
WHEN `pytest tests/unit/` is run (excluding pre-existing 2 monitor_watch failures verified unrelated via git stash)
THEN test count is ≥ 3137 PASS (3139 achieved), zero new failures
AND KNOWN_FAILURES baseline is reduced by 2 (the `2 doctor_main` entries that asserted == 18 now correctly assert == 20).

#### Scenario: roadmap coverage matrix

GIVEN the user's original question "现在 rdd-doctor 可以诊断 roadmap 的所有问题了吗" (2026-10-07 user request)
WHEN the `.rddf/roadmap/` diagnostic matrix is consulted
THEN features are checked by `roadmap-feature` + `roadmap-refs` (R1-R8 cross-refs)
AND objectives are checked by `objective-structure` + `objective-lifecycle`
AND phases are checked by `roadmap-phases` (frontmatter, AUTO-INDEX sync, main-doc consistency)
AND the main `.rddf/roadmap.md` document is checked by `roadmap-md-integrity` (table schema, ADR links, AUTO-INDEX segments, AUTO-SPRINT drift)
AND NO `.rddf/roadmap/` artifact class lacks a dedicated rdd-doctor diagnostic category.