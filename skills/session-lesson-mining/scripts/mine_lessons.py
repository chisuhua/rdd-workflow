#!/usr/bin/env python3
"""从归一化会话 JSONL 里挖「候选教训」——只产出候选，不产出结论。

设计原则（为什么是"候选"）：
  - 会话里能机械识别的只是**现象**（命令失败、测试红、用户纠正、同一命令重试）；
  - "这暴露了什么教训 / 该不该固化成判据" 仍需人（或 AI 复核阶段）判断；
  - 因此本脚本只输出**带定位的候选清单**，交给 SKILL.md 的 P2/P3 处理。

用法：
    python3 session_export.py --since 2026-11-19 --out /tmp/s.jsonl
    python3 mine_lessons.py --in /tmp/s.jsonl --out /tmp/lessons.md
    python3 mine_lessons.py --in /tmp/s.jsonl --detector failure_signature --format json

检测器（都只看单行；跨行关系见 retry_loop）：
    tool_error         工具状态 error，或 shell 退出码非 0
    failure_signature  输出里出现典型失败行（command not found / not ok / Traceback / …）
    test_failure       测试框架失败行（bats `not ok` / bun `fail` / pytest `FAILED`）
    retry_loop         同一 (tool, input) 在同一会话里重复 ≥3 次（改法没生效 / 反复试）
    user_correction    用户消息含纠正语（不对 / 错了 / 还是 / 又 / 我说过 …）
    self_correction    assistant 文本/推理含自我纠正语（我错 / 漏了 / 搞错 …）
    guard_selfhit      判据命中"自己"的形态（自匹配 / 空转 / 假绿 / 用例名被求值 …）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict

FAILURE_PATTERNS = [
    (re.compile(r"command not found"), "命令不存在"),
    (re.compile(r"No such file or directory"), "路径不存在"),
    (re.compile(r"Permission denied"), "权限拒绝"),
    (re.compile(r"invalid format character"), "格式串/转义错误"),
    (re.compile(r"Traceback \(most recent call last\)"), "Python 异常"),
    (re.compile(r"\bENOENT\b|\bETIMEDOUT\b"), "Node/系统错误码"),
    (re.compile(r"SyntaxError|TypeError|ReferenceError"), "脚本语法/类型错误"),
    (re.compile(r"^error: |^ERROR: ", re.M), "编译器/工具错误"),
]

TEST_PATTERNS = [
    (re.compile(r"^not ok \d+", re.M), "bats 用例失败"),
    (re.compile(r"^\s*✗", re.M), "用例失败（✗）"),
    (re.compile(r"^\s*\d+ fail\b", re.M), "bun 失败计数"),
    (re.compile(r"^FAILED ", re.M), "pytest 失败"),
    (re.compile(r"AssertionError"), "断言失败"),
]

USER_CORRECTION = re.compile(
    r"不对|错了|不是这样|还是不行|还是没有|又(犯|出|错|来)|我说过|别再|应该(是|用)|"
    r"你(搞错|漏了|没)|重新|再看(一下|看)|这不是我要"
)

SELF_CORRECTION = re.compile(
    r"我(的)?错|我犯|我漏|我误|搞错(了)?|搞混|漏了|没注意到|疏忽|"
    r"自捕|同一(个)?教训|正好是|这也是|又踩"
)

GUARD_SELFHIT = re.compile(
    r"自匹配|空转|假绿|恒绿|命中自身|匹配到自身|被当成|被求值|无效豁免|误报"
)

DETECTORS = [
    "tool_error",
    "failure_signature",
    "test_failure",
    "retry_loop",
    "user_correction",
    "self_correction",
    "guard_selfhit",
]


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def loc(rec) -> str:
    return f"{rec['session']}#seq{rec['seq']}"


def one_line(s: str, n: int = 180) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[:n] + "…"


def scan(recs):
    """返回 {detector: [candidate, ...]}；candidate = dict(detector, loc, when, why, evidence)"""
    hits = defaultdict(list)
    seen_inputs = Counter()
    norm_input = {}

    for rec in recs:
        tool = rec.get("tool") or ""
        inp = (rec.get("input") or "").strip()
        text = rec.get("text") or ""
        exit_code = rec.get("exit")
        status = rec.get("status") or ""

        # retry_loop 的键：命令去掉明显的变量部分（时间戳/随机后缀不处理，保持简单）
        if tool and inp:
            key = (rec["session"], tool, re.sub(r"\s+", " ", inp))
            seen_inputs[key] += 1
            norm_input[key] = rec

        if rec.get("kind") == "tool":
            if status == "error" or (isinstance(exit_code, int) and exit_code != 0):
                why = f"status={status} exit={exit_code}"
                hits["tool_error"].append(
                    dict(detector="tool_error", loc=loc(rec), when=rec.get("ts"),
                         why=why, evidence=one_line(inp or text))
                )
            for rx, label in FAILURE_PATTERNS:
                m = rx.search(text)
                if m:
                    line = text[max(0, m.start() - 60): m.end() + 60]
                    hits["failure_signature"].append(
                        dict(detector="failure_signature", loc=loc(rec), when=rec.get("ts"),
                             why=label, evidence=one_line(line))
                    )
                    break
            for rx, label in TEST_PATTERNS:
                if rx.search(text):
                    hits["test_failure"].append(
                        dict(detector="test_failure", loc=loc(rec), when=rec.get("ts"),
                             why=label, evidence=one_line(text))
                    )
                    break

        if rec.get("role") == "user" and text:
            m = USER_CORRECTION.search(text)
            if m:
                hits["user_correction"].append(
                    dict(detector="user_correction", loc=loc(rec), when=rec.get("ts"),
                         why=f"纠正语「{m.group(0)}」", evidence=one_line(text))
                )

        if rec.get("role") == "assistant" and text:
            m = SELF_CORRECTION.search(text)
            if m:
                hits["self_correction"].append(
                    dict(detector="self_correction", loc=loc(rec), when=rec.get("ts"),
                         why=f"自我纠正「{m.group(0)}」", evidence=one_line(text))
                )
            m2 = GUARD_SELFHIT.search(text)
            if m2:
                hits["guard_selfhit"].append(
                    dict(detector="guard_selfhit", loc=loc(rec), when=rec.get("ts"),
                         why=f"判据自身形态「{m2.group(0)}」", evidence=one_line(text))
                )

    # 跨行：重复命令（只报第 3 次起的位置，前两次作为"重试"证据）
    for (sid, tool, inp), n in seen_inputs.items():
        if n >= 3:
            rec = norm_input[(sid, tool, inp)]
            hits["retry_loop"].append(
                dict(detector="retry_loop", loc=loc(rec), when=rec.get("ts"),
                     why=f"同一 {tool} 输入重复 {n} 次", evidence=one_line(inp))
            )

    for det in hits:
        hits[det].sort(key=lambda c: (c["loc"], c["when"] or 0))
    return hits


def aggregate(hits, top: int, min_count: int):
    """按 (detector, 归一化证据) 合并同类候选，按出现次数降序。

    为什么必须聚合：一次 red-green 循环会产生几十条同类失败；不聚合的话
    "候选 1591 条"里 841 条都是同一类测试红 —— 反而淹没真正的信号。
    """
    out = defaultdict(lambda: {"count": 0, "first": None, "last": None, "whys": Counter(), "evidence": ""})
    for det, rows in hits.items():
        for c in rows:
            # 纠正类天然一次性（每条措辞都不同）⇒ 按 marker 聚合；其余按证据文本聚合
            key = (
                c["why"]
                if det in ("user_correction", "self_correction", "guard_selfhit")
                else re.sub(r"\s+", " ", c["evidence"]).strip()[:120]
            )
            cls = out[(det, key)]
            cls["count"] += 1
            cls["whys"][c["why"]] += 1
            if cls["first"] is None:
                cls["first"] = c["loc"]
                cls["evidence"] = c["evidence"]
            cls["last"] = c["loc"]
    agg = defaultdict(list)
    for (det, _key), cls in out.items():
        if cls["count"] < min_count:
            continue
        agg[det].append(dict(detector=det, count=cls["count"], first=cls["first"],
                             last=cls["last"], why=cls["whys"].most_common(1)[0][0],
                             evidence=cls["evidence"]))
    for det in agg:
        agg[det].sort(key=lambda c: -c["count"])
        del agg[det][top:]
    return agg


def render_md(hits, path: str) -> str:
    total = sum(len(v) for v in hits.values())
    out = [f"# 会话教训候选清单\n", f"> 来源：`{path}`",
           f"> 候选总数：{total} 类（**候选 ≠ 结论**，需 P2 复核）\n"]
    out.append("| 检测器 | 候选数 |")
    out.append("|---|---|")
    for det in DETECTORS:
        out.append(f"| `{det}` | {len(hits.get(det, []))} |")
    out.append("")
    for det in DETECTORS:
        rows = hits.get(det, [])
        if not rows:
            continue
        out.append(f"## {det}（{len(rows)} 类）\n")
        out.append("| 次数 | 首次定位 | 判据 | 证据（截断） |")
        out.append("|---|---|---|---|")
        for c in rows:
            ev = str(c["evidence"]).replace("|", "\\|")
            why = str(c["why"]).replace("|", "\\|")
            out.append(f"| {c['count']} | `{c['first']}` | {why} | {ev} |")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="会话 JSONL → 候选教训清单")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", default="-")
    ap.add_argument("--detector", action="append", default=[],
                    help=f"只看某检测器（可重复）：{', '.join(DETECTORS)}")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--top", type=int, default=40, help="每个检测器最多输出多少类")
    ap.add_argument("--min-count", type=int, default=1, help="只保留出现 ≥N 次的类别")
    args = ap.parse_args()

    recs = list(load(args.inp))
    if not recs:
        sys.exit(f"{args.inp} 里没有记录")
    hits = scan(recs)
    if args.detector:
        hits = {k: v for k, v in hits.items() if k in args.detector}
    raw_total = sum(len(v) for v in hits.values())
    hits = aggregate(hits, args.top, args.min_count)

    if args.format == "json":
        payload = json.dumps(hits, ensure_ascii=False, indent=2)
    else:
        payload = render_md(hits, args.inp)
    if args.out == "-":
        sys.stdout.write(payload)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"候选 {raw_total} 条 → 聚合 {sum(len(v) for v in hits.values())} 类 → {args.out}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
