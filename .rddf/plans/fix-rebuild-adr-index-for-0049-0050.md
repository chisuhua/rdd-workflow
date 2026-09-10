# fix-rebuild-adr-index-for-0049-0050 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate docs/adr/README.md ADR index table to include ADR-0049 and ADR-0050 (currently missing).

**Architecture:** Run `_lib/adr_index_generator.py::render_table(scan_adrs(...))` and replace the section between `<!-- ADR_INDEX_START -->` and `<!-- ADR_INDEX_END -->` markers. Update the header sync comment to today's commit hash.

**Tech Stack:** Python 3.11+, pathlib, re.

---

## File Structure


### Production Code


### Docs

| `docs/adr/README.md` | Replace ADR index table between markers; update header sync comment with current commit hash. |

---

### Task 1: Regenerate ADR index with ADR-0049/0050 entries

**Files:**
Modify: docs/adr/README.md

- [ ] **Step 1: Verify 2 tests fail in baseline**

Run: `pytest tests/unit/test_adr_index_gate.py -v`
Expected: 2 tests fail — `test_adr_numbering_is_unique` and `test_readme_index_matches_generator_output` — because README is missing ADR-0049 and ADR-0050 entries.

- [ ] **Step 2: Regenerate the ADR index table**

Run:
```bash
python3 -c "from _lib.adr_index_generator import render_table, scan_adrs; from pathlib import Path; print(render_table(scan_adrs(Path('docs/adr'))))"
```
Capture output. Then edit docs/adr/README.md:
- Replace the section between `<!-- ADR_INDEX_START -->` and `<!-- ADR_INDEX_END -->` markers with the captured output.
- Update the header comment '上次同步' to today's date and current commit hash.

- [ ] **Step 3: Verify both tests pass**

Run: `pytest tests/unit/test_adr_index_gate.py -v`
Expected: 2/2 pass.
Run: `grep -E 'ADR-0049|ADR-0050' docs/adr/README.md` — confirm ≥2 matches each.

- [ ] **Step 4: Commit**

Stage and commit: `refactor(docs): regenerate ADR index with ADR-0049/0050 entries (commit <short-hash>)`
Update tests/KNOWN_FAILURES.txt to remove the 2 entries this proposal unblocks.

