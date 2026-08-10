# proposal-how-leakage-detection Specification

## Purpose
TBD - created by archiving change add-proposal-how-leakage-warning. Update Purpose after archive.
## ADDED Requirements

### Requirement: 启发式 HOW 泄漏检测 — 默认 warning-only

The system SHALL apply an interpretable, heuristic HOW-leakage detector to `improvements/<name>.md` and generated `proposal.md` content at the design content-review layer. The detector SHALL emit warning-only results, MUST NOT block create / approve / design-done / plan-done by default, and MUST NOT auto-rewrite content. Per ADR-0019 §3.1, signals SHALL be conservative, per-section-scoped, and combined with multi-signal suppression so a single weak signal does not fire.

#### Scenario: 多信号触发 warning

- GIVEN an improvement's WHY/WHAT sections contain ≥2 code fences, ≥2 function signatures, or ≥3 consecutive implementation steps
- WHEN the content review runs
- THEN the detector emits a warning record per fired signal
- AND each record includes the signal name, threshold, and section location
- AND the workflow continues (no block)

#### Scenario: 单信号不触发

- GIVEN an improvement contains only one code fence, one function signature, or a sparse set of technical terms
- WHEN the content review runs
- THEN the detector does NOT emit a HOW-leakage warning
- AND the workflow proceeds normally

#### Scenario: 必要范围文件名不触发

- GIVEN a proposal's In Scope section lists specific file paths (e.g. `skills/foo/bar.py`) but has no other high-intensity signals
- WHEN the content review runs
- THEN the detector treats the file list as low-confidence
- AND emits no HOW-leakage warning
- AND does not block the workflow

#### Scenario: 合法技术约束不被误报

- GIVEN a `技术约束` section that includes a function signature or a short code example used to illustrate the constraint
- WHEN the content review runs
- THEN per-section weighting suppresses the warning (technical terms in `技术约束` are expected)

### Requirement: 信号可解释且按段落定位

The detector SHALL use interpretable signals (code-fence density, function/method signatures, file/module change lists, implementation-step density). Each warning record SHALL identify the signal that fired, the threshold exceeded, and the section where the signal was detected. The detector SHALL NOT emit an opaque score without context.

#### Scenario: warning 报告包含信号与段落

- GIVEN a warning fires on a specific section
- WHEN the user views the report
- THEN the warning text names the signal (e.g. "code-fence density")
- AND names the section (e.g. "架构依据")
- AND explains the suggested action (review manually / ignore)

#### Scenario: 不输出无上下文的分数

- GIVEN the detector returns a result
- WHEN the content review emits the record
- THEN the record contains at least one named signal and at least one section reference
- AND does NOT consist solely of an unlabeled numeric score

### Requirement: 不修改 improvement / proposal 内容

The detector SHALL NOT edit, crop, or delete improvement / proposal content. The user SHALL be able to confirm or ignore a single warning without modifying the detector state, and the original improvement / proposal file content SHALL remain unchanged after the review runs.

#### Scenario: 用户确认 warning 不修改内容

- GIVEN the detector emitted a warning
- WHEN the user confirms or ignores the warning
- THEN the original improvement / proposal file is unchanged
- AND the detector does not write back any auto-edit

#### Scenario: 缺失段落或非标准 Markdown 不引发异常

- GIVEN an improvement or proposal with missing sections, empty file, or non-standard Markdown
- WHEN the content review runs
- THEN the detector finishes without raising an unhandled exception
- AND existing content review behavior is preserved (non-fatal)

### Requirement: 不使用 LLM 或不可解释分类器

The detector SHALL NOT use LLM-based semantic classifiers, embedding-based retrieval, or any opaque model judgment to make its default decision. If a future iteration needs such a method, it MUST be added via a separate proposal with empirical false-positive data and MUST default to warning-only per ADR-0019 §3.1.

#### Scenario: 默认判定无 LLM 依赖

- GIVEN the detector's default behavior
- WHEN the content review runs
- THEN the default decision is made by interpretable heuristics only
- AND no LLM call, vector DB query, or external runtime is invoked for the default judgment

### Requirement: 命中统计与未来阈值调整依据 ADR-0019 §3.1

The detector SHALL persist hit statistics (signal fired, section location, user override outcome) to a local view file so that future threshold tuning is grounded in empirical data, not preemptive rule widening. Per ADR-0019 §3.1, threshold expansion MUST NOT happen before empirical hit data is available.

#### Scenario: 命中统计可复核

- GIVEN the detector has fired over multiple review sessions
- WHEN the user inspects the persisted hit statistics
- THEN the view file lists per-signal hit counts, per-section distributions, and user override outcomes
- AND the data can be used to compute a user-confirmed false-positive rate