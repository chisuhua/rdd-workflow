# add-deferral-registration-guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use skill_use("execute") to implement task-by-task.
> 详细 TDD 步骤见 `openspec/changes/add-deferral-registration-guard/tasks.md`（**执行真相源**）。

**Goal**：「另案立项」必须带登记载体（improvement slug 或 backlog 占位），否则 doctor 报出来；
存量噪音一次性登记（豁免清单入库），不反复出现。

**Architecture**（约定先行 ⇒ 扫描 ⇒ 接线）：

1. `_lib/deferral_registration.py`（新）：**约定单一真源** —— 措辞清单、两种豁免格式、
   目标语法、扫描器、豁免清单读写、豁免漂移检测；
2. `docs/architecture/deferral-registration.md`（新）：约定的**展开**（含全部措辞与两种格式）；
3. `skills/rdd-doctor/scripts/checks/deferral_registration_check.py`（新）：doctor category
   `deferral-registration`（WARNING 不阻断）+ 注册进 `_CHECKERS` + advisory 列表 +
   `skills/rdd-doctor/SKILL.md`；
4. `.rddf/deferral-exemptions.txt`（新，入库）：存量 33 个文件的豁免登记（可审计账本）；
5. `skills/rdd-planner/SKILL.md`：作者侧规则（指向约定文档，不复制清单）。

**Tech Stack**：Python 3.11 stdlib（`re` / `pathlib` / `dataclasses`），无新依赖。

**Plan verification**：每 task 红→绿；T4 Step 4 变异腿（措辞正则改窄 ⇒ AC1 红）；
收口 `./test.sh --gates` + `./test.sh --unit` + `openspec validate --strict` + 本仓零噪音核对。

---

## File Structure

| File | 责任 |
|---|---|
| `_lib/deferral_registration.py` | 约定常量 + `scan_text` / `scan_project` / `load_exemptions` / `stale_exemptions`。 |
| `docs/architecture/deferral-registration.md` | 约定文本（措辞清单 + 两种豁免格式 + 指引）。 |
| `skills/rdd-doctor/scripts/checks/deferral_registration_check.py` | doctor category（WARNING）。 |
| `skills/rdd-doctor/scripts/doctor_main.py` | 注册 category（`_CHECKERS` + advisory 列表）。 |
| `skills/rdd-doctor/SKILL.md` | usage 行的 category 列表 + 类别表新增一行。 |
| `.rddf/deferral-exemptions.txt` | 存量豁免清单（入库）。 |
| `skills/rdd-planner/SKILL.md` | 作者侧规则（指向约定文档）。 |
| `tests/unit/test_deferral_registration.py`（新） | AC1–AC6。 |

## 代码形状（关键片段）

```python
# _lib/deferral_registration.py
DEFERRAL_PHRASES: tuple[str, ...] = ("另案", "另立", "另行立项", "后续另案")
REGISTERED_FORM = "另案（已登记：<improvement-slug>）"
BACKLOG_FORM = "另案（backlog：<topic>）"
TARGET_MARKER_RE = re.compile(r"(?:已登记|backlog)\s*[:：]\s*[^）\n]+")
SCAN_DIRS = (".rddf/improvements", ".rddf/reviews")
EXEMPTIONS_FILE = ".rddf/deferral-exemptions.txt"


def scan_text(text: str, path: str = "") -> list[DeferralFinding]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        phrases = _phrases_in(line)
        if not phrases or is_registered(line):
            continue
        findings.append(DeferralFinding(path, lineno, phrases[0], line.strip()[:120]))
    return findings
```

```python
# skills/rdd-doctor/scripts/checks/deferral_registration_check.py
def run(project_root: str) -> list[Finding]:
    findings = []
    exemptions = load_exemptions(project_root)
    for item in scan_project(project_root, exemptions):
        findings.append(Finding(
            severity=Severity.WARNING,
            category=_CATEGORY,
            file=item.path,
            line=item.line,
            message=(f"deferral 「{item.phrase}」 没有登记目标 ⇒ "
                     f"补「另案（已登记：<slug>）」或「另案（backlog：<topic>）」"),
        ))
    for rel in stale_exemptions(project_root, exemptions):
        findings.append(Finding(
            severity=Severity.WARNING,
            category=_CATEGORY,
            file=EXEMPTIONS_FILE,
            message=f"豁免条目已不再命中，可从清单删除：{rel}",
        ))
    return findings
```

## 边界（不做什么）

- 不自动创建 improvement 文件（只报警）；
- 不改 improvement 生命周期状态机；
- 不扫代码注释里的 TODO（`review-debt` category 的地盘）；
- 不回改存量文档（存量只登记豁免清单）。

## 执行顺序

T1（约定 + 扫描器）→ T2（约定文本 + 作者规则）→ T3（doctor category + 豁免清单）→
T4（划界 + 变异腿）→ T5（回归 + 零噪音核对）→ T6（收口）。
