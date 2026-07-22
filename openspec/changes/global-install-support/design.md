## Design

install.sh 检测 `--global` 参数后的行为：
1. Symlink skills/ 到 ~/.agents/skills/spec-workflow/
2. pip install --user -r requirements.txt
3. 写入 .pth 文件到 site-packages 目录
4. Symlink rddf CLI 到 ~/.local/bin/rddf

保持向后兼容：不带参数时行为不变（项目安装）。
