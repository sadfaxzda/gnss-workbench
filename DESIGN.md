---
name: "GNSS Workbench"
description: "可靠、稳重、联动且可追溯的测绘分析工作台"
colors:
  canvas: "#dadcd6"
  surface: "#fdfdfb"
  surface-subtle: "#eceee8"
  ink: "#292e2a"
  secondary: "#505951"
  muted: "#636b63"
  line: "#bdc3b9"
  line-soft: "#e0e4dc"
  control-border: "#74806d"
  navy: "#343c36"
  on-navy: "#f4f5ef"
  on-navy-muted: "#c5cec3"
  accent: "#365f71"
  accent-soft: "#e5ece8"
  success: "#365f43"
  success-soft: "#e8eee5"
  warning: "#806018"
  warning-soft: "#f5ecd7"
  danger: "#a33f34"
  danger-soft: "#f5e8e3"
  baseline: "#98763b"
  focus: "#8a6a1b"
  action: "#d7b65c"
  action-hover: "#c8a347"
  action-border: "#957328"
  on-action: "#292e2a"
  plot: "#242c27"
  plot-text: "#cbd5c8"
  plot-grid: "#47534a"
  white: "#ffffff"
  clock: "#60758b"
  plot-baseline: "#d3b66b"
  plot-improved: "#8bb7ca"
  plot-selected: "#ead17a"
  plot-axis: "#82917f"
  nav-active: "#4a524b"
  nav-focus: "#e9cb77"
  metric-surface: "#eef0e9"
  replay-surface: "#e9ece4"
typography:
  brand:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "16px"
    fontWeight: 650
    letterSpacing: "0.015em"
  title:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "13px"
    fontWeight: 500
  detail:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "12px"
    fontWeight: 400
  label:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "11px"
    fontWeight: 400
  measurement:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "16px"
    fontWeight: 500
    lineHeight: 1.5
  measurement-detail:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "12px"
    fontWeight: 400
rounded:
  square: "0px"
  status: "3px"
  control: "4px"
  popover: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  panel: "16px"
  toolbar: "18px"
  field: "20px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.on-action}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-outline:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  button-outline-hover:
    backgroundColor: "{colors.surface-subtle}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  button-ghost-hover:
    backgroundColor: "{colors.surface-subtle}"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.white}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "6px 8px"
  toolbar-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "3px 8px"
  navigation:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.on-navy-muted}"
    height: "52px"
    padding: "0 18px"
  navigation-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.white}"
  status:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.status}"
    padding: "2px 6px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
  panel-heading:
    backgroundColor: "{colors.surface-subtle}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    padding: "12px 16px"
  trajectory:
    backgroundColor: "{colors.plot}"
    textColor: "{colors.plot-text}"
    rounded: "{rounded.square}"
  metric:
    backgroundColor: "{colors.metric-surface}"
    textColor: "{colors.ink}"
    typography: "{typography.measurement}"
  replay:
    backgroundColor: "{colors.replay-surface}"
    textColor: "{colors.secondary}"
    padding: "8px 18px 7px"
---

# Design System: GNSS Workbench

## Overview

**Creative North Star: "测绘分析工作台"**

以“测绘分析工作台”为视觉北极星：石墨框架稳定定位，设备灰工具栏和标题承托操作，白色数据纸面承托表格与检查，深色轨迹区集中呈现测量几何。设备黄标记主要运行动作和导航当前位置，蓝色表达改进解与次级交互。色彩的作用由任务与数据确定，可靠感来自清楚的层级、联动与结果出处。

本系统按用户授权的成熟测绘软件方向和实际代码更新。Leica Infinity、Topcon MAGNET Office、Trimble Business Center 的官方资料支持中性工具框架、按内容选择绘图底色和图形/属性联动的设计判断；这些是本项目的取舍，色值并非厂商原值。此前已确认的紧凑连接面板、按需检查和统一历元回放继续使用；保留 GNSS Workbench 名称，不采用参考产品的商标或截图。

**Key Characteristics:**

- 石墨框架、设备灰操作层、白色数据纸面与深色轨迹视图各有职责。
- 设备黄用于主要动作和导航标记，蓝色用于数据和次级交互。
- 面板、时间与卫星选择联动；状态同时提供文字、图形和颜色。

