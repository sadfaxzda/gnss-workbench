# 提交前审查与复现记录

审查起点为队友提交 `01444ea`，由 `55d8d3a` 快进同步。依据原始任务书、MODEL_SPEC、INTERFACE 和原评价器。软件交付范围包含源码、可运行前端、结果和报告；用户明确要求真实分工先留空。教师未公开案例和成员答辩不标记通过。

## 审查发现与处理

1. **CI 失败**：新增冻结实验源码被 Ruff 当成维护代码检查。仅排除 `docs/experiments/**/development-source`，保留封存字节与哈希，应用、脚本和测试仍完整检查。
2. **Windows 验证失败**：两项新测试按 cp1252 读取 UTF-8 中文诊断日志，触发 UnicodeDecodeError。显式使用 UTF-8；未改变算法或跳过 Windows 测试。原失败记录：[39014967414](https://github.com/sadfaxzda/gnss-workbench/actions/runs/39014967414)、[39042006260](https://github.com/sadfaxzda/gnss-workbench/actions/runs/39042006260)。
3. **当前钟差不易找到**：数值移到常显“位置与钟差”属性组；无效历元仍显示空值。Chrome/Safari 流程覆盖数值可见、无效清空和回放恢复。
4. **提交材料版本混杂**：Git 打包不再嵌套 `deliverables/` 中的旧 ZIP；实验原始证据归档仍保留。先封存源码、在临时目录复算再打包。
5. **报告偏向开发过程**：整理为六页课程报告，包含模型、诊断、公开数据、新种子消融、失败条件和复现。中文微软雅黑，英文数字 Times New Roman；个人分工单元格留空。
6. **本机入口导入失败**：按 README 执行 `uv sync --locked` 重建可编辑安装后，直接入口和测试恢复；最终交付另做全新目录、独立虚拟环境验证。

算法审查未发现教师真值、案例名称、故障时间表或未来观测进入计算核心。普通解独立等权；改进解历史作用于诊断证据，每历元位置重新拟合。保留 `coherent_proposals=False`，不在本轮新验证数据上继续调参。暂定剔除与确认剔除在状态、日志、表格中分开。

## 原始要求与核验

| 原始要求 | 本轮证据 | 判断范围 |
|---|---|---|
| GPS L1 四未知数、规定物理改正 | 24 个星历检查点；D01/D02/D03 解算；26 个教师文件与最初 ZIP 逐字节一致 | 通过已核验输入 |
| 独立普通解 | 对比 `55d8d3a` 的 1,220 历元，状态、参与数和数值完全一致，排除耗时 | 通过对照 |
| 正常精度 | D02 水平 P95 1.590 m，有效解 100%，误报 0 | 公开数据通过 |
| 单星故障诊断 | D03 P95 1.594 m，60 个强故障全部正确标记，10 m 成功率 100% | 公开数据通过；扩展结果见下 |
| 4／3／0 星状态 | D03 对应 50 历元正确；新数量变化中 140 个特设状态历元正确 | 状态通过，不代表少星带故障精度通过 |
| 共同偏差、坏几何 | 新共同偏差分组检查坐标、钟差和误报；秩不足与高 PDOP 测试 | 已覆盖 |
| 文件与 TCP 同核心、因果性 | 集成测试、TCP 分帧、暂停恢复、6001 历元刷新与导出 | 已覆盖 |
| 14 列 CSV、每历元一行、无效留空 | 原评价器逐案例检查；27,283 个新输入契约违规 0 | 已核验 |
| 双解、消融与证据 | 关闭改进 vs 默认，同输入对比；保存输入/代码哈希、配置、逐例指标 | 已核验 |
| GUI 必看数据 | 双轨迹、位置和钟差、卫星数、PDOP、逐星残差/标记、状态 | 实际浏览器核验 |
| 报告与复现 | 六页报告、锁文件、源码、前端、结果、诊断、校验清单 | 交付包另做独立复验 |
| 个人贡献与答辩 | 三名成员姓名已记录；用户要求分工先空着 | 留空待成员填写；未声称答辩完成 |

## 新生成输入，逐场景报告

种子在运行前确定，算法和默认参数保持不变。正向生成新轨迹、钟差、噪声和故障，与关闭改进对照；共享课程星历和物理函数，非外场或教师隐藏测试。

| 场景 | 种子 | 案例 / 历元 | 关闭改进 P95 | 默认 P95 | 默认 10 m 成功率 | 逐例未达全部门槛 |
|---|---:|---:|---:|---:|---:|---:|
| 八星 | 2026101701 | 83 / 6,640 | 38.506 m | 1.771 m | 99.985% | 0 |
| 六星连续 | 2026101702 | 196 / 15,680 | 61.934 m | 3.606 m | 97.813% | 24 |
| 七星 | 2026101703 | 56 / 4,480 | 42.983 m | 2.064 m | 100% | 0 |
| 星数变化与中断 | 2026101704 | 7 / 483 | 35.917 m | 33.308 m | 83.051% | 4 |

八星强故障正确标记率 99.979%，出现 3 次暂定错剔、0 次错误确认，正常误报 0。六星强故障正确标记率 97.068%，确认且正确比例 85.968%，295 次错剔中有 6 次错误确认，正常误报 0.014%。数量变化包含四／五星故障，精度失败保留；140 个特设状态历元正确率 100%。

水平 P95 在要求定位且有位置的历元上计算，10 m 成功率分母包括全部要求定位历元；强故障指单星偏差绝对值 ≥30 m。逐例检查含误报、可用率、共同偏差钟差等，不能用全程平均稀释短时失败。六星整体通过不替代 24 个具体失败。

完整汇总、逐类、逐例、输入和源码哈希：[submission-20261017](experiments/submission-20261017/)。原始输入、真值、双解和诊断留于本地 `runtime/submission-audit-20261017/`；交付不携带这批大型运行目录，可用固定命令重建。第八轮额外高噪声失败仍以原归档为准。

## 复现命令

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -q
uv run python scripts/verify_fixture.py
uv run python scripts/validate_course.py
pnpm --dir web install --frozen-lockfile
pnpm --dir web lint
pnpm --dir web test
pnpm --dir web build
pnpm --dir web exec playwright install chromium webkit
pnpm --dir web test:e2e
uv run python scripts/validate_six_satellite.py --comparison ablation --suite eight --seed 2026101701 --out runtime/recheck-submission-eight
uv run python scripts/validate_six_satellite.py --comparison ablation --suite continuous --seed 2026101702 --out runtime/recheck-submission-six
uv run python scripts/validate_six_satellite.py --comparison ablation --suite seven --seed 2026101703 --out runtime/recheck-submission-seven
uv run python scripts/validate_six_satellite.py --comparison ablation --suite variable --seed 2026101704 --out runtime/recheck-submission-variable
uv run --group research python scripts/build_submission_report.py
```

输出目录必须为空。`previous` 为关闭改进模块，`new` 为当前默认；与第八轮含义不同，读取各自 manifest 配置。浏览器测试前先关闭已运行的本地 API，避免复用旧进程。报告生成需要已安装的指定字体，见 README；交付 PDF 已嵌入字形。

本地完成 160 项 Python、16 项 Vitest、16 项 Chromium/WebKit 流程；UI 检查覆盖 1280 桌面和 390 窄屏，确认当前钟差常显及无效清空。保留 Starlette/httpx 弃用和 Vite 大包提示。GitHub 三系统验证和解压安装结果，以最终交付核验文件及对应提交的 Actions 为准。
