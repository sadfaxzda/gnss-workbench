"""Build the six-page iteration-seven report from frozen evidence and confirmed names.

Requires reportlab (uv sync --group research). Does not rerun or tune the solver.
The prior build_report.py remains the reproducible historical report builder.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/experiments/diagnosis-iteration6"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
    )
    parser.add_argument("--out", type=Path, default=ROOT / "docs/report.pdf")
    args = parser.parse_args()
    if not args.font.is_file():
        raise SystemExit("Provide --font with a licensed Chinese TrueType font")
    pdfmetrics.registerFont(TTFont("ReportCJK", str(args.font)))
    summary = json.loads((EVIDENCE / "summary.json").read_text())
    latest = json.loads((ROOT / "docs/experiments/diagnosis-iteration7/summary.json").read_text())
    team = json.loads((ROOT / "docs/team.json").read_text())
    blue, grey = colors.HexColor("#27516C"), colors.HexColor("#53616B")
    styles = {
        "title": ParagraphStyle(
            "title",
            fontName="ReportCJK",
            fontSize=22,
            leading=30,
            textColor=blue,
            spaceAfter=16,
            wordWrap="CJK",
        ),
        "h": ParagraphStyle(
            "h",
            fontName="ReportCJK",
            fontSize=13,
            leading=20,
            textColor=blue,
            spaceBefore=10,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "body", fontName="ReportCJK", fontSize=10, leading=16, spaceAfter=9, wordWrap="CJK"
        ),
        "small": ParagraphStyle(
            "small",
            fontName="ReportCJK",
            fontSize=8.5,
            leading=13,
            spaceAfter=7,
            wordWrap="CJK",
            textColor=grey,
        ),
        "cell": ParagraphStyle(
            "cell", fontName="ReportCJK", fontSize=9, leading=14, wordWrap="CJK"
        ),
    }
    story = []

    def p(text, style="body"):
        story.append(Paragraph(escape(text), styles[style]))

    def heading(number, title):
        if number > 1:
            story.append(PageBreak())
        p(f"GNSS WORKBENCH  /  实验报告  /  {number:02d}", "small")
        p(title, "title")

    def table(rows, widths):
        data = [[Paragraph(escape(str(cell)), styles["cell"]) for cell in row] for row in rows]
        t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E1E6")),
                ]
            )
        )
        story.extend([t, Spacer(1, 10)])

    heading(1, "原始观测驱动的GPS定位\n与故障诊断系统")
    p("第七轮实现与验证 · 2026-10-17 · 分工与个人核验待确定", "h")
    p(
        "从GPS L1 C1伪距和广播星历逐历元求三维位置与米制钟差，同时输出独立等权普通解与异常处理后的改进解。文件和TCP回放调用同一计算核心，网页显示双轨迹、逐星残差、几何质量与实时状态。"
    )
    p(
        "本轮完成83个全八星新案例共6,640历元的独立补验，每例达到对应建议门槛；修复无Git源码副本无法打包的问题，结果从封存源码生成并可校验。新增分段历史诊断实验在六星冷启动中变差，未合入默认。部分低冗余与高噪声条件仍未达标。"
    )
    table(
        [
            ["教师要求", "实现与核验"],
            ["自主定位与完整改正", "广播轨道、钟差、TGD、自转、电离层及对流层；至少四颗独立观测"],
            ["普通/改进对照与消融", "同历元双解；关闭FDE后等于普通解；新增历史尺度消融"],
            ["实时软件与统一输出", "文件/TCP同核心；14列CSV；空历元保留；无效数值留空"],
            ["成功案例与方法局限", "公开D03显著改善；六星首历元和部分换星仍会误选"],
        ],
        [145, 350],
    )
    p("数据边界", "h")
    p(
        "D01是20历元真实历史C1摘录，没有独立位置真值；D02/D03与本轮扩展集是受控仿真。原始26个教师文件未改变。所有精度指标只适用于所列仿真输入，不代表真实道路、手机接收机或教师隐藏案例。"
    )
    p(
        "小组成员：马晨曦、张淳贺、刘芸睿（用户已确认）。实际分工与个人核验待确定，见第6页。本文结合第六轮算法证据与第七轮新输入补验，不代表已通过教师隐藏测试。",
        "small",
    )

    heading(2, "计算模型与失败条件")
    p("观测模型与独立普通解", "h")
    p(
        "P = ρ + b - c·dt_sat + c·TGD + I + T + ε + f。状态为[x,y,z,b]，b=c·接收机钟差，单位m；卫星钟差含周期相对论，不含TGD。发射时刻迭代后，将卫星坐标旋转到接收时刻ECEF，只改正一次地球自转。"
    )
    p(
        "Klobuchar采用导航参数；Saastamoinen按教师固定气象公式；统一3°截止角。地心初值阶段暂不使用不合理的大气参数，获得近地表粗解后继续迭代。用最小二乘库求增量，未收敛或几何失效返回对应无效状态。"
    )
    p(
        "普通解每历元独立等权。上一解仅作迭代初值，不能固定坐标或高度绕过少星条件。PDOP来自实际参与卫星的未加权几何矩阵；残差RMS不是坐标RMSE。"
    )
    table(
        [
            ["条件", "状态与行为"],
            ["0星 / 1至3星", "NO_OBSERVATIONS / INVALID_INSUFFICIENT；位置、钟差、PDOP及残差留空"],
            ["4星且几何可解", "NO_REDUNDANCY；可解算，但零残差不能证明没有故障"],
            ["5星", "可检测不一致；剔一星后无验证冗余，不盲目确认或剔星"],
            ["6星及以上", "检验候选残差、几何及身份；证据不足时保持SUSPECT"],
            ["差几何 / 不收敛", "GEOMETRY_WARNING或对应INVALID状态；失败恢复须通过完整模型重算"],
        ],
        [140, 355],
    )
    p("诊断与因果性", "h")
    p(
        "默认consensus先枚举单星排除，没有通过者再考虑最多双星。候选至少保留五星，满足当前残差与几何门限。当前及最多16个过去历元的相对似然达到20:1才考虑确认；暂定剔除仍标SUSPECT。位置始终由当前历元求解，历史只支持诊断，不平滑未来轨迹。"
    )

    heading(3, "诊断改进与实验取舍")
    p("已采用：历史证据随噪声尺度修正", "h")
    p(
        "第六轮保存每帧统计量及噪声尺度。因果噪声估计增大时，旧统计量乘以(旧尺度/新尺度)²，偏差方差同步扩大；尺度回落不重新增强旧证据。窗口16历元、名义尺度1m、假警参数0.001和20:1确认门槛保持不变。"
    )
    p(
        "新独立高噪声输入中，P95由27.631m降至26.586m、错剔1185→1156、错误确认146→140；改善有限且仍未达标。候选水平解差显示不同通过子集的位置差，不是真值误差、置信区间或保护水平。"
    )
    p("本轮未采用：分段历史故障模型", "h")
    p(
        "试验在最多16个已接收历元的奇偶残差上，对无故障、单星常偏、线性偏差进行分段拟合，用模型复杂度与变化点代价抑制过拟合；最终四未知数仍由当前观测独立拟合。以下复用第六轮输入，属于开发回归。"
    )
    table(
        [
            ["开发指标", "当前默认", "分段实验"],
            ["六星冷启动强故障P95", "27.329m", "32.559m"],
            ["连续六星全部错剔", "220次", "221次"],
            ["不规则六星全部错剔", "114次", "112次"],
            ["不规则六星错误确认", "3次", "3次"],
        ],
        [235, 130, 130],
    )
    p(
        "局部指标改善不能抵消冷启动退化，因此未替换生产算法；源码和全部开发指标保留，未利用新八星结果继续调参。复杂度惩罚受Schwarz (1978) BIC启发，是工程评分，不是校准后的故障正确概率。"
    )
    p("两种消融", "h")
    p(
        "--disable-history-rescaling对照第五轮尺度行为；--disable-fde关闭改进模块，得到独立等权普通解。本轮八星使用后者作为同输入对照，避免把跨种子差异误当作算法收益。课程CSV与API合同未改变。"
    )

    heading(4, "新八星补验：83例 / 6,640历元")
    p(
        "预先固定种子625308与案例覆盖后运行：正常1例、共同偏差正负各1例；冷启动、阶跃、渐变、一次换星、快速换星各覆盖8颗初始目标星×正负号，每例80历元。每例生成新轨迹、钟差和噪声；仅按课程可见性筛选起点，没有按解算结果删减。"
    )
    labels = [
        ("clean", "正常"),
        ("common", "共同偏差"),
        ("cold_stream", "故障冷启动"),
        ("step", "单星阶跃"),
        ("ramp", "单星渐变"),
        ("switch", "一次换星"),
        ("rapid", "快速换星"),
    ]
    rows = [["场景 / 历元", "普通P95", "改进P95", "10m成功率"]]
    raw = json.loads(
        (ROOT / "docs/experiments/diagnosis-iteration7/eight-metrics.json").read_text()
    )
    for key, label in labels:
        m, old = raw[key + "/new"], raw[key + "/previous"]
        rows.append(
            [
                f"{label} / {m['epochs']:,}",
                f"{old['h_p95_m']:.3f}m",
                f"{m['h_p95_m']:.3f}m",
                f"{m['required_success10']:.0%}",
            ]
        )
    table(rows, [175, 110, 110, 100])
    all_rows = latest["groups"]["all"]
    p(
        f"整体普通解P95为{latest['ablation']['h_p95_m']:.3f}m，改进解为{all_rows['h_p95_m']:.3f}m。所有要求定位历元均有解且在10m内；强故障正确标记率100%，错剔0、错误确认0、正常标记/状态误报0；83例逐例检查无失败。"
    )
    p(
        "共同偏差正负100m主要由钟差吸收，其钟差距离项误差P95为1.220m。每历元双解和消融输出均经课程评价器检查，契约违规0；两条运行路径的普通解最大数值差2.91×10⁻⁷m以内，状态和星数一致。"
    )
    p("成功案例与评价边界", "h")
    p(
        "公开D03改进解P95为1.594m（普通解23.859m），570/570个要求定位历元有效，60/60强故障正确标星，0/3/4星规定状态正确率100%。八星结果不覆盖下一页的六星失败，也不代表教师隐藏数据或外场实测。"
    )
    p(
        "基础噪声σ=0.8m，另叠加0.25m平滑扰动。P95以有效位置计算；10m成功率分母包含全部要求定位历元。完整输入、真值和日志在runtime/diagnosis-iteration7/final-eight，紧凑指标和冻结哈希在docs/experiments/diagnosis-iteration7。",
        "small",
    )

    heading(5, "保留失败：低冗余与噪声失配")
    p(
        "以下为第六轮预留种子624291至624296的独立证据；本轮生产数值源码未变，因此保留全部局限，不用新的八星通过结果替代。各组要求定位可用率均为100%。"
    )
    rows = [["条件 / 历元", "水平P95", "10m成功率", "错剔 / 错误确认"]]
    for key, label in [
        ("continuous", "连续六星"),
        ("irregular", "不规则六星"),
        ("cold", "孤立六星首历元"),
        ("stress", "2.4m高噪声"),
        ("seven", "七星"),
        ("membership", "可见集合变化"),
        ("variable", "星数变化/中断"),
    ]:
        m = summary[key]["new"]
        rows.append(
            [
                f"{label} / {m['epochs']:,}",
                f"{m['h_p95_m']:.3f}m",
                f"{m['required_success10']:.2%}",
                f"{m['wrong_exclusions']} / {m['confirmed_wrong_exclusions']}",
            ]
        )
    table(rows, [190, 85, 100, 120])
    p(
        "连续六星冷启动强故障P95=27.329m、10m成功率93.10%；冷启动/阶跃/渐变/一次换星/快速换星分别有5/2/2/3/3个星组未达标。可见集合变化强故障P95=35.984m；四/五星故障精度也仍失败。"
    )
    p("本轮重新核验的冷启动歧义", "h")
    p(
        "同一组六星的两种单星强故障世界，位置水平相距128.635m，六维伪距均值距离仅0.142m；高度角均>5.92°、PDOP约2.533、星历年龄<1033秒。以独立0.8m高斯噪声、两世界等先验为条件，最佳二选一身份判别成功率也仅53.53%。"
    )
    p(
        "该构造仅说明首历元故障身份可能难区分，不是课程水平误差门槛的普遍不可能性证明，也不是免责理由。复验脚本从物理模型重新生成观测，未把真值交给定位器。证据不足继续显示SUSPECT，不把低残差或低PDOP解释为正确故障身份。",
        "small",
    )
    p(
        "恢复与状态：既有数量变化组140个0/3/4星状态100%正确；连续六星全部换星前10历元P95=4.880m，恢复P95=2.223m且仍有1次暂定误报。TCP过期位置只作历史显示，必须收到新历元才恢复当前位置。",
        "small",
    )

    heading(6, "工程交付、复现与个人核验")
    table(
        [
            ["验证项", "证据"],
            [
                "本轮自动检查",
                "154项pytest、13项Vitest通过；Ruff、Pyright、ESLint、TypeScript/Vite通过",
            ],
            ["浏览器与实时流程", "第六轮Chromium/WebKit共16项通过；本轮未改UI流程"],
            ["原始资料与计算边界", "26个教师文件和数值核心未变；新八星契约违规0"],
            ["保留提示", "Starlette/httpx依赖弃用提示、Vite既有大包提示"],
        ],
        [155, 340],
    )
    p("可核验交付", "h")
    p(
        "下载的源码目录没有Git元数据。新增显式--source-snapshot模式：按源文件清单计算SHA256身份，先封存字节，再在临时目录运行封存源码生成D01/D02/D03结果与D03消融；不会虚构Git提交号。ZIP含内置前端、依赖锁、报告、诊断和校验清单，不含本机运行历史或凭证。"
    )
    for line in [
        "uv sync --locked",
        "uv run gnss serve --port 18000",
        "uv run python scripts/package_submission.py --source-snapshot --out ../submission.zip",
        "python scripts/verify_submission.py --root .",
    ]:
        p(line, "small")
    p(
        "解压后先校验，再安装依赖并运行。首次安装需要网络，包内前端无需Node重建。SHA256校验检测交付文件改动，不是数字签名；输出目录/ZIP不得覆盖既有证据。八星与歧义复验完整命令见README与docs/diagnosis-iteration7.md。",
        "small",
    )
    p("真实分工：姓名已确认，其余待确定", "h")
    rows = [["成员", "实际负责模块", "已完成的个人核验"]]
    for member in team["members"]:
        rows.append(
            [
                member["name"],
                member["actual_responsibility"] or "待确定",
                member["completed_verification"] or "待确定",
            ]
        )
    table(rows, [105, 175, 215])
    p(
        "来源：教师任务书、MODEL_SPEC、INTERFACE；ESA Navipedia RAIM与Positioning Error；Schwarz (1978), DOI 10.1214/aos/1176344136（仅用于未采纳试验）。方法、数据和来源链接见两轮验证记录。AI辅助开发不替代每名成员的模型解释、个人核验或现场答辩。",
        "small",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9E1E6"))
        canvas.line(50, 42, A4[0] - 50, 42)
        canvas.setFont("ReportCJK", 8)
        canvas.setFillColor(grey)
        canvas.drawString(50, 28, "GNSS编程作品 · 第七轮技术报告 · 分工与个人核验待确定")
        canvas.drawRightString(A4[0] - 50, 28, f"{doc.page} / 6")
        canvas.restoreState()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(args.out),
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=44,
        bottomMargin=55,
        title="GNSS定位与故障诊断实验报告 第七轮",
        author="马晨曦、张淳贺、刘芸睿",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.out)


if __name__ == "__main__":
    main()
