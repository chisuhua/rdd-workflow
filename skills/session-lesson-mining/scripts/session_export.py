#!/usr/bin/env python3
"""把 opencode 的会话历史导出成**归一化 JSONL**（供 mine_lessons.py / 人工复核）。

为什么要先导出：会话库是 sqlite，且 V1（message/part）与 V2（session_v2/session_message）
两套 schema 并存；后续的教训挖掘与用例生成都希望吃**同一种**行格式。

用法：
    python3 session_export.py --list                     # 列出会话（id / 时间 / 目录 / 标题）
    python3 session_export.py --last 3 --out /tmp/x.jsonl
    python3 session_export.py --session ses_xxx --out -
    python3 session_export.py --since 2026-11-19 --out /tmp/x.jsonl

行格式（每行一个 part，按 (session, seq) 排序）：
    {"session","seq","msg","ts","role","agent","kind","tool","input","exit","status","text"}
      kind   : text | reasoning | tool
      tool   : bash/shell/read/edit/write/...（kind=tool 时）
      input  : 命令或文件路径等（截断到 --max-text）
      exit   : shell 退出码（有则给）
      text   : 文本 / 推理 / 工具输出（截断到 --max-text）

只用标准库；不修改会话库。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime

DEFAULT_DB = os.path.expanduser(
    os.environ.get("OPENCODE_DB")
    or os.path.join(
        os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
        "opencode/opencode.db",
    )
)


def connect(db: str) -> sqlite3.Connection:
    if not os.path.exists(db):
        sys.exit(f"找不到会话库：{db}（用 --db 指定，或设 OPENCODE_DB）")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def has_table(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "select 1 from sqlite_master where type='table' and name=?", (name,)
    ).fetchone()
    return row is not None


def iso(ms: int | None) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def list_sessions(con: sqlite3.Connection, last: int | None) -> list[dict]:
    if has_table(con, "session_v2"):
        # V2：session_v2 有 title/directory/time_updated；消息在 session_message
        rows = con.execute(
            """select s.id, s.title, s.directory, s.time_created,
                      (select count(*) from session_message m
                        where m.session_id = s.id and m.type='user') as turns
                 from session_v2 s
                order by s.time_created desc
                limit ?""",
            (last or 50,),
        ).fetchall()
        out = []
        for r in rows:
            if r["turns"] == 0:
                continue
            out.append(
                {
                    "id": r["id"],
                    "title": r["title"] or "",
                    "directory": r["directory"] or "",
                    "time": iso(r["time_created"]),
                    "turns": r["turns"],
                    "schema": "v2",
                }
            )
        return out
    rows = con.execute(
        """select s.id, s.title, s.directory, s.time_created,
                  (select count(*) from message m
                    where m.session_id = s.id and json_extract(m.data,'$.role')='user') as turns
             from session s order by s.time_created desc limit ?""",
        (last or 50,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "title": r["title"] or "",
            "directory": r["directory"] or "",
            "time": iso(r["time_created"]),
            "turns": r["turns"],
            "schema": "v1",
        }
        for r in rows
        if r["turns"] > 0
    ]


def _out_text(content) -> str:
    """把工具的 content 数组拼成文本（V2 的 state.content / V1 的 output）。"""
    if isinstance(content, str):
        return content
    chunks = []
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    chunks.append(c.get("text", ""))
                elif "text" in c:
                    chunks.append(str(c["text"]))
    return "\n".join(chunks)


def _clip(s: str, n: int) -> str:
    """n <= 0 ⇒ 不截断（挖掘时用 0：失败行可能出现在输出中段）。"""
    if s is None:
        return ""
    s = str(s)
    if n <= 0 or len(s) <= n:
        return s
    return s[:n] + f"…(+{len(s) - n})"


def _clip_tool(s: str, n: int, tail: int = 800) -> str:
    """工具输出保留**头 + 尾**：报错常常打在末尾（测试跑完才汇总），只截头会漏掉它。"""
    if s is None:
        return ""
    s = str(s)
    if n <= 0 or len(s) <= n:
        return s
    kept_tail = min(tail, max(len(s) - n, 0))
    return s[:n] + f"\n…(截断 {len(s) - n - kept_tail} 字)…\n" + (s[-kept_tail:] if kept_tail else "")


def export_v2(con, sessions: list[str], max_text: int, include_reasoning: bool):
    for sid in sessions:
        rows = con.execute(
            """select id, type, seq, time_created, data from session_message
                where session_id=? order by seq""",
            (sid,),
        ).fetchall()
        for r in rows:
            data = json.loads(r["data"] or "{}")
            role = r["type"]
            agent = data.get("agent", "")

            # ⚠ user 行没有 content 数组，正文在 data.text 里（V2 实测）。
            #   初版只遍历 content ⇒ 用户消息全被丢掉 ⇒ 纠正类检测器恒零。
            if role == "user":
                text = data.get("text") or _out_text(data.get("content"))
                if text:
                    yield {
                        "session": sid,
                        "seq": r["seq"],
                        "msg": r["id"],
                        "ts": r["time_created"],
                        "role": role,
                        "agent": agent,
                        "kind": "text",
                        "tool": "",
                        "input": "",
                        "exit": None,
                        "status": "",
                        "text": _clip(text, max_text),
                    }
                continue

            for part in data.get("content", []) or []:
                kind = part.get("type")
                if kind == "reasoning" and not include_reasoning:
                    continue
                rec = {
                    "session": sid,
                    "seq": r["seq"],
                    "msg": r["id"],
                    "ts": r["time_created"],
                    "role": role,
                    "agent": agent,
                    "kind": kind,
                    "tool": "",
                    "input": "",
                    "exit": None,
                    "status": "",
                    "text": "",
                }
                if kind == "text":
                    rec["text"] = _clip(part.get("text", ""), max_text)
                elif kind == "reasoning":
                    rec["text"] = _clip(part.get("text", ""), max_text)
                elif kind == "tool":
                    st = part.get("state") or {}
                    rec["tool"] = part.get("name", "")
                    rec["status"] = st.get("status", "")
                    inp = st.get("input") or {}
                    if isinstance(inp, dict):
                        rec["input"] = _clip(
                            inp.get("command")
                            or inp.get("filePath")
                            or inp.get("path")
                            or json.dumps(inp, ensure_ascii=False),
                            max_text,
                        )
                    rec["exit"] = (st.get("metadata") or {}).get("exit")
                    if st.get("status") == "error":
                        rec["text"] = _clip(str(st.get("error", "")), max_text)
                    else:
                        rec["text"] = _clip_tool(_out_text(st.get("content")), max_text)
                else:
                    continue
                yield rec


def export_v1(con, sessions: list[str], max_text: int, include_reasoning: bool):
    for sid in sessions:
        rows = con.execute(
            """select p.id, p.time_created, p.data, m.data as mdata
                 from part p join message m on m.id = p.message_id
                where p.session_id=? order by p.time_created, p.id""",
            (sid,),
        ).fetchall()
        for i, r in enumerate(rows):
            part = json.loads(r["data"] or "{}")
            mdata = json.loads(r["mdata"] or "{}")
            kind = part.get("type")
            if kind == "reasoning" and not include_reasoning:
                continue
            if kind not in ("text", "reasoning", "tool"):
                continue
            rec = {
                "session": sid,
                "seq": i,
                "msg": "",
                "ts": r["time_created"],
                "role": mdata.get("role", ""),
                "agent": mdata.get("agent", ""),
                "kind": kind,
                "tool": "",
                "input": "",
                "exit": None,
                "status": "",
                "text": "",
            }
            if kind == "tool":
                st = part.get("state") or {}
                rec["tool"] = part.get("tool", "")
                rec["status"] = st.get("status", "")
                inp = st.get("input") or {}
                rec["input"] = _clip(
                    (inp.get("command") if isinstance(inp, dict) else None)
                    or json.dumps(inp, ensure_ascii=False),
                    max_text,
                )
                rec["exit"] = (st.get("metadata") or {}).get("exit")
                rec["text"] = (
                    _clip(str(st.get("error", "")), max_text)
                    if st.get("status") == "error"
                    else _clip_tool(_out_text(st.get("output") or st.get("content")), max_text)
                )
            else:
                rec["text"] = _clip(part.get("text", ""), max_text)
            yield rec


def main() -> int:
    ap = argparse.ArgumentParser(description="导出 opencode 会话历史为归一化 JSONL")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--list", action="store_true", help="列出会话后退出")
    ap.add_argument("--session", action="append", default=[], help="会话 id（可重复）")
    ap.add_argument("--last", type=int, default=0, help="最近 N 个会话")
    ap.add_argument("--since", default="", help="只导出该日期之后的会话（YYYY-MM-DD）")
    ap.add_argument("--out", default="-", help="输出文件（- = stdout）")
    ap.add_argument("--max-text", type=int, default=2000)
    ap.add_argument("--include-reasoning", action="store_true")
    args = ap.parse_args()

    con = connect(args.db)
    if args.list:
        for s in list_sessions(con, args.last or 30):
            print(f"{s['id']}\t{s['time']}\t{s['turns']:>4} turns\t{s['directory']}\t{s['title'][:60]}")
        return 0

    sessions = list(args.session)
    if args.since or args.last:
        cand = list_sessions(con, args.last or 500)
        if args.since:
            cand = [s for s in cand if s["time"][:10] >= args.since]
        for s in cand:
            if s["id"] not in sessions:
                sessions.append(s["id"])
    if not sessions:
        sys.exit("没有选中会话：用 --session / --last / --since 指定（或先 --list 看看）")

    gen = export_v2 if has_table(con, "session_message") else export_v1
    buf = []
    for rec in gen(con, sessions, args.max_text, args.include_reasoning):
        buf.append(json.dumps(rec, ensure_ascii=False))
    payload = "\n".join(buf) + ("\n" if buf else "")
    if args.out == "-":
        sys.stdout.write(payload)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"导出 {len(buf)} 行 → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
