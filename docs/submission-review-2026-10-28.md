# 提交前审查与核验记录

2026-10-28 对照用户原始作业文件包重新审查。代码取自 GitHub 主分支 f51ff061e2f2be541dbfb2f3c8e61a3c384a0132 的 Safari 认证下载，不使用桌面较旧源码副本。当前邮件交付以 SOURCE_MANIFEST.json 的 SHA256 身份为准。仓库地址：<https://github.com/sadfaxzda/gnss-workbench>。

## 本次发现与修复

1. 观测解析把 JSON 布尔值当作 Python 数值，可能接受 pseudorange_m=true 或 cn0_dbhz=false。增加显式类型拒绝；观测错误返回 INVALID_DATA，保留历元且下一有效历元继续处理，不产生伪坐标。卫星编号也显式要求字符串。
2. 导航 JSON 顶层为列表/null/数字时，在 schema 检查前可能触发 AttributeError。现在统一给出明确 ValueError，不把无效导航当作有效数据。
3. README、报告、分工和打包提示仍有旧的“分工待确定”文字。按用户确认写入：张淳贺负责 UI 和初版编程；马晨曦在其基础上优化；刘芸睿负责报告；三人共同审查。个人现场答辩没有虚构为完成。
4. 增加统一复现脚本和分段分析脚本；封装脚本从封存源码复跑公开案例、消融及六星局限，保留完整输入和逐星诊断。排除旧 deliverables ZIP、环境、缓存及本机运行历史。
5. 报告更新为六页，使用本次真实浏览器运行截图；公开结果为本次复算，扩展实验明确标为历史证据。报告和 README 均给出仓库地址。

默认诊断算法、阈值与物理公式未调整。原始课程文件未编辑。源码审查及既有测试覆盖卫星钟差/TGD、自转、大气改正、独立基线、因果诊断、0/3/4 星、几何退化、完整 CSV、暂停/恢复与导出；未发现真值、案例名或公开故障时间表进入定位核心。

## 本机核验

| 项目 | 本次结果 |
|---|---|
| 独立依赖安装 | 新目录执行 uv sync --locked，Python 3.14.4；pnpm 11.25.0 按前端锁文件安装 |
| Python 单元与集成 | 166 项通过；161 项在初次全量运行通过，5 项 TCP 因沙箱不能绑定端口而在允许本机端口的环境复跑全部通过 |
| 新增输入回归 | 6 项覆盖布尔观测、错误卫星类型、导航顶层格式及后续历元恢复 |
| Ruff / 格式 / Pyright | 通过，Pyright 0 errors / 0 warnings |
| 前端 | lint 通过；Vitest 16 项通过；生产构建通过 |
| 浏览器 | Chromium / WebKit 共 16 项流程通过，含 TCP 暂停恢复、6001 历元输入、回放、导出与窄屏 |
| 原包完整性 | 26 个文件与用户提供目录逐字节一致；24 个星历位置/钟差检查点测试通过 |
| 公开与派生实验 | D01 20、D02 600、D03 600、D03 消融 600、六星局限 35 历元；评价组 CSV 契约违规均为 0 |
| 报告 | 6 页 PDF，逐页渲染检查，无重叠、截字或缺字；原始 UI PNG 随代码保留 |
| 最终包 | 从封存字节重新解算，逐文件 SHA256 校验；最终检查见邮件总目录中的核验说明 |

原始检查日志见 docs/experiments/submission-20261028/checks/。初次沙箱端口失败是执行环境限制，已重跑核实；浏览器旧缓存缺少本机可执行文件，安装所需浏览器后通过。保留 Starlette/httpx 弃用提示和 Vite 分包体积提示，不影响本次运行。仅本机 macOS 实测，不将本次结果称为在 Windows/Linux 重新验证。

## 指标与局限

D02 水平 P95 1.590 m，D03 普通 23.859 m、改进 1.594 m。D03 要求定位 570 历元，两者可用率均 100%；10 m 成功率分别 89.474% 与 100%。60 个强故障全部正确标记和排除，510 个无逐星故障历元误报为 0；20 个四星与 30 个三星/零星状态全部正确。

D03 故障窗口水平 P95 为普通 24.450 m、改进 1.738 m。共同偏差窗口水平 P95 为 1.394 m、米制钟差误差 P95 为 1.388 m，无逐星误报。D01 无独立位置真值，不报告绝对精度。

六星已知失败复现：D02 前 35 历元保留前六颗卫星，对 G07 加 -30 m。首历元暂定排除 G20，状态 SUSPECT、残差 RMS 0.01486 m、PDOP 2.512，但水平误差 33.559 m；35 历元共 1 次错剔，0 次错误确认。该派生案例展示局限，不作为新的保留验证。历史大规模扩展的失败按原日期保留，未用本次公开结果覆盖。

## 复现与核验方法

    uv sync --locked
    uv run python scripts/reproduce_submission.py --out runtime/reproduction
    uv run python scripts/analyze_submission.py --results runtime/reproduction --out runtime/reproduction/analysis.json
    uv run python fixtures/course/tools/evaluate.py --input fixtures/course/data/D03_sim_demo.jsonl --truth fixtures/course/reference/D03_sim_demo_truth.csv --solution runtime/reproduction/D03_sim_demo/improved.csv --out runtime/reproduction/D03_sim_demo/course-evaluation.json
    python scripts/verify_submission.py --root .

输入、真值、输出必须属于同一案例。先比每历元编号、状态和无效空值，再比定位数值和卫星标记；耗时不做字节一致性要求。diagnostics.jsonl 每行的 baseline / improved 下的 diagnostics 是逐星数据；candidate_scores 和 algorithm_trace 是诊断依据。真值只用于求解结束后的评价。

各成员按 docs/demo-guide.md 说明自己的输入、模型、输出与失败条件。个人贡献依据用户提供信息记录，自动测试不能替代成员答辩；教师隐藏案例仍待现场验收。


## 报告与交付材料修订

根据小组要求，报告署期为 2026 年 10 月 21 日，实际运行日志仍保留 2026-10-28 的核验时间。仓库经 GitHub 元数据确认现为 public，URL 不变，README 和提交说明已更新访问方式。

报告采用六页实验报告结构，正文为 Songti SC（宋体），标题为 Heiti SC（黑体），字体嵌入 PDF；图表编号、三线表、公式与页码统一。新增从 D03 结果 CSV 计算的真值误差曲线，补充实验配置、评价分母、消融解释、六星残差自由度分析和统计适用边界。两张 UI 截图保留实际运行内容。排版结构参考 [Monash 工程实验报告指南](https://www.monash.edu/student-academic-success/excel-at-writing/annotated-assessment-samples/engineering/engineering-lab-report) 与 [多伦多大学工程实验报告指南](https://ecp.engineering.utoronto.ca/resources/online-handbook/types-of-documents/lab-reports/)，内容与页数仍以本课程任务书为准。

本次仅修改报告生成、绘图和交付文档；算法与前端保持已核验版本。重新封装时从新封存源码复算全部五组，重新生成源码身份、逐文件清单及顶层核验记录，避免文档修订后沿用失效哈希。
