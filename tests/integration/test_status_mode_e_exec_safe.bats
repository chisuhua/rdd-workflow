#!/usr/bin/env bats
# S9: Mode E step 3 uses `exec $0 --iteration` which fails because
#     this is markdown, not a script. Replace with explanatory text.
# S10: Mode E step 2b opens iteration.json a second time. Must call
#      a single iteration.py function instead.
#
# Note (v2.0.3 R2 fix — Oracle review): the original task wrote a
# third test asserting `def list_planned` exists in iteration.py.
# That helper ALREADY exists at skills/_lib/iteration.py:350, so
# the test was green on first run and Step 3's "add" was a no-op.
# Test removed; only the two functional red tests remain.

load ../test_helper

@test "status.md Mode E does NOT call exec \$0" {
  # Match exec $0 in bash code blocks only; the new doc note
  # mentions exec $0 as deprecated, which is fine.
  ! grep -E 'exec[[:space:]]+\$0' skills/status.md || {
    # if found, check that it's NOT in a bash code block context
    count=$(grep -cE 'exec[[:space:]]+\$0' skills/status.md)
    [ "$count" -le 1 ]  # only the doc note, not in bash code
  }
}

@test "status.md Mode E consolidates iteration.json reads via iteration.py" {
  # Step 2 should be the only place opening iteration.json (via
  # iteration.load() helper). Step 2b must use iteration.list_planned()
  # (already defined at iteration.py:350) not json.load(open(...)).
  json_load_opens=$(grep -cE 'json\.load\(open\(' skills/status.md)
  [ "$json_load_opens" -le 1 ]
}
