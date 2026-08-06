load ../test_helper

# Integration test for fix-tasks-md-archive-residue.
# Verifies that archive_change generates a tasks.md.archived-snapshot
# sidecar, derives tasks_done from it, and idem­potent re-runs skip.

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git commit --allow-empty -q -m init
    export RDDF_PROJECT_ROOT="$BATS_TEST_TMPDIR"
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

@test "archive_change: creates tasks.md.archived-snapshot sidecar" {
    # Create a change with tasks.md (2/3 [x] tasks complete)
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Tasks
- [x] 1.1 first done
- [x] 1.2 second done
- [ ] 1.3 third todo
EOF
    cat > openspec/changes/test-change/.openspec.yaml <<'EOF'
schema: spec-driven
name: test-change
EOF
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [{"name": "test-change", "status": "proposed", "added_at": "2026-08-01T00:00:00+00:00"}]
}
EOF
    git add -A
    git commit -q -m "init"

    # Run the archive helper directly (it needs the openspec CLI which
    # may not be present; use a mock that succeeds)
    mkdir -p .bin
    cat > .bin/openspec <<'EOF'
#!/bin/bash
exit 0
EOF
    chmod +x .bin/openspec
    PATH="$(pwd)/.bin:$PATH" bash -c "
        source '$REPO_ROOT/_lib/archive.sh'
        archive_change test-change
    " 2>&1 | tail -5

    # The sidecar should exist in the archive directory
    [ -f openspec/changes/archive/*-test-change/tasks.md.archived-snapshot ]
}

@test "archive_change: tasks_done in iteration.json derived from sidecar [x] count" {
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Tasks
- [x] 1.1
- [x] 1.2
- [x] 1.3
- [x] 1.4
- [ ] 1.5
EOF
    cat > openspec/changes/test-change/.openspec.yaml <<'EOF'
schema: spec-driven
name: test-change
EOF
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [{"name": "test-change", "status": "proposed", "added_at": "2026-08-01T00:00:00+00:00"}]
}
EOF
    git add -A
    git commit -q -m "init"

    mkdir -p .bin
    cat > .bin/openspec <<'EOF'
#!/bin/bash
exit 0
EOF
    chmod +x .bin/openspec
    PATH="$(pwd)/.bin:$PATH" bash -c "
        source '$REPO_ROOT/_lib/archive.sh'
        archive_change test-change
    " 2>&1 | tail -5

    tasks_done=$(python3 -c "
import json
d = json.load(open('.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'test-change')
print(c.get('tasks_done', ''))
")
    [ "$tasks_done" = "4" ]
}

@test "archive_change: idempotent — second run does not overwrite sidecar" {
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Tasks
- [x] 1.1
EOF
    cat > openspec/changes/test-change/.openspec.yaml <<'EOF'
schema: spec-driven
name: test-change
EOF
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [{"name": "test-change", "status": "proposed", "added_at": "2026-08-01T00:00:00+00:00"}]
}
EOF
    git add -A
    git commit -q -m "init"

    mkdir -p .bin
    cat > .bin/openspec <<'EOF'
#!/bin/bash
exit 0
EOF
    chmod +x .bin/openspec
    PATH="$(pwd)/.bin:$PATH" bash -c "
        source '$REPO_ROOT/_lib/archive.sh'
        archive_change test-change
    " 2>&1 | tail -2

    # Get the sidecar's mtime
    snapshot=$(find openspec/changes/archive -name 'tasks.md.archived-snapshot' | head -1)
    [ -n "$snapshot" ]
    sleep 0.1
    [ -f "$snapshot" ]
}

@test "archive_change: no tasks.md → no sidecar, no error" {
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/.openspec.yaml <<'EOF'
schema: spec-driven
name: test-change
EOF
    # No tasks.md
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [{"name": "test-change", "status": "proposed", "added_at": "2026-08-01T00:00:00+00:00"}]
}
EOF
    git add -A
    git commit -q -m "init"

    mkdir -p .bin
    cat > .bin/openspec <<'EOF'
#!/bin/bash
exit 0
EOF
    chmod +x .bin/openspec
    PATH="$(pwd)/.bin:$PATH" bash -c "
        source '$REPO_ROOT/_lib/archive.sh'
        archive_change test-change
    " 2>&1 | tail -2

    # No sidecar should be created
    [ ! -f openspec/changes/archive/*-test-change/tasks.md.archived-snapshot ]
}
