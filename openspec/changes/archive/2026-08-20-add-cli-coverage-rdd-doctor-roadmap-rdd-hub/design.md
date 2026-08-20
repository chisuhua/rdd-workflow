## Context

当前 `rddf` CLI 暴露 22 个子命令，但 `skills/` 目录下 28 个 skill 中仅 10 个有 CLI 入口。用户必须通过 `bash skills/<name>/scripts/<script>.sh [--args]` 调用无 CLI 暴露的 skill，路径不一致且不易发现。

本 change 为 3 个核心 skill 各补一个薄 CLI wrapper：

- `rdd-doctor` — 只读诊断工具（8 个 category）
- `roadmap` — 路线图 migrate + validate-fragments
- `rdd-hub-bootstrap` — Hub 仓库初始化

## Goals / Non-Goals

**Goals:**
- 为 `rdd-doctor` 暴露 `rddf doctor [--json] [--category <name>] [--quiet] [--version]`
- 为 `roadmap` 暴露 `rddf roadmap <sub> [--args]` (migrate / validate-fragments)
- 为 `rdd-hub-bootstrap` 暴露 `rddf rdd-hub-bootstrap [init|status|...] [--dry-run|--yes|--org|--repo]`
- 透传 exit code 0/1/2/3
- 所有 10 个 AC 测试通过

**Non-Goals:**
- 修改 skill 内部 Python/Bash 逻辑
- 把其他 15 个 skill（execute / propose / guide-* 等）暴露 CLI
- Python-only 重写（本次仅薄包装）

## Decisions

### 1. 薄包装模式 (thin wrapper)

每个 `_cmd.py` 5-30 行，转发到 `bash skills/<name>/scripts/<script>.sh "$@"`。

**Alternatives considered:**
- Python-only 重写：拒绝，成本高且风险大（doctor 含复杂 dispatcher，roadmap 含 awk/bash 特性，bootstrap 含 gh CLI）
- 全部集成到 `_lib/cli/` 统一调度：拒绝，现有架构已是 `cmd_<name>(args)` 模式，不应改动

### 2. 入口命名

- `rddf doctor`（不是 `rdd-doctor`，短且与 skill 命名一致）
- `rddf roadmap`（直接对齐 skill 名）
- `rddf rdd-hub-bootstrap`（完整对齐 skill 名，非缩写）

**Alternatives considered:**
- `rddf rdd-hub` 或 `rddf hub`: 拒绝，与 `sync-hub` / `watch-hub` 命名风格不一致，且 `rdd-hub-bootstrap` 已有文档

### 3. exit code 透传

每个 wrapper 通过 `subprocess.run(...).returncode` 或 `return $?` 透传底层脚本的退出码。

**Alternatives considered:**
- 统一映射为 0/1: 拒绝，丢失 `rdd-doctor` 2/3 的语义（skip/error）

## Risks / Trade-offs

- bash PATH 找不到 skill scripts: 用 `__file__` 解析 repo root 相对路径，不依赖 `PWD`
- exit code 透传漏: `cmd_doctor()` 必须 `return subprocess.run(...).returncode`
- Performance: < 100ms 子进程启动开销（可接受）
- 回滚: 单 commit revert，< 5 分钟