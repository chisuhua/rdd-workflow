# Spec-Workflow 修复计划

## 任务概述
根据 CODE_REVIEW.md 审查报告，修复 40 个代码质量问题。

## 修复优先级

### Wave 1: P0 - Critical Bugs (5个)
1. **propose.md:93** - Python f-string 语法错误
2. **propose.md:81** - Shell 变量在 Python f-string 中不展开
3. **execute.md:102, status.md:376, guide.md:268** - wc -l 空字符串返回1
4. **多处** - 未加引号的变量扩展导致空格路径问题
5. **status.md:345** - git worktree remove 空路径风险

### Wave 2: P1 - 平台兼容性 (5个)
6. **plan.md:72** - GNU-specific stat -c
7. **INSTALL.md:83** - GNU-specific readlink -f
8. **execute.md:179** - nproc 在 macOS 不存在
9. **多处** - Git worktree 列表解析空格路径问题
10. **status.md:134** - 算术展开空值风险

### Wave 3: P2 - 健壮性改进 (10个)
11. **install.sh:6** - 添加 set -euo pipefail
12. **多处** - &> 改为 POSIX 兼容写法
13. **propose.md:166** - JSON 构造脆弱
14. **INSTALL.md:38** - read -p bash 特有
15. **guide.md:154** - grep regex 元字符问题
16. **guide.md:360** - git show HEAD 空仓库
17. **guide.md:632** - cd 进入 worktree 无错误检查
18. **deps.md:489** - grep 单引号在双引号中问题
19. **多处** - mktemp /tmp 硬编码
20. **plan.md:46** - git branch --format 兼容性

### Wave 4: P3 - 一致性修复 (10个)
21. **所有文件** - 统一技能命名
22. **所有文件** - 统一 PROJECT_ROOT 定义
23. **package.json:3** - 版本格式 "1.0" → "1.0.0"
24. **package.json:15-17** - 非 npm 依赖移到 engines
25. **guide.md vs USAGE.md** - 状态文件格式一致
26. **多处** - 替换 ls 解析为 glob
27. **多处** - grep -E 替代 \|
28. **多处** - 添加错误处理模板
29. **deps.md:67** - 数组赋值空格问题
30. **guide.md:833** - git merge --ff-only 缺少回退

### Wave 5: 逻辑修复 (10个)
31. **guide.md:602** - worktree 按路径而非分支检测
32. **guide.md:840** - git branch -d 可能失败
33. **execute.md:312** - awk 退出码检查在重定向后
34. **guide.md:864** - grep "status: 待创建" 格式假设
35. **guide.md:833** - git merge --ff-only 缺少回退处理
36. **status.md:287** - git checkout 在子shell中不影响父shell
37. **deps.md:104** - grep -oE GNU-specific
38. **deps.md:143** - ${!var} bash特有
39. **多处** - 硬编码项目路径 /workspace/project/CppHDL
40. **status.md:137** - git worktree list 解析空格路径

## 实施策略
- 每个 wave 独立修复，不依赖其他 wave
- 每修复一个问题，验证其上下文
- 保留原始代码备份
- 所有修改使用 Edit 工具精确修改
