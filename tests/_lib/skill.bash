#!/usr/bin/env bash
# tests/_lib/skill.bash
#
# Shared helper for parsing OpenSpec skill Markdown files.
# Loaded by test files via `load_lib skill` (see tests/test_helper.bash).
#
# Public API:
#   skill_frontmatter_block <file>
#       Print the YAML frontmatter block (between the first --- pair).
#       Returns non-zero if the file has no frontmatter.
#
#   skill_field <file> <key>
#       Print the value of a top-level YAML scalar in the frontmatter.
#       Strips surrounding double or single quotes.
#       Returns non-zero if the key is missing or the file is unreadable.
#
#   skill_meta_field <file> <key>
#       Print the value of a key under the `metadata:` block.
#       Strips surrounding quotes and end-of-line comments.
#       Returns non-zero if `metadata:` is missing or the key is absent.
#
#   skill_commands <file>
#       Print one command per line, extracted from markdown table rows
#       of the form: `| \`<cmd>\` | <desc> |`
#       Returns 0 even if no commands are found (empty output).
#
#   skill_has_section <file> <heading>
#       Return 0 if any heading line (`^#+ `) starts with `<heading>`,
#       1 otherwise. The match is a literal prefix; trailing characters
#       (e.g. "：状态概览") are allowed.
#
# All functions tolerate missing files: they print nothing useful and
# return non-zero, never crashing the calling test.

# Strip surrounding ASCII double or single quotes from a value, if any.
_skill_strip_quotes() {
  local v="$1"
  v="${v%\"}"
  v="${v#\"}"
  v="${v%\'}"
  v="${v#\'}"
  printf '%s' "$v"
}

# Print the frontmatter block (lines between the first pair of `---`).
skill_frontmatter_block() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "skill_frontmatter_block: file not found: $f" >&2
    return 1
  fi
  awk '
    /^---[[:space:]]*$/ { c++; next }
    c == 1 { print }
    c >= 2 { exit }
  ' "$f"
}

# Print the value of a top-level YAML scalar key in the frontmatter.
skill_field() {
  local f="$1" key="$2"
  if [[ ! -f "$f" ]]; then
    echo "skill_field: file not found: $f" >&2
    return 1
  fi
  if [[ -z "$key" ]]; then
    echo "skill_field: empty key" >&2
    return 1
  fi
  # Match `^key:` at the start of a frontmatter line, strip the prefix
  # and any inline comment, then strip quotes.
  local raw
  raw=$(skill_frontmatter_block "$f" | awk -v k="$key" '
    $0 ~ "^" k ":[[:space:]]*" {
      sub("^" k ":[[:space:]]*", "")
      # Strip trailing inline comment (very rough; do not handle "# in string")
      sub(/[[:space:]]+#[^"]*$/, "")
      sub(/[[:space:]]+#.*$/, "")
      print
      exit
    }
  ')
  if [[ -z "$raw" ]]; then
    return 1
  fi
  _skill_strip_quotes "$raw"
}

# Print the value of a key under the `metadata:` block.
skill_meta_field() {
  local f="$1" key="$2"
  if [[ ! -f "$f" ]]; then
    echo "skill_meta_field: file not found: $f" >&2
    return 1
  fi
  if [[ -z "$key" ]]; then
    echo "skill_meta_field: empty key" >&2
    return 1
  fi
  local raw
  raw=$(skill_frontmatter_block "$f" | awk -v k="$key" '
    /^metadata:[[:space:]]*$/ { in_meta=1; next }
    in_meta && /^[^[:space:]]/ { in_meta=0 }
    in_meta && $0 ~ "^[[:space:]]+" k ":[[:space:]]*" {
      sub("^[[:space:]]+" k ":[[:space:]]*", "")
      sub(/[[:space:]]+#[^"]*$/, "")
      sub(/[[:space:]]+#.*$/, "")
      print
      exit
    }
  ')
  if [[ -z "$raw" ]]; then
    return 1
  fi
  _skill_strip_quotes "$raw"
}

# Print one command per line from markdown command tables.
# A command row looks like: `| \`<cmd> [args]\` | <desc> |`
# Only the leading command identifier is returned (split on the first
# whitespace inside the backticks), so callers can do exact-match checks.
skill_commands() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "skill_commands: file not found: $f" >&2
    return 1
  fi
  awk '
    /^\|[[:space:]]*`[^`]+`[[:space:]]*\|/ {
      match($0, /`[^`]+`/)
      cmd = substr($0, RSTART + 1, RLENGTH - 2)
      # Skip separator rows
      if (cmd ~ /^-+$/) next
      # Take only the leading identifier (drop inline args)
      sub(/[[:space:]].*$/, "", cmd)
      print cmd
    }
  ' "$f"
  return 0
}

# Return 0 if any heading line starts with `<heading>`.
skill_has_section() {
  local f="$1" heading="$2"
  if [[ ! -f "$f" ]]; then
    echo "skill_has_section: file not found: $f" >&2
    return 1
  fi
  if [[ -z "$heading" ]]; then
    echo "skill_has_section: empty heading" >&2
    return 1
  fi
  if grep -qE "^#+[[:space:]]+${heading}" "$f"; then
    return 0
  fi
  return 1
}
