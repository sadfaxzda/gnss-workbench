# 第七轮：完整八星补验、交付修复与真实分工记录

2026-10-17。重新阅读教师任务书、MODEL_SPEC、INTERFACE，核对当前源码及第六轮冻结证据。本轮补验的83个八星案例全部达到对应建议门槛，修复下载源码无法制作可核验提交包的问题；分段故障证据实验出现退化，未采用。**六星冷启动、部分换星/集合变化及高噪声局限仍然存在，不能宣称所有条件已全面达标。**

## 1. 算法试验：保留有效修改，拒绝有退化的新默认

生产数值核心与第六轮一致：每历元独立等权普通解、完整课程改正、16历元以内因果故障证据、增大噪声尺度时折减旧证据、候选水平解差、证据不足保持SUSPECT。没有输入真值、未来观测或固定高度。

本轮实验对奇偶空间残差进行分段拟合，选择无故障/单星常偏/单星线性变化，使用模型复杂度与分段搜索代价。灵感来自[Schwarz (1978) 原文](https://www.andrew.cmu.edu/user/kk3n/simplicity/schwarzbic.pdf)，DOI 10.1214/aos/1176344136；是工程评分，非经过校准的身份概率。位置始终由当前观测重新求解。

| 第六轮输入上的开发回归 | 当前默认 | 分段实验 |
|---|---:|---:|
| 连续六星冷启动强故障P95 | 27.329m | 32.559m |
| 连续六星全部错剔 | 220 | 221 |
| 不规则六星全部错剔 | 114 | 112 |
| 不规则六星错误确认 | 3 | 3 |

冷启动退化，局部改善不稳定，因此未合入默认或新增可选算法，未再使用预留验证输入调参。保留[实验源码](experiments/diagnosis-iteration7/rejected-segmented/segmented_experiment.py)、[连续开发指标](experiments/diagnosis-iteration7/segmented-dev-continuous-metrics.json)、[不规则开发指标](experiments/diagnosis-iteration7/segmented-dev-irregular-metrics.json)。这些是开发回放，不是新的独立验证。

## 2. 预注册后新生成的八星补验

[计划](diagnosis-iteration7-plan.md)在生成前明确种子625308、83例×80历元：正常1例、共同偏差±100m各1例；冷启动、阶跃、渐变、一次换星、快速换星各覆盖8颗初始目标星×正负号。每例独立生成接收机轨迹、钟差和噪声；仅按课程高度角条件筛选起点，不按结果删除案例。

基础噪声标准差0.8m，加0.25m平滑扰动。共享课程星历和已通过检查点的物理函数，因此属于受控仿真，存在共同模型局限，不是教师隐藏数据或外场实测。对照为同输入关闭FDE，生成双解及逐星日志；当前算法冻结后未根据结果修改。

| 条件 | 历元 | 关闭FDE P95 | 改进P95 | 改进10m成功率 |
|---|---:|---:|---:|---:|
| 正常 | 80 | 1.428m | 1.428m | 100% |
| 共同偏差±100m | 160 | 1.513m | 1.513m | 100% |
| 故障冷启动 | 1,280 | 45.138m | 1.749m | 100% |
| 单星阶跃 | 1,280 | 38.587m | 1.713m | 100% |
| 单星渐变 | 1,280 | 33.415m | 1.861m | 100% |
| 一次换星 | 1,280 | 52.296m | 1.808m | 100% |
| 快速换星 | 1,280 | 41.955m | 1.721m | 100% |
| 全部 | 6,640 | 45.365m | 1.763m | 100% |

全部要求定位历元有效；强故障正确标记率100%，错剔0、错误确认0、正常标记/状态误报0。共同偏差钟差距离项误差P95为1.220m。**83例逐例检查均通过**，包含渐变早期弱故障，不只统计强故障片段。P95基于有效位置；成功率以全部要求定位历元为分母。

两条运行路径的普通解状态与参与星数一致，最大数值差2.903×10⁻⁷m，来自迭代初值路径。课程评价器契约违规0。新增`--suite eight`与`--comparison ablation`；已有历史比较命令语义不变。

证据：[完整汇总与逐例门槛](experiments/diagnosis-iteration7/summary.json)、[各组指标](experiments/diagnosis-iteration7/eight-metrics.json)、[逐例指标](experiments/diagnosis-iteration7/eight-case_metrics.json)、[源代码冻结](experiments/diagnosis-iteration7/frozen-eight.json)、[配置与输入哈希](experiments/diagnosis-iteration7/eight-manifest.json)。原始输入、真值、双解、全部逐星诊断及失败记录保存在`runtime/diagnosis-iteration7/final-eight/`。交付ZIP不包含大体积运行历史，可按相同命令重新生成。

## 3. 没有被八星通过替代的失败

[第六轮完整证据](diagnosis-iteration6.md)继续有效：六星孤立首历元P95为32.840m；连续六星冷启动强故障P95为27.329m、10m成功率93.10%；可见集合变化强故障P95为35.984m；2.4m高噪声整体P95为26.586m。部分冷启动/换星星组和四/五星故障精度仍失败。任务书对4/3/0星要求的状态处理通过，不等于四五星具备可靠故障隔离能力。

本轮把旧的首历元歧义构造变成可重算脚本：同组六星中，世界A为G07−120m，世界B为G28+45.590m；两真实位置水平相距128.635m，六维观测均值距离仅0.141629m。两世界最低高度角>5.92°、PDOP约2.533、椭球高分别161.504m/63.044m、星历年龄≤1032.076秒；重新计算均值与存档完全一致。

在只观察一个历元、两假设等先验且噪声为独立同方差0.8m高斯分布时，将观测投影到两均值差方向，中点为最优二选一边界；身份判别成功率为Φ(‖μA−μB‖/(2σ))=53.53%。**该结论只针对该二选一身份问题，不是课程水平P95的普遍上界，也不代替课程验收。** 它说明正常PDOP和低残差无法独立证明故障身份正确。

[构造输入](experiments/diagnosis-iteration7/cold-identifiability-input.json)、[重算结果](experiments/diagnosis-iteration7/identifiability-verification.json)、[复验脚本](../scripts/verify_identifiability.py)。脚本只做事后分析，没有把两世界真值传入生产求解器。

## 4. 工程交付修复

当前目录是没有`.git`的下载源码，原打包脚本只能对干净Git仓库运行。现在保留原路径，并增加显式`--source-snapshot`：

- 用允许的源码目录/配置清单封存实际字节，包含Vitest、格式配置等重建依赖；排除运行历史、缓存、虚拟环境、node_modules、隐藏凭证和符号链接。
- `SOURCE_MANIFEST.json`保留逐文件哈希与`snapshot-sha256:…`身份，不虚构提交号。运行记录能识别该身份；原Git提交号仍兼容。
- 先将封存字节写入临时目录，再用该源码生成D01/D02/D03结果及D03消融；打包期间修改原工作目录不会改变已经捕获的计算源码。
- `SHA256SUMS.json`覆盖源码、前端、报告、结果及来源元数据；新标准库脚本校验每个交付文件、来源一致性和安全路径。它检测改动，不提供签名认证。
- ZIP必须是新路径，既有证据不会被覆盖。交付版本保留实际分工待确定和已知数值局限。

## 5. 检查、报告与成员

本轮154项pytest、13项Vitest通过；Ruff与格式、Pyright、ESLint、TypeScript/Vite构建通过。新增6项交付测试覆盖来源变更、敏感目录排除、符号链接、缺失源码、校验改动和越界路径/丢失元数据。数值核心、教师26个文件和API合同保持不变。第六轮Chromium/WebKit共16项流程测试仍为既有证据；本轮未改UI流程，未重复宣称新浏览器验收。保留Starlette/httpx依赖弃用提示与Vite大包提示。

报告更新为6页，逐页渲染检查；第六轮报告另存`report-pre-iteration7.pdf`。用户确认成员为**马晨曦、张淳贺、刘芸睿**，保存于[成员记录](team.json)并写入报告和[演示分工表](demo-guide.md)。实际负责模块、个人核验与现场讲解仍待确定，未分配虚构贡献。

```bash
uv sync --locked
uv run pytest -q
uv run python scripts/validate_six_satellite.py --comparison ablation --suite eight --seed 625308 --out runtime/recheck-eight-v7
uv run python scripts/verify_identifiability.py --case docs/experiments/diagnosis-iteration7/cold-identifiability-input.json --out runtime/recheck-ambiguity-v7.json
uv run --group research python scripts/build_iteration7_report.py
pnpm --dir web build
uv run python scripts/package_submission.py --source-snapshot --out ../GNSS_Workbench_iteration7_candidate.zip
# 解压后进入gnss-workbench目录
python scripts/verify_submission.py --root .
uv run gnss serve --port 18000
```

下一步仍需改进六星身份歧义条件下的实际表现，并由成员完成真实分工及个人核验。八星通过、源码可封存与工程测试通过不等于完成教师隐藏验收或个人答辩。
