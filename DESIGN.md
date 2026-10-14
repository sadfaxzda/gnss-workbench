---
name: "GNSS Workbench"
description: "紧凑、联动、可追溯的 GNSS 专业分析工作区"
colors:
  canvas: "#f1f4f5"
  surface: "#ffffff"
  surface-subtle: "#f6f8f9"
  ink: "#23333d"
  secondary: "#52636e"
  muted: "#62727d"
  line: "#d6dfe3"
  line-soft: "#e8edef"
  navy: "#172b38"
  on-navy: "#f4f8fa"
  on-navy-muted: "#b7c9d4"
  accent: "#087882"
  accent-hover: "#055e69"
  accent-soft: "#e8f4f4"
  success: "#236b4d"
  success-soft: "#eaf4ee"
  warning: "#915409"
  warning-soft: "#fff5e7"
  danger: "#b43e38"
  danger-soft: "#fff0ee"
  baseline: "#b86e1b"
  focus: "#087882"
  clock: "#426da6"
  chart-muted: "#a3afb7"
  nav-active: "#243d4c"
  nav-indicator: "#8cdbdd"
  nav-focus: "#91dadd"
  metric-surface: "#fbfcfc"
  replay-surface: "#f9fbfc"
typography:
  brand:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "16px"
    fontWeight: 650
    letterSpacing: "0.015em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "13px"
    fontWeight: 500
  detail:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "12px"
    fontWeight: 400
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "11px"
    fontWeight: 400
  measurement:
    fontFamily: "\"SFMono-Regular\", Consolas, \"Liberation Mono\", monospace"
    fontSize: "16px"
    fontWeight: 500
    lineHeight: 1.5
  measurement-detail:
    fontFamily: "\"SFMono-Regular\", Consolas, \"Liberation Mono\", monospace"
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
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-outline:
    backgroundColor: "{colors.surface}"
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
    textColor: "{colors.surface}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "6px 8px"
  navigation:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.on-navy-muted}"
    height: "52px"
    padding: "0 18px"
  navigation-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.surface}"
  status:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.status}"
    padding: "2px 6px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
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

**Creative North Star: "专业分析工作区"**

以“专业分析工作区”为视觉北极星：石墨蓝顶栏提供稳定定位，冷白连接面板把空间交给轨迹、观测和检验证据。中文标签简短明确，数值密集但保持对齐；青色表示操作与当前关注对象，其他色彩承担具体数据或状态语义。

本系统来自用户已授权的 Emlid、Felt、Foxglove 竞品式方向及实际实现。参考其紧凑操作、联动面板和统一回放的工作方式，保留 GNSS Workbench 名称；不采用产品商标或截图。新页面沿用平实的工具界面，不再引入展示性大标题、宽大侧栏或彼此悬浮的卡片海。

**Key Characteristics:**

- 浅色连接面板与细分隔线，桌面充分利用可视区域。
- 面板、时间与卫星选择联动；数值、单位及数据范围就近呈现。
- 操作和状态以文字、图形与颜色共同表达。

本文件按 2026-10-14 的已实现界面更新；代码依据为 `web/src/styles.css`、`web/src/lib/chartTheme.ts`、`web/src/App.tsx` 及图表、天空图、卫星检查与状态回放组件。顶层 token 是规范值，下面说明其用途。产品与数据真实性边界以 `PRODUCT.md` 为准，竞品方向见 `.impeccable/direction.md`。

## Colors

石墨蓝框架、冷白表面与低饱和青色构成主体；暖橙、蓝和状态色仅承载有名称的数据角色。

### Primary

- **操作青色**（`accent`、`accent-hover`、`accent-soft`）：主要按钮、改进解、选中卫星、选中表格行与焦点。
- **焦点青色**（`focus`）：常规控件键盘轮廓；深色顶栏使用更亮的 `nav-focus`。

### Secondary

- **普通解暖橙**（`baseline`）：普通解虚线与已剔除观测的残差柱；剔除状态在表格中配以文字和浅警告底色。
- **钟差蓝**（`clock`）：接收机钟差曲线，区别于轨迹双解。
- **状态色**（`success` / `warning` / `danger` 及各自 soft）：有效、警告与无效状态；天空图被剔除卫星使用 danger，不能与残差柱的暖橙语义互换。

### Neutral

