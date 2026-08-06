"""Hook comment whitelist for developer experience observability.

Per improvements/developer-experience-observability.md:
- Skip hook warnings on certain comment patterns:
  - bash idioms: BASH_SOURCE, set -u/e/o pipefail
  - magic numbers: numeric thresholds with explanations
  - ticket references: TODO(<ticket-id>)
"""
import re

# Whitelist patterns for comments that should NOT trigger hook warnings
# Pattern groups:
#   Group 1: bash idioms (BASH_SOURCE, set -u/e/o pipefail)
#   Group 2: magic number annotations (Threshold/timeout durations with explanations)
#   Group 3: ticket references (TODO(bug-123), FIXME(rddf-456))
_WHITELIST_PATTERNS = [
    # Bash idioms: BASH_SOURCE[0] guard + set -u/e/o pipefail
    re.compile(r"^\s*#?\s*BASH_SOURCE\[0\]", re.IGNORECASE),
    re.compile(r"^\s*#?\s*set\s+-[euo]+\s*$", re.IGNORECASE),
    re.compile(r"^\s*#?\s*set\s+-o\s+pipefail", re.IGNORECASE),
    # Magic number annotations: numeric thresholds with explanations
    re.compile(r"^\s*#?\s*(threshold|timeout|interval|delay|period)\s*:", re.IGNORECASE),
    re.compile(r"^\s*#?\s*\d+\s*(ms|milliseconds|s|seconds|min|minutes)\s*", re.IGNORECASE),
    # Ticket references: TODO(FIX-123), FIXME(bug-456), etc.
    re.compile(r"^\s*#?\s*(TODO|FIXME|HACK|XXX)\s*\(\s*[a-zA-Z]+-\d+\s*\)", re.IGNORECASE),
]


def is_whitelisted_comment(line: str) -> bool:
    """Check if a line is a comment that matches the whitelist.

    Args:
        line: A single line of code/comment to check.

    Returns:
        True if the line matches any whitelist pattern, False otherwise.
    """
    if not isinstance(line, str):
        return False
    stripped = line.lstrip()
    # Must be a comment (starts with #)
    if not stripped.startswith("#"):
        return False
    for pattern in _WHITELIST_PATTERNS:
        if pattern.match(line):
            return True
    return False
