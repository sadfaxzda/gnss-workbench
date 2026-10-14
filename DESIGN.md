---
name: "GNSS Workbench"
description: "灰白、单蓝、联动且可追溯的测绘分析工作台"
colors:
  canvas: "#f2f3f4"
  surface: "#ffffff"
  surface-subtle: "#f2f3f4"
  ink: "#293139"
  secondary: "#535d66"
  muted: "#626c75"
  line: "#c4c9cf"
  line-soft: "#e2e5e8"
  control-border: "#7a858e"
  navy: "#30373d"
  on-navy: "#f7f8f9"
  on-navy-muted: "#c5cbd0"
  accent: "#355f79"
  accent-hover: "#294b61"
  accent-soft: "#edf2f6"
  warning: "#805d1e"
  warning-soft: "#f7f1e4"
  danger: "#a3463e"
  danger-soft: "#faecea"
  baseline: "#707b84"
  focus: "#355f79"
  action: "#355f79"
  action-hover: "#294b61"
  action-border: "#355f79"
  on-action: "#ffffff"
  plot: "#ffffff"
  plot-text: "#535d66"
  plot-grid: "#e2e5e8"
  white: "#ffffff"
  clock: "#626c75"
  satellite: "#626c75"
  residual: "#626c75"
  excluded: "#a3463e"
  plot-baseline: "#707b84"
  plot-improved: "#355f79"
  plot-selected: "#355f79"
  plot-axis: "#7a858e"
  nav-active: "#424a50"
  nav-focus: "#a8c4d8"
  metric-surface: "#f2f3f4"
  replay-surface: "#f2f3f4"
  segment-good: "#a6adb3"
  segment-accent: "#65717b"
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
  field: "12px"
  content-start: "12px"
  cell-block: "8px"
  overlay: "20px"
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
    padding: "6px 12px"
  toolbar-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "4px 12px"
  navigation:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.on-navy-muted}"
    height: "52px"
    padding: "0 18px"
  navigation-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.white}"
  status:
    backgroundColor: "transparent"
    textColor: "{colors.secondary}"
    rounded: "{rounded.status}"
    padding: "2px 0"
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

以“测绘分析工作台”为视觉北极星：石墨顶栏稳定定位，灰白工具栏、面板与绘图区承托密集数据，单一测量蓝标记主要动作、改进解、选择和焦点。可靠感来自清楚的层级、联动与结果出处，色彩只在需要表达动作或状态时出现。

本系统按用户最新的“配色还是太复杂了”和“字离边框有的太近”反馈更新，以实际代码为依据。此前确认的专业、紧凑连接面板、按需检查与统一历元回放继续使用；本轮收敛可见色相，普通状态回归中性文字，错误和真实警告保留专用语义。保留 GNSS Workbench 名称，不采用参考产品的商标或截图。

**Key Characteristics:**

- 石墨顶栏、灰白操作层、白色数据和绘图表面形成连续工作区。
- 单一测量蓝服务动作、改进解、选择和焦点；红与琥珀仅用于异常和警告。
- 统一内容内距；面板、时间与卫星选择联动，状态有明确文字与图形。

本文件按2026-10-14的实际实现更新。代码依据为 `web/src/styles.css`、`web/src/lib/chartTheme.ts`、`web/src/fonts.css`、`web/src/lib/fonts.ts`、`web/src/App.tsx` 及图表、天空图、卫星检查与状态回放组件。顶层 token 为已解析的规范值；CSS 中 action、action-hover、action-border 分别复用 accent、accent-hover、accent，plot、plot-text、plot-grid 分别复用 surface、secondary、line-soft。保留这些语义角色不会增加色相；未被组件使用的旧 success/success-soft 声明不纳入规范。产品与科学语义见 `PRODUCT.md`，调研及字体来源见 `docs/interface-research.md`，方向契约见 `.impeccable/direction.md`。

## Colors

中性灰白建立工具层级，测量蓝是唯一日常强调色。不同任务保留各自的 token 名称并共享颜色；本轮减少的是同时出现的色相，而非声称语义 token 更少。

### Primary

