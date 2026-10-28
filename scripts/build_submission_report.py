"""Build the six-page course report using Songti body and Heiti headings.

Requires reportlab and locally installed Songti/SimSun and Heiti/SimHei fonts.
Fonts are not redistributed; metrics, charts and UI captures live under
docs/experiments and docs/media.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/sadfaxzda/gnss-workbench"


def register_font(name: str, environment: str, candidates: list[tuple[Path, int]]) -> None:
    supplied = os.environ.get(environment)
    choices = (
        [(Path(supplied), int(os.environ.get(environment + "_INDEX", "0")))]
        if supplied
        else candidates
    )
    for path, index in choices:
        if path.is_file():
            pdfmetrics.registerFont(TTFont(name, str(path), subfontIndex=index))
            return
    raise SystemExit(f"Set {environment} to an installed licensed font file")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence", type=Path, default=ROOT / "docs/experiments/submission-20261028"
    )
    parser.add_argument("--out", type=Path, default=ROOT / "docs/report.pdf")
    parser.add_argument("--report-date", default="2026 年 10 月 21 日")
    args = parser.parse_args()
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    register_font(
        "ReportSong",
        "GNSS_REPORT_SONG_FONT",
        [(windows / "simsun.ttc", 0), (Path("/System/Library/Fonts/Supplemental/Songti.ttc"), 6)],
    )
    register_font(
        "ReportHei",
        "GNSS_REPORT_HEI_FONT",
        [(windows / "simhei.ttf", 0), (Path("/System/Library/Fonts/STHeiti Medium.ttc"), 1)],
    )
    analysis = json.loads((args.evidence / "analysis.json").read_text(encoding="utf-8"))
    metrics = {
        key: json.loads((args.evidence / f"{key}-metrics.json").read_text(encoding="utf-8"))
        for key in ("D02_sim_clean", "D03_sim_demo", "D03_sim_demo_ablation")
    }
    team = json.loads((ROOT / "docs/team.json").read_text(encoding="utf-8"))
    styles = {}
    for name, font, size, leading, after in (
        ("title", "ReportHei", 19, 29, 12),
        ("section", "ReportHei", 15, 23, 15),
        ("heading", "ReportHei", 11.5, 18, 7),
        ("body", "ReportSong", 10.5, 17.2, 8),
        ("small", "ReportSong", 9, 13.6, 6),
        ("caption", "ReportSong", 9, 13, 10),
        ("cell", "ReportSong", 9.5, 14, 0),
        ("cellhead", "ReportHei", 9.5, 14, 0),
        ("formula", "ReportSong", 10.5, 18, 8),
    ):
        styles[name] = ParagraphStyle(
            name,
            fontName=font,
            fontSize=size,
            leading=leading,
            textColor=colors.black,
            spaceAfter=after,
            wordWrap="CJK",
            alignment=TA_CENTER if name in {"title", "formula"} else 0,
            keepWithNext=name in {"section", "heading"},
        )
    styles["meta"] = ParagraphStyle("meta", parent=styles["small"], alignment=TA_CENTER)
    styles["body"].firstLineIndent = 21

    def text(value, style="body"):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

    story = []

    def p(value, style="body"):
        story.append(text(value, style))

    def equation(markup):
        story.append(Paragraph(markup, styles["formula"]))

    def page(title):
        if story:
            story.append(PageBreak())
        p(title, "section")

    def table(caption, rows, widths):
        p(caption, "caption")
        result = Table(
            [
                [text(cell, "cellhead" if i == 0 else "cell") for cell in row]
                for i, row in enumerate(rows)
            ],
            colWidths=widths,
            repeatRows=1,
            hAlign="CENTER",
        )
        result.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 0.9, colors.black),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                    ("LINEBELOW", (0, -1), (-1, -1), 0.9, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([result, Spacer(1, 11)])

    def figure(name, caption, width=495):
        picture = Image(str(ROOT / "docs/media" / name))
        picture.drawHeight *= width / picture.drawWidth
        picture.drawWidth = width
        story.append(KeepTogether([picture, Spacer(1, 5), text(caption, "caption")]))

    p("原始观测驱动的 GPS 定位\n与故障诊断系统", "title")
    p("空间信息与数字技术专业 · GNSS 课程实践实验报告", "meta")
    p("小组成员：张淳贺、马晨曦、刘芸睿    日期：" + args.report_date, "meta")
    story.append(
        Paragraph(f'公开代码仓库：<link href="{REPOSITORY}">{REPOSITORY}</link>', styles["meta"])
    )
    story.append(Spacer(1, 9))
    p("摘  要", "heading")
    p(
        "针对原始伪距中的异常观测，本实验实现 GPS L1 C1 单点定位与可解释故障诊断。"
        "系统以广播星历和伪距为输入，同时计算独立等权最小二乘普通解，以及经残差一致性检验、"
        "候选剔星和因果历史证据处置后的改进解。受控仿真 D03 的水平误差 P95 由 23.859 m "
        "降至 1.594 m，要求定位历元的有效解比例保持 100%；关闭故障处置后，指标回到普通解水平。"
        "六星冷启动案例出现 33.559 m 水平误差，揭示了低冗余条件下的故障识别歧义。"
        "结果表明，残差诊断与候选选择能够抑制单星偏差，低冗余条件下的候选歧义是主要误差来源。"
    )
    p("关键词：GPS 单点定位；伪距；残差一致性；故障排除；可复现实验", "small")
    p("1  实验目的与系统概览", "heading")
    p(
        "实验依据课程模型与接口规范 [1]，验证从原始观测求解三维位置及接收机钟差的正确性，"
        "比较普通解、改进解与消融结果，并检查少星及传输中断时的状态表达。"
        "图 1 展示文件回放后的实际界面；同一计算核心也供 TCP 实时模式调用。"
    )
    figure(
        "submission-workbench.png",
        "图 1  D03 实际运行界面。轨迹为相对首次有效改进解原点的 ENU 位移，"
        "用于观察解算连续性；定位精度由第 4 节与真值的比较给出。",
        465,
    )

    page("2  定位原理与实验条件")
    p("2.1  四未知数观测模型", "heading")
    equation(
        "P<sub>i</sub> = ρ<sub>i</sub> + b - c·dt<sub>sat,i</sub> + c·TGD<sub>i</sub> + I<sub>i</sub> + T<sub>i</sub> + ε<sub>i</sub> + f<sub>i</sub>　(1)"
    )
    p(
        "状态向量为 [x, y, z, b]，前三项是 WGS 84 ECEF 坐标，b = c·Δt 为米制接收机钟差。"
        "ρ_i 是几何距离，dt_sat,i 包含卫星钟差及周期相对论项，TGD_i 只改正一次；"
        "I_i、T_i 分别为电离层和对流层延迟，ε_i 为噪声，f_i 为故障偏差。"
    )
    p(
        "根据广播星历计算卫星轨道，迭代发射时刻，并对信号传播期间的地球自转作一次坐标旋转。"
        "电离层采用 Klobuchar 模型并统一角度单位；对流层采用固定气象参数的 "
        "Saastamoinen 公式。地心初值先求粗解，再启用大气改正；星历有效时间范围为参考时刻前后两小时。"
    )
    p("2.2  普通解、残差与几何精度", "heading")
    equation(
        "H<sub>i</sub> = [(x-x<sub>si</sub>)/ρ<sub>i</sub>, (y-y<sub>si</sub>)/ρ<sub>i</sub>, (z-z<sub>si</sub>)/ρ<sub>i</sub>, 1]　(2)"
    )
    equation(
        "δu = arg min ||H·δu - v||<super>2</super>,　Q = (H<super>T</super>H)<super>-1</super>,　PDOP = √(Q<sub>xx</sub>+Q<sub>yy</sub>+Q<sub>zz</sub>)　(3)"
    )
    p(
        "每历元按式 (2) 线性化并迭代等权最小二乘。上一历元解用作迭代初值，"
        "各历元分别估计三维坐标与钟差。残差 RMS 衡量观测拟合程度；PDOP 由实际参与卫星的"
        "未加权几何矩阵计算，表征卫星几何对位置估计的误差放大。定位误差通过 ENU 坐标系中的真值比较计算。"
    )
    table(
        "表 1  统一数据、配置与软件环境",
        [
            ["项目", "设置与用途"],
            [
                "D01 / D02 / D03",
                "20 历元真实摘录 / 600 历元正常仿真 / 600 历元异常仿真；D02、D03 为 1 Hz",
            ],
            ["模型与迭代", "高度角截止 3°；最多 20 次迭代；状态增量收敛阈值 0.0001 m"],
            ["默认诊断", "consensus；初始噪声尺度 1 m；检验显著性 0.001；最多排除 2 星"],
            ["因果历史", "最多 16 历元；相对证据门槛 20:1；完整配置保存在各组 manifest.json"],
            [
                "软件与依赖",
                "macOS；Python 3.14.4 主复核、3.12.14 交叉复跑；uv.lock 与 pnpm-lock.yaml 锁定依赖",
            ],
        ],
        [105, 390],
    )
    p(
        "D01 取自 RTKLIB 历史测试数据 [2]，用于验证真实观测的读取和定位流程。"
        "D02、D03 提供仿真轨迹、钟差和异常观测，精度评价采用配套的位置与钟差真值。"
        "卫星位置与钟差计算通过 24 个配套检查点验证。",
        "small",
    )

    page("3  故障诊断与实时实现")
    p("3.1  残差检验与候选选择", "heading")
    p(
        "普通解的残差先作卡方一致性检验。检验异常时枚举单星剔除；无通过候选时再检查最多双星，"
        "每个候选至少保留五星，并重新检验残差与几何。最终位置仍由当前历元保留观测计算。"
        "多个候选均可解释观测时，使用已收到历元的残差证据辅助判断，并检查换星、时间间隔与当前反证。"
    )
    p(
        "候选首先接受一致性与几何检验，再依据当前历元或因果历史的相对证据选择。满足确认规则时，状态记为 FAULT_EXCLUDED；"
        "候选身份存在歧义时记为 SUSPECT，并可采用暂定子集计算位置。四星可解时标记 NO_REDUNDANCY；少于四星时输出无效状态，"
        "XYZ、钟差等字段留空。图 2 展示了逐星残差、候选检验统计量与排除结果。"
    )
    figure(
        "submission-diagnostics.png",
        "图 2  D03 历元 121 的逐星诊断界面。系统显示 G19 的异常残差与排除标记，"
        "并列出各候选子集的检验统计量与判定结果。",
    )
    p("3.2  时间因果性与输出契约", "heading")
    p(
        "文件与 TCP 共用 PositioningEngine，按输入 GPST 逐历元推进。TCP 按 LF 分帧，处理拆包、"
        "粘包及结束帧；超过 max(3 秒, 3×回放间隔) 无数据即标记过期，接收恢复后按实际到达历元继续更新。"
        "诊断按当前与过去观测递推，UI 同步显示接收状态并保留历史轨迹供回看。"
    )
    p(
        "baseline.csv 与 improved.csv 均逐历元输出规定的 14 列，空观测也保留一行。"
        "diagnostics.jsonl 保存逐星残差、权重、角度、候选评分和算法轨迹；manifest.json 保存"
        "输入哈希、源码身份与全部配置。运行结果及日志随源代码文件夹提交。",
        "small",
    )

    page("4  对照实验与成功案例分析")
    p("4.1  评价方法与对照设置", "heading")
    p(
        "对同一输入保留普通解和默认改进解，另关闭 FDE 作消融；除故障处置开关外条件相同。"
        "用教师评价器将估计坐标与真值之差转为 ENU，取水平模长。P95 在要求定位且有解的历元上计算；"
        "有效解比例和 10 m 成功率以全部要求定位历元为分母。D03 分母为 570：保留 20 个四星历元，"
        "另核查 20 个三星及 10 个零星历元的无效状态。"
    )
    rows = [["数据与模式", "要求历元", "有效解比例", "水平 P95/m", "10 m 成功率"]]
    for dataset, mode, label in (
        ("D02_sim_clean", "baseline", "D02 普通"),
        ("D02_sim_clean", "improved", "D02 改进"),
        ("D03_sim_demo", "baseline", "D03 普通"),
        ("D03_sim_demo", "improved", "D03 改进"),
        ("D03_sim_demo_ablation", "improved", "D03 关闭 FDE"),
    ):
        item = metrics[dataset][mode]
        rows.append(
            [
                label,
                item["position_required_epochs"],
                f"{item['availability_on_required']:.0%}",
                f"{item['h_p95_m']:.3f}",
                f"{item['success_within_10m_on_required']:.3%}",
            ]
        )
    table("表 2  同输入对照与消融结果", rows, [116, 72, 94, 103, 110])
    figure(
        "submission-error.png",
        "图 3  D03 逐历元水平真值误差（从提交 CSV 绘制）。灰色区间标记偏差注入及卫星数量变化；"
        "三星、零星历元折线中断，表示状态机未输出有效位置。",
    )
    p("4.2  单星偏差、共同偏差与消融解释", "heading")
    p(
        "历元 120-179 对 G19 注入 +80 m，60 次均正确标记并排除；该窗口水平 P95 从 24.450 m "
        "降至 1.738 m，510 个无逐星故障的要求定位历元误报为 0。图 3 显示收益集中于故障窗口；"
        "D02 双解一致，关闭 FDE 后 D03 P95 回到 23.859 m，支持收益来自异常观测处置。"
    )
    p(
        "历元 300-359 的全星共同 +100 m 主要被接收机钟差吸收，水平与钟差误差 P95 分别为 "
        "1.394 m、1.388 m，未产生逐星报警。20 个四星、30 个三星/零星历元的状态判定全部正确，"
        "600 行输出完整保留。",
        "small",
    )

    page("5  方法局限、误差来源与结论")
    p("5.1  六星冷启动：低冗余条件下的误选", "heading")
    p(
        "从 D02 取前 35 历元，每历元仅保留输入顺序的前六星，对 G07 施加 -30 m 伪距偏差，"
        "其余观测及位置、钟差真值保持不变。通过该实验观察卫星数减少与冷启动对候选选择的影响，"
        "结果见表 3。"
    )
    item = analysis["six_satellite_limit"]
    table(
        "表 3  六星案例的异常现象及定位结果",
        [
            ["观察项", "结果"],
            ["首历元真实故障 / 暂定排除", "G07 / G20"],
            ["输出状态 / 实际参与卫星数", "SUSPECT / 5"],
            ["后验残差 RMS / PDOP", "0.01486 m / 2.512"],
            ["首历元水平真值误差", f"{item['epoch0_horizontal_error_m']:.3f} m"],
            [
                "35 历元错剔 / 错误确认",
                f"{item['wrong_exclusions']} / {item['confirmed_wrong_exclusions']}",
            ],
        ],
        [250, 245],
    )
    p("5.2  误选机制与误差来源", "heading")
    p(
        "六星删一星只剩五条观测、四个未知数，即一个残差检验自由度。不同剔星候选可能以相近残差拟合观测，"
        "故障偏差可被位置及钟差吸收；冷启动缺少历史证据，最小残差候选未必对应真实故障星。"
        "表 3 中，错误排除 G20 后的残差 RMS 为 0.01486 m、PDOP 为 2.512，而水平误差达到 33.559 m，说明该候选以较小残差吸收了故障偏差。"
        "系统将该次选择标记为 SUSPECT，记录暂定排除星及候选比较结果。"
    )
    p(
        "误差还受卫星几何、噪声尺度假设和模型误差影响。四星无冗余，五星删一星后无法再检验；"
        "故障切换或观测集合变化会削弱历史证据，改变候选间的相对分数。"
        "噪声尺度设定影响检验阈值，模型误差则进入残差并影响位置与钟差估计。"
    )
    p(
        "已有扩展实验 [3] 中，六星 196 例中 24 例未满足全部检查门槛，出现 295 次错剔与 "
        "6 次错误确认。第八轮 coherent_proposals 虽改善部分高噪声结果，却使一个不规则换星案例由通过变为失败，因此默认关闭。"
        "这表明历史信息的引入需要兼顾噪声抑制与故障切换响应。",
        "small",
    )
    p("5.3  实验结论", "heading")
    p(
        "在本套受控数据中，残差检验结合候选处置显著降低单星偏差引起的定位误差，评价覆盖全部要求定位历元。"
        "共同偏差主要进入钟差；少星时状态机区分输出无冗余或无解。后续工作聚焦独立观测、噪声标定与"
        "候选确认规则的检验，并在未参与调参的数据上复验方法稳定性。"
    )

    page("6  实验复现与小组分工")
    p("6.1  运行环境与复现步骤", "heading")
    p("在提交目录的“源代码”中依次执行：", "small")
    for line in (
        "python scripts/verify_submission.py --root .",
        "uv sync --locked",
        "uv run gnss serve",
        "uv run python scripts/reproduce_submission.py --out runtime/reproduction",
    ):
        p(line, "small")
    p(
        "第三条命令运行期间，在浏览器打开 http://127.0.0.1:8000；第四条在另一终端运行。"
        "邮件代码已含预构建 UI，运行无需 Node；首次安装 Python 依赖需联网。复现目录须为空，"
        "TCP 回放、单组评价、开发依赖和重建报告命令见 README。公开仓库可直接访问下载。",
        "small",
    )
    p("6.2  小组分工与模块核验", "heading")
    table(
        "表 4  小组分工与模块核验内容",
        [
            ["成员", "主要工作", "模块核验内容"],
            [
                "张淳贺",
                "完成 UI 设计与实现；先行完成初版编程",
                "演示双轨迹、逐星信息、状态切换与导出",
            ],
            ["马晨曦", "在张淳贺初版代码基础上进行优化", "解释普通解、诊断依据、消融与失败条件"],
            ["刘芸睿", "负责实验报告撰写与整理", "从 CSV 复核指标，解释分母、成功案例与局限"],
        ],
        [63, 215, 217],
    )
    p(
        "小组共同完成观测模型、输入输出接口及实验结果的一致性审查，"
        "并通过同输入对照、逐星日志抽查和界面回放交叉核对各模块。",
        "small",
    )
    p("6.3  实现验证与结果核对", "heading")
    p(
        "实现验证覆盖数值模型、数据接口和实时交互。结果核对采用相同输入重算、教师评价器计算以及逐历元和逐星日志检查。"
        "本机检查 Python 166 项、Vitest 16 项、Chromium/WebKit 流程 16 项全部通过；锁定依赖的 "
        "Python 3.12 与 3.14 输出共 3710 行对照，除耗时外完全一致。检查日志、输入哈希、配置与执行时间随包保存。",
        "small",
    )
    p("参考资料", "heading")
    for entry in (
        "[1] 课程组. 原始观测驱动的 GPS 定位与故障诊断系统：作业任务书、MODEL_SPEC.md、INTERFACE.md. GNSS-COURSE-1.0. 见 fixtures/course/docs/。",
        "[2] RTKLIB. 历史观测与广播星历测试数据. 摘录来源、范围及许可见 fixtures/course/data/provenance.json 与 LICENSE_RTKLIB.txt。",
        "[3] 本小组. 算法研究及扩展验证记录. docs/research.md、docs/diagnosis-iteration7.md、docs/diagnosis-iteration8.md；本次指标见 docs/experiments/submission-20261028/。",
        "[4] 本小组. GNSS Workbench 完整源代码与复现说明. " + REPOSITORY + "。",
    ):
        p(entry, "small")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#888888"))
        canvas.setLineWidth(0.4)
        canvas.line(50, 38, A4[0] - 50, 38)
        canvas.setFont("ReportSong", 8)
        canvas.drawString(50, 24, "GNSS 课程实践实验报告")
        canvas.drawRightString(A4[0] - 50, 24, f"第 {doc.page} 页 / 共 6 页")
        canvas.restoreState()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(args.out),
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=43,
        bottomMargin=51,
        title="原始观测驱动的 GPS 定位与故障诊断系统",
        author="、".join(m["name"] for m in team["members"]),
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.out)


if __name__ == "__main__":
    main()
