# 提交材料阅读与核验导航

公开仓库：<https://github.com/sadfaxzda/gnss-workbench>。实验报告署期：2026 年 10 月 21 日。实际复核时间见各日志；报告署期不改写运行记录。

## 建议阅读顺序

1. 阅读总目录中的六页 PDF（与 `docs/report.pdf` 完全一致）：实验原理、真实 UI、对照与消融、成功案例、六星局限、分工及核验方法。
2. 阅读源码根目录 `README.md`：依赖、安装、文件与 TCP 模式、单案例评价和完整复现命令。
3. 查看 `submission-results/` 中的原始输出，并与报告表 2、表 3、图 3 核对。
4. 需要细查时阅读 `docs/submission-review-2026-10-28.md` 及 `docs/experiments/submission-20261028/checks/`。

## 已附实验结果

以下相对路径均以“源代码”目录为起点。每个解算目录含 `baseline.csv`、`improved.csv`、`diagnostics.jsonl`、`manifest.json`；有真值的目录另含 `metrics.json`。

| 目录 | 历元数 | 用途与核验重点 |
|---|---:|---|
| `submission-results/D01_real_excerpt/` | 20 | 真实历史数据兼容性；无独立位置真值，不作绝对精度评分 |
| `submission-results/D02_sim_clean/` | 600 | 正常动态仿真；普通/改进水平 P95 均为 1.590 m |
| `submission-results/D03_sim_demo/` | 600 | 公开异常集；普通/改进 P95 为 23.859 m / 1.594 m |
| `submission-results/D03_sim_demo_ablation/` | 600 | 关闭 FDE；双解一致，P95 回到 23.859 m |
| `submission-results/six_satellite_limit/` | 35 | 已知六星冷启动失败；首历元真故障 G07、暂定错剔 G20 |
| `submission-results/six_satellite_input/` | 35 | 派生输入、真值及生成规则，独立于定位核心 |

D03 的要求定位分母为 570，含四星 20 历元；三星 20 历元及零星 10 历元另查状态，CSV 仍保留全部 600 行。真值只用于求解后评价。`processing_ms` 随机器变化，不能作为结果逐字节一致性的要求。

## 代表历元与日志字段

- 成功案例：D03 的 `epoch_id=120..179`，G19 注入 +80 m；可重点查看 `epoch_id=121`，它与报告图 2 对应。
- 共同偏差：D03 的 `epoch_id=300..359`，全星 +100 m，应主要进入接收机钟差且无逐星误报。
- 特殊状态：D03 的 `420..439` 为四星，`460..479` 为三星，`520..529` 为零星。四星为 `NO_REDUNDANCY`；后三星/零星的无效位置字段留空。
- 局限案例：六星输入 `epoch_id=0`，真实 G07 故障却暂定排除 G20，状态 `SUSPECT`，水平误差 33.559 m。后验残差仅 0.01486 m，故“小残差”不能作为故障识别正确的证明。

逐星 JSONL 的一行对应一个历元。`baseline` 和 `improved` 分别保存双解；各自的 `diagnostics` 包含 `sat_id`、`residual_m`、`normalized_residual`、`weight`、`excluded`、高度角与方位角。`candidate_scores`、`algorithm_trace` 保存候选评价与选择依据。CSV 中 `flagged_sats` 表示标记，`excluded_sats` 表示实际剔除，不能将暂定剔除等同于已确认故障。

## 最小复现与核验

在“源代码”中运行：

```bash
python scripts/verify_submission.py --root .
uv sync --locked
uv run python scripts/reproduce_submission.py --out runtime/reproduction
uv run python scripts/analyze_submission.py --results runtime/reproduction --out runtime/reproduction/analysis.json
```

输出目录必须为空。第一条只检查交付文件完整性，不检查程序是否正确；后两条从实际输入求解并生成指标，用于核对报告。

教师评价器单独复核 D03 改进解：

```bash
uv run python fixtures/course/tools/evaluate.py --input fixtures/course/data/D03_sim_demo.jsonl --truth fixtures/course/reference/D03_sim_demo_truth.csv --solution runtime/reproduction/D03_sim_demo/improved.csv --out runtime/reproduction/D03_sim_demo/course-evaluation.json
```

界面验证另开终端执行 `uv run gnss serve`，访问 <http://127.0.0.1:8000>。TCP 暂停恢复的双终端命令见 README。依赖安装后可离线运行，首次安装依赖需联网。

## 交付范围与历史记录

邮件代码文件夹含完整维护源码、教师数据、锁文件、测试、预构建 UI、结果与日志；不含虚拟环境、node_modules、Git 元数据、旧压缩包和本机运行缓存。历史扩展研究保留在 `docs/`，其日期、输入和参数按原记录解释；当前提交的主结论以报告、上述五组输出和对应核验记录为准。

三人分工与共同审查见 `docs/team.json`；个人核验安排见 `docs/demo-guide.md`。自动测试不能替代成员现场说明或教师未知案例验收。
