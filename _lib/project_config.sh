#!/usr/bin/env bash
# _lib/project_config.sh
# Bash helper for reading .rddf/project.yaml without requiring yq.
# Falls back to Python subprocess when yq is unavailable.
#
# Usage:
#   source _lib/project_config.sh
#   project_yaml_get <dotted.key> [default_value]
#
# Returns the value (string) or the default if missing.

PROJECT_CONFIG_CACHE=""

_load_project_config_python() {
    local project_root="${1:-$PROJECT_ROOT}"
    local config_file="$project_root/.rddf/project.yaml"
    if [ ! -f "$config_file" ]; then
        echo ""
        return 0
    fi
    PROJECT_CONFIG_FILE="$config_file" PYTHONPATH="${project_root}:${PYTHONPATH:-}" \
        python3 -c '
import os, json, yaml
try:
    with open(os.environ["PROJECT_CONFIG_FILE"]) as f:
        cfg = yaml.safe_load(f) or {}
    print(json.dumps(cfg))
except Exception as e:
    print(f"ERROR: {e}", file=__import__("sys").stderr)
    print("{}")
'
}

project_yaml_get() {
    local key="$1"
    local default="${2:-}"
    local project_root="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

    if [ -z "$PROJECT_CONFIG_CACHE" ]; then
        local cache_file="$project_root/.rddf/state/.project-config-cache.json"
        if [ -f "$cache_file" ] && [ -z "${PROJECT_CONFIG_NO_CACHE:-}" ]; then
            PROJECT_CONFIG_CACHE=$(cat "$cache_file" 2>/dev/null || echo "{}")
        else
            PROJECT_CONFIG_CACHE=$(_load_project_config_python "$project_root")
            mkdir -p "$(dirname "$cache_file")" 2>/dev/null
            echo "$PROJECT_CONFIG_CACHE" > "$cache_file" 2>/dev/null || true
        fi
    fi

    local value
    value=$(PROJECT_CONFIG_JSON="$PROJECT_CONFIG_CACHE" PROJECT_CONFIG_KEY="$key" \
        python3 -c '
import os, json
cfg = json.loads(os.environ["PROJECT_CONFIG_JSON"])
key = os.environ["PROJECT_CONFIG_KEY"]
parts = key.split(".")
cur = cfg
for p in parts:
    if isinstance(cur, dict) and p in cur:
        cur = cur[p]
    else:
        print("")
        exit(0)
if isinstance(cur, (dict, list)):
    print(json.dumps(cur))
else:
    print(cur)
')
    if [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

project_yaml_clear_cache() {
    PROJECT_CONFIG_CACHE=""
    local project_root="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    rm -f "$project_root/.rddf/state/.project-config-cache.json" 2>/dev/null || true
}
