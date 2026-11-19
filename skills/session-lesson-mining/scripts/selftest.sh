#!/usr/bin/env bash
# 自测：两个脚本各自必须有「反例必报、正例不误报」的判别力。
#
#   bash scripts/selftest.sh
#
# 为什么要自测：本 skill 的产出是**判据**；若挖掘器自己恒绿（或恒红），
# 整条流水线就没有意义。故用合成夹具把每个检测器都点一次。
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FAIL=0

note() { printf '%s\n' "$*"; }
bad() { printf '✗ %s\n' "$*" >&2; FAIL=$((FAIL + 1)); }

# ── 1) miner：每个检测器都必须被夹具触发 ─────────────────────
cat > "$TMP/fixture.jsonl" <<'EOF'
{"session":"s1","seq":1,"msg":"m1","ts":1,"role":"user","agent":"","kind":"text","tool":"","input":"","exit":null,"status":"","text":"这样不对，你再看看之前的结论"}
{"session":"s1","seq":2,"msg":"m2","ts":2,"role":"assistant","agent":"build","kind":"tool","tool":"shell","input":"foo","exit":1,"status":"completed","text":"bash: foo: command not found"}
{"session":"s1","seq":3,"msg":"m3","ts":3,"role":"assistant","agent":"build","kind":"tool","tool":"shell","input":"pytest -q","exit":1,"status":"completed","text":"not ok 3 - some case\n1 fail"}
{"session":"s1","seq":4,"msg":"m4","ts":4,"role":"assistant","agent":"build","kind":"tool","tool":"write","input":"/tmp/x","exit":null,"status":"error","text":"File not found: /tmp/x"}
{"session":"s1","seq":5,"msg":"m5","ts":5,"role":"assistant","agent":"build","kind":"text","tool":"","input":"","exit":null,"status":"","text":"我又踩了同一个坑：漏了证据指针"}
{"session":"s1","seq":6,"msg":"m6","ts":6,"role":"assistant","agent":"build","kind":"text","tool":"","input":"","exit":null,"status":"","text":"这个判据会自匹配，导致假绿"}
{"session":"s1","seq":7,"msg":"m7","ts":7,"role":"assistant","agent":"build","kind":"tool","tool":"shell","input":"git status","exit":0,"status":"completed","text":"clean"}
{"session":"s1","seq":8,"msg":"m8","ts":8,"role":"assistant","agent":"build","kind":"tool","tool":"shell","input":"git status","exit":0,"status":"completed","text":"clean"}
{"session":"s1","seq":9,"msg":"m9","ts":9,"role":"assistant","agent":"build","kind":"tool","tool":"shell","input":"git status","exit":0,"status":"completed","text":"clean"}
EOF

python3 "$HERE/mine_lessons.py" --in "$TMP/fixture.jsonl" --out "$TMP/hits.json" --format json >/dev/null 2>&1 \
    || bad "mine_lessons.py 运行失败"

python3 - "$TMP/hits.json" <<'PY' || FAIL=$((FAIL + 1))
import json, sys
hits = json.load(open(sys.argv[1]))
want = ["tool_error", "failure_signature", "test_failure", "retry_loop",
        "user_correction", "self_correction", "guard_selfhit"]
missing = [d for d in want if not hits.get(d)]
if missing:
    print(f"✗ 检测器未触发（该检测器恒绿）：{missing}", file=sys.stderr)
    raise SystemExit(1)
for d in want:
    print(f"✓ {d}: {len(hits[d])} 类")
PY

# 正例不误报：干净的工具体不应触发 tool_error / failure_signature
python3 - "$HERE" "$TMP" <<'PY' || FAIL=$((FAIL + 1))
import json, subprocess, sys, os
here, tmp = sys.argv[1], sys.argv[2]
clean = os.path.join(tmp, "clean.jsonl")
rows = [{"session": "s2", "seq": 1, "msg": "m", "ts": 1, "role": "assistant", "agent": "build",
         "kind": "tool", "tool": "shell", "input": "ls", "exit": 0, "status": "completed",
         "text": "a.txt\nb.txt"},
        {"session": "s2", "seq": 2, "msg": "m2", "ts": 2, "role": "assistant", "agent": "build",
         "kind": "text", "tool": "", "input": "", "exit": None, "status": "",
         "text": "一切正常，测试 42 pass / 0 fail。"}]
