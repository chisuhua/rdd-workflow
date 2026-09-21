#!/usr/bin/env bats
# tests/unit/test_rddf_setup_help.bats
# Unit tests for `rddf setup --help` output.

load ../test_helper

bats_require_minimum_version 1.5.0

@test "setup --help: shows ai-context subcommand" {
  run python3 -m _lib.cli setup --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"ai-context"* ]]
}

@test "setup ai-context --help: shows all flags" {
  run python3 -m _lib.cli setup ai-context --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
  [[ "$output" == *"--yes"* ]]
  [[ "$output" == *"--uninstall"* ]]
  [[ "$output" == *"--target"* ]]
}