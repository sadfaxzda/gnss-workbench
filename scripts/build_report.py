"""Build the six-page course report draft from committed experiment summaries.

uv run --group research python scripts/build_report.py --font /path/to/Chinese.ttf
On macOS, the bundled Arial Unicode font is detected automatically.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

plt.switch_backend("Agg")

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument(
    "--font", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
)
args = parser.parse_args()
if not args.font.is_file():
    raise SystemExit(
        "Supply --font with a licensed Chinese TrueType font available on this machine"
    )
pdfmetrics.registerFont(TTFont("Chinese", str(args.font)))
report = json.loads((ROOT / "docs/experiments/holdout-metrics.json").read_text())
metrics = report["metrics"]
media = ROOT / "docs/media"
media.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), layout="constrained")
families = ["clean", "single", "ramp", "double", "common", "heavy_tail", "noise_mismatch"]
labels = [
    "Clean",
    "Single fault",
    "Ramp fault",
    "Two faults",
    "Common bias",
    "Heavy tails",
    "Sigma mismatch",
]
y = np.arange(len(families))
for offset, method, label, color in [
    (-0.18, "single_fde", "Single-fault FDE", "#e9a15c"),
    (0.18, "consensus", "Multi-hypothesis", "#188f83"),
]:
    axes[0].scatter(
        [metrics[f][method]["h_p95_m"] for f in families],
        y + offset,
        color=color,
        label=label,
        s=24,
    )
    axes[1].barh(
        y + offset,
        [100 * metrics[f][method]["success_within_10m"] for f in families],
        height=0.32,
        color=color,
    )
axes[0].set_yticks(y, labels)
axes[0].set_xscale("log")
axes[0].set_xlim(1, 100)
axes[0].set_xticks([1, 3, 10, 30, 100], ["1", "3", "10", "30", "100"])
axes[0].xaxis.set_minor_formatter(plt.NullFormatter())
axes[0].set_xlabel("Horizontal P95 (m, log scale)")
axes[0].legend(loc="lower right", fontsize=8)
axes[1].set_yticks(y, labels)
axes[1].set_xlim(0, 105)
axes[1].set_xlabel("All-epoch success within 10 m (%)")
for ax in axes:
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
figure = media / "algorithm-comparison.png"
fig.savefig(figure, dpi=200)
plt.close(fig)

styles = {
    "title": ParagraphStyle(
        "title",
        fontName="Chinese",
        fontSize=25,
        leading=34,
        textColor=colors.HexColor("#183449"),
        spaceAfter=18,
        wordWrap="CJK",
    ),
    "h2": ParagraphStyle(
        "h2",
        fontName="Chinese",
        fontSize=16,
        leading=24,
        textColor=colors.HexColor("#188f83"),
        spaceBefore=14,
        spaceAfter=9,
        wordWrap="CJK",
    ),
    "body": ParagraphStyle(
        "body", fontName="Chinese", fontSize=10.2, leading=17.5, spaceAfter=10, wordWrap="CJK"
    ),
    "small": ParagraphStyle(
        "small", fontName="Chinese", fontSize=8.2, leading=13, spaceAfter=7, wordWrap="CJK"
    ),
    "cell": ParagraphStyle("cell", fontName="Chinese", fontSize=8.5, leading=13, wordWrap="CJK"),
    "tag": ParagraphStyle(
        "tag",
        fontName="Chinese",
        fontSize=10,
        leading=16,
        textColor=colors.HexColor("#188f83"),
        spaceAfter=16,
    ),
}
story = []


def p(text: str, style: str = "body") -> None:
    story.append(Paragraph(escape(text), styles[style]))


def table(rows: list[list[str]], widths: list[int]) -> None:
    wrapped = [[Paragraph(escape(str(cell)), styles["cell"]) for cell in row] for row in rows]
    item = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f2f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dbe5ec")),
            ]
        )
    )
    story.extend([item, Spacer(1, 12)])


def page(title: str, index: int) -> None:
    if index > 1:
        story.append(PageBreak())
    p(f"GNSS WORKBENCH  /  TECHNICAL REPORT  /  {index:02d}", "tag")
    p(title, "title")


page("原始观测驱动的 GPS 定位\n与故障诊断系统", 1)
p("v0.2 · 技术报告草稿 · 2026-10-14", "h2")
p(
    "目标是在 macOS、Windows 与 Linux 上使用同一计算核心，按历元从 GPS L1 C1 伪距及广播星历求三维坐标与接收机钟差，展示独立等权基线与可解释的异常处理结果。系统由 React 网页、FastAPI 服务、独立 Python 计算进程和持久化实验记录组成。"
)
p(
    "本轮优先补齐教师要求的可验收功能，再比较多星故障算法和前沿鲁棒估计。默认采用最多两星的最小故障数一致性诊断；受 ICCV 2025 SAC-GNC 启发的自适应 GNC 保留为实验选项。"
)
table(
    [
        ["验收对象", "当前证据"],
        ["D02 正常 600 历元", "水平 P95 1.590 m；可用率100%；误报0"],
        ["D03 混合异常 600 历元", "水平 P95 1.594 m；60个强故障全部检出；CSV契约违规0"],
        ["保留种子双星 84 历元", "10m内成功率：1.2% → 95.2%；水平P95：78.24m → 3.47m"],
        ["独立工具校验", "gnss_lib_py1.1.0；78个snapshot；最大状态差1.66e-7m"],
    ],
    [158, 329],
)
p("结论的适用范围", "h2")
p(
    "公开数据与扩展实验均采用课程提供的广播星历和 D02 几何。真实 D01 仅20历元且无独立轨迹真值；不宣称城市峡谷实测精度、隐藏测试全通过或算法达到领域领先。重尾噪声和噪声先验失配的失败结果完整报告。"
)
p(
    "待小组填写：成员姓名、真实分工、贡献凭证与答辩记录。本草稿由实际运行产物生成，尚未作为最终课程报告提交。",
    "small",
)

page("观测模型与可追溯实现", 2)
p("四未知数与课程改正模型", "h2")
p(
    "状态为 [x, y, z, b]，b=c·dt_receiver，以米表示。使用 GPS 广播星历迭代发射时刻，求卫星轨道与系统钟差，加入周期相对论项并处理 TGD；卫星坐标旋转到接收时刻 ECEF。电离层采用 Klobuchar，对流层采用课程标准 Saastamoinen，截止高度角3°。"
)
p(
    "观测模型：P = ||r-s|| + b - c·dt_code + I + T + epsilon。线性化矩阵每行为 [(r-s)/rho, 1]。基线以 NumPy 最小二乘直接解四未知量，不固定高度或坐标；上一有效解仅作为数值初值。"
)
p("独立基线与诊断检验", "h2")
p(
    "普通等权 LS 始终独立保存。残差检验统计量为 T=vᵀv/sigma²，自由度为 n-4，alpha=0.001、默认sigma=1m。普通状态与改进状态同时输出。PDOP始终由保留观测的未加权几何矩阵计算，不能以鲁棒权重造成的精度因子冒充课程PDOP。"
)
table(
    [
        ["输入或几何条件", "行为"],
        ["0星 / 1-3星", "NO_OBSERVATIONS / INVALID_INSUFFICIENT；坐标等字段为空"],
        ["恰好4星且几何可解", "NO_REDUNDANCY；不能由单历元残差检验故障"],
        ["PDOP>30 / 秩不足", "GEOMETRY_WARNING / INVALID_GEOMETRY；几何告警优先"],
        ["合法ID/时间，观测内容损坏", "INVALID_DATA并继续后续历元；身份缺失/重复则拒绝输入"],
        ["共同伪距偏差", "由接收机钟差吸收；不能全星标记异常"],
    ],
    [160, 327],
)
p(
    "课程24个卫星检查点最大坐标差约7.53e-7m。Stanford工具交叉验证使用共享且冻结的大气与星钟改正，因此只独立检查WLS数值阶段，不能替代物理模型或外场真值检验。",
    "small",
)

page("多故障算法与前沿适配", 3)
p("默认：最小故障数多假设一致性", "h2")
p(
    "先做全局检验，正常历元直接保留。检验失败时枚举单星剔除；若单星没有通过候选，再枚举双星。每个候选重做OLS，要求剩余至少5星、卡方检验通过且PDOP≤30。最小剔星数存在唯一合格候选才输出FAULT_EXCLUDED，否则返回SUSPECT并保留全部证据。"
)
p(
    "8星最多需要8+28=36个候选。算法另设预算600；搜索未完整时不能声称唯一。多重检验后的风险没有经过认证，不将该流程称为保护级或安全完好性保证。"
)
p("实验：SAC-GNC启发的自适应GM估计 [1]", "h2")
p(
    "从OLS残差启动，使用GM损失rho(r)=r²/(1+r²/s²)，权重w=(s²/(s²+r²))²。尝试1.4、2.6、4.9三种退火速率，按MSAC截断评分保留最好权重，以宽度3、深度6探索，每分支最多5次IRLS。权重用于排序候选，最终仍通过相同的无权子集验收。"
)
p(
    "原论文研究位姿图和三维配准。这里是独立编写的GNSS简化适配，没有完整复现原文的优先队列、随机采样、初始化与停止准则，也没有实现因子图。受控实验中最终精度与多假设法一致，耗时更大，故未设为默认。"
)
table(
    [
        ["配置", "角色与消融"],
        ["OLS / --disable-fde", "所有观测等权，关闭检测与剔除"],
        ["single_fde", "保留v0.1唯一单星检验，检验多星改进的来源"],
        ["consensus", "默认最多两星，最小故障数与唯一性检验"],
        ["adaptive_gnc", "研究提议权重、搜索轨迹与运行代价"],
    ],
    [142, 345],
)
p(
    "GNC基础参考RA-L2020 [2]；GNSS GNC因子图参考TVT2022 [3]。TRO2024多传感器连续时间因子图[4]需要当前数据没有的传感器条件，本项目没有直接套用。",
    "small",
)

page("受控实验与成功案例", 4)
p("实验设计与评价口径", "h2")
p(
    "先固定配置与种子，再运行开发20261014、验证20261015、保留20261016。每种子7类×84历元×4配置，共7056次方法-历元比较。沿用D02观测并新增随机故障和噪声；双星覆盖28种卫星对；正常、单星、渐变、共同偏差、重尾和sigma失配分别计分。"
)
p(
    "所有要求定位的历元保留在10m成功率分母。位置可用包括SUSPECT，另报告被检测器接受的比例；错误百分位不能脱离可用率与成功率阅读。强故障按每颗卫星|bias|≥30m统计，区别于课程单故障的按历元口径。"
)
story.append(Image(str(figure), width=487, height=170.5))
p("图1  保留种子对照（每类84历元）；右图分母包含全部历元。", "small")
rows = [["保留组场景", "原单星FDE P95", "多假设 P95", "多假设10m成功率"]]
for family, label in [
    ("clean", "正常"),
    ("single", "单星"),
    ("ramp", "渐变"),
    ("double", "双星"),
    ("common", "共同偏差"),
]:
    old, new = metrics[family]["single_fde"], metrics[family]["consensus"]
    rows.append(
        [
            label,
            f"{old['h_p95_m']:.3f} m",
            f"{new['h_p95_m']:.3f} m",
            f"{new['success_within_10m']:.1%}",
        ]
    )
table(rows, [110, 126, 126, 125])
p(
    "成功案例：独立测试在历元73向G03加85m、G20减90m。原单星算法无法归因；新方法唯一排除这两星，保留6星/2个验证自由度。单星、正常与渐变结果维持原有精度。"
)

page("失败案例与系统验收", 5)
p("双星仍可能不可唯一归因", "h2")
p(
    "保留组84个双星历元中4个仍为SUSPECT；这些历元没有从分母删除，也没有用真值帮助选择候选。单历元伪距的残差空间维度有限，相关故障可能形成多个一致假设，因此不能仅凭低残差断言定位可靠。"
)
p("噪声模型失配的实际代价", "h2")
p(
    "保留组重尾噪声下，多假设水平P95约24.31m、10m成功率78.6%，未稳定改善。实际附加高斯噪声为4m而检测sigma仍设1m时，错剔历元率32.1%；10m成功率96.4%，低于等权基线98.8%。这说明过度自信的先验会损伤表现，应在独立标定数据上研究历史噪声估计。"
)
p("GNC并非无条件收益", "h2")
p(
    "保留组双星场景GNC与consensus精度相同，P95耗时约57.6ms和12.4ms。当前8星问题可完整枚举，GNC排序尚未带来最终精度收益。保留研究轨迹以便未来比较，不以论文级别替代有效性证明。"
)
table(
    [
        ["系统要求", "自动验收"],
        ["课程模型/状态/导出/渐变/导入", "48项Python测试；其中8星×正负渐变全部达标"],
        ["浏览器操作与恢复", "2项前端单测；Chromium/WebKit共8项端到端"],
        ["输入与状态分离", "文件与拆包TCP逐字段一致；暂停期间不捏造历元"],
        ["过期与恢复", "历史值显式标记；刷新或仅恢复字节不能恢复当前有效位置"],
        ["原件与复现", "25个原包文件核验；原docx清单既有差异单独记录"],
    ],
    [171, 316],
)
p(
    "网页导入限制5000历元/16MiB，更长数据用CLI。服务当前为单API进程、单活动计算任务、本机访问；不具备多人公网权限系统。报告中的自动检查不能替代教师隐藏用例。",
    "small",
)

page("复现、参考文献与贡献记录", 6)
p("最短复现路径", "h2")
p(
    "安装：uv sync --locked；pnpm --dir web install --frozen-lockfile；pnpm --dir web build；uv run gnss serve。浏览器访问127.0.0.1:8000。批量与TCP命令见README；课程验收运行 scripts/validate_course.py。"
)
p(
    "实验：uv run gnss benchmark --out runtime/benchmark --seed 20261016 --samples 84。工具交叉校验：uv run --group research gnss cross-check。报告：uv run --group research python scripts/build_report.py --font <本机中文TTF路径>。所有命令在仓库根目录执行。"
)
p(
    "证据：docs/experiments/包含3组指标、报告、完整保留实验ZIP及交叉校验结果。网页每次运行保存输入、双解、诊断、事件、配置与输入/星历哈希；真值只用于运行后评估。原包哈希差异见docs/validation.md。"
)
p("参考文献与工具", "h2")
refs = [
    "[1] Piedade et al. SAC-GNC: SAmple Consensus for adaptive Graduated Non-Convexity. ICCV 2025, Highlight, 5780-5790. DOI:10.1109/ICCV51701.2025.00547. merl.com/research/highlights/sac-gnc",
    "[2] Yang et al. Graduated Non-Convexity for Robust Spatial Perception. IEEE RA-L, 2020. DOI:10.1109/LRA.2020.2965893. arxiv.org/abs/1909.08605",
    "[3] Wen, Zhang, Hsu. GNSS Outlier Mitigation via Graduated Non-Convexity Factor Graph Optimization. IEEE TVT 71(1):297-310, 2022. DOI:10.1109/TVT.2021.3130909.",
    "[4] GNSS/Multisensor Fusion Using Continuous-Time Factor Graph Optimization for Robust Localization. IEEE TRO 40, 2024. ieeexplore.ieee.org/document/10637732/",
    "[5] Stanford-NavLab/gnss_lib_py, version1.1.0. github.com/Stanford-NavLab/gnss_lib_py. 本项目仅接入snapshot WLS校验。",
    "[6] 课程原始任务书、MODEL_SPEC.md、INTERFACE.md与evaluate.py。完整来源与实现差异见docs/research.md。",
]
for reference in refs:
    p(reference, "small")
p("待真实成员补充（未完成）", "h2")
table(
    [
        ["成员", "实际工作与贡献凭证", "答辩核验"],
        ["待填写", "模型推导/实现与相关提交", "四未知量与各改正项"],
        ["待填写", "诊断与实验设计、结果复核", "成功及失败案例解释"],
        ["待填写", "界面、传输与交付验证", "暂停恢复和复现演示"],
    ],
    [72, 249, 166],
)


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#dce5eb"))
    canvas.line(54, 46, A4[0] - 54, 46)
    canvas.setFont("Chinese", 8)
    canvas.setFillColor(colors.HexColor("#758190"))
    canvas.drawString(54, 31, "GNSS Workbench v0.2 | 课程技术报告草稿 | 2026-10-14")
    canvas.drawRightString(A4[0] - 54, 31, str(document.page))
    canvas.restoreState()


pdf = ROOT / "docs/report.pdf"
SimpleDocTemplate(
    str(pdf),
    pagesize=A4,
    leftMargin=54,
    rightMargin=54,
    topMargin=46,
    bottomMargin=60,
    title="GNSS Workbench v0.2 技术报告草稿",
    author="GNSS Workbench",
).build(story, onFirstPage=footer, onLaterPages=footer)
print(pdf)
