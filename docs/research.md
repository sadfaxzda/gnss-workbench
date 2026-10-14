# 研究依据与实现边界

检索日期：2026-10-14。以下以原论文、作者机构或项目官方文档为依据；实现不以“来自顶会”替代实验。

## 已加入的前沿适配

Piedade、Chitturi、Gaspar、Govindu、Miraldo：**SAC-GNC: SAmple Consensus for adaptive Graduated Non-Convexity**，ICCV 2025 Highlight，pp. 5780-5790，DOI 10.1109/ICCV51701.2025.00547。

- [CVF 正式论文页](https://openaccess.thecvf.com/content/ICCV2025/html/Piedade_SAC-GNC_SAmple_Consensus_for_adaptive_Graduated_Non-Convexity_ICCV_2025_paper.html)
- [MERL 作者机构的方法说明](https://www.merl.com/research/highlights/sac-gnc)
- [作者论文 PDF](https://www.merl.com/publications/docs/TR2025-146.pdf)
- [作者代码](https://github.com/merlresearch/sac-gnc)

原文针对位姿图优化和 3D 配准，自适应尝试多个退火参数，以鲁棒评分探索 GNC 假设树。本项目独立实现其启发的 **GNSS 简化适配**：GM 损失 rho(r)=r²/(1+r²/s²)，IRLS 权重 w=(s²/(s²+r²))²，三种确定性退火速率，宽度3、深度6的搜索；每分支最多5次加权迭代，以3 sigma截断的 MSAC 分数保留最好权重。

差别必须保留：这里使用有界 beam 搜索和固定最低尺度，没有复现原论文全部采样、初始化、优先队列与停止准则；观测模型是单历元 GPS 伪距，没有位姿图；鲁棒权重只排列剔星假设，最终解由完整的无权子集检验和 OLS 重拟合确认。因此当前 8 星数据中，其最终精度与 consensus 相同，耗时更高，**保持实验选项，不作为默认**。没有证据支持“复现论文 SOTA”或“GNSS 新 SOTA”。未复制作者代码。

## 稳健估计的基础与 GNSS 相关工作

1. Yang、Antonante、Tzoumas、Carlone，**Graduated Non-Convexity for Robust Spatial Perception: From Non-Minimal Solvers to Global Outlier Rejection**，IEEE RA-L 2020，DOI 10.1109/LRA.2020.2965893。[原文](https://arxiv.org/abs/1909.08605)。这是 GNC 的基础参考，不称为最新论文；当前没有另外实现其完整 GNC-TLS 基线。
2. Wen、Zhang、Hsu，**GNSS Outlier Mitigation via Graduated Non-Convexity Factor Graph Optimization**，IEEE Transactions on Vehicular Technology 71(1), 297-310, 2022，DOI 10.1109/TVT.2021.3130909。[作者机构存档](https://ira.lib.polyu.edu.hk/handle/10397/92728)。证明 GNSS 中应用 GNC 值得研究；本项目未实现该文完整因子图。
3. **GNSS/Multisensor Fusion Using Continuous-Time Factor Graph Optimization for Robust Localization**，IEEE Transactions on Robotics，2024，40卷。[IEEE 原文](https://ieeexplore.ieee.org/document/10637732/)。其多传感器/里程计条件与课程单频伪距不符，作为未来扩展参考，没有声称接入激光或 IMU。

## 已接入的独立工具

[Stanford-NavLab/gnss_lib_py](https://github.com/Stanford-NavLab/gnss_lib_py)，锁定 PyPI 1.1.0，可选 research 依赖组；[官方 FDE 教程](https://gnss-lib-py.readthedocs.io/en/stable/tutorials/algorithms/tutorials_fde_notebook.html)同时介绍 EDM 多故障排除（ION GNSS+ 2023）和 greedy residual FDE。ION GNSS+ 是领域会议，本文不将其等同 ICCV 或 IEEE 顶刊。

本次实际集成是独立 snapshot WLS 交叉校验：先固定本系统算出的星钟、大气改正和接收时刻卫星坐标，把改正伪距交给 gnss_lib_py，从零初值独立解四未知量。78 个 D01/D02/D03 抽样历元的四维状态差最大约 1.66e-7 m（验收阈值1 mm）。这验证数值 WLS 阶段，**没有独立验证共享的大气/星历模型或真实轨迹精度**。EDM FDE 尚未接入比较。

```bash
uv sync --group research
uv run --group research gnss cross-check --out runtime/cross-check.json
```

选择可选依赖是因为研究工具同时带来绘图和 RINEX 生态依赖，普通解算和 Web 服务无需安装它们。项目依赖沿用上游许可证，不将第三方实现宣称为原创。

## 下一阶段值得做什么

保留种子显示噪声 sigma 设小会产生明显错剔，重尾噪声下新方法也未稳定胜出。下一步应围绕仅使用历史的稳健噪声标定、异方差模型与外部真实数据设计新的预注册实验，而非继续根据已公开的保留种子调参数。任何滤波/因子图扩展必须保留独立单历元基线，并明确动态先验与错误锁定风险。
