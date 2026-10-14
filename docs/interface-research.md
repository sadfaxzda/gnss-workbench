# 配色调研与字体规则

本轮按用户要求重构配色：稳重、可信，接近长期使用的测绘工作站。调研观察的是软件工作界面，网站营销页的品牌色不直接作为操作界面的主色。以下观察来自厂商自己的资料；项目配色是据此作出的设计判断，并非厂商原始色值或认证。

## 调研依据

| 参考 | 实际观察 | 项目采用的原则 |
|---|---|---|
| [Leica Infinity 官方产品与手册](https://leica-geosystems.com/products/gnss-systems/software/leica-infinity?sc_lang=en) | 手册中的工作界面有中性灰工具栏、暗色几何视图与醒目的选中对象；营销页另有红色品牌表达 | 工具栏、绘图区、选择状态分别定义颜色角色 |
| [Topcon 官方软件手册](https://www.topconpositioning.com/content/dam/topcon_digital_asset_hub/collateral/ebooks/topcon_software_enGL23ebk.pdf) | MAGNET Office 的灰色菜单和工具栏承托深色 CAD 视图；文档与表格另有浅色界面 | 深色绘图区与白色数据表并存，按内容决定底色 |
| [Trimble Business Center 官方视图说明](https://help.fieldsystems.trimble.com/tbc/5455.htm)、[Plan View 实际界面](https://help.fieldsystems.trimble.com/tbc/1891.png) | 白色平面视图上使用线、点、标记传达测量对象；属性和图形视图共同组织工作 | 表格保持清晰的纸面底色，数据与属性联动，不用品牌色填满界面 |

## 本项目的颜色关系

- 石墨色 `#343c36` 用于顶栏；设备灰 `#eceee8` 用于工具栏、面板标题；白纸色 `#fdfdfb` 用于数据表和检查内容。
- 轨迹区独立使用 `#242c27`。浅蓝实线表示改进解，金褐虚线表示普通解；选中历元另有标记。横纵轴始终保持相同米/像素，无效历元保持断点。
- 设备黄 `#d7b65c` 用于主要运行动作、品牌小标识和导航指示；常规数据与次级操作使用 `#365f71`。主要操作色与改进解的数据色分开。
- 有效、警告与无效分别使用绿、琥珀、砖红，同时保留状态文字；天空图剔除点有文字与诊断证据。图表线型、选中圆环及表格选择也提供颜色之外的提示。
- 浅色表面与深色轨迹有各自的文字和曲线颜色，避免直接反转整页。精确 token 与组件规则以 [DESIGN.md](../DESIGN.md) 为准。

## 字体与跨平台运行

用户指定中文使用微软雅黑（Microsoft YaHei），英文和数字使用 Times New Roman。`web/src/fonts.css` 通过 Unicode 范围绑定统一字体别名：中文与全角标点使用微软雅黑，拉丁字符、英文缩写与数字使用 Times New Roman；400/700 分别绑定本机常规/粗体。图表和 tooltip 继承同一规则，并等待字体加载后测量布局。

字体通过 `local()` 使用，仓库没有附带微软字体二进制。每台演示电脑须先安装这两种字体；Windows/Mac/Linux 的实际可用情况以本机为准，缺少时浏览器会回退。本次用户 Mac 已安装微软雅黑并验证两种字体的常规及粗体加载结果。旧版微软雅黑粗体的 PostScript 名与常规冲突，仅将本机粗体的该名字调整为 `MicrosoftYaHei-Bold`，字形与字族未改变。

本机字体来源为微软历史发布的 `VistaFont_CHS.EXE` 的 Internet Archive 存档：原下载地址 `https://download.microsoft.com/download/c/7/e/c7e5397d-004f-468b-a441-dd0828dc1a17/VistaFont_CHS.EXE`；归档包 SHA1 为 `6a825eeb1a36628ef25fb777d259d0aff3749afb`，下载后校验一致。仅提取字体文件，未执行 Windows 安装程序。字体族说明见 [Microsoft YaHei 官方文档](https://learn.microsoft.com/en-us/typography/font-list/microsoft-yahei)。

## 本轮验证

已检查 1440×900、1280×720、用户实际 1414 宽视口和 390×844 手机视口的定位、诊断与实验页面。手机宽表格在自身区域滚动；Chart 限制在容器内，视口变化后由 ResizeObserver 更新 Canvas 和等比例坐标范围。

主要前景/背景对比度：正文/纸面 13.58，辅助文字/灰面 4.71，按钮文字/设备黄 7.07，控件边框/灰面 3.56，轨迹刻度/深底 9.48，浅蓝曲线/深底 6.64，金褐曲线/深底 7.29。这里只报告这些已计算的配对，不等同于整站无障碍认证。

前端 ESLint、7 项 Vitest、TypeScript/Vite 构建、Chromium/WebKit 共 10 项 Playwright 流程测试通过；类型排版检测没有发现项。未更改数值算法、课程原始数据和解算规则。
