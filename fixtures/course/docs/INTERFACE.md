# 数据接口与输出约定
版本：GNSS-COURSE-1.0 / 2026-09-05。本文是自动评价的接口合同；两种模式均须遵守。

## 1. 输入文件
JSONL 是权威输入格式，UTF-8 编码，每行一个 JSON 对象。CSV 是等价的逐星展开视图，便于查看；**空观测历元不出现在逐星 CSV 中，不能因此删除这些历元**，完整时间轴在配套 `_epochs.csv`。

第一行为 meta，随后每行为一个 epoch。离线 JSONL 不含 end；TCP 回放结束会增加 end。
```json
{"type":"epoch","epoch_id":0,"gps_week":1316,"gps_sow":518400.0,"observations":[{"sat_id":"G03","pseudorange_m":24767686.375,"cn0_dbhz":null}]}
```
上面仅演示一条观测的结构，不是一组可独立定位的完整观测。

| 字段 | 含义 |
|---|---|
| epoch_id | 从0开始的唯一历元编号。须原样保留，不用行号替代。 |
| gps_week, gps_sow | GPS周与周内秒，不是UTC。秒的小数部分不能截断。 |
| sat_id | GPS卫星编号，固定格式 G03、G07 等。 |
| pseudorange_m | GPS L1 C1伪距，单位m；输入不是已经解算的经纬度。 |
| cn0_dbhz | 载噪比，单位dB-Hz；null表示源数据没有该项，不能改写成0。 |
| observations=[] | 该历元数据包已到达，但没有可用卫星观测；仍须输出一行状态。 |

配套 `navigation.json` 提供 ephemerides 字典与电离层参数；`gps_20050402_subset.nav` 为同一组广播星历的RINEX 2格式摘录。任选一种读取，不重复改正。此版仅含8颗GPS卫星的短时间配套星历，不用于当前日期定位。

## 2. 两种运行模式
必须支持：①读文件逐历元处理并输出CSV；②接收TCP数据逐历元解算、绘图并输出相同CSV。两种模式应调用同一核心模块。

TCP：默认127.0.0.1:8765，UTF-8 JSON对象以LF（字节0x0A）结尾。必须处理拆包、粘包；不能假设一次recv等于一个历元。单行大小上限1 MiB。server每次只服务一个客户端。

```bash
python tools/replay.py --input data/D03_sim_demo.jsonl --port 8765 --interval 0.1
python tools/client_skeleton.py --port 8765
```
以上两条在两个终端运行。示例客户端只实现接收和超时提示，不提供定位或界面答案。

`--interval`是相邻历元发送的墙钟时间；只改变回放速度，**不改变数据中的GPST**。真实样例约30秒采样，仿真样例1秒采样。算法必须使用数据时间，不使用动画播放时间。

meta在TCP模式增加`replay_interval_wall_s`。超过 `max(3秒, 3×replay_interval_wall_s)` 没有收到数据，应显示`TRANSPORT_STALE`；恢复后显示`TRANSPORT_RESUMED`。这些是界面/事件日志状态，不替代已有历元CSV行，也不能捏造中断期间的新历元。历史位置可灰显，但不能标成当前有效解。

```bash
python tools/replay.py --input data/D03_sim_demo.jsonl --interval 0.1 --pause-before 250 --pause-seconds 5 --event-log out/server_events.csv
```
TCP结束帧：`{"type":"end","epochs_sent":600}`。有序结束与意外断开应区分；自动重连不作为必做项。

## 3. 统一输出
分别保存 `baseline.csv` 与 `improved.csv`。列名、单位、含义固定：
```text
epoch_id,gps_week,gps_sow,status,x_m,y_m,z_m,clock_bias_m,n_used,pdop,flagged_sats,excluded_sats,residual_rms_m,processing_ms
```
`x_m,y_m,z_m`为WGS84定义的ECEF坐标；高度若在界面显示，使用椭球高，不与海拔混淆。`clock_bias_m=c×接收机钟差`，单位**米**。`pdop`为实际参与解算卫星的未加权几何PDOP，不是实际定位误差；`residual_rms_m`为参与解算观测的后验残差RMS，不是坐标RMSE。

`flagged_sats`是被识别为异常/可疑的卫星；`excluded_sats`是确实被剔除的卫星。多个编号用分号，例如`G03;G19`，无则空。采用降权而非剔除时，可以标记但不剔除；应另交逐星权重与残差日志。`n_used`为有效参与解算的卫星数，不应把被剔除卫星计入。

`processing_ms`为该历元计算耗时；自报数值只作诊断，正式实时性由现场观察和教师墙钟计时判断。

### 状态
| 状态 | 使用场景 |
|---|---|
| VALID | 可解算且未触发当前方法的质量警告；不等同于安全认证。 |
| FAULT_EXCLUDED / FAULT_MITIGATED | 已采取剔除/降权等措施，仍输出位置，列出异常卫星。 |
| SUSPECT | 有疑点但不能可靠定位故障，不得宣称已排除风险。 |
| NO_REDUNDANCY | 4颗卫星且几何可解，无单历元观测冗余。 |
| GEOMETRY_WARNING | PDOP>30或有充分的等价几何劣化依据；可附位置但需明显警告。 |
| INVALID_INSUFFICIENT | 1—3颗卫星，不能完成本作业的独立三维位置+钟差解算。 |
| NO_OBSERVATIONS | 本历元0颗卫星。 |
| INVALID_GEOMETRY | 几何秩不足或严重病态，不能可靠解算。 |
| INVALID_CONVERGENCE | 数值迭代不收敛；不能伪装成正常解。 |
| INVALID_DATA / INVALID_EPHEMERIS | 输入或星历无法使用，日志说明原因。 |

无有效解的状态（INVALID_*与NO_OBSERVATIONS）下，XYZ、钟差、PDOP与残差字段留空。不能写NaN、Inf、0坐标或上一历元位置冒充有效结果。每个输入历元必须有且仅有一行；NO_REDUNDANCY/GEOMETRY_WARNING优先于普通VALID提示。不能用“上一时刻已知高度”绕开3颗卫星测试，本作业基础解为每历元独立四未知数。

## 4. 学生自测
```bash
python -m pip install -r requirements.txt
python tools/evaluate.py --input data/D02_sim_clean.jsonl --truth reference/D02_sim_clean_truth.csv --solution out/improved.csv --out out/metrics.json
```
输入、真值、输出必须来自同一案例。`evaluate.py`只比较既有结果，不替代学生定位算法；不会给出总分，也不能自动核实界面效果或个人贡献。

## 5. 评价口径
水平误差由位置差转换至真值处ENU后计算；报告中位数、95%分位数。有效解比例、10m内成功比例的分母均为所有“要求输出位置”的历元，不能先删除失败历元。3颗/0颗卫星以及特设极差几何窗口不计入正常精度分母，分别评价状态处理。误差分位数仅基于已输出的有效位置，必须连同可用率报告。

强故障检出率统计真实注入幅度绝对值≥30m的逐星单故障历元；缓慢偏差早期不强求全部检出。误报率在明确没有逐星注入故障的仿真历元统计。全星共同偏差属于钟差测试，不应作为逐星故障报警。真实样例无逐星故障真值，不能以同一口径统计其“误报率”。