- **测量蓝**（`accent`、`action`、`action-border`、`focus`、`plot-improved`、`plot-selected`）：主要按钮、改进解实线、选中历元与卫星圆环、次级链接、滑块、输入光标和常规焦点。主要按钮的 `on-action` 为白字。
- **测量蓝深阶与浅阶**（`accent-hover`、`action-hover`、`accent-soft`、`nav-focus`）：主要按钮悬浮、选中行浅底与深色导航中的浅蓝指示/焦点。它们属于同一蓝色体系，不引入第二个日常强调色。
- **例外语义**（`danger`、`excluded`、`danger-soft`、`warning`、`warning-soft`）：红色用于剔除观测、无效/错误状态和已有危险操作；琥珀仅用于真实警告。浅底仅用于相应错误或警告提示，不铺满正常状态或诊断表行。

### Neutral

- **工作底、纸面与浅灰工具面**（`canvas`、`surface`、`surface-subtle`、`white`）：页面、工具栏、标题和数据区；轨迹 `plot` 与数据纸面共享白色，不再建立独立深色绘图区。
- **正文与辅助文字**（`ink`、`secondary`、`muted`、`plot-text`）：主要说明、辅助标签、弱化信息和图表文字。普通有效、已处置及中性状态均为 `secondary` 文字、透明背景。
- **面板分界与字段边缘**（`line`、`line-soft`、`control-border`、`plot-grid`、`plot-axis`）：连接面板、内部行分隔、字段边界和图表网格；字段边缘有独立深灰，不能用内部细线替代。
- **石墨框架**（`navy`、`on-navy`、`on-navy-muted`、`nav-active`）：顶部导航、柔和文字与悬浮/当前底色；保留现有 `navy` token 名，当前值为石墨灰。
- **普通测量数据**（`baseline`、`plot-baseline`、`clock`、`satellite`、`residual`）：普通解为灰色虚线；钟差、正常残差和正常卫星为统一中性灰，名称与位置保持不同数据角色。
- **指标与回放**（`metric-surface`、`replay-surface`、`segment-good`、`segment-accent`）：指标带和回放底共享浅灰；普通有效和已处置区段使用灰色明度区别，警告/失效区段才使用对应例外色。

**The Single Blue Rule.** 主要动作、改进解、选择与常规焦点共用测量蓝；普通解、钟差、正常残差和正常卫星以中性灰表达。减少可见色相，不删除不同数据角色的语义 token。

**The Exceptional Color Rule.** 红色用于剔除或无效观测、失效及错误状态和已有危险操作；琥珀用于实际警告。普通有效与已处置状态使用透明背景和中性文字，不为每种正常状态分配色相。

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

桌面使用满高工作区（100dvh），顶部为固定高度的石墨导航（52px）和紧凑工具栏（最小65px）。工具栏按数据源、输入方式、回放速度、高级设置与运行动作排列。没有页面外层留白或独立展示标题；面板之间共享细缝（1px）。面板左右内容共用 `--panel-inset`（桌面16px，手机12px），工具栏沿用原有间距。

实时页左侧为可伸展轨迹，右侧为白色解算与卫星检查区（默认290px）。轨迹下方残差与钟差并列，底部图带高度随视口限制在165–230px。右检查区自身纵向滚动，保证较矮桌面仍可访问最后一行；它不压缩或覆盖底部回放。共享回放处于工作区底部，串联状态区段、选中历元、时间轴、进度与导出。

诊断页左上卫星表、左下检验证据，右侧天空图与卫星详情（默认310px）；桌面上下行按1.15:1分配并保留各自最小高度。实验页使用两个平行面板，历史页使用表格；均沿用相同标题、字段、分隔线与滚动语法。

### Responsive behavior

- **宽桌面（≥1600px）**：实时检查区330px，诊断右栏350px。
- **紧凑桌面（≤1150px）**：隐藏品牌副名、收紧导航和工具栏；实时检查区265px、诊断右栏280px。
- **窄窗口（≤900px）或极矮窗口（高度≤620px）**：页面转为自然高度滚动，顶栏吸顶，工具栏换行；实时及诊断右栏255px，轨迹高度350px，底部图带210px。检查区不再承担独立滚动，回放转为纵向布局。
- **手机（≤600px）**：导航仍在顶部（50px），保留四项文字并隐藏图标。内容单列：轨迹、残差、钟差、检查区、回放；诊断页为表、证据、天空图。轨迹300px，两幅底图各200px；指标保持四列。工具栏字段最小38px、主要按钮40px、回放方向按钮38px、导出链接40px。宽表格仅在自己的区域横向滚动。

### Content spacing

面板标题、指标、检查详情、证据、表格和表单的左右文字起点尽量对齐。普通字段、工具栏字段和回放下拉框共用 `--field-inset`（12px）；其上下 padding 分别为6px、4px和4px。文件输入为6px 12px，高级设置浮层仍为20px内距。

