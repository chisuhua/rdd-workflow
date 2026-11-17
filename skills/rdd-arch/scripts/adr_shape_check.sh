#!/usr/bin/env bash
# skills/rdd-arch/scripts/adr_shape_check.sh — ADR 形态检查（决策文档边界）
#
# 判定逻辑的**唯一真源**是 `_lib/arch_quality_gate.py::adr_shape_findings()`。
# 本脚本只负责参数解析与输出 —— 不得内联复制判定规则，也不得硬编码预算默认值
# （预算从 `_DEFAULT_ADR_LINE_LIMIT` / `_DEFAULT_ADR_STATUS_MAX` 取，或由
# `ARCH_ADR_LINE_LIMIT` / `ARCH_ADR_STATUS_MAX` 覆盖）。
#
# 检出的越界信号：
#   1. 正文行数超预算          （ARCH_ADR_LINE_LIMIT，默认 250）
#   2. 缺必备章节              （Context / Decision / Consequences / 备选方案）
#   3. 缺/空 Verification 章   （前瞻验收判据）
#   4. 备选方案表不合规        （缺表 / 少于 3 行 / 缺『结论』列）
#   5. 正文混入过程日志        （审稿轮次 / BLOCKER 清单 / 队列号 / 台账 Entry）
#   6. 标题级过程日志 / 越界成实施细节
#   7. Status 行承载整条版本史 （ARCH_ADR_STATUS_MAX，默认 200）
#
# 用法：
#   adr_shape_check.sh <file> [<file> ...]   # 增量：只检查指定文件
#   adr_shape_check.sh --all                 # 全量扫描项目全部 ADR
#   adr_shape_check.sh --strict <file>       # 有发现即 exit 1
#
# 退出码：0 = 无发现，或有发现但未加 --strict；1 = 有发现且加了 --strict；2 = 用法错误

set -uo pipefail

STRICT=0
ALL=0
FILES=()
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    --all) ALL=1 ;;
    -h|--help)
      sed -n '2,32p' "$0"
      exit 0
      ;;
    *) FILES+=("$arg") ;;
  esac
done

if [ "$ALL" -eq 1 ] && [ "${#FILES[@]}" -gt 0 ]; then
  echo "用法错误：--all 不能与显式文件同时使用" >&2
  exit 2
fi

if [ "$ALL" -eq 0 ] && [ "${#FILES[@]}" -eq 0 ]; then
  echo "未指定文件。用法：adr_shape_check.sh <file> [...] 或 adr_shape_check.sh --all" >&2
  exit 2
fi

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export PROJECT_ROOT

python3 - "$PROJECT_ROOT" "$ALL" "${FILES[@]+"${FILES[@]}"}" <<'PYEOF'
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from skills._lib.arch_quality_gate import adr_shape_findings

project_root = sys.argv[1]
scan_all = sys.argv[2] == "1"
files = sys.argv[3:]

ctx = {"project_root": project_root}
if files:
    ctx["adr_files"] = files

findings = adr_shape_findings(ctx)

if not findings:
    print("✓ ADR 形态检查通过")
    sys.exit(0)

print(f"⚠️  ADR 形态越界（{len(findings)} 项）：")
for f in findings:
    where = f.file or "(项目级)"
    print(f"  - [{f.signal}] {where}: {f.detail}")

# 3 = 有发现（不是错误）—— bash 侧据此决定是否按 --strict 失败
sys.exit(3)
PYEOF
rc=$?

case "$rc" in
  0) exit 0 ;;
  3) if [ "$STRICT" -eq 1 ]; then exit 1; fi; exit 0 ;;
  *) exit "$rc" ;;
esac
