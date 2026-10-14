# 小组协作

仓库地址：https://github.com/sadfaxzda/gnss-workbench

本仓库保持私有。受邀成员先登录自己的 GitHub 账号，打开 [邀请页面](https://github.com/sadfaxzda/gnss-workbench/invitations) 并接受邀请，之后即可查看、克隆和提交代码。写权限允许参与开发，不需要仓库管理权限。

## 首次运行

安装 Git、uv、Node.js 24 和 pnpm 11，随后按 [README 快速运行](README.md#快速运行) 操作。若 HTTPS 克隆提示没有权限，先确认已接受邀请，并使用受邀账号完成 GitHub 身份验证；安装了 GitHub CLI 的成员可以运行 `gh auth login`。

网页在每个人自己的电脑上运行：`http://127.0.0.1:8000`。这个地址不是其他队友能够直接访问的在线演示地址。首次同步依赖需要联网。

## 提交修改

建议每项任务使用独立分支，提交后发起 Pull Request，说明改了什么、为什么改、如何验证：

```bash
git switch main
git pull --ff-only
git switch -c feature/your-task
# 完成修改后，把需要提交的文件明确加入暂存区
git add path/to/changed-file
git commit -m "Describe the change"
git push -u origin feature/your-task
```

在 GitHub 上发起 Pull Request，等待自动检查完成并由另一位成员阅读后合并。合并前重新检查修改范围，避免提交个人凭证、本地运行记录、虚拟环境或依赖目录。

## 验证与分工

- Python、前端、API 与数值模型的修改要求见 [AGENTS.md](AGENTS.md)；具体命令见 [README 验证](README.md#验证)。不要修改课程原始输入，也不要让算法读取真值或故障标签。
- 接任务前在群里说清范围，尤其是同时修改 `web/src/App.tsx` 或核心算法时，避免多人覆盖同一部分。
- UI 变化附实际运行截图；数值变化附输入、配置、结果与失败情况，不能用准备好的结果替代验证。
- 姓名、学号和实际贡献由成员自己核实后填写 [演示与答辩说明](docs/demo-guide.md)。
