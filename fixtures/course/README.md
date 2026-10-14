# GNSS原理与应用：学生实践作业包 v1.0
## 原始观测驱动的GPS定位与故障诊断系统

先阅读 `docs/作业任务书.docx`，再把 `docs/MODEL_SPEC.md` 和 `docs/INTERFACE.md` 作为开发规范。

本包可直接发给学生；不含教师验收案例、私有真值、生成器或参考定位解算器。

## 给了什么
| 内容 | 数量 / 含义 |
|---|---|
| D01_real_excerpt | 20历元真实GPS C1观测，160条伪距，约30秒采样，无独立测量位置真值。 |
| D02_sim_clean | 600历元1Hz仿真动态观测，有位置和钟差真值，用于正确性调试。 |
| D03_sim_demo | 600历元1Hz仿真观测，有公开故障/缺测/共同偏差，供诊断开发。 |
| navigation.json / .nav | 上述数据配套的8颗真实历史GPS卫星广播星历，二选一读取。 |
| reference/ | 开发集仿真真值和24个卫星轨道/钟差检查点，只用于校核，不作为实时算法输入。 |
| tools/ | TCP回放器、仅通信的客户端骨架、输出评价器、完整性校验工具。 |

真实观测与仿真数据严格分开。D01源文件头的近似坐标不是测量真值；D02/D03不是城市道路实测。来源见`data/provenance.json`，模型边界见`docs/MODEL_SPEC.md`。

## 第一次运行（在本目录打开终端）
需要Python 3.10+。回放器和客户端骨架只使用标准库；评价器需要NumPy。

```bash
python -m pip install -r requirements.txt
python tools/verify_integrity.py
python tools/replay.py --input data/D03_sim_demo.jsonl --interval 0.1
```
第二个终端：
```bash
python tools/client_skeleton.py
```
看到历元编号和卫星数量说明输入通道正常。骨架没有定位功能；须用自己开发的定位模块和界面替换on_epoch。

完成自己的输出后：
```bash
python tools/evaluate.py --input data/D03_sim_demo.jsonl --truth reference/D03_sim_demo_truth.csv --solution out/improved.csv --out out/metrics.json
```
`out/improved.csv`由你的软件产生，本包不预置。正式验收还会使用未公开的输入数据，不只是重复D03。

## 边界
核心为广播星历计算、伪距解算、异常诊断和可验证软件行为；不要求手机采集、购置接收机、网络地图、RTK/PPP或IMU。可充分使用Codex，但必须解释模型并提交可复现测试。不要把文件读取、界面包装或接收机已有坐标显示当成定位算法。

测试记录：工具在Linux/Python3.13.5/NumPy2.3.5运行核验；其他系统需自行运行本地自测。macOS/Linux的命令也可用python3；Windows使用已安装Python的python或py。没有包含任何平台专用可执行文件。
