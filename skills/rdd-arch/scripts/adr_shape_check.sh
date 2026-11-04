#!/usr/bin/env bash
# _lib/adr_shape_check.sh — ADR 形态检查（决策文档边界）
#
# 检出 ADR 是否越界成「设计规格 / 流程台账」：
#   1. 正文行数超预算          （ARCH_ADR_LINE_LIMIT，默认 300）
#   2. 缺必备章节              （Context / Decision / Consequences / 备选方案）
#   3. 正文混入过程日志        （审稿轮次 / BLOCKER 清单 / 队列号 / 台账 Entry）
#   4. Status 行承载整条版本史 （ARCH_ADR_STATUS_MAX，默认 200）
#
# 用法：
#   adr_shape_check.sh                 # 扫描项目全部 ADR
#   adr_shape_check.sh docs/adr/ADR-0012-x.md ...   # 只扫指定文件
#   adr_shape_check.sh --strict        # 有发现即 exit 1
#
# Exit: 0 = 无发现；1 = 有发现（--strict）；2 = 用法错误

set -uo pipefail

STRICT=0
FILES=()
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *) FILES+=("$arg") ;;
  esac
done

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export PROJECT_ROOT

python3 - "$PROJECT_ROOT" "${FILES[@]+"${FILES[@]}"}" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from skills._lib.arch_quality_gate import _check_adr_shape, _read_handoff

project_root = sys.argv[1]
files = sys.argv[2:]

ctx = {"project_root": project_root}
if files:
    ctx["adr_files"] = files

passed, severity = _check_adr_shape(ctx)
if passed:
    print("✓ ADR 形态检查通过")
    sys.exit(0)

# Re-run to surface the per-file findings (the check returns a summary only).
import os
from pathlib import Path
from skills._lib.arch_quality_gate import (
    _PROCESS_LOG_PATTERNS,
    _SHAPE_REQUIRED_SECTIONS,
    _iter_adr_files,
)

paths = _read_handoff(project_root)
line_limit = int(os.environ.get("ARCH_ADR_LINE_LIMIT", "300"))
status_max = int(os.environ.get("ARCH_ADR_STATUS_MAX", "200"))
targets = [Path(f) for f in files] if files else list(_iter_adr_files(project_root, paths))

print("⚠️  ADR 形态越界：")
for f in targets:
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    lines = text.splitlines()
    notes = []
    if len(lines) > line_limit:
        notes.append(f"正文 {len(lines)} 行 > {line_limit}")
    missing = [s for s, p in _SHAPE_REQUIRED_SECTIONS.items() if not p.search(text)]
    if missing:
        notes.append("缺章节 " + ", ".join(missing))
    hits = sum(len(p.findall(text)) for p in _PROCESS_LOG_PATTERNS)
    if hits:
        notes.append(f"过程日志标记 {hits} 处")
    for line in lines:
        st = line.strip()
        if st.startswith(">") and ("状态" in st or "Status" in st):
            if len(st) > status_max:
                notes.append(f"Status 行 {len(st)} 字符 > {status_max}")
            break
    if notes:
        print(f"  - {f.name}: " + "；".join(notes))

sys.exit(1)
PYEOF
rc=$?

if [ "$STRICT" = "1" ] && [ "$rc" = "1" ]; then
  exit 1
fi
exit "$rc"
