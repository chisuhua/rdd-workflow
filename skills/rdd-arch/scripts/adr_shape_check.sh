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
# 存量 / 增量（基线机制，per `fix-adr-shape-debt-convergence`）：
#   docs/adr/.adr-shape-baseline.json 冻结存量 findings（per-file × per-signal），
#   `--diff-baseline` 只报基线外的新增债务。这是把形态门接进 CI 的前提：存量 56 项
#   `missing_verification` 按 ADR-0060 不追溯、永远清不完，故门只能检「是否新增」。
#
# ⚠️ `alternatives_table_missing` 与 `missing_section` 互斥：补一个备选方案章节只会把
#   `missing_section` 换成 `alternatives_table_missing`（缺对比表），净收益为 0。
#   为凑绿而造一张假备选表不改变形态债，只是把债挪了个信号 —— 别这么做。
#
# 用法：
#   adr_shape_check.sh <file> [<file> ...]      # 增量：只检查指定文件
#   adr_shape_check.sh --all                    # 全量扫描项目全部 ADR
#   adr_shape_check.sh --all --summary          # 折叠为 per-signal 计数
#   adr_shape_check.sh --all --baseline         # 只读列出冻结账本
#   adr_shape_check.sh --all --diff-baseline    # 只报基线外的新增（CI 用这个）
#   adr_shape_check.sh --all --write-baseline   # 写基线（唯一写路径；只降不升）
#   adr_shape_check.sh --strict <file>          # 有发现即 exit 1
#
# 退出码：
#   0 = 无发现 / 增量模式下无新增 / 写基线成功
#   1 = 有发现且加了 --strict / 增量模式发现新增 / 写基线被 ratchet 拒绝
#   2 = 用法错误 / 基线缺失·非法·为空

set -uo pipefail

STRICT=0
ALL=0
SUMMARY=0
MODE=scan
MODE_SET=0
FILES=()

_set_mode() {
  if [ "$MODE_SET" -eq 1 ]; then
    echo "用法错误：--baseline / --diff-baseline / --write-baseline 互斥" >&2
    exit 2
  fi
  MODE_SET=1
  MODE="$1"
}

for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    --all) ALL=1 ;;
    --summary) SUMMARY=1 ;;
    --baseline) _set_mode baseline ;;
    --diff-baseline) _set_mode diff ;;
    --write-baseline) _set_mode write ;;
    -h|--help)
      sed -n '2,48p' "$0"
      exit 0
      ;;
    *) FILES+=("$arg") ;;
  esac
done

if [ "$ALL" -eq 1 ] && [ "${#FILES[@]}" -gt 0 ]; then
  echo "用法错误：--all 不能与显式文件同时使用" >&2
  exit 2
fi

if [ "$MODE" != "scan" ] && [ "$ALL" -eq 0 ]; then
  echo "用法错误：基线模式需要 --all（基线是项目级账本，不能按文件读/写）" >&2
  exit 2
fi

if [ "$ALL" -eq 0 ] && [ "${#FILES[@]}" -eq 0 ]; then
  echo "未指定文件。用法：adr_shape_check.sh <file> [...] 或 adr_shape_check.sh --all" >&2
  exit 2
fi

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export PROJECT_ROOT

python3 - "$PROJECT_ROOT" "$ALL" "$MODE" "$SUMMARY" "${FILES[@]+"${FILES[@]}"}" <<'PYEOF'
import sys
from collections import Counter

sys.path.insert(0, sys.argv[1])
from skills._lib.arch_quality_gate import (
    ShapeBaselineError,
    adr_shape_findings,
    diff_shape_findings,
    read_shape_baseline,
    write_shape_baseline,
)

project_root = sys.argv[1]
scan_all = sys.argv[2] == "1"
mode = sys.argv[3]
summary = sys.argv[4] == "1"
files = sys.argv[5:]

ctx = {"project_root": project_root}
if files:
    ctx["adr_files"] = files

findings = adr_shape_findings(ctx)


def ledger_total(payload):
    return sum(
        int(entry.get("count", 1))
        for per_file in payload.values()
        for entry in per_file.values()
    )


def print_folded(items):
    counts = Counter(f.signal for f in items)
    for signal, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  - {signal}: {n}")


def print_findings(items):
    for f in items:
        where = f.file or "(项目级)"
        print(f"  - [{f.signal}] {where}: {f.detail}")


if mode == "baseline":
    try:
        payload = read_shape_baseline(project_root)
    except ShapeBaselineError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(2)
    print(f"📋 ADR 形态基线：{len(payload)} 个文件 / {ledger_total(payload)} 项冻结 finding")
    for name in sorted(payload):
        frozen = ", ".join(
            f"{signal}×{int(entry.get('count', 1))}"
            for signal, entry in sorted(payload[name].items())
        )
        print(f"  - {name}: {frozen}")
    sys.exit(0)

if mode == "diff":
    try:
        baseline = read_shape_baseline(project_root, require_non_empty=False)
        new = diff_shape_findings(findings, baseline)
    except ShapeBaselineError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(2)
    if not new:
        print(f"✓ ADR 形态增量门通过（存量 {len(findings)} 项已冻结，新增 0）")
        sys.exit(0)
    print(f"❌ ADR 形态新增 debt（{len(new)} 项，基线外）：")
    if summary:
        print_folded(new)
    else:
        print_findings(new)
    print("  修掉新增项后不需要动基线；基线只在新债被消灭时才缩小。")
    sys.exit(1)

if mode == "write":
    try:
        payload = write_shape_baseline(project_root, findings)
    except ShapeBaselineError as exc:
        print(f"❌ 拒绝写入基线：{exc}", file=sys.stderr)
        sys.exit(1)
    print(f"✓ 基线已写入：{len(payload)} 个文件 / {ledger_total(payload)} 项冻结 finding")
    sys.exit(0)

if not findings:
    print("✓ ADR 形态检查通过")
    sys.exit(0)

if summary:
    print(f"⚠️  ADR 形态越界（{len(findings)} 项，按信号折叠）：")
    print_folded(findings)
else:
    print(f"⚠️  ADR 形态越界（{len(findings)} 项）：")
    print_findings(findings)

# 3 = 有发现（不是错误）—— bash 侧据此决定是否按 --strict 失败
sys.exit(3)
PYEOF
rc=$?

case "$rc" in
  0) exit 0 ;;
  3) if [ "$STRICT" -eq 1 ]; then exit 1; fi; exit 0 ;;
  *) exit "$rc" ;;
esac
