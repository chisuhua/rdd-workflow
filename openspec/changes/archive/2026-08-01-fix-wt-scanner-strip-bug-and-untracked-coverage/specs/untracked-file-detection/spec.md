## ADDED Requirements

### Requirement: individual untracked files are reported as untracked_file
`_detect_working_tree_issues` SHALL report every non-hidden untracked file that is not excluded by `.gitignore` or `.git/info/exclude` as a `WorkingTreeIssue` with `category="untracked_file"` and `severity="info"`.

#### Scenario: New improvements file is detected
- **GIVEN** a new file `improvements/foo.md` exists in the working tree and is not tracked, ignored, or hidden
- **WHEN** `_detect_working_tree_issues` is called
- **THEN** it returns one issue with `category="untracked_file"`, `path="improvements/foo.md"`, and `severity="info"`

#### Scenario: Untracked file does not trigger a gate
- **GIVEN** the only working-tree issue is an `untracked_file` with `severity="info"`
- **WHEN** the `guide` recommender synthesizes a recommendation
- **THEN** the recommendation action, reason, and confidence match the output for a clean tree

### Requirement: large untracked directories remain reported as untracked_dirs
Untracked directories larger than 10 MB SHALL continue to be reported as `category="untracked_dirs"` with `severity="safe_auto_fix"` and a `fix_command` that appends the directory to `.gitignore`.

#### Scenario: Large build directory is flagged
- **GIVEN** an untracked `build/` directory containing 50 MB of files
- **WHEN** `_detect_working_tree_issues` is called
- **THEN** it returns one issue with `category="untracked_dirs"`, `path="build/"`, `severity="safe_auto_fix"`, and `fix_command='echo "build/" >> .gitignore'`

### Requirement: hidden and ignored untracked entries are excluded
Hidden directories and entries ignored by `.gitignore` or `.git/info/exclude` SHALL NOT be reported as `untracked_file` or `untracked_dirs`.

#### Scenario: Hidden directory is ignored
- **GIVEN** a hidden directory `.venv/` exists in the working tree and is not tracked
- **WHEN** `_detect_working_tree_issues` is called
- **THEN** no issue is returned for `.venv/`

#### Scenario: Gitignored directory is ignored
- **GIVEN** a directory `node_modules/` exists in the working tree and `node_modules/` is listed in `.gitignore`
- **WHEN** `_detect_working_tree_issues` is called
- **THEN** no issue is returned for `node_modules/`

### Requirement: WorkingTreeIssue category and consumer summary include untracked_file
The `WorkingTreeIssue` docstring SHALL list `"untracked_file"` in the category enumeration, and the cleanup-menu summary in `_build_options_from_state` SHALL count untracked files alongside `deleted`, `modified`, and `staged`.

#### Scenario: Cleanup menu mentions untracked files
- **GIVEN** `_detect_working_tree_issues` returns one `deleted` issue and one `untracked_file` issue
- **WHEN** `_build_options_from_state` constructs the cleanup menu option
- **THEN** the option description includes "1 deleted, 1 untracked"
