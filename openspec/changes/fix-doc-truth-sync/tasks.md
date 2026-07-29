# fix-doc-truth-sync — Implementation Tasks

## Task 1: Write failing test that confirms 3 skills missing from package.json

**Write failing test**: Create a test that asserts the 3 missing skills are absent from `package.json skills[]`.

Step 1a: Write the test assertion:
```python
# Verify that add-improve, openspec-gate, and rdd-workflow-brainstorm are missing
import json
data = json.load(open("package.json"))
skills = set(data.get("skills", []))
missing = {"add-improve", "openspec-gate", "rdd-workflow-brainstorm"}
# This should fail initially — confirming the gap
assert missing.issubset(skills), f"Missing: {missing - skills}"
```

Step 1b: Run the test:
```bash
python3 -c "import json; data=json.load(open('package.json')); skills=data.get('skills',[]); print('skills count:', len(skills)); missing=['add-improve','openspec-gate','rdd-workflow-brainstorm']; [print(f'  MISSING: {s}') for s in missing if s not in skills]"
```

**Expected**: The test fails — 3 skills are not in `package.json skills[]`.

## Task 2: Add 3 missing skills to package.json

**Implement**: Edit `package.json` to add `add-improve`, `openspec-gate`, and `rdd-workflow-brainstorm` to the `skills[]` array.

The current `skills[]` array is:
```json
"skills": [
  "INSTALL",
  "guide",
  "guide-arch",
  "guide-plan",
  "guide-ship",
  "feature",
  "rddf-session",
  "propose",
  "execute",
  "status",
  "roadmap",
  "deps",
  "rdd-workflow-writing-plans"
]
```

After the change, it should be:
```json
"skills": [
  "INSTALL",
  "guide",
  "guide-arch",
  "guide-plan",
  "guide-ship",
  "feature",
  "rddf-session",
  "propose",
  "execute",
  "status",
  "roadmap",
  "deps",
  "add-improve",
  "openspec-gate",
  "rdd-workflow-brainstorm",
  "rdd-workflow-writing-plans"
]
```

The 3 new entries are inserted in alphabetical order before `rdd-workflow-writing-plans`.

## Task 3: Verify all doc_truth_sync tests pass

**Verify pass**: Run the full doc_contracts test suite:

```bash
bats tests/integration/test_doc_contracts.bats
```

**Expected**: All 8 tests pass (1..8, all ok).

Also run the metadata consistency smoke tests:
```bash
bats tests/integration/test_skill_metadata_consistency.bats
bats tests/smoke.bats
```

Commit the change with a descriptive message.

## Task 4: Commit

```bash
git add package.json
git commit -m "fix(package.json): add 3 missing skills to skills[] array

add-improve, openspec-gate, and rdd-workflow-brainstorm were added to
disk but never registered in package.json skills[] manifest, causing
doc_truth_sync test #1 to fail.

Closes: fix-doc-truth-sync
"
```