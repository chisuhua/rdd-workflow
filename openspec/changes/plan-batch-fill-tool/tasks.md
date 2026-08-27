# plan-batch-fill-tool — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `plan_batch_fill.py` 批量 fill 核心 (Python)
- [x] Task 2: 6 个 unit test 全部通过 (含 invalid name 累积到 result.failed 而非 raise)
- [x] Task 3: iteration.json 自动 status planned → proposed (atomic write via core.atomic_write.atomic_write_json)
- [x] Task 4: idempotent — 跳过已 fill 的 change (design.md 已存在)
- [x] Task 5: `_validate_change_name` 拒绝 path traversal (../escape 等)
- [x] Task 6: `bash tests/scripts/report_regression.sh` 不增加新 failure
