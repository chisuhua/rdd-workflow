# Spec: proposal-from-issue

> Capability covering GitHub issue-driven proposal creation via `add-improve --from-issue <N>`, with repo detection, dedup, and scaffold generation.

## ADDED Requirements

### Requirement: add-improve-from-issue-mode

The `add-improve` skill MUST support a `--from-issue <N>` mode that creates a proposal scaffold from a GitHub issue.

#### Scenario: from-issue creates scaffold

- GIVEN a user runs `add-improve --from-issue 42` in a project with a GitHub repo
- WHEN the gh CLI is authenticated and the issue exists
- THEN a new `.rddf/improvements/<slug>-i42.md` file is created with the issue title and body pre-filled
- AND the entry is registered in `proposal-suggestions.md`

#### Scenario: gh CLI not authenticated

- GIVEN `gh auth status` returns non-zero
- WHEN the user runs `add-improve --from-issue 42`
- THEN the command exits with code 2 and stderr message "gh 未认证，请运行 `gh auth login`"
- AND no files are written

### Requirement: repo-detection-fallback-chain

The `from-issue` flow MUST detect the current project's GitHub repo using a 3-step fallback chain:
1. `RDDF_PROPOSAL_GH_REPO` env var (explicit override)
2. `gh repo view --json nameWithOwner` (subprocess + 10s timeout)
3. `git remote get-url origin` parse + GitHub URL extraction

If all 3 fail, exit 2 with a clear error message.

#### Scenario: env override takes priority

- GIVEN `RDDF_PROPOSAL_GH_REPO=myorg/my-fork` is set
- WHEN the user runs `add-improve --from-issue 42`
- THEN `myorg/my-fork` is used as the target repo
- AND `gh repo view` is skipped

#### Scenario: gh repo view fallback

- GIVEN no env var is set, but `gh repo view` returns a valid `nameWithOwner`
- WHEN the user runs `add-improve --from-issue 42`
- THEN the detected repo is used

#### Scenario: git remote parse fallback

- GIVEN no env var, no `gh` but `git remote get-url origin` returns a GitHub URL
- WHEN the user runs `add-improve --from-issue 42`
- THEN the parsed owner/repo is used

### Requirement: dedup-against-existing-proposals

The `from-issue` flow MUST scan two locations for existing issue references and warn if the issue is already tracked:
- `.rddf/improvements/*.md` frontmatter `issue_ref: N` field
- `openspec/changes/*/roadmap-meta.yaml::issue_refs`

#### Scenario: issue already in improvements

- GIVEN `.rddf/improvements/foo.md` has `issue_ref: 42` in frontmatter
- WHEN the user runs `add-improve --from-issue 42`
- THEN the user is shown the existing proposal file and asked to skip or create a new one

### Requirement: slug-collision-handling

When the issue title generates a slug that already exists, the `from-issue` flow MUST append `-i<N>` (issue number) to produce a deterministic, grep-able filename.

#### Scenario: title produces duplicate slug

- GIVEN issue #10 and #20 both have titles that slugify to "fix-foo"
- WHEN the user creates proposals for both
- THEN issue #10 produces `fix-foo.md` and issue #20 produces `fix-foo-i20.md`

### Requirement: issue-body-truncation

When the issue body exceeds 4000 characters, the `from-issue` flow MUST truncate and append a reference to the original URL.

#### Scenario: long issue body

- GIVEN issue #42 has a 6000-character body
- WHEN the scaffold is generated
- THEN the body is truncated to ~4000 characters
- AND a "... (剩余 N 字符，参见 <URL>)" suffix is appended

### Requirement: close-issues-comment-repo-neutral

The `_lib/close_issues.py:180` comment template MUST be repo-neutral — it MUST NOT hardcode the string "rdd-workflow" in the comment text.

#### Scenario: archive comment for third-party repo

- GIVEN a change is archived in a third-party repo (not rdd-workflow)
- WHEN `_close_issue` is called
- THEN the GitHub comment does NOT contain "Fixed in rdd-workflow"
- AND instead uses repo-neutral language referencing the change_name and version

### Requirement: gh-missing-or-unauthenticated-exits-cleanly

When `gh` CLI is missing or unauthenticated, the `from-issue` flow MUST exit with code 2 and a clear stderr message, without writing any files.

#### Scenario: gh CLI missing

- GIVEN `gh` is not installed
- WHEN the user runs `add-improve --from-issue 42`
- THEN exit code is 2
- AND stderr shows "gh CLI not found, install with: https://cli.github.com"
- AND no files are written
