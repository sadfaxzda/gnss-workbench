"""Build the course report from the audited release evidence and real team fields.

Requires reportlab and locally installed, licensed Microsoft YaHei/Times New Roman.
No font binaries are distributed. Historical iteration reports remain reproducible.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]


def font_path(environment: str, candidates: list[Path]) -> Path:
    supplied = os.environ.get(environment)
    paths = [Path(supplied)] if supplied else candidates
    for path in paths:
        if path.is_file():
            return path
    raise SystemExit(f"Set {environment} to an installed licensed font file")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence", type=Path, default=ROOT / "docs/experiments/submission-20261017"
    )
    parser.add_argument("--out", type=Path, default=ROOT / "docs/report.pdf")
    args = parser.parse_args()
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    chinese = font_path(
        "GNSS_REPORT_CHINESE_FONT",
        [Path.home() / "Library/Fonts/msyh.ttf", windows / "msyh.ttc"],
    )
    english = font_path(
        "GNSS_REPORT_ENGLISH_FONT",
        [Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf"), windows / "times.ttf"],
    )
    pdfmetrics.registerFont(TTFont("ReportChinese", str(chinese)))
    pdfmetrics.registerFont(TTFont("ReportEnglish", str(english)))
    summary = json.loads((args.evidence / "summary.json").read_text(encoding="utf-8"))
    public = {
        key: json.loads((args.evidence / f"{key}-metrics.json").read_text(encoding="utf-8"))
        for key in ("D02_sim_clean", "D03_sim_demo")
    }
    compatibility = json.loads((args.evidence / "compatibility.json").read_text(encoding="utf-8"))
    team = json.loads((ROOT / "docs/team.json").read_text(encoding="utf-8"))
    ink, blue = colors.HexColor("#293139"), colors.HexColor("#355f79")
    styles = {
        name: ParagraphStyle(
            name,
            fontName="ReportChinese",
            fontSize=size,
            leading=leading,
            textColor=blue if name == "title" else ink,
            spaceAfter=after,
            wordWrap="CJK",
        )
        for name, size, leading, after in (
            ("title", 19, 29, 18),
            ("heading", 12, 19, 8),
            ("body", 10, 17, 10),
            ("small", 8.5, 13, 7),
            ("cell", 9, 14, 0),
        )
    }

    def text(value, style="body"):
        # Latin letters, digits and Greek mathematical symbols use Times New Roman.
        parts = re.split(r"([\x00-\u024f\u0370-\u03ff\u2200-\u22ff]+)", str(value))
        markup = "".join(
            f'<font name="ReportEnglish">{escape(part)}</font>' if i % 2 else escape(part)
            for i, part in enumerate(parts)
        )
        return Paragraph(markup, styles[style])

    story = []

    def p(value, style="body"):
        story.append(text(value, style))

    def page(title):
        if story:
            story.append(PageBreak())
        p(title, "title")

    def table(rows, widths):
        result = Table(
            [[text(cell, "cell") for cell in row] for row in rows], colWidths=widths, repeatRows=1
        )
        result.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef0f2")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4c9cf")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.extend([result, Spacer(1, 12)])

    page("原始观测驱动的 GPS 定位与故障诊断系统")
    p("课程实践实验报告 · 2026-10-17", "heading")
    p("小组成员：" + "、".join(member["name"] for member in team["members"]))
    p(
        "本系统读取 GPS L1 C1 伪距与广播星历，逐历元估计接收机三维位置和钟差，同时保留独立等权普通解与故障处置后的改进解。浏览器工作台支持轨迹、逐星诊断、实验对照、历史回放与结果导出；文件和 TCP 输入调用同一计算核心。"
    )
    table(
        [
            ["任务要求", "对应实现与提交证据"],
            [
                "自主定位",
                "广播轨道与钟差、发射时刻、自转、TGD、电离层和对流层改正；卫星检查点与公开数据复算",
            ],
            ["异常诊断", "残差检验、多假设比较与因果历史证据；保存处置卫星、残差、权重和候选决策"],
            [
                "实时软件",
                "文件逐历元 / TCP 回放；显示位置、钟差、卫星数、PDOP、残差和状态；暂停与恢复提示",
            ],
            [
                "可评价输出",
                "两份 14 列 CSV，每输入历元各一行；无效坐标留空；输入、配置与日志可追溯",
            ],
            [
                "对照与解释",
                "关闭改进模块消融；公开和新生成数据分开；成功案例、少星失败与真实分工栏",
            ],
        ],
        [100, 395],
    )
    p("数据与评价范围", "heading")
    p(
        "D01 为 20 历元真实历史观测，无独立位置真值；D02 和 D03 各 600 历元，具有仿真真值。新生成验证改变位置、轨迹、钟差、噪声、故障星与时刻，但仍共享课程星历及物理函数。本文中的米级精度是受控仿真结果，未以真实片段或教师隐藏数据宣称验收通过。"
    )
    p(
        "本报告对应提交前复核的软件版本。成员姓名已核实；按小组要求，实际分工和个人核验暂留空，见第 6 页。"
    )

    page("观测模型与独立定位")
    p("观测方程", "heading")
    p("P = ρ + b − c·dt_sat + c·TGD + I + T + ε + f")
    p(
        "状态量为 [x, y, z, b]，位置采用 WGS 84 ECEF 米，b = c·Δt_receiver 为米制钟差。ρ 为接收时刻坐标系下的几何距离；dt_sat 包含周期相对论改正，TGD 另计一次。I、T 分别为电离层和对流层延迟，ε 为噪声，f 为异常偏差。"
    )
    p(
        "由广播星历迭代求发射时刻卫星位置和钟差，将卫星坐标旋转到接收时刻 ECEF。电离层采用 Klobuchar，注意半圆与弧度；对流层采用教师规定气象常数的 Saastamoinen 模型，统一截止高度角 3°。地心初值阶段先求粗解，再启用大气改正。"
    )
    p("线性化与质量量", "heading")
    p(
        "每条观测的设计矩阵行为 [(x−x_s)/ρ, (y−y_s)/ρ, (z−z_s)/ρ, 1]。通过最小二乘库逐次求四个未知数增量，重新计算改正和残差直到收敛。普通解始终独立等权；上一解只作数值初值，不固定高度、位置或轨迹。"
    )
    p(
        "Q = (H^T H)^(-1)；PDOP = sqrt(Qxx + Qyy + Qzz)。使用参与解算卫星的未加权几何矩阵；秩不足时不输出有效 PDOP。残差 RMS 描述模型拟合程度，与真值处 ENU 水平误差分别报告。"
    )
    table(
        [
            ["条件", "输出规则"],
            ["0 星 / 1—3 星", "NO_OBSERVATIONS / INVALID_INSUFFICIENT；位置、钟差、PDOP、残差留空"],
            ["4 星且几何可解", "NO_REDUNDANCY；四未知数恰定，没有单历元检验冗余"],
            ["差几何 / 不收敛", "给出 GEOMETRY_WARNING 或对应 INVALID 状态；保留原因与诊断日志"],
        ],
        [135, 360],
    )
    p(
        f"与改动前版本 55d8d3a 对照 {compatibility['epochs_compared']} 历元，普通解状态及参与数一致，数值最大差 {compatibility['max_baseline_numeric_difference']:.3g}。{compatibility['teacher_files_byte_identical']} 个教师原文件与最初 ZIP 逐字节一致。",
        "small",
    )

    page("异常诊断与实时处理")
    p("当前观测决定位置，历史残差辅助身份判断", "heading")
    p(
        "默认 consensus 对四未知数拟合残差作卡方一致性检验；枚举单星排除，无通过候选时再检验最多双星。候选必须至少保留五颗卫星，满足残差与几何门限。通过的候选和采用的候选分别记录，避免将低残差直接当作正确故障身份。"
    )
    p(
        "少星歧义时，最多使用 16 个已收到历元的残差证据比较单星假设；相对证据门槛为 20:1，并检查当前反证、时间连续性、换星和偏差变化。诊断噪声尺度由过去的不重叠历元对估计。最终坐标仍由当前观测独立拟合。"
    )
    table(
        [
            ["处置结果", "解释"],
            ["FAULT_EXCLUDED", "方法的确认条件通过，明确记录实际排除卫星；属于算法诊断结论"],
            ["SUSPECT", "身份未确认；可能给出暂定子集解，日志和界面明确区分暂定与确认"],
            ["5 星异常", "剔一星后无验证冗余；保持疑似异常，不凭当前低残差确认故障身份"],
            ["实验选项", "coherent_proposals 默认关闭；独立验证出现新增失败后未替换生产默认"],
        ],
        [135, 360],
    )
    p("实时接口与证据保存", "heading")
    p(
        "文件和 TCP 逐历元调用同一 PositioningEngine，不读取未来观测，不把真值传入核心。TCP 以 LF 分帧，处理拆包、粘包和结束帧；超过 max(3 秒, 3×回放间隔) 提示数据过期，收到新数据后恢复。暂停期间不伪造历元，历史位置不标为当前有效。"
    )
    p(
        "保存原始输入、变换后输入、导航、配置、源码标识、两份 CSV、逐星诊断和事后评价。每次运行单独建目录；CLI 遇坏帧保存已完成结果并非零退出。关闭 FDE 后，改进结果与普通解一致。"
    )

    page("公开数据与新生成对照实验")
    rows = [["公开案例", "普通解水平 P95", "改进解水平 P95", "有效解比例"]]
    for name, label in (("D02_sim_clean", "D02 正常"), ("D03_sim_demo", "D03 异常")):
        data = public[name]
        rows.append(
            [
                label,
                f"{data['baseline']['h_p95_m']:.3f} m",
                f"{data['improved']['h_p95_m']:.3f} m",
                f"{data['improved']['availability_on_required']:.2%}",
            ]
        )
    table(rows, [105, 130, 130, 130])
    d03 = public["D03_sim_demo"]["improved"]
    p(
        f"D03 的 {d03['strong_fault_epochs_bias_ge_30m']} 个强故障历元正确标星率 {d03['fault_detection_recall']:.2%}，正常误报率 {d03['false_alarm_epoch_rate']:.2%}；20 个四星、30 个不足观测历元状态正确。D01 的 20 历元可解算，仅用于真实格式兼容。"
    )
    p("新种子验证与消融", "heading")
    p(
        "固定当前算法后使用种子 2026101701—2026101704。每份输入运行关闭改进模块和当前默认两种配置；真值仅在求解后评价。单星阶跃、渐变、冷启动、换星、恢复及共同偏差均保留，逐例门槛检查不以整体平均替代。"
    )
    rows = [["场景 / 历元", "关闭改进 P95", "默认 P95", "默认 10 m 成功率"]]
    for key, label in (
        ("eight", "八星"),
        ("seven", "七星"),
        ("six", "六星"),
        ("variable", "星数变化"),
    ):
        item = summary[key]
        a, b = item["ablation"], item["default"]
        rows.append(
            [
                f"{label} / {b['epochs']:,}",
                f"{a['required_h_p95_m']:.3f} m",
                f"{b['required_h_p95_m']:.3f} m",
                f"{b['required_success10']:.2%}",
            ]
        )
    table(rows, [125, 120, 115, 135])
    p(
        "八星 83 例、七星 56 例逐例达到本次所检查的建议线。六星虽整体通过，196 例中仍有 24 例未达到全部门槛。星数变化含四／五星故障，7 例中 4 例未达到全部门槛，140 个特设状态历元判断正确。"
    )
    p(
        "水平 P95 基于要求定位且已输出位置的历元；10 m 成功率分母包括全部要求定位历元。强故障为单星偏差绝对值 ≥30 m。所有新案例的课程 CSV 契约违规为 0；完整逐例结果、参数、种子和源码哈希见 docs/experiments/submission-20261017。",
        "small",
    )

    page("结果分析与方法局限")
    p("成功案例：单星偏差的诊断与恢复", "heading")
    p(
        "公开 D03 在历元 120—179 对 G19 增加 80 m 伪距偏差。普通解受到影响，默认方法识别并排除 G19，随后恢复正常使用。整组水平 P95 从 23.859 m 降至 1.594 m。全星共同 +100 m 的窗口主要体现为钟差变化，未把所有卫星误判为故障。"
    )
    six = summary["six"]["default"]
    p("失败案例：少星条件下的故障歧义", "heading")
    p(
        f"新六星验证中，强故障正确标星率 {six['correct_flag_recall']:.2%}，确认且正确的比例 {six['confirmed_correct_recall']:.2%}；出现 {six['wrong_exclusions']} 次错剔，其中 {six['confirmed_wrong_exclusions']} 次被错误确认。两者分开报告，暂定标星不能当作确认率。"
    )
    p(
        "删除不同卫星后，剩余观测可能同时拟合良好。冷启动没有历史，故障切换可能破坏持续身份假设；五星排除后仅四条观测，也不能通过零残差验证选对了卫星。四星无冗余状态正确，不代表四星带故障时仍可保证精度。"
    )
    p("压力结果与默认选择", "heading")
    p(
        "第八轮实验归档的额外 2.4 m 噪声压力中，默认整体水平 P95 为 26.366 m；实验提议降至 24.504 m，但在一个不规则案例把 10 m 成功率从 95.83% 降至 94.79%。因此实验默认关闭。该历史压力结果保留原始归档，没有被本轮名义噪声结果覆盖。"
    )
    p("建议线的适用范围", "heading")
    p(
        "任务书明确列出正常动态、单星偏差／渐变、4／3／0 星、共同偏差、极差几何及传输暂停；没有单独规定五星一故障或任意少星叠加故障的统一数值保证。扩展试验用于暴露限制，不冒充教师隐藏案例；已有失败也不因未被逐字列出而删去。"
    )
    p(
        "改进方向是引入可验证的额外观测或更充分的因果诊断证据，并在未参与调参的数据上分场景复验。不能以固定高度、借用真值、未来平滑或删掉失败历元提高成绩。"
    )

    page("复现、交付与个人核验")
    p("使用交付包", "heading")
    for line in (
        "python scripts/verify_submission.py --root .",
        "uv sync --locked",
        "uv run gnss serve",
        "浏览器访问 http://127.0.0.1:8000",
    ):
        p(line, "small")
    p(
        "包内已构建前端，首次安装 Python 依赖需要网络；完成安装后可用 uv run --offline gnss serve 演练。批处理命令、教师 TCP 回放、消融与新种子复现命令见 README 和提交审查记录。"
    )
    p("交付内容与核验", "heading")
    p(
        "完整源码、锁文件、六页报告、预构建前端、D01／D02／D03 新运行结果与 D03 消融，以及输入、导航、诊断日志和 SHA256 清单。封存源码后再在临时目录运行；不包含虚拟环境、凭证、本机历史或旧版本交付 ZIP。安装、API、批处理和浏览器流程的本轮实测记录随包保存。"
    )
    p(
        "源码测试覆盖模型、因果性、普通解独立性、少星状态、TCP 分帧与恢复、持久化和导出。软件测试通过与教师隐藏数据验收、个人答辩分别记录。"
    )
    p("真实分工与个人核验", "heading")
    table(
        [["成员", "实际负责模块", "已完成个人核验"]]
        + [
            [m["name"], m["actual_responsibility"] or "", m["completed_verification"] or ""]
            for m in team["members"]
        ],
        [100, 195, 200],
    )
    p(
        "分工栏按小组要求暂留空，提交前由成员据实补充。每人须能解释负责模块的输入、模型、输出和失败条件；AI 辅助编码和测试不替代个人理解。",
        "small",
    )
    p("参考资料与方法来源", "heading")
    p(
        "[1] 教师《作业任务书》、MODEL_SPEC.md、INTERFACE.md，GNSS-COURSE-1.0。\n[2] RTKLIB 提供真实历史观测与广播星历摘录，来源与许可见课程 provenance.json、LICENSE_RTKLIB.txt。\n[3] ESA Navipedia: RAIM；Positioning Error。\n[4] 论文启发的 GNC 实验及方法出处见 docs/research.md；诊断历次设计、失败与部署决定见 docs/diagnosis-iteration8.md。",
        "small",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#c4c9cf"))
        canvas.line(50, 42, A4[0] - 50, 42)
        line = text("GNSS 定位与故障诊断 · 课程实践报告", "small")
        line.wrap(400, 15)
        line.drawOn(canvas, 50, 24)
        canvas.setFont("ReportEnglish", 9)
        canvas.drawRightString(A4[0] - 50, 28, f"{doc.page} / 6")
        canvas.restoreState()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(args.out),
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=45,
        bottomMargin=58,
        title="原始观测驱动的 GPS 定位与故障诊断系统",
        author="、".join(m["name"] for m in team["members"]),
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.out)


if __name__ == "__main__":
    main()
