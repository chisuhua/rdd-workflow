# Design: add-proposal-how-leakage-warning

## Context

ADR-0025 §D2 / §D4 split the proposal review into two layers:

- **improvements 层**: structure (5 sections), ADR reference, head fields, quantifiable acceptance.
- **openspec proposal 层**: length, ADR reference, In/Out Scope, plus `openspec validate <name> --json`.

Neither layer catches the *content-layer boundary* problem: an improvement / proposal that drifts from WHY/WHAT into HOW too early. ADR-0019 §3.1 / §3.2 establishes the conservative anti-pattern checking philosophy: prefer low false-positive, default warning, expand rules only after empirical hits, never use a broad rule that erodes gate credibility.

The user-visible symptoms today:

- An improvement with many code fences, function signatures, and step-by-step "Implementation" sections still passes existing checks.
- Reviewers must manually flag the HOW leakage after the proposal is already on disk.
- Late-stage rewrites cost more than early-stage warnings.

ADR-0025 §D1 preserves a user-confirmation step after `generate_full_proposal.py`, so an early-stage warning is compatible with the existing UX: the user can ignore or amend the warning without leaving the workflow.

This change adds a **warning-only**, **heuristic**, **non-blocking** HOW-leakage detector at the content-review layer. It does not replace existing checks; it sits beside them.

## Goals / Non-Goals

**Goals**
- Add an interpretable, heuristic HOW-leakage signal that fires on excessive code fences, function/method signatures, file/module change lists, and dense implementation steps in WHY/WHAT sections.
- Default to warning; preserve user override path; never auto-rewrite content.
- Reuse the ADR-0025 layered review entry point so improvements and proposal layers share the message format.

**Non-Goals**
- Introducing LLM semantic classifiers, embedding retrieval, or any opaque model judgment.
- Defaulting to a hard block (warning-only).
- Expanding to `design.md` / `spec.md` / `tasks.md` / plan execution content (out of scope; would alter review granularity).
- Deciding implementation correctness, replacing ADR alignment, `openspec validate`, task tracing, or plan quality checks.

## Decisions

### Decision 1: Conservative heuristic signals, not semantic classification

We use four simple, transparent signals:

1. **Code-fence density**: count of ` ``` ` fenced blocks within WHY/WHAT sections.
2. **Function / method signatures**: regex match for `def ` / `class ` / `(self` / `()` patterns at line starts or after `def|class|function`.
3. **File / module change lists**: bullet density of patterns matching `**/*.py` / `path/to/file` / `package/submodule`.
4. **Implementation-step density**: count of consecutive `1.` / `2.` / `Step 1` style ordinal markers.

A warning fires when **two or more** high-intensity signals exceed threshold OR when a single signal exceeds a hard cap. This guards against single-weak-signal false positives.

**Alternatives considered**

- *LLM semantic classifier*: rejected — violates ADR-0019 §3.1 "interpretable signals"; adds a non-deterministic, non-reproducible dependency.
- *Single-signal hard threshold*: rejected — high false-positive rate on legitimate technical terminology.

### Decision 2: Warning-only, no default block

The detector emits a warning record: signal name, threshold, paragraph location, suggested action ("review manually" / "ignore"). It does NOT block any workflow by default. ADR-0019 §3.1 explicitly says "do not weaken gate credibility" — and a false-positive hard block would erode that credibility faster than a missed signal.

If a future iteration wants strict mode, it MUST use a new independent env var following the existing `STRICT_*_GATE=yes` convention and MUST evaluate empirical hit data first.

**Alternatives considered**

- *Always block*: rejected — see ADR-0019 §3.1.
- *Skip-warning, only-blocking mode*: rejected — defeats the early-stage signal purpose.

### Decision 3: Section-scoped, not whole-file

The detector scans per-section (`架构依据` / `范围` / `关键场景` / `技术约束` / `验收标准`). WHY/WHAT sections (`架构依据`, `范围`) are weighted higher than `技术约束` (which legitimately contains technical terms). The detector reports the section each signal fired in.

**Alternatives considered**

- *Whole-file scan*: rejected — would generate warnings for legitimate constraints and acceptance bullets.
- *Section-blind regex count*: rejected — same false-positive concern.

### Decision 4: No content rewriting

The detector never edits, crops, or rewrites improvement / proposal content. Its output is advisory. The user (or future automation with explicit consent) decides what to do.

**Alternatives considered**

- *Auto-strip code blocks from WHY sections*: rejected — violates ADR-0019 §3.1 ("we do not auto-rewrite content"). A single false-positive rewrite would destroy user trust.

## Risks / Trade-offs

- **[Risk]** Heuristics may misfire on legitimately technical content (e.g. an acceptance criterion that references a function signature). → **Mitigation**: per-section weighting + multi-signal-threshold suppression; manual override path is always available; ADR-0019 §3.1 mandates empirical expansion rather than preemptive rule widening.
- **[Risk]** Detector adds runtime to content review. → **Mitigation**: linear scan over small files (improvements typically <300 lines, proposals <500); regex compilation is once per scan; expected overhead <10ms.
- **[Risk]** Detector creates inconsistency between improvements-layer and proposal-layer outputs. → **Mitigation**: both layers reuse the same threshold configuration and emit the same warning record format.

## Migration Plan

1. Land this change in a single PR.
2. Run `./test.sh --full --regression` to confirm no new failures vs. `KNOWN_FAILURES.txt` baseline.
3. Hit statistics (which signals fire, how often users override) are persisted to a local view file so future iterations can tune thresholds per ADR-0019 §3.1.
4. Rollback: revert the PR — no data migration needed.

## Open Questions

- What is the right metric for "false-positive rate below 20%" in the acceptance criteria? Operational definition will be finalized in the implementation PR; current text uses the user-confirmed-false-positive ratio as the proxy.