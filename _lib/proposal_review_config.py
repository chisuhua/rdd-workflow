"""skills/_lib/proposal_review_config.py — HOW-leakage threshold configuration.

Externalized thresholds for the heuristic HOW-leakage detector in
`skills/_lib/proposal_review.py`. Per design decision (Group 5 in
.rddf/plans/add-proposal-how-leakage-warning.md) and ADR-0019 §3.1,
thresholds are configuration data, not code constants — future tuning
must not require editing the detector.

Threshold rationale (per signal):

  code_fence:
    high=2, hard_cap=4
    A single short code example is legitimate (e.g. illustrating an
    API contract). Two or more in the same section is suspicious.
    Hard cap 4 catches documents that are mostly code.

  function_signature:
    high=2, hard_cap=5
    One signature is fine (e.g. "the `foo()` method returns X").
    Two or more starts to indicate HOW. Hard cap 5 catches
    implementation walkthroughs.

  file_list:
    high=3, hard_cap=6
    One or two path references for context is normal (e.g. "modify
    `src/foo.py`"). Three or more suggests a change-list format.
    Hard cap 6 catches documents enumerating the entire diff.

  step_density:
    high=3, hard_cap=6
    Three consecutive ordinals ("1. 2. 3.") starts to look like a
    how-to. Hard cap 6 catches full enumerated plans.

  section_weights:
    WHY/WHAT sections (架构依据, 范围) weighted 1.0 because they
    should stay declarative. 关键场景 / 验收标准 weighted 0.6-0.8
    because they may legitimately contain technical examples.
    技术约束 weighted 0.4 because it is expected to contain code
    and file references by definition.

  multi_signal_threshold=2:
    Per design decision 1: warn when 2+ independent signals each
    fire in some section. Single-signal fires are suppressed.

  weighted_score_block=1.5:
    Per future extension — not yet used by the detector. Reserved
    for future "section-weighted score" sum-mode if multi-signal
    rule proves too noisy in practice (per ADR-0019 §3.1 empirical
    expansion policy).
"""
THRESHOLDS = {
    "code_fence": {"high": 2, "hard_cap": 4},
    "function_signature": {"high": 2, "hard_cap": 5},
    "file_list": {"high": 3, "hard_cap": 6},
    "step_density": {"high": 3, "hard_cap": 6},
    "section_weights": {
        "架构依据": 1.0,
        "范围": 1.0,
        "关键场景": 0.8,
        "技术约束": 0.4,
        "验收标准": 0.6,
    },
    "multi_signal_threshold": 2,
    "weighted_score_block": 1.5,
}

__all__ = ["THRESHOLDS"]