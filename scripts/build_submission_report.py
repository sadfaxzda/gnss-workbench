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
        "--evidence", type=Path, default=ROOT / "docs/experiments/submission-20261028"
    )
    parser.add_argument("--out", type=Path, default=ROOT / "docs/report.pdf")
    args = parser.parse_args()
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    chinese = font_path(
        "GNSS_REPORT_CHINESE_FONT",
        [
            Path.home() / "Library/Fonts/msyh.ttf",
            windows / "msyh.ttc",
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        ],
    )
    english = font_path(
        "GNSS_REPORT_ENGLISH_FONT",
        [Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf"), windows / "times.ttf"],
    )
    pdfmetrics.registerFont(TTFont("ReportChinese", str(chinese)))
    pdfmetrics.registerFont(TTFont("ReportEnglish", str(english)))
    analysis = json.loads((args.evidence / "analysis.json").read_text(encoding="utf-8"))
    public = {
        key: json.loads((args.evidence / f"{key}-metrics.json").read_text(encoding="utf-8"))
        for key in ("D02_sim_clean", "D03_sim_demo")
    }

    team = json.loads((ROOT / "docs/team.json").read_text(encoding="utf-8"))
    ink = blue = colors.black
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
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D9D9")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.extend([result, Spacer(1, 12)])

    def figure(name, width, caption):
        picture = Image(str(ROOT / "docs/media" / name))
        picture.drawHeight *= width / picture.drawWidth
        picture.drawWidth = width
        story.append(KeepTogether([picture, Spacer(1, 6), text(caption, "small")]))

    page("原始观测驱动的 GPS 定位与故障诊断系统")
    p("课程实践实验报告  2026 年 10 月 28 日", "heading")
    p("小组成员  张淳贺  马晨曦  刘芸睿")
    p("代码仓库  https://github.com/sadfaxzda/gnss-workbench", "small")
    p("实验目的与主要结论", "heading")
    p(
        "我们从 GPS L1 C1 伪距和广播星历计算接收机三维位置及米制钟差，比较独立等权普通解与残差诊断后的改进解。文件和 TCP 回放调用同一计算核心，UI 同时显示双轨迹、逐星信息和状态。本次复跑中，D03 水平误差 P95 从 23.859 m 降至 1.594 m；六星冷启动仍可能选错故障星，报告保留这一局限。"
    )
    figure(
        "submission-workbench.png",
        495,
        "图 1  本次实际运行的 D03 工作台。轨迹为首次有效改进解原点下的 ENU 位移，不能直接作为真值误差；右侧显示当前位置、钟差、卫星数与 PDOP。",
    )
    p("数据与评价范围", "heading")
    p(
        "D01 是 20 历元真实历史 C1 摘录，没有独立位置真值，仅检查真实数据兼容性。D02、D03 各 600 历元，位置、钟差与故障均为仿真。六星局限案例由 D02 派生，属于已知失败复现。本文米级指标仅适用于所列受控仿真，不代表外场实测精度或教师隐藏案例成绩。"
    )
    p(
        "源码、锁文件、预构建 UI、课程原数据、双解结果和逐星诊断随邮件文件夹提交。仓库目前为私有；邮件代码目录可独立安装运行，无需 GitHub 访问权限。",
        "small",
    )

    page("观测模型与独立定位")
    p("观测方程与改正", "heading")
    p("P = ρ + b - c·dt_sat + c·TGD + I + T + ε + f")
    p(
        "状态量为 [x, y, z, b]，坐标采用 WGS 84 ECEF 米，b = c·Δt_receiver 是米制钟差。ρ 为几何距离，卫星系统钟差 dt_sat 包含周期相对论项，TGD 只改正一次；I、T 为电离层、对流层延迟，ε 为噪声，f 为故障偏差。"
    )
    p(
        "根据广播星历求解开普勒方程及轨道摄动，迭代发射时刻后，将卫星坐标旋转到接收时刻 ECEF。单频电离层采用 Klobuchar，显式区分半圆与弧度；对流层采用课程规定固定气象的 Saastamoinen 公式。截止高度角统一为 3°，地心初值先求粗解，再启用大气改正；超出配套星历两小时范围拒绝外推。"
    )
    p("普通解与质量量", "heading")
    p(
        "每条观测的设计矩阵行为 [(x-x_s)/ρ, (y-y_s)/ρ, (z-z_s)/ρ, 1]。用线性最小二乘求状态增量，逐次更新改正和残差直到收敛。普通解每历元独立等权；上一解仅作迭代初值，不作为高度或轨迹约束。关闭故障处置后，改进输出与同次普通解相同。"
    )
    p(
        "Q = (H^T H)^(-1)；PDOP = sqrt(Qxx + Qyy + Qzz)。PDOP 使用实际参与卫星的未加权几何矩阵。残差 RMS 反映模型拟合程度；定位误差则由估计位置减仿真真值并转至真值处 ENU 计算，两者不能互换。"
    )
    table(
        [
            ["观测条件", "输出与解释"],
            [
                "0 星 / 1 至 3 星",
                "NO_OBSERVATIONS / INVALID_INSUFFICIENT；XYZ、钟差、PDOP 和残差留空",
            ],
            ["4 星且几何满秩", "NO_REDUNDANCY；可求四未知数，没有单历元检验冗余"],
            ["差几何或未收敛", "给出 GEOMETRY_WARNING 或相应 INVALID 状态，保留原因"],
            ["输入或星历不可用", "INVALID_DATA / INVALID_EPHEMERIS；不以旧位置或零坐标冒充结果"],
        ],
        [130, 365],
    )
    p(
        "本次核验覆盖 24 个卫星坐标/钟差检查点及少星、共同偏差、因果性等测试；26 个课程文件与用户原包逐字节一致。原包任务书与其原始校验清单的既有差异单独记录，未修改教师文件。",
        "small",
    )

    page("故障诊断与实时软件")
    p("残差检验与候选处置", "heading")
    p(
        "默认 consensus 对普通解残差进行卡方一致性检验。先枚举单星排除，无通过候选时再检验最多双星；每个候选至少保留五颗卫星，并检查残差与几何。处置后重新用当前历元保留观测计算位置，记录被标记和实际排除的卫星。候选通过检验不等于故障身份正确。"
    )
    p(
        "多个单星候选都可解释当前观测时，最多使用 16 个已收到历元的残差证据，按 20:1 相对证据门槛辅助确认，并检查当前反证、换星、时间和观测集合连续性。历史仅辅助诊断，不读取未来轨迹。证据不足时保持 SUSPECT，可能给出暂定子集解；暂定剔除不能记为已确认故障。"
    )
    figure(
        "submission-diagnostics.png",
        495,
        "图 2  D03 故障历元的逐星诊断实拍。当前伪距计算出的残差及处置结果，可与 diagnostics.jsonl 按历元和卫星编号核对。",
    )
    p("文件 TCP 与证据保存", "heading")
    p(
        "TCP 按 LF 分帧，处理拆包、粘包和正常结束帧。超过 max(3 秒, 3×回放间隔) 无数据则提示过期，恢复接收后更新；暂停期间不捏造历元。文件与 TCP 使用同一 PositioningEngine，算法按输入 GPST 推进。"
    )
    p(
        "每组输出 baseline.csv、improved.csv 和 diagnostics.jsonl；manifest 保存输入/导航哈希与配置。逐星日志包含残差、权重、角度及排除标记，候选与算法轨迹保存选择依据。所有 CSV 均遵守 14 列接口，空观测历元也保留一行。",
        "small",
    )

    page("对照实验与成功案例")
    p("统一评价口径", "heading")
    p(
        "本页为 2026-10-28 在同一锁定依赖环境复跑的结果。P95 对要求定位且已输出位置的历元计算；有效解比例和 10 m 成功率以全部要求定位历元为分母。D03 的 20 个三星和 10 个零星历元另行检查状态，要求定位分母为 570；20 个四星历元仍保留在精度评价中。"
    )
    rows = [["数据与模式", "要求历元", "有效解", "水平 P95", "10 m 成功率"]]
    for dataset, mode, label in [
        ("D02_sim_clean", "baseline", "D02 普通"),
        ("D02_sim_clean", "improved", "D02 改进"),
        ("D03_sim_demo", "baseline", "D03 普通"),
        ("D03_sim_demo", "improved", "D03 改进"),
    ]:
        m = public[dataset][mode]
        rows.append(
            [
                label,
                m["position_required_epochs"],
                f"{m['availability_on_required']:.0%}",
                f"{m['h_p95_m']:.3f} m",
                f"{m['success_within_10m_on_required']:.3%}",
            ]
        )
    abl = json.loads(
        (args.evidence / "D03_sim_demo_ablation-metrics.json").read_text(encoding="utf-8")
    )["improved"]
    rows.append(
        [
            "D03 关闭 FDE",
            570,
            "100%",
            f"{abl['h_p95_m']:.3f} m",
            f"{abl['success_within_10m_on_required']:.3%}",
        ]
    )
    table(rows, [123, 70, 70, 107, 125])
    p("消融说明", "heading")
    p(
        "关闭 FDE 后，同次运行的两份解在定位数值与卫星处置上相同，D03 P95 回到 23.859 m。改进收益来自异常观测处置，而非改变轨迹显示或删除困难历元。本次各组 CSV 契约违规均为 0。耗时因机器而异，不用于逐字节复现判断。"
    )
    p("单星故障窗口", "heading")
    p(
        "D03 历元 120–179 对 G19 注入 +80 m 偏差。60 个历元均正确标记并排除 G19；该窗口普通解水平 P95 为 24.450 m，改进解为 1.738 m。510 个无逐星注入历元误报为 0。故障结束后恢复使用正常观测，未将固定故障时间表写入定位核心。"
    )
    p("共同偏差与特殊状态", "heading")
    p(
        "历元 300–359 全星共同 +100 m，偏差主要由接收机钟差吸收；改进解水平 P95 为 1.394 m、米制钟差误差 P95 为 1.388 m，未触发逐星报警。20 个四星历元均标为无冗余，30 个三星/零星历元均无有效位置且字段留空；D01 的 20 历元可解算，仅作为真实数据兼容证据。"
    )

    page("方法局限与实验讨论")
    p("六星冷启动的可复现误选", "heading")
    p(
        "取公开 D02 前 35 历元，每历元保留输入顺序的前六颗卫星，对 G07 增加 -30 m 伪距偏差，其余观测与位置真值保持不变。该输入由复现脚本显式生成，与定位算法分离；这是已知局限演示，不作为新的独立保留验证。"
    )
    item = analysis["six_satellite_limit"]
    table(
        [
            ["首历元观察量", "结果"],
            ["真实注入故障 / 暂定排除", "G07 / G20"],
            ["改进解状态", "SUSPECT，故障身份未确认"],
            ["后验残差 RMS / PDOP", "0.01486 m / 2.512"],
            ["水平位置误差", f"{item['epoch0_horizontal_error_m']:.3f} m"],
            [
                "35 历元错剔 / 错误确认",
                f"{item['wrong_exclusions']} / {item['confirmed_wrong_exclusions']}",
            ],
        ],
        [245, 250],
    )
    p("为什么小残差仍会大误差", "heading")
    p(
        "排除不同卫星后，剩余观测可能都能被四未知数模型良好拟合；六星删一星仅剩一个验证自由度，故障影响可能被位置与钟差吸收。冷启动没有历史证据，最低残差候选未必是正确故障星。本例即使 PDOP 较小、残差接近零，暂定子集解仍偏离真值 33.559 m。因此系统保留 SUSPECT，并展示候选依据，不把暂定剔除宣传为可靠归因。"
    )
    p("已有扩展验证与适用边界", "heading")
    p(
        "仓库 2026-10-17 保存的扩展实验中，六星 196 例仍有 24 例未达到全部检查门槛，存在 295 次错剔和 6 次错误确认；这些是历史封存证据，本次未宣称重新运行全部扩展集。第八轮额外高噪声压力下也存在失败，coherent_proposals 因新增退化而默认关闭。"
    )
    p(
        "四星无冗余、五星排除后无验证冗余；故障切换和观测集合变化会破坏历史身份假设。系统准确报告状态并不保证这些条件下的带故障定位精度。改进应依赖额外观测或可验证的因果证据，并在未参与调参的数据上复验，不能借助真值、固定高度或未来平滑。"
    )

    page("复现步骤小组分工与核验")
    p("从邮件代码文件夹运行", "heading")
    for line in (
        "python scripts/verify_submission.py --root .",
        "uv sync --locked",
        "uv run gnss serve",
        "uv run python scripts/reproduce_submission.py --out runtime/reproduction",
    ):
        p(line, "small")
    p(
        "浏览器打开 http://127.0.0.1:8000。邮件包已含构建前端，首次安装 Python 依赖需网络；重建 UI 时按 README 安装 Node 与 pnpm。Python 依赖由 uv.lock 锁定，前端由 pnpm-lock.yaml 锁定。批处理输出目录需为空，TCP 回放命令见 README。",
        "small",
    )
    p("实际分工与共同审查", "heading")
    table(
        [["成员", "实际分工", "建议个人核验"]]
        + [[m["name"], m["actual_responsibility"], m["defense_focus"]] for m in team["members"]],
        [65, 200, 230],
    )
    p(
        "三人共同审查代码、实验结果和提交材料；分工据小组确认记录。AI 辅助参与代码审查、测试和材料整理，成员仍需解释模型、输入输出和失败条件。个人现场答辩和教师隐藏案例未标记为通过。",
        "small",
    )
    p("核验方法与审查修复", "heading")
    p(
        "按 SHA256 清单检查交付字节；运行教师评价器对照两份 CSV；按历元/卫星编号检查诊断；关闭 FDE 做同输入消融。Python 检查覆盖数值模型、因果性、状态和 TCP，浏览器检查覆盖显示、暂停恢复、回放与导出。验证明细随包保留。本次修复布尔值伪装观测数值、导航顶层格式错误，以及陈旧分工/交付说明；未调优默认算法以迎合案例。",
        "small",
    )
    p("参考资料与源码", "heading")
    p(
        "[1] 教师作业文件包 作业任务书、MODEL_SPEC.md、INTERFACE.md，GNSS-COURSE-1.0。\n[2] RTKLIB 真实历史观测/广播星历摘录，来源及许可见 fixtures/course/data/provenance.json、LICENSE_RTKLIB.txt。\n[3] 算法来源与研究边界见 docs/research.md；本次指标见 docs/experiments/submission-20261028，历史扩展证据保留原日期。\n[4] 仓库 https://github.com/sadfaxzda/gnss-workbench。",
        "small",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9D9D9"))
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
