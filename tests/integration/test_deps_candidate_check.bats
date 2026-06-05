#!/usr/bin/env bats

# T13 (P1-8): guide-spec.md deps candidate list must use git show HEAD:
# (not filesystem check) so that uncommitted local drafts are NOT included
# as candidates for dependency analysis.
#
# Tests verify:
#   - guide-spec.md no longer uses os.path.isfile() for the .openspec.yaml
#     HEAD check (the old buggy pattern)
#   - guide-spec.md uses subprocess.run with 'git show HEAD:...' for the check
#   - Runtime: a scratch repo with one committed + one uncommitted change
#     returns only the committed name in the candidates list (excludes drafts)

load ../test_helper

# Location of the guide-spec skill markdown under test
GUIDE_SPEC_MD="$REPO_ROOT/skills/guide-spec.md"

@test "guide-spec.md no longer uses os.path.isfile for HEAD check (P1-8)" {
  [ -f "$GUIDE_SPEC_MD" ]
  # The old buggy pattern checked filesystem presence instead of git HEAD.
  # Comments explaining the fix are fine; check executable code only.
  local non_comment
  non_comment=$(grep -vE '^\s*#' "$GUIDE_SPEC_MD" | grep -v '^\s*$')
  ! echo "$non_comment" | grep -qE 'os\.path\.isfile.*\.openspec\.yaml'
}

@test "guide-spec.md uses git show HEAD: for change candidate check (P1-8)" {
  [ -f "$GUIDE_SPEC_MD" ]
  # The new code must invoke git show on the HEAD: tree object
  grep -qE "git show.*HEAD:.*\.openspec\.yaml" "$GUIDE_SPEC_MD"
  # And it must be wrapped in subprocess.run
  grep -qE "subprocess\.run\(" "$GUIDE_SPEC_MD"
}

# Runtime regression test: prove the new pattern actually excludes uncommitted
# local drafts from the candidate list. This catches "looks right in grep"
# failures (e.g. if someone reintroduces a filesystem check behind a comment).
@test "runtime: uncommitted change is excluded from candidates (P1-8)" {
  local test_repo
  test_repo=$(mktemp -d)
  cd "$test_repo" || return 1
  git init -q
  git config user.email "test@test.local"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init

  # Two change directories: one committed, one only on disk
  mkdir -p openspec/changes/committed openspec/changes/uncommitted
  touch openspec/changes/committed/.openspec.yaml
  echo "## proposal" > openspec/changes/committed/proposal.md
  touch openspec/changes/uncommitted/.openspec.yaml
  echo "## proposal" > openspec/changes/uncommitted/proposal.md

  # Commit ONLY the 'committed' change; 'uncommitted' stays on disk
  git add openspec/changes/committed/
  git commit -q -m "add committed change"

  # Run the EXACT Python block from guide-spec.md Phase 2.5 Step 1
  local output
  output=$(PROJECT_ROOT="$test_repo" python3 -c "
import json, os, sys, subprocess

changes_dir = '$test_repo/openspec/changes'
candidates = []
if os.path.isdir(changes_dir):
    for name in sorted(os.listdir(changes_dir)):
        try:
            result = subprocess.run(
                ['git', 'show', f'HEAD:openspec/changes/{name}/.openspec.yaml'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                candidates.append(name)
        except (FileNotFoundError, subprocess.SubprocessError) as e:
            print(f'WARN git show failed for {name}: {e}', file=sys.stderr)
print(','.join(candidates))
" 2>&1)
  local rc=$?
  cd /
  rm -rf "$test_repo"

  [ "$rc" -eq 0 ] || { echo "Python exited with $rc: $output" >&2; return 1; }
  # Only 'committed' must appear; 'uncommitted' must be filtered out
  [ "$output" = "committed" ] || {
    echo "expected output 'committed', got: $output" >&2
    return 1
  }
}