标题下的解算状态与检验证据统计由 `--content-start`（12px）留出起始空间；表头和普通数据单元格共用 `--cell-block`（8px）上下内距。实验对照表单元格沿用16px、历史行沿用12px上下内距。残差/钟差标题上下均为8px，图表上方单位标签的 grid top 为26px；主要标题、指标带、工具栏、底部图带与时间轴总高度保持原实现。紧凑桌面表格仍可按既有响应式规则使用12px左右内距。

**The Content Inset Rule.** 面板内容共用 panel-inset，字段文字共用 field-inset；标题分隔线后的状态与证据共用 content-start。为文字留出内距，同时保留主要标题、指标、工具栏、图带和时间轴的总高度。

## Elevation & Depth

界面以浅灰标题和工具栏、白色数据与绘图表面及细分隔线建立层级，普通面板没有投影。高级设置覆盖内容时才使用石墨色双层柔和投影（`0 12px 40px #30373d2b, 0 2px 6px #30373d17`）；其层级高于数据区。顶栏吸顶时保持实色背景。

**The Connected Surface Rule.** 数据面板以灰白明度层级和共享细分隔线建立层级，普通数据面板保持无阴影；高级设置浮层使用投影说明覆盖关系。

## Shapes

主要数据面板为直角、连续连接的表面；控件采用小圆角（control），透明状态标签保留紧凑形状（status），高级设置浮层使用较缓圆角（popover）。状态圆点、天空图卫星点与选中圆环属于数据符号。分隔线一般为1px；常规蓝色焦点轮廓为2px并外偏3px，石墨顶栏的浅蓝焦点向内偏4px。

## Components

### Buttons

紧凑而明确的操作控件。主要、描边、幽灵与危险四种变体共用 control 形状、文字与间距；桌面最小高度34px。主要按钮的 action 与 action-border 绑定 accent、on-action 为白字，悬浮转 action-hover。描边按钮为纯白底与 control-border；描边/幽灵按钮悬浮使用浅灰，幽灵文字使用测量蓝。已有危险按钮为 danger 与纯白字。背景过渡140ms ease-out；禁用状态降低到0.5不透明度并显示不可操作光标，键盘焦点为测量蓝。图标使用 SVG，与文字共同说明动作。

### Chips

状态以小圆点和明确文字呈现，透明背景、上下2px且无额外左右填充。有效、已处置和中性状态共用辅助灰文字；警告为琥珀，失效/错误为红。状态回放的普通区段也使用灰色，警告/失效区段才使用例外语义色；当前选择增加不透明度与蓝色描边。

### Cards / Containers

数据容器为连接面板，surface 背景、直角、无阴影。主标题采用浅灰横向栏，上下12px、左右 panel-inset，由 line 下边界分开标题与内容；检查标题、支撑图标题和表格遵循各自的既有高度。正文、数值与表格共用相应内距角色。剔除行保持透明普通底；选中行一律为 accent-soft，即使同时为剔除行也保留浅蓝底，具体剔除含义由状态文字和红色数据符号表达。

### Inputs / Fields

普通表单字段为纯白底、control-border 边界、小圆角（control）、最小34px高，上下6px、左侧 field-inset。工具栏位于浅灰表面，字段为 surface 白底、最小30px高、上下4px；回放下拉同为上下4px。所有单选下拉框保留原生菜单与键盘行为；闭合态统一使用12px SVG箭头，箭头右侧距边框12px，文字右侧预留36px。长选项允许省略显示；高对比度模式恢复原生箭头。标签在字段上方，输入光标和焦点为测量蓝。高级输入折叠在设置入口内，桌面浮层宽580px且受视口限制、内距20px；文件输入为6px 12px。窄屏使用固定浮层并内部滚动，启动成功后关闭。

### Navigation

石墨顶部导航以文字和 SVG 表示实时定位、逐星诊断、实验设计与运行记录。未选中文字柔和，悬浮和当前页面使用 nav-active 底色和纯白字；当前页面另有底部2px浅蓝指示线。手机保留顶部文字导航与可识别选中边界，深色顶栏焦点使用同一浅蓝 nav-focus。

### Measurement and evidence

