"""Build the current six-page report from frozen iteration-six evidence.

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
    course = {
        name: json.loads((EVIDENCE / f"{name}-metrics.json").read_text())
        for name in ["D02_sim_clean", "D03_sim_demo"]
    }
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
    p("第六轮实现与验证 · 2026-10-16 · 个人贡献待成员核实", "h")
    p(
        "从GPS L1 C1伪距和广播星历逐历元求三维位置与米制钟差，同时输出独立等权普通解与异常处理后的改进解。文件和TCP回放调用同一计算核心，网页显示双轨迹、逐星残差、几何质量与实时状态。"
    )
    p(
        "本轮重点：修正噪声增大后历史故障证据仍过强的问题，显示不同候选的位置差，并修复换星边界统计遗漏。公开用例保持通过；45,283个新独立仿真历元显示高噪声有有限改善，部分低冗余条件仍失败。"
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
        "小组成员：待填写；实际分工与贡献核验见第6页。旧版报告另存report-pre-iteration6.pdf，本文以冻结后的第六轮证据为依据。",
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

    heading(3, "本轮修改与消融取舍")
    p("噪声尺度修正", "h")
    p(
        "原实现当前残差除以当前噪声方差，但早期累计证据保留旧单位。现在保存每帧尺度，因果估计增大时，旧统计量乘以(旧尺度/新尺度)²，偏差方差同步扩大；尺度回落不再次增强旧证据。窗口16历元、1m名义尺度、0.001假警参数和20:1门限不变。"
    )
    p(
        "示例：8帧每帧候选代价差为1，原对数证据比为4。尺度由1m增至3m后，累计值为4/9，低于ln(20)，不能继续据此确认。这是工程证据分数，不是经过校准的故障正确概率。"
    )
    p("同输入开发回归", "h")
    table(
        [
            ["指标", "第五轮", "本轮尺度修正"],
            ["渐变强故障水平P95", "4.488m", "4.239m"],
            ["渐变故障错剔", "75次", "70次"],
            ["高噪声整体水平P95", "27.517m", "25.197m"],
            ["高噪声错剔 / 错误确认", "1175 / 169", "1112 / 156"],
        ],
        [235, 130, 130],
    )
    p(
        "以上复用第五轮输入，只属开发回归。另试验过用历史带符号偏差的直线预测清除旧证据，虽改善高噪声，却令不规则故障错剔67→69、P95 3.426→3.433m，未纳入生产算法。实验源码和失败结果保留。"
    )
    p("可解释性与验证修正", "h")
    p(
        "新增候选水平解差，以本历元采用解为ENU参照，采用候选为0、未通过者留空。它不是真值误差或保护水平。验证器按事后标签统计所有故障出现、身份/符号变化及恢复的前10个历元，遇下一变化即截止，避免遗漏快速换星与重复计数。"
    )
    p(
        "消融：--disable-history-rescaling对照第五轮；--disable-fde得到独立等权普通解。新标记和诊断字段保存在JSON日志，课程14列CSV与OpenAPI不变。",
        "small",
    )

    heading(4, "冻结后的独立仿真结果")
    p(
        "先冻结数值源码、配置和测试，再运行预留种子624291至624296；没有根据新测试结果继续调参数。每个输入运行新旧方法，保存全部输入、真值、CSV、逐星诊断、失败与哈希。仿真共享课程星历和已验证物理函数，仍有共同模型局限。"
    )
    labels = [
        ("continuous", "连续六星"),
        ("irregular", "不规则六星"),
        ("cold", "孤立六星首历元"),
        ("stress", "2.4m高噪声"),
        ("seven", "七星"),
        ("membership", "可见集合变化"),
        ("variable", "星数变化/中断"),
    ]
    rows = [["条件 / 历元", "水平P95", "10m成功率", "错剔 / 错误确认"]]
    for key, label in labels:
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
        "P95基于输出位置；10m成功率的分母为要求定位的历元，不能删除失败提高成绩。各组要求定位可用率均100%。强故障为单星偏差绝对值≥30m；标星包括暂定身份，错误确认单独报告。",
        "small",
    )
    old, new = summary["stress"]["previous"], summary["stress"]["new"]
    p(
        f"高噪声同输入对照：整体P95 {old['h_p95_m']:.3f}→{new['h_p95_m']:.3f}m，错剔{old['wrong_exclusions']}→{new['wrong_exclusions']}，错误确认{old['confirmed_wrong_exclusions']}→{new['confirmed_wrong_exclusions']}。正常标记/状态误报率仍为4.84%；阶跃/渐变短正常段为12.32%/12.86%，未全面达标。"
    )
    p("不能被汇总平均掩盖的失败", "h")
    p(
        "连续六星冷启动强故障P95=27.329m，10m成功率93.10%。28个星组中，冷启动/阶跃/渐变/一次换星/快速换星分别有5/2/2/3/3组失败。不规则随机换星/非线性/间歇故障分别有1/1/4组失败。可见集合变化强故障P95=35.984m。"
    )
    p(
        "新数量变化组140个0/3/4星状态判断100%正确，但四/五星故障精度仍失败。本轮未重新扫描全部四/五星子集；第五轮的既有局限继续有效。"
    )

    heading(5, "成功案例、误选与恢复")
    p("公开D03：单星故障处理有效", "h")
    rows = [["数据", "普通解P95", "改进解P95", "可用率 / 10m成功率"]]
    for key, label in [("D02_sim_clean", "D02正常"), ("D03_sim_demo", "D03混合故障")]:
        b, i = course[key]["baseline"], course[key]["improved"]
        rows.append(
            [
                label,
                f"{b['h_p95_m']:.3f}m",
                f"{i['h_p95_m']:.3f}m",
                f"{i['availability_on_required']:.0%} / {i['success_within_10m_on_required']:.0%}",
            ]
        )
    table(rows, [110, 110, 110, 165])
    p(
        "D03的570个要求定位历元均有效；60/60个强故障正确标星并剔除；0/3/4星规定状态100%；正常误报0。输入与评价真值同案例，真值不传入求解器。D01仅验证20历元真实输入兼容性，不给出绝对精度分数。"
    )
    p("失败案例：残差小不能证明身份正确", "h")
    table(
        [
            ["六星已知反例", "剔G07候选", "暂定剔G20候选"],
            ["当前检验统计量", "约0.79", "约0.00"],
            ["检验阈值", "约10.83", "约10.83"],
            ["相对采用解的水平解差", "约33.97m", "0m（参照）"],
            ["真值仅供事后核验", "实际注入星为G07", "暂定身份错误，保持SUSPECT"],
        ],
        [185, 150, 160],
    )
    p(
        "该例取D02首历元前六星，在G07注入-30m。两组都能以很小残差拟合，所处位置却相距约34m。本轮只是让歧义后果可见，没有把错误暂定剔星算成正确修复，也没有用真值替换选择。四星无冗余、五星验证不足与部分六星近共线故障方向构成实际限制。"
    )
    p("恢复阶段也纳入统计", "h")
    p(
        "新连续六星全部1120个换星后前10历元：P95=4.880m，10m成功率97.23%，新旧方法相同。1400个恢复历元P95=2.223m，仍有1次暂定误报。不规则组恢复1024历元P95=2.180m，误报0。TCP超时显示历史位置过期，收到新历元前不恢复为当前有效位置。"
    )

    heading(6, "工程验收、复现与成员核验")
    table(
        [
            ["验证项", "结果"],
            ["Python / 前端单元 / 浏览器", "148 / 13 / 16项通过；Chromium与WebKit"],
            ["静态检查与构建", "Ruff与格式、Pyright、ESLint、TypeScript/Vite通过"],
            ["普通解、资料与合同", "公开1220历元普通解一致；26个教师文件和OpenAPI不变"],
            ["扩展契约与数值兼容", "45,283输入历元，契约违规0；普通解最大差≤2.03×10⁻⁷m"],
        ],
        [155, 340],
    )
    p(
        "保留告警：依赖弃用、Vite既有大包提示及客户端关闭的代理日志。首次沙箱端口限制和默认端口冲突的记录保留；解除测试限制并使用独立端口后完整重跑通过。本机未进行教师隐藏验收。",
        "small",
    )
    p("复现命令（项目目录）", "h")
    for line in [
        "uv sync --locked",
        "uv run pytest -q",
        "uv run gnss serve --port 18000",
        "uv run python scripts/validate_six_satellite.py --comparison iteration6 --suite stress --seed 624294 --out runtime/recheck-v6",
        "GNSS_API_PORT=18000 GNSS_WEB_PORT=15173 pnpm --dir web test:e2e",
    ]:
        p(line, "small")
    p(
        "源码依赖使用uv.lock与pnpm-lock.yaml；本机Python3.14.4。精简指标、冻结哈希和失败示例位于docs/experiments/diagnosis-iteration6；完整输入、双解与诊断位于runtime/diagnosis-iteration6/final-*。输出目录要求为空。",
        "small",
    )
    p("小组分工与核验（待成员如实补全）", "h")
    table(
        [
            ["负责人", "负责范围", "核验与答辩要点"],
            ["待填写", "星历与定位模型", "解释发射时刻/TGD/单位，复跑检查点与正常集"],
            ["待填写", "故障诊断与实验", "解释门限、暂定/确认、错剔及本轮失败"],
            ["待填写", "软件与交付", "演示TCP暂停/恢复、导出，核对依赖和输入哈希"],
        ],
        [80, 145, 270],
    )
    p(
        "来源：教师任务书、MODEL_SPEC.md、INTERFACE.md；ESA Navipedia RAIM与Positioning Error（gssc.esa.int/navipedia）。方法参数、数据边界、完整来源链接和未采纳试验见docs/diagnosis-iteration6.md。AI辅助编码和测试不替代成员对本人负责模型的解释与核验。",
        "small",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9E1E6"))
        canvas.line(50, 42, A4[0] - 50, 42)
        canvas.setFont("ReportCJK", 8)
        canvas.setFillColor(grey)
        canvas.drawString(50, 28, "GNSS编程作品 · 第六轮技术报告 · 成员信息待核实")
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
        title="GNSS定位与故障诊断实验报告 第六轮",
        author="GNSS项目组（成员待核实）",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.out)


if __name__ == "__main__":
    main()