本文件按 2026-10-14 的实际实现更新。代码依据为 `web/src/styles.css`、`web/src/lib/chartTheme.ts`、`web/src/fonts.css`、`web/src/lib/fonts.ts`、`web/src/App.tsx` 及图表、天空图、卫星检查与状态回放组件。顶层 token 是规范值；未被组件使用的旧 `accent-hover` 声明不纳入规范。产品与科学语义见 `PRODUCT.md`，调研、字体来源和已计算的对比度配对见 `docs/interface-research.md`，方向契约见 `.impeccable/direction.md`。

## Colors

配色以设备界面的分工建立工业感：框架、工具、数据纸面和轨迹视图采用不同明度，主要操作与数据曲线使用不同色相。

### Primary

- **设备黄**（`action`、`action-hover`、`action-border`、`on-action`）：主要运行动作的背景、悬浮、边界与文字；品牌小标识和当前导航的下边线沿用设备黄。
- **黄褐焦点**（`focus`、`nav-focus`）：常规控件使用黄褐键盘轮廓，深色顶栏使用更亮的黄焦点；焦点与数据选择分开。

### Secondary

- **测量蓝**（`accent`、`accent-soft`）：浅色图表的改进解、选中卫星与表格行、次级操作和输入光标。深色轨迹区使用对应的浅蓝 `plot-improved` 保持可读性。
- **基线褐与轨迹金**（`baseline`、`plot-baseline`）：浅色残差图的已剔除观测使用褐色；深色轨迹上的普通解使用金色虚线。普通解和改进解在线型与图例中保持可辨识。
- **钟差灰蓝**（`clock`）：接收机钟差曲线，区别于轨迹双解；钟差图当前历元的参考线沿用测量蓝。
- **选中历元浅黄**（`plot-selected`）：深色轨迹上的选中点，以点形和描边区别于双解曲线。
- **状态色**（`success` / `warning` / `danger` 及各自 soft）：有效、警告与无效状态。天空图被剔除卫星使用 danger，并有卫星名称和诊断证据；不能与残差柱的基线褐语义互换。

### Neutral

- **工作底、纸面与设备灰**（`canvas`、`surface`、`surface-subtle`）：页面底、数据表与检查内容、工具栏和面板标题。`white` 对应代码中实际的纯白字段与描边按钮。
- **正文与辅助文字**（`ink`、`secondary`、`muted`）：主要说明、辅助标签与弱化信息；浅色图表和天空图沿用同组文字颜色。
- **面板分界与控件边框**（`line`、`line-soft`、`control-border`）：连接面板边界、内部行分隔和可操作字段边缘。控件边缘有独立深色，不能用内部细线替代。
- **石墨框架**（`navy`、`on-navy`、`on-navy-muted`、`nav-active`）：顶部导航及其文字与当前/悬浮底色。保留 `navy` 作为现有代码 token 名；其颜色为石墨灰绿。
- **深色轨迹面**（`plot`、`plot-text`、`plot-grid`、`plot-axis`）：仅轨迹视图采用深色底，对应浅文字、网格和轴线；残差、钟差与天空图保留浅色底。
- **指标与回放底**（`metric-surface`、`replay-surface`）：摘要带与底部回放控制的设备灰色阶，属于同一连接工作区。

**The Action and Data Rule.** 设备黄承担主要运行动作与导航标记，测量蓝承担数据和次级交互；不能把主要按钮重新绑定到改进解颜色。

**The Semantic Color Rule.** 普通解、改进解、钟差与失效状态保留有名称的数据角色；浅色和深色绘图区使用各自的可读色值，并以图例、实虚线、点形、选中圆环和文字维持对应。

## Typography

**Body Font:** 用户指定中文微软雅黑（Microsoft YaHei）、英文与数字 Times New Roman。`fonts.css` 通过 Unicode 范围分配到统一 `GNSS Course Font`：中文和全角标点使用微软雅黑，拉丁字符、英文缩写与数字使用 Times New Roman。字体通过 `local()` 读取本机文件，仓库不分发字体二进制。
**Measurement Font:** `data-font` 与 `ui-font` 使用同一字体规则，测量值、单位和图表刻度也使用 Times New Roman。实际本机字重只有常规（400）和粗体（700）；代码的 500 请求匹配到 400，600/650 请求匹配到 700。`font-synthesis: none` 禁止伪造粗体或斜体，不能把这些请求描述成独立字体文件。

### Hierarchy

- **Brand**：小型产品标识（16px，字重请求650，实际匹配700）；桌面附带 Workbench，窄屏精简文字。
- **Title**：面板标题（14px，字重请求600，实际匹配700，行高1.5）；嵌套检查标题（13px）。
- **Body**：全局基准（14px，400，行高1.5）；说明、表格与坐标多为细节角色（12px）。较长方法说明限制在72ch内。
- **Control**：主要控件（13px，字重请求500，实际匹配400）；辅助标签（11px），手机紧凑指标标签（10px）。
- **Measurement**：指标数字（16px，字重请求500，实际匹配400，行高1.5），手机（15px）；坐标及卫星详情（12px）。检验证据数字使用（18px，手机17px）。

