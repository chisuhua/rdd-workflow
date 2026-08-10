# Tasks: add-proposal-how-leakage-warning

## 1. Heuristic Definition

- [x] 1.1 Define the four signals: code-fence density, function/method signatures, file/module change lists, implementation-step density
- [x] 1.2 Define per-section weights (WHY/WHAT sections weighted higher than `技术约束`)
- [x] 1.3 Define the multi-signal firing rule (≥2 high-intensity signals OR single signal above hard cap)

## 2. Implementation

- [x] 2.1 Add the detector as a new function in `skills/_lib/proposal_review.py` (or equivalent location, by repo convention)
- [x] 2.2 The detector accepts improvement / proposal text and returns a list of `{signal, threshold, section, action}` records
- [x] 2.3 Use regex precompilation; expected per-scan runtime <10ms

## 3. Integration with content review layers

- [x] 3.1 Wire the detector into the improvements-layer review at `skills/guide-design/scripts/design_content_review.sh`
- [x] 3.2 Wire the detector into the openspec proposal-layer review at `skills/propose/scripts/propose_quality_check.py::run_design_checks`
- [x] 3.3 Confirm both layers emit the same warning record format (signal + threshold + section)

## 4. Default Behavior

- [x] 4.1 Default mode: warning-only. Detector emits records but does NOT block create / approve / design-done / plan-done
- [x] 4.2 User can ignore or confirm a single warning without modifying detector state
- [x] 4.3 Original content is preserved; no auto-rewrite / strip / crop

## 5. Threshold Configuration

- [x] 5.1 Externalize thresholds to a configuration block so future tuning doesn't require code edits
- [x] 5.2 Document the rationale for each threshold inline in the configuration

## 6. Regression Coverage

- [x] 6.1 Add unit tests for each heuristic signal (code-fence, signature, file list, step density)
- [x] 6.2 Add unit tests for single-signal suppression (no warning if only one weak signal)
- [x] 6.3 Add unit tests for section-aware weighting
- [x] 6.4 Add unit tests for non-fatal parse failures (missing section, empty file, non-standard Markdown)
- [x] 6.5 Add unit tests confirming the detector does not auto-rewrite content (read-only)
- [x] 6.6 Run `./test.sh --full --regression` and confirm no new failures vs. `KNOWN_FAILURES.txt`

## 7. Empirical Hit Collection (per ADR-0019 §3.1)

- [x] 7.1 Persist hit statistics to a local view file (signal fired, paragraph location, user override outcome)
- [x] 7.2 Document the metric used to decide future threshold tuning (user-confirmed false-positive rate, target ≤20%)

## 8. Verification

- [x] 8.1 Run `openspec validate add-proposal-how-leakage-warning --type change --json` and confirm no errors
- [x] 8.2 Confirm the existing test suite passes without LLM / vector DB / external runtime dependency additions
- [x] 8.3 Confirm `proposal-suggestions.md`, all existing proposals, ADR files, and git history outside this change are unmodified