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
  chrome: "#e8ebee"
  nav-active: "#f2f3f4"
  nav-focus: "#355f79"
  metric-surface: "#ffffff"
  replay-surface: "#f2f3f4"
  segment-good: "#a6adb3"
  segment-accent: "#65717b"
typography:
  brand:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "15px"
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
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.5
  measurement-detail:
    fontFamily: "GNSS Course Font, Times New Roman, Microsoft YaHei, 微软雅黑, serif"
    fontSize: "12px"
    fontWeight: 400
rounded:
  square: "0px"
  status: "3px"
  control: "2px"
  popover: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  panel: "16px"
  toolbar: "14px"
  field: "12px"
  content-start: "12px"
  cell-block: "6px"
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
    backgroundColor: "{colors.chrome}"
    textColor: "{colors.secondary}"
    height: "42px"
    padding: "0 14px"
  navigation-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.ink}"
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
    padding: "8px 16px"
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
    padding: "5px 14px 4px"
---

# Design System: GNSS Workbench

## Direction

GNSS 测绘分析工作台。采用专业桌面软件的工作方式：紧凑工具栏、连续面板、正式数据网格、对象属性与独立状态栏。保留实时定位、逐星诊断、实验设计、运行记录四个实际工作视图；按现有功能组织命令。

灰白与中性灰构成工作面，测量蓝标记主要操作、改进解、当前选择和焦点；异常观测与实际警告保留红色、琥珀色。专业感来自精确数据、明确的选择关系和稳定交互。

当前实现以 `web/src/styles.css`、`App.tsx`、`DataGrid.tsx`、`SatelliteTable.tsx`、`Chart.tsx` 为准。参考来源见 `docs/interface-research.md`，科学定义见 `PRODUCT.md`。字体二进制和第三方品牌资产不进入仓库。

## Typography

中文使用微软雅黑，英文和数字使用 Times New Roman。DOM、SVG 与 Canvas 均通过 `GNSS Course Font` 的 unicode-range 分配字形，并关闭字体合成。Mac 上的粗体 PostScript 名兼容处理与来源见界面调研文档；缺少本机字体时允许系统回退。

桌面产品名15px；面板标题13px；主要数据12px；表头、字段标签、工具提示与状态栏11px；指标数字15px。全局正文基准14px。Times New Roman 并非等宽字体：数值列采用右对齐与一致的小数位，另请求 tabular-nums。字体只有实际可用的常规/粗体文件，不能把500/600/650称作独立字重文件。

## Layout

桌面采用100dvh的连续工作区。顶部42px浅灰导航以页签边界标记当前视图；下方运行工具栏最小48px，含观测数据、输入方式、回放速度/端口、算法与自定义数据、导出结果和运行控制。较窄桌面字段标签移至上方，必要时换行。

实时页顶部是一条紧凑指标行。绘图区分为轨迹、时间趋势两列，右侧为解算状态、坐标、天空图与卫星属性。轨迹列使用 `minmax(400px, 43%)`；残差与钟差上下分配1.12:1。图组显式使用零最小值网格行，右侧属性区可独立滚动；任何图都不能覆盖回放区。

诊断页左上卫星网格、左下检验证据，右侧天空图和选中卫星属性。网格与证据各自滚动。实验与历史保留原有实际功能，数据表统一单元格分隔线与数值格式。

底部回放控制和应用状态栏分开：前者包含状态区段、GPST、逐历元按钮和时间滑块；后者为27px分区条，显示当前运行状态、已处理历元、输入来源/算法、坐标和时间基准。仅运行中显示计算进度。导出位于工具栏，保留全部六类原始结果文件。

## Data grids and properties

卫星表使用行号、固定表头、完整横纵网格线、紧凑行高29px、数值右对齐和单位列名。当前行用浅蓝底与行号区标记；异常只通过实际处置文字和数据符号表达。

- 表头排序按原始数值处理，缺失项排在末尾；卫星编号自然排序。
- 拖动列分隔线调整宽度，左右键每次调整16px，Home或双击恢复默认值；范围64–420px。
- 整行点击或卫星按钮选中；上下键、Home、End按当前排序选择，联动天空图和属性区，并将对应行滚动到可见范围。
- 可筛选全部、参与定位或剔除观测；底部显示实际记录数与选择数。
- 复制选中行生成含列名的TSV，可粘贴到电子表格；权限不可用时提示可手动选择文字复制。
- 宽表格在自身区域横向滚动，不能撑宽整页；表格只读，不伪装成可编辑字段。

坐标与卫星详情使用两列属性网格：浅灰属性名、白底数值、29px行高和12px左右内距。检验证据使用普通解/改进解对照表，分别列出各自统计量、阈值、自由度与残差检验结果；候选假设另用表格列出排除卫星、统计量、阈值和判定。

## Linked charts

轨迹保持横纵轴相同米/像素，绘制普通解灰色虚线与改进解蓝色实线；无效历元保留断点。原点为首次有效改进解。点击点、回放与时序图共同选择历元；逐星图、卫星表和天空图共同选择卫星。

残差默认显示全程趋势，可选总体RMS或具体卫星，另保留当前历元逐星对比。两条趋势分别来自普通解与改进解，剔除观测保留红色标记。缺测保留空值，不跨缺测补线。

轨迹、残差与钟差均支持放大、缩小、复位、展开、拖动平移和Ctrl+滚轮。残差与钟差共用时间窗；切换历元或观测量保留当前缩放范围。时间轴默认覆盖本次全部已接收历元，缩放时纵轴保留全程数据范围，便于总体比较。展开视图保留工具栏和回放，Escape返回。图表动画关闭。

## Responsive behavior

- ≥1600px：实时属性栏330px，诊断右栏350px。
- ≤1100px或高度≤620px：工作区进入自然文档流；轨迹350px，残差290px、钟差240px上下排列；回放纵向排列。
- ≤600px：44px顶部文字导航；工作区单列；轨迹300px，残差300px、钟差250px；字段和主要操作最小36px，网格行32px。四项指标保持紧凑四列，宽表局部滚动。

面板文字左右16px，手机12px。表格单元格一般6px×12px，卫星网格4px×10px；标题上下8px。控件2px圆角，数据面板直角。仅算法浮层与导出菜单使用轻投影，普通面板靠细分隔线建立边界。

## Language and data semantics

状态使用短句与具体数据：参与解算卫星、三维解差、候选权重、文件回放、异常待确认。卫星不足、无观测、无冗余、搜索未完成和候选不唯一保留差别。诊断方法按需展开，完整求解原因保存在日志。

指标前三项属于当前历元；水平误差P95属于整次有匹配真值的运行，保持可见的“仿真·全程”标记。无评价值时显示“—”，不使用双解差值替代真值误差。历史位置保持划线和过期提示；当前卫星缺测时显示缺失，不代入其他卫星。

## Review constraints

保留课堂指定字体、数值算法与无效坐标契约。新增界面操作必须真正可用，不能添加没有功能的菜单或装饰数据。不能通过分别拉伸XY、平滑曲线、跨失效连线或隐藏异常点获得更好看的图。桌面图表不可覆盖回放，手机整页不可横向溢出。实际截图与验证记录见 `docs/media/screenshots.json` 和 `docs/validation.md`。