Canvas 等待常规和粗体中英文样本加载完成或明确回退后初始化，再按实际字体测量；tooltip 继承同一 `fontFamily`。缺少指定字体时浏览器保留回退能力，不能仅凭字体列表声称字体已加载。本机字体来源和检查记录由 `docs/interface-research.md` 保存。

**The Measurement Type Rule.** 中英文按用户指定字体分配，数字使用 Times New Roman，关闭字体合成；单位就近呈现。保留 tabular-nums 请求，但不将其视为字体提供了等宽数字的证明。

## Layout

桌面使用满高工作区（100dvh），顶部为固定高度的石墨导航（52px）和紧凑工具栏（最小65px）。工具栏按数据源、输入方式、回放速度、高级设置与运行动作排列。没有页面外层留白或独立展示标题；面板之间共享细缝（1px）。标题与数据块通常采用 panel 间距，工具栏采用 toolbar 间距。

实时页左侧为可伸展轨迹，右侧为浅色解算与卫星检查区（默认290px）。轨迹下方残差与钟差并列，底部图带高度随视口限制在165–230px。右检查区自身纵向滚动，保证较矮桌面仍可访问最后一行；它不压缩或覆盖底部回放。共享回放处于工作区底部，串联状态区段、选中历元、时间轴、进度与导出。

诊断页左上卫星表、左下检验证据，右侧天空图与卫星详情（默认310px）；桌面上下行按1.15:1分配并保留各自最小高度。实验页使用两个平行面板，历史页使用表格；均沿用相同标题、字段、分隔线与滚动语法。

### Responsive behavior

- **宽桌面（≥1600px）**：实时检查区330px，诊断右栏350px。
- **紧凑桌面（≤1150px）**：隐藏品牌副名、收紧导航和工具栏；实时检查区265px、诊断右栏280px。
- **窄窗口（≤900px）或极矮窗口（高度≤620px）**：页面转为自然高度滚动，顶栏吸顶，工具栏换行；实时及诊断右栏255px，轨迹高度350px，底部图带210px。检查区不再承担独立滚动，回放转为纵向布局。
- **手机（≤600px）**：导航仍在顶部（50px），保留四项文字并隐藏图标。内容单列：轨迹、残差、钟差、检查区、回放；诊断页为表、证据、天空图。轨迹300px，两幅底图各200px；指标保持四列。工具栏字段最小38px、主要按钮40px、回放方向按钮38px、导出链接40px。宽表格仅在自己的区域横向滚动。

## Elevation & Depth

界面以设备灰标题和工具栏、白色数据纸面、深色轨迹及细分隔线建立层级，普通面板没有投影。高级设置覆盖内容时才使用石墨色双层柔和投影（`0 12px 40px #343c362b, 0 2px 6px #343c3617`）；其层级高于数据区。顶栏吸顶时保持实色背景。

**The Connected Surface Rule.** 数据面板以共享细分隔线和职责明确的底色建立层级，普通数据面板保持无阴影；高级设置浮层使用投影说明覆盖关系。

## Shapes

主要数据面板为直角、连续连接的表面；控件采用小圆角（control），状态标签更紧凑（status），高级设置浮层使用较缓圆角（popover）。状态圆点、天空图卫星点与选中圆环属于数据符号。分隔线一般为1px，焦点轮廓为2px并外偏3px；顶栏内的焦点使用亮黄且向内偏4px。

## Components

### Buttons

紧凑而明确的操作控件。主要、描边、幽灵与危险四种变体共用 control 形状、文字与间距；桌面最小高度34px。主要按钮使用 action 背景、on-action 文字和 action-border 边界，悬浮转 action-hover。描边按钮为纯白底与 control-border；描边/幽灵按钮悬浮使用设备灰，幽灵文字使用测量蓝。危险按钮为 danger 与纯白字，无独立悬浮变色。背景过渡140ms ease-out。禁用状态降低到0.5不透明度并显示不可操作光标；键盘焦点为黄褐。图标使用 SVG，与文字共同说明动作。

### Chips

状态以小圆点、明确文字与浅色背景呈现，使用 status 形状。有效、改进处置、警告、失效和中性五种语义均有对应颜色；不要只靠圆点判断状态。状态回放区段沿用同一语义，并以不透明度和描边呈现当前选择。

