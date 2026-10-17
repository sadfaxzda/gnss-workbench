"""Build the six-page iteration-eight report from frozen evidence and confirmed names.

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
EVIDENCE = ROOT / "docs/experiments/diagnosis-iteration8"


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
    p("第八轮实现与验证 · 2026-10-17 · 分工与个人核验待确定", "h")
    p(
        "从GPS L1 C1伪距和广播星历逐历元求三维位置与米制钟差，同时输出独立等权普通解与异常处理后的改进解。文件和TCP回放调用同一计算核心，网页显示双轨迹、逐星残差、几何质量与实时状态。"
    )
    p(
        "本轮新增故障选择证据展示和显式实验开关，完成51,923个新输入历元的默认/实验对照。实验改善部分高噪声误选，却新增一个不规则场景失败，因此默认保持关闭；完整记录收益与退化，不宣称全面达标。"
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
        "小组成员：马晨曦、张淳贺、刘芸睿（用户已确认）。实际分工与个人核验待确定，见第6页。本文结合既有算法证据与本轮新输入补验，不代表已通过教师隐藏测试。",
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

    heading(3, "条件提议与确认身份分开")
    p("现有默认与本轮试验", "h")
    p(
        "默认仍采用已验证的残差一致性、多假设比较、历史尺度折减及弱故障因果检测。强故障时扩展历史偏差证据的两个方案均在开发回放中使名义六星退化，未合入。第三项只调整未确认的条件位置提议，不升级故障身份。"
    )
    table(
        [
            ["开发回放", "默认", "线性 / 阶数选择 / 仅提议"],
            ["连续六星错剔", "220", "228 / 230 / 219"],
            ["不规则六星错剔", "114", "114 / 112 / 115"],
            ["高噪声错剔", "1156", "1102 / 1105 / 1117"],
            ["高噪声错误确认", "140", "148 / 148 / 140"],
        ],
        [180, 80, 235],
    )
    p(
        "开发数据复用第六轮输入，不算新验证。仅提议方案要求历史相对分数达到既有20:1、当前候选残差和几何通过、一步预测通过且没有强反证。已经确认的身份不被覆写；提议保持SUSPECT，不反馈到后续位置初值或诊断证据。"
    )
    p("独立验证后的部署决定", "h")
    p(
        "新数据中高噪声错剔1137→1063，但一个原本通过的不规则案例10m成功率从95.83%降至94.79%。因此coherent_proposals默认False，只通过CLI的--enable-coherent-proposals显式开启实验。没有利用新验证继续调参数，也没有把总体改善写成所有场景进步。"
    )
    p("界面改进：让选择依据可核验", "h")
    p(
        "新增“本次选择证据”，展示实际采用候选、当前/历史来源、证据历元数、对数证据比与门槛、历史噪声尺度。暂定选择不会因高分显示为确认；当前暂定选择不展示另一历史领先模型的分数。旧单星FDE记录缺selected字段时，按实际excluded_sats显示采用行。"
    )
    p(
        "历史阶数选择受Schwarz (1978) BIC启发，仅为未采用试验；线性偏差证据亦不等于校准后故障概率。任何位置仍由当前观测独立拟合，真值只用于事后评价。",
        "small",
    )

    heading(4, "新独立验证：51,923历元")
    p(
        "冻结候选数值源码和配置后，使用预留种子626311至626318。每份输入同时运行默认关闭与显式开启提议的配置，保存全部输入、真值、诊断、CSV与逐例门槛。比较期间未调参数；下表“实验”均不是生产默认。"
    )
    rows = [["场景 / 历元", "默认P95", "实验P95", "默认/实验10m成功率"]]
    for key, label in [
        ("continuous", "连续六星"),
        ("irregular", "不规则六星"),
        ("cold", "孤立首历元"),
        ("stress", "2.4m噪声"),
        ("seven", "七星"),
        ("membership", "集合变化"),
        ("variable", "数量变化/中断"),
        ("eight", "八星完整覆盖"),
    ]:
        a, b = summary[key]["default"], summary[key]["experimental"]
        rows.append(
            [
                f"{label} / {a['epochs']:,}",
                f"{a['h_p95_m']:.3f}m",
                f"{b['h_p95_m']:.3f}m",
                f"{a['required_success10']:.2%} / {b['required_success10']:.2%}",
            ]
        )
    table(rows, [175, 80, 80, 160])
    p(
        "全部要求定位历元可用率100%；51,923个输入的两种配置均无课程CSV契约违规，普通解各数值字段完全一致（排除耗时）。特殊0/3/4星状态检查140历元正确率100%。"
    )
    p(
        "八星83例逐例通过；其默认P95为1.769m、10m成功率100%、强故障正确标记100%，有1次弱故障错剔，实验为0。共同偏差不按逐星故障报警。七星本轮全部通过。有限样本通过不覆盖其他星数组合或教师隐藏数据。"
    )
    p(
        "精度P95只对有效位置计算，10m成功率以所有要求定位历元为分母。基础σ=0.8m+0.25m平滑扰动；2.4m是额外噪声压力。共享课程星历及物理函数，仍有共同模型局限，非外场实测。",
        "small",
    )
    p(
        "完整指标与失败见docs/experiments/diagnosis-iteration8；原始输入、双解与诊断在runtime/diagnosis-iteration8/final-*。默认与实验对应存档的previous与new，不能混用。",
        "small",
    )

    heading(5, "成功与失败必须同时保留")
    p("实验有收益的例子", "h")
    p(
        "高噪声set20-03-step第13历元：实际G28偏差+85.801m。默认暂定剔G20，水平误差198.324m；历史提议改为暂定剔G28，误差3.240m。两者均为SUSPECT，不把本次改正称为已确认身份。全组高噪声P95从26.366m降至24.504m，仍远未达到10m。"
    )
    p("新增失败决定默认不开启", "h")
    table(
        [
            ["不规则set23-random_switch", "默认", "实验"],
            ["第31历元采用排除星", "G19（真实故障）", "G11（误选）"],
            ["该历元水平误差", "0.431m", "22.051m"],
            ["整例96历元10m成功率", "95.83%", "94.79%"],
            ["整例水平P95", "4.273m", "6.296m"],
            ["错误确认数 / 状态", "0 / SUSPECT", "0 / SUSPECT"],
        ],
        [235, 130, 130],
    )
    p(
        "此例G19偏差−35.721m，候选在历史一致性模型下也可能误选。不能以高噪声整体错剔减少74次来掩盖该新失败。本轮在新数据上没有继续调阈值，保留默认并开放显式实验复验。"
    )
    p("仍未解决的低冗余条件", "h")
    p(
        "默认六星孤立首历元P95=30.831m；本轮连续快速换星与不规则随机换星仍有明显失败。集合变化冷启动强故障P95约55.271m；数量变化中四/五星故障精度仍失败。4星无冗余、3/0星无效状态通过，不能解释为故障定位能力通过。"
    )
    p(
        "第七轮可重算反例仍成立：正常PDOP约2.533时，两种单星强故障世界位置相距128.635m，观测均值仅相差0.142m。它说明身份可能难区分，不是课程水平精度门槛的普遍不可能性证明。报告保留所有失败，不把低残差视为真值精度。",
        "small",
    )

    heading(6, "工程交付、复现与个人核验")
    table(
        [
            ["验证项", "证据"],
            [
                "本轮自动检查",
                "160项pytest、16项Vitest通过；Ruff、Pyright、ESLint、TypeScript/Vite通过",
            ],
            ["浏览器与实时流程", "本轮Chromium/WebKit共16项通过；新证据展示与移动端已核验"],
            ["原始资料与计算边界", "26个教师文件和物理模型未变；默认行为回归；全部新输入契约违规0"],
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
        "uv run gnss solve --input INPUT.jsonl --out NEW_DIR --enable-coherent-proposals",
        "python scripts/verify_submission.py --root .",
    ]:
        p(line, "small")
    p(
        "解压后先校验，再安装依赖并运行。首次安装需要网络，包内前端无需Node重建。SHA256校验检测交付文件改动，不是数字签名；输出目录/ZIP不得覆盖既有证据。打包、消融及全部验证命令见README与docs/diagnosis-iteration8.md。",
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
        "来源：教师任务书、MODEL_SPEC、INTERFACE；ESA Navipedia RAIM与Positioning Error；Schwarz (1978), DOI 10.1214/aos/1176344136（未采用的阶数选择试验）。方法、数据和来源链接见两轮验证记录。AI辅助开发不替代每名成员的模型解释、个人核验或现场答辩。",
        "small",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9E1E6"))
        canvas.line(50, 42, A4[0] - 50, 42)
        canvas.setFont("ReportCJK", 8)
        canvas.setFillColor(grey)
        canvas.drawString(50, 28, "GNSS编程作品 · 第八轮技术报告 · 分工与个人核验待确定")
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
        title="GNSS定位与故障诊断实验报告 第八轮",
        author="马晨曦、张淳贺、刘芸睿",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.out)


if __name__ == "__main__":
    main()