- **工作底与数据纸面**（`canvas`、`surface`、`surface-subtle`）：页面底、主要数据区与表头/字段背景。
- **细分界**（`line`、`line-soft`）：连接面板边界与内部行分隔；图表网格沿用 `line-soft`。
- **正文与辅助信息**（`ink`、`secondary`、`muted`）：由主数据说明到辅助标签；图表文本对应 secondary。
- **石墨框架**（`navy`、`on-navy`、`on-navy-muted`）：顶栏和导航文字；`nav-active` 与 `nav-indicator` 共同标明当前页面。
- **指标与回放底**（`metric-surface`、`replay-surface`）：轻微色阶区分摘要与底部控制区域；`chart-muted` 用于天空图刻度。

**The Semantic Color Rule.** 普通解、改进解、钟差和失效状态的颜色在图例、图表、表格与检查区保持对应；普通解同时使用虚线。

## Typography

**Body Font:** 平台中文无衬线栈（`ui-font`）；沿用系统中文字体，不依赖外部字体网络加载。
**Label/Mono Font:** `data-font` 等宽栈，仅用于测量、时间与诊断数值。界面没有独立展示字或营销标题角色。

### Hierarchy

- **Brand**：小型产品标识（16px、650）；桌面附带 Workbench，窄屏精简文字。
- **Title**：面板标题（14px、600、1.5）；嵌套检查标题（13px）。
- **Body**：全局基准（14px、400、1.5）；说明和表格多为细节角色（12px）。较长方法说明限制在 72ch 内。
- **Control**：主要控件（13px、500）；辅助标签（11px），手机紧凑指标标签（10px）。
- **Measurement**：指标数字（16px、500、1.5），手机（15px）；坐标及卫星详情（12px）。检验证据的强调数字单独使用（18px，手机17px）。

**The Measurement Type Rule.** 测量值使用等宽字体和等宽数字，单位就近呈现；导航、标题与解释使用界面字体。

## Layout

桌面使用满高工作区（100dvh），顶部为固定高度的石墨导航（52px）和紧凑工具栏（最小65px）。工具栏按数据源、输入方式、回放速度、高级设置与运行动作排列。没有页面外层留白或独立展示标题；面板之间共享细缝（1px）。标题与数据块通常采用 panel 间距，工具栏采用 toolbar 间距。

实时页左侧为可伸展轨迹，右侧为浅色解算与卫星检查区（默认290px）。轨迹下方残差与钟差并列，底部图带高度随视口限制在165–230px。右检查区自身纵向滚动，保证较矮桌面仍可访问最后一行；它不压缩或覆盖底部回放。共享回放处于工作区底部，串联状态区段、选中历元、时间轴、进度与导出。

诊断页左上卫星表、左下检验证据，右侧天空图与卫星详情（默认310px）；桌面上下行按1.15:1分配并保留各自最小高度。实验页使用两个平行面板，历史页使用表格；均沿用相同标题、字段、分隔线与滚动语法。

### Responsive behavior

- **宽桌面（≥1600px）**：实时检查区330px，诊断右栏350px。
- **紧凑桌面（≤1150px）**：隐藏品牌副名、收紧导航和工具栏；实时检查区265px、诊断右栏280px。
- **窄窗口（≤900px）或极矮窗口（高度≤620px）**：页面转为自然高度滚动，顶栏吸顶，工具栏换行；实时及诊断右栏255px，轨迹高度350px，底部图带210px。检查区不再承担独立滚动，回放转为纵向布局。
- **手机（≤600px）**：导航仍在顶部（50px），保留四项文字并隐藏图标。内容单列：轨迹、残差、钟差、检查区、回放；诊断页为表、证据、天空图。轨迹300px，两幅底图各200px；指标保持四列。字段最小38px、主要按钮40px、回放方向按钮38px、导出链接40px。宽表格仅在自己的区域横向滚动。

## Elevation & Depth

界面以白色与浅底色阶、细分隔线和局部选中状态建立层级，普通面板没有投影。高级设置作为覆盖内容的浮层才使用双层柔和投影（`0 12px 40px #172b382b, 0 2px 6px #172b3817`）；其层级高于数据区。顶栏吸顶时保持实色背景。

**The Connected Surface Rule.** 数据面板以共享细分隔线建立层级，不用阴影把每个区块变成悬浮卡片；只有高级设置浮层具有投影。

## Shapes