### Cards / Containers

数据容器为连接面板，surface 背景、直角、无阴影。标题使用设备灰横向栏（12px 16px），line 下边界将操作标题与纸面内容分开；表格、图表和检查内容各有自己的细分界。选中行使用 accent-soft；剔除行用 warning-soft，同时选中且剔除时保留暖色底与蓝色选中文字。

### Inputs / Fields

普通表单字段为纯白底、control-border 边界、小圆角（control）、最小34px高。工具栏位于设备灰表面，其字段使用 surface 纸面白、control-border 边界、最小30px高；不能把工具栏字段和栏面填成同一灰色。标签在字段上方，输入光标为测量蓝；焦点为黄褐轮廓。高级输入折叠在设置入口内，桌面浮层宽580px且受视口限制；窄屏使用固定浮层并内部滚动，启动成功后关闭。

### Navigation

石墨顶部导航以文字和 SVG 表示实时定位、逐星诊断、实验设计与运行记录。未选中文字柔和，悬浮和当前页面使用 nav-active 底色和纯白字；当前页面另有底部2px设备黄指示线。手机保留顶部文字导航与可识别选中边界，焦点使用 nav-focus。

### Measurement and evidence

一条设备灰指标带按卫星数、位置精度因子、后验残差、水平误差 P95 排列，不使用独立大卡片。前三项对应选中历元；P95 对应整次有匹配真值的运行，直接显示“水平误差 P95”和“仿真 · 全程”。没有评价值时显示缺省符号“—”，不能用普通解/改进解差值替代。算法修正距离旁保留解释，历史位置使用划线和明确的历史提示。

### Linked charts and inspector

轨迹绘制实际 ENU，以首次有效改进解为原点；横纵轴保持相同米/像素，尺寸变化后重新计算范围。轨迹使用 plot 深色底、plot-baseline 金色虚线、plot-improved 浅蓝实线及 plot-selected 浅黄选中点；无效历元保留断点。浅色残差、钟差和天空图按对应的普通/改进/失效角色使用各自色值，不对整页反色。轨迹点、钟差图和回放共同选择历元；残差、卫星表与天空图共同选择卫星。天空图选中点有圆环；键盘 Enter/空格可选择。显式选中的卫星在当前历元无数据时显示缺失，不延用旧值。图表禁用动画，位置不通过装饰平滑。

### Shared replay

状态区段按已接收历元的实际数量分配长度，选中区段提升不透明度并描边。下拉框和方向按钮跳至区段起点；历元按钮、拖动条和“回到最新”控制同一选中状态。范围使用已接收结果的首末历元编号，不补造缺失编号；TCP 暂停提示独立存在。回放以 replay-surface 设备灰底承托纯白控件，control-border 标出可操作边缘；滑块和次级链接使用测量蓝。图表与回放在桌面共享固定工作区，在手机进入文档流。

## Do's and Don'ts

### Do:

- **Do** 保持设备黄主要动作、蓝色数据/次级交互与石墨轨迹区的职责分工。
- **Do** 使用语义色、实虚线差异、状态文字、点形与明确的选中边界。
- **Do** 保持 ENU 横纵轴每像素对应相同米数，在容器变化后重新计算范围。
- **Do** 将“水平误差 P95”与可见的“仿真 · 全程”放在同一指标内；没有匹配真值时保留缺省值。
- **Do** 保留短桌面的检查区独立滚动，以及手机表格自身的横向滚动。
- **Do** 保持键盘焦点、空数据、禁用、异常、暂停与过期位置可见。
- **Do** 验证本机中英文字体加载结果，保持字体合成关闭，再测量图表布局。

### Don't:

- **Don't** 将主要按钮改回数据蓝，也不要把深色轨迹底延伸到全部数据表与检查区。
- **Don't** 用展示性大标题、大圆角悬浮面板或手机底栏替换当前紧凑连接结构。
- **Don't** 以平滑、跨失效历元连线、历史坐标或装饰填补无效解。
- **Don't** 把双解距离或 ENU 位移命名为真值误差；不得发明底图、地理位置或绝对精度。
- **Don't** 让当前历元指标与整次运行评价共享含糊标签，也不要把评价范围仅藏在悬浮提示中。
- **Don't** 为选中但当前历元缺失的卫星代入另一颗卫星或旧数值。
- **Don't** 声称存在独立500/600/650字体文件、把 Times New Roman 称作等宽字体，或把字体二进制加入仓库。