open(clean, "w").write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
out = subprocess.run([sys.executable, os.path.join(here, "mine_lessons.py"), "--in", clean,
                      "--format", "json"], capture_output=True, text=True)
hits = json.loads(out.stdout)
noisy = [d for d in ("tool_error", "failure_signature", "test_failure", "retry_loop") if hits.get(d)]
if noisy:
    print(f"✗ 正例被误报：{noisy}", file=sys.stderr)
    raise SystemExit(1)
print("✓ 干净会话不误报（tool_error/failure_signature/test_failure/retry_loop 均空）")
PY

# ── 2) exporter：V2 schema 下 user 正文与 exit 码都要在 ──────
DB="$TMP/fake.db"
sqlite3 "$DB" <<'SQL'
create table session_v2 (id text primary key, title text, directory text, time_created integer);
create table session_message (id text primary key, session_id text, type text, seq integer,
                              time_created integer, time_updated integer, data text);
insert into session_v2 values ('ses_a','标题','/tmp',1000);
insert into session_message values ('m1','ses_a','user',1,1001,1001,
  '{"time":{"created":1001},"text":"用户正文必须被导出"}');
insert into session_message values ('m2','ses_a','assistant',2,1002,1002,
  '{"agent":"build","content":[{"type":"tool","name":"shell","state":{"status":"completed","input":{"command":"false"},"content":[{"type":"text","text":"boom"}],"metadata":{"exit":1}}}]}');
SQL
python3 "$HERE/session_export.py" --db "$DB" --session ses_a --max-text 0 --out "$TMP/out.jsonl" >/dev/null 2>&1 \
    || bad "session_export.py 运行失败"

python3 - "$TMP/out.jsonl" <<'PY' || FAIL=$((FAIL + 1))
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
users = [r for r in rows if r["role"] == "user" and "用户正文" in r["text"]]
tools = [r for r in rows if r["tool"] == "shell" and r["exit"] == 1]
if not users:
    print("✗ user 正文未被导出（V2 的 data.text 分支失效）", file=sys.stderr)
    raise SystemExit(1)
if not tools:
    print("✗ 工具 exit 码未被导出", file=sys.stderr)
    raise SystemExit(1)
print(f"✓ exporter: {len(rows)} 行、user 正文在、exit 码在")
PY

# ── 3) exporter：--max-text 0 必须是"不截断" ────────────────
python3 - "$TMP" <<'PY' || FAIL=$((FAIL + 1))
import json, subprocess, sys, os
tmp = sys.argv[1]
long_text = "A" * 5000 + "BOOM" + "B" * 5000
db = os.path.join(tmp, "fake2.db")
import sqlite3
con = sqlite3.connect(db)
con.execute("create table session_v2 (id text primary key, title text, directory text, time_created integer)")
con.execute("create table session_message (id text primary key, session_id text, type text, seq integer, time_created integer, time_updated integer, data text)")
con.execute("insert into session_v2 values ('ses_b','t','/tmp',1)")
con.execute("insert into session_message values ('m1','ses_b','assistant',1,1,1,?)",
            (json.dumps({"content": [{"type": "tool", "name": "shell",
                                      "state": {"status": "completed", "input": {"command": "x"},
                                                "content": [{"type": "text", "text": long_text}],
                                                "metadata": {"exit": 0}}}]}),))
con.commit(); con.close()
PY
python3 "$HERE/session_export.py" --db "$TMP/fake2.db" --session ses_b --max-text 0 --out "$TMP/o2.jsonl" >/dev/null 2>&1
if grep -q 'BOOM' "$TMP/o2.jsonl"; then
    note "✓ --max-text 0 不截断（中段内容保留）"
else
    bad "--max-text 0 丢掉了中段内容"
fi

if (( FAIL > 0 )); then
    printf '\n自测失败：%d 项\n' "$FAIL" >&2
    exit 1
fi
printf '\n自测通过：7 个检测器均能报出反例、干净会话不误报、导出器保留 user 正文/exit 码/中段内容。\n'