主要数据面板为直角、连续连接的表面；控件采用小圆角（control），状态标签更紧凑（status），高级设置浮层使用较缓圆角（popover）。状态圆点、天空图卫星点与选中圆环属于数据符号。分隔线一般为1px，焦点轮廓为2px并外偏3px；顶栏内的焦点使用亮色且向内偏4px。

## Components

### Buttons

紧凑而明确的操作控件。主要、描边、幽灵与危险四种变体共用 control 形状、文字与间距；桌面最小高度34px。主要按钮悬浮转深青，描边/幽灵按钮悬浮使用浅底；危险按钮沿用危险色，无独立悬浮变色。背景过渡140ms ease-out。禁用状态降低到0.5不透明度并显示不可操作光标；键盘焦点保持可见。图标使用 SVG，与文字共同说明动作。

### Chips

状态以小圆点、明确文字与浅色背景呈现，使用 status 形状。有效、改进处置、警告、失效和中性五种语义均有对应颜色；不要只靠圆点判断状态。

### Cards / Containers

数据容器为连接面板，surface 背景、直角、无阴影。标题使用紧凑横向栏（12px 16px），内部表格、图表和检查内容各有自己的细分界。选中行使用 accent-soft；剔除行用 warning-soft，同时选中且剔除时保留暖色底与青色选中文字。

### Inputs / Fields

普通表单字段为白底、line 边界、小圆角（control）、最小34px高；工具栏字段使用 surface-subtle、最小30px高。标签在字段上方，输入光标为 accent。高级输入折叠在设置入口内，桌面浮层宽580px且受视口限制；窄屏使用固定浮层并内部滚动，启动成功后关闭。

### Navigation

石墨蓝顶部导航以文字和 SVG 表示实时定位、逐星诊断、实验设计与运行记录。未选中文字柔和，悬浮和当前页面使用较亮底色；当前页面另有底部2px青色指示线。手机保留顶部文字导航与可识别选中边界。

### Measurement and evidence

一条浅底指标带按卫星数、位置精度因子、后验残差、水平误差 P95 排列，不使用独立大卡片。前三项对应选中历元；P95 对应整次有匹配真值的运行，直接显示“水平误差 P95”和“仿真 · 全程”。没有评价值时显示缺省符号“—”，不能用普通解/改进解差值替代。算法修正距离旁保留解释，历史位置使用划线和明确的历史提示。

### Linked charts and inspector

轨迹绘制实际 ENU，以首次有效改进解为原点；横纵轴保持相同米/像素，尺寸变化后重新计算范围。普通解虚线、改进解实线；无效历元保留断点。轨迹点、钟差图和回放共同选择历元；残差、卫星表与天空图共同选择卫星。天空图选中点有圆环；键盘 Enter/空格可选择。显式选中的卫星在当前历元无数据时显示缺失，不延用旧值。图表禁用动画，位置不通过装饰平滑。

### Shared replay

状态区段按已接收历元的实际数量分配长度，选中区段提升不透明度并描边。下拉框和方向按钮跳至区段起点；历元按钮、拖动条和“回到最新”控制同一选中状态。范围使用已接收结果的首末历元编号，不补造缺失编号；TCP 暂停提示独立存在。图表与回放在桌面共享固定工作区，在手机进入文档流。

## Do's and Don'ts

### Do:

- **Do** 使用共享语义色、实虚线差异、状态文字与明确的选中边界。
- **Do** 保持 ENU 横纵轴每像素对应相同米数，在容器变化后重新计算范围。
- **Do** 将“水平误差 P95”与可见的“仿真 · 全程”放在同一指标内；没有匹配真值时保留缺省值。
- **Do** 保留短桌面的检查区独立滚动，以及手机表格自身的横向滚动。
- **Do** 保持键盘焦点、空数据、禁用、异常、暂停与过期位置可见。

### Don't:

- **Don't** 用过去的深色解算卡、展示性大标题、大圆角面板或手机底栏替换当前结构。
- **Don't** 以平滑、跨失效历元连线、历史坐标或装饰填补无效解。
- **Don't** 把双解距离或 ENU 位移命名为真值误差；不得发明底图、地理位置或绝对精度。
- **Don't** 让当前历元指标与整次运行评价共享含糊标签，也不要把评价范围仅藏在悬浮提示中。
- **Don't** 为选中但当前历元缺失的卫星代入另一颗卫星或旧数值。
