# 配色调研与字体规则

本轮按用户最新反馈简化配色并修正文字贴边：灰白为主，常规界面只保留一个蓝色色相，异常与警告按需突出。调研观察的是软件工作界面，网站营销页的品牌色不直接作为操作界面的主色。以下观察来自厂商自己的资料；项目配色是据此作出的设计判断，并非厂商原始色值或认证。

## 调研依据

| 参考 | 实际观察 | 项目采用的原则 |
|---|---|---|
| [Leica Infinity 官方产品与手册](https://leica-geosystems.com/products/gnss-systems/software/leica-infinity?sc_lang=en) | 手册中的工作界面有中性灰工具栏、暗色几何视图与醒目的选中对象；营销页另有红色品牌表达 | 工具栏、绘图区、选择状态分别定义颜色角色 |
| [Topcon 官方软件手册](https://www.topconpositioning.com/content/dam/topcon_digital_asset_hub/collateral/ebooks/topcon_software_enGL23ebk.pdf) | MAGNET Office 的灰色菜单和工具栏承托深色 CAD 视图；文档与表格另有浅色界面 | 深色绘图区与白色数据表并存，按内容决定底色 |
| [Trimble Business Center 官方视图说明](https://help.fieldsystems.trimble.com/tbc/5455.htm)、[Plan View 实际界面](https://help.fieldsystems.trimble.com/tbc/1891.png) | 白色平面视图上使用线、点、标记传达测量对象；属性和图形视图共同组织工作 | 表格保持清晰的纸面底色，数据与属性联动，不用品牌色填满界面 |

## 本项目的颜色与空间关系

- 石墨色 `#30373d` 用于顶栏；浅灰 `#f2f3f4` 用于工具栏、标题与指标带；数据表、详情和轨迹全部使用白色。不同区域靠标题和分隔线组织，不靠不同色块。
- 常规彩色角色统一为蓝色 `#355f79`：主要操作、改进解实线、选中对象与键盘焦点。普通解为灰色虚线，钟差、正常残差柱、正常卫星点为中性灰。颜色与线型共同区分两种解。
- 正常状态与已完成标签使用中性文字，无常驻绿色底色。已剔除、无效观测及错误使用红色 `#a3463e`，实际警告使用琥珀色 `#805d1e`；正常表格不铺警告底色，仅选中行使用浅蓝。状态文字、选中圆环和时间区段说明始终保留。
- 桌面面板内容左右 inset 为16px，手机统一12px；字段文字左右12px。解算状态与诊断统计在标题分隔线后增加12px起点，辅助图标题上下均8px，表格单元格上下8px。高级浮层保留20px内边距，文件字段改为6px×12px。
- 控制栏、主标题、指标、托盘与回放的整体高度保持紧凑；新增留白集中在滚动检查区和正文边缘。辅助图单位标签距离顶部增加6px，ENU轨迹坐标范围及等比例计算未改变。
- token 记录不同语义角色，即使多个角色共用灰色或同一蓝色，也保留名称供维护。这里减少的是同时出现的色相与彩色背景，不把状态和数据语义合并。精确值以 [DESIGN.md](../DESIGN.md) 为准。

## 字体与跨平台运行

用户指定中文使用微软雅黑（Microsoft YaHei），英文和数字使用 Times New Roman。`web/src/fonts.css` 通过 Unicode 范围绑定统一字体别名：中文与全角标点使用微软雅黑，拉丁字符、英文缩写与数字使用 Times New Roman；400/700 分别绑定本机常规/粗体。图表和 tooltip 继承同一规则，并等待字体加载后测量布局。

字体通过 `local()` 使用，仓库没有附带微软字体二进制。每台演示电脑须先安装这两种字体；Windows/Mac/Linux 的实际可用情况以本机为准，缺少时浏览器会回退。本次用户 Mac 已安装微软雅黑并验证两种字体的常规及粗体加载结果。旧版微软雅黑粗体的 PostScript 名与常规冲突，仅将本机粗体的该名字调整为 `MicrosoftYaHei-Bold`，字形与字族未改变。

本机字体来源为微软历史发布的 `VistaFont_CHS.EXE` 的 Internet Archive 存档：原下载地址 `https://download.microsoft.com/download/c/7/e/c7e5397d-004f-468b-a441-dd0828dc1a17/VistaFont_CHS.EXE`；归档包 SHA1 为 `6a825eeb1a36628ef25fb777d259d0aff3749afb`，下载后校验一致。仅提取字体文件，未执行 Windows 安装程序。字体族说明见 [Microsoft YaHei 官方文档](https://learn.microsoft.com/en-us/typography/font-list/microsoft-yahei)。

## 本轮验证

实际浏览器检查1440×900与1280×720桌面，以及390×844手机视口下的定位、诊断与实验页面；高级表单另有1280×720截图。手机宽表格在自身区域滚动；面板左右inset、状态/统计起点和字段文字内距已读取计算样式核验。

主要前景/背景对比度：正文/白底13.19，辅助文字/浅灰6.05，弱化文字/浅灰4.82，白色按钮文字/蓝底6.85，控件边框/浅灰3.39，普通解灰线/白底4.33，剔除红色/白底5.99，警告文字/浅灰5.40。仅报告这些配对，不等同于整站无障碍认证。

前端ESLint、7项Vitest、TypeScript/Vite构建、Chromium/WebKit共10项Playwright流程测试通过；布局检测前后均没有发现项。本轮未更改数值算法、运行生命周期、课程原始数据和解算规则。


## 桌面工程软件交互适配（2026-10-14）

用户明确以专业桌面软件的数据操作体验为参考。检查了以下官方资料及实际软件截图：

- [ArcGIS Pro 界面](https://doc.esri.com/en/arcgis-pro/latest/get-started/introducing-arcgis-pro.html)与[属性表交互](https://doc.esri.com/en/arcgis-pro/latest/help/data/tables/interact-with-a-table.html)：工作视图、表头排序、行选择及独立数据区。
- [ArcGIS 选择记录](https://doc.esri.com/en/arcgis-pro/latest/help/data/tables/view-all-or-only-the-selected-records.html)：选择状态与显示记录的明确区分。
- Trimble Business Center [界面](https://help.fieldsystems.trimble.com/tbc/5455.htm)、[属性窗格](https://help.fieldsystems.trimble.com/tbc/259.htm)、[状态栏](https://help.fieldsystems.trimble.com/tbc/258.htm)和[电子表格](https://community.trimble.com/blogs/hannah-poon/2022/01/24/view-spreadsheets)：紧凑字段、网格化数值、工作区与全局状态分离。

适配为四个现有工作视图、真实卫星网格操作、坐标/卫星属性表、双解检验对照、底部独立状态栏；保留原回放控制与全部导出。页签、网格线、行号、数值对齐和真实交互共同形成桌面工具感。不复制参考产品的菜单规模或品牌资产。

同时完成残差时间趋势与三图缩放：时间窗共享、当前选择保留、全程纵轴参照、展开恢复。仍为浏览器应用，无需Windows运行环境。当前规范以DESIGN.md为准；上文旧配色记录为迭代历史。