一条浅灰指标带按卫星数、位置精度因子、后验残差、水平误差 P95 排列，不使用独立大卡片。前三项对应选中历元；P95 对应整次有匹配真值的运行，直接显示“水平误差 P95”和“仿真 · 全程”。没有评价值时显示缺省符号“—”，不能用普通解/改进解差值替代。两解三维差值使用准确字段名“三维解差”，不附常驻解释。解算状态使用短摘要与真实数量，例如“卫星数不足 / 可用卫星3颗 · 最低要求4颗”；历史位置使用划线和明确的历史提示。证据统计从标题分隔线后 content-start 开始，左右与同一面板正文对齐。

### Linked charts and inspector

轨迹绘制实际 ENU，以首次有效改进解为原点；横纵轴保持相同米/像素，尺寸变化后重新计算范围。轨迹使用白色 plot、灰色 plot-baseline 虚线、测量蓝 plot-improved 实线及同蓝 plot-selected 选中点；点的白色描边保持辨识，无效历元保留断点。正常残差、钟差和正常卫星均为中性灰，剔除观测为红。轨迹点、钟差图和回放共同选择历元；残差、卫星表与天空图共同选择卫星。天空图选中点有蓝色圆环；键盘 Enter/空格可选择。显式选中的卫星在当前历元无数据时显示缺失，不延用旧值。图表禁用动画，位置不通过装饰平滑。

### Shared replay

状态区段按已接收历元的实际数量分配长度，正常区段使用灰色明度，警告与失效保留琥珀与红；选中区段提升不透明度并以蓝色描边。下拉框和方向按钮跳至区段起点；历元按钮、拖动条和“回到最新”控制同一选中状态。范围使用已接收结果的首末历元编号，不补造缺失编号；TCP 暂停提示独立存在。回放以浅灰 replay-surface 承托纯白控件，control-border 标出字段边缘；滑块和次级链接使用测量蓝。图表与回放在桌面共享固定工作区，在手机进入文档流。

## 界面语言

采用简短、直接的测绘工具措辞：字段命名准确，状态表达当前事实，错误提供恢复动作。工作台不常驻论文式限制说明、假设风险段落或自我辩护式免责声明。算法机制放在“诊断方法”等按需展开区域；界面摘要与求解器归档原因分开，既有运行也使用当前界面措辞。

统一名称包括“参与解算卫星”“三维解差”“候选权重”“文件回放”“异常待确认”。算法名使用“等权最小二乘”“单星 FDE”“多假设一致性检验”“自适应 GNC”；高级选择器保留 GNC 的实验状态。卫星数不足、无观测、四星无检验冗余、搜索未完成和候选不唯一按当前数据简短显示；停用故障检测时不显示“残差检验通过”。导入限制、星历默认值与真实故障的恢复信息继续出现在相应操作处。科学评估定义和研究局限保存在技术文档与导出日志。

## Do's and Don'ts

### Do:

- **Do** 使用灰白表面与单一测量蓝；用中性灰承托普通数据，红和琥珀只表达具体异常与警告。
- **Do** 按 panel-inset、field-inset、content-start 和 cell-block 对齐文字起点并留足边框内距。
- **Do** 用实虚线差异、状态文字、点形与明确的选中边界区分语义。
- **Do** 保持 ENU 横纵轴每像素对应相同米数，在容器变化后重新计算范围。
- **Do** 将“水平误差 P95”与可见的“仿真 · 全程”放在同一指标内；没有匹配真值时保留缺省值。
- **Do** 保留短桌面的检查区独立滚动，以及手机表格自身的横向滚动。
- **Do** 保持键盘焦点、空数据、禁用、异常、暂停与过期位置可见。
- **Do** 验证本机中英文字体加载结果，保持字体合成关闭，再测量图表布局。

### Don't:

- **Don't** 恢复设备黄主按钮、金色轨迹、深绿绘图区、持续绿色状态胶囊或整行警告染色。
- **Don't** 为普通解、钟差、正常残差和正常卫星再增配色相；语义区分依靠名称、位置、线型和选择边界。
- **Don't** 用展示性大标题、大圆角悬浮面板或手机底栏替换当前紧凑连接结构。
- **Don't** 以平滑、跨失效历元连线、历史坐标或装饰填补无效解。
- **Don't** 把双解距离或 ENU 位移命名为真值误差；不得发明底图、地理位置或绝对精度。
- **Don't** 让当前历元指标与整次运行评价共享含糊标签，也不要把评价范围仅藏在悬浮提示中。
- **Don't** 为选中但当前历元缺失的卫星代入另一颗卫星或旧数值。
- **Don't** 声称存在独立500/600/650字体文件、把 Times New Roman 称作等宽字体，或把字体二进制加入仓库。
