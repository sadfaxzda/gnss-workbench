# GNSS Workbench — 测绘分析工作台

2026-10-14。用户要求重构配色，可靠、稳重，并参考长期使用的测绘企业软件界面。本次采用实际实现为依据的 Operate / code-led 路径，沿用已确认的紧凑联动面板；用户已委托具体取舍，不另起风格投票或概念竞赛。

## 已确认方向

Leica Infinity、Topcon MAGNET Office、Trimble Business Center 的官方界面和资料是本轮配色研究依据：中性灰工具框架、按内容区分深色绘图区与浅色数据表、图形与属性联动。项目据此建立自己的颜色关系，不复制厂商原值、商标或截图，也不声称厂商认证。此前 Emlid、Felt、Foxglove 参考所形成的紧凑处理流程、工作区分配和统一回放结构继续保留，配色以本轮测绘软件研究与实际代码为准。

视觉北极星为“测绘分析工作台”。可靠感来自稳定的工业工具层级：石墨顶栏 `#343c36`、设备灰工具栏和面板标题 `#eceee8`、白色数据纸面 `#fdfdfb`、独立深色轨迹区 `#242c27`。这是一套按职责组织的色彩系统，框架、操作、数据与状态各有辨识。

设备黄 `#d7b65c` 用于主要运行动作、品牌小标识和导航指示；测量蓝 `#365f71` 用于浅色图表数据、选中对象和次级交互。深色轨迹上，改进解使用浅蓝实线 `#8bb7ca`，普通解使用金色虚线 `#d3b66b`，选中历元另有浅黄点 `#ead17a`。浅色残差中的剔除观测为基线褐 `#98763b`；天空图的剔除点为砖红。有效、警告、无效保留绿/琥珀/红及文字、线型、点形和圆环，颜色不独自承担含义。规范 token、状态与组件详见 `DESIGN.md` 和 `.impeccable/design.json`。

## 第一屏契约

52px 顶部导航，设备灰紧凑数据源与运行工具栏，主要面积交给轨迹与观测。左侧深色轨迹和底部浅色残差/钟差，右侧白色解算状态与卫星检查，统一历元回放位于桌面底部。面板连接、直角、细分界；标题使用设备灰。保持当前信息密度与联动关系，不以展示性大标题、宽大侧栏或悬浮卡片重新组织首屏。

主要按钮为设备黄底、深色字与黄褐边界；次级操作为蓝色文字或纯白描边按钮。工具栏字段使用纸面白与独立 `control-border`，普通表单字段和回放控件为纯白。常规键盘焦点为黄褐，石墨导航使用亮黄焦点。普通面板无投影，只有高级设置浮层使用石墨透明度投影。

## 字体契约

用户指定中文统一使用微软雅黑（Microsoft YaHei），英文与数字使用 Times New Roman。统一别名 `GNSS Course Font` 由 Unicode 范围分配；中文与全角标点属于微软雅黑，拉丁字符、英文缩写与数字属于 Times New Roman。两种字体均读取本机常规400与粗体700，仓库不分发字体二进制。

`font-synthesis: none` 关闭伪造字体；代码500请求匹配400，600/650请求匹配700，不能声称这些是独立字体文件。数据、UI、Canvas 和 tooltip 使用同一规则；Canvas 等待中英文常规/粗体字体加载结果或明确回退后测量布局。缺少字体时保留回退能力，演示电脑按实际安装情况验证；本机来源与验证记录见 `docs/interface-research.md`。

## 核心交互契约

历元时间轴、状态分段、前后历元按钮、轨迹点和钟差图共享选择状态。当前坐标、残差、天空图、诊断表与证据随同一历元更新。卫星表、天空图、残差图共享卫星选择；已选卫星在某历元无记录时明确显示缺失，不能沿用旧值。轨迹 XY 等比例，失效历元不连线、不造坐标。仿真 P95 明确属于整次运行，真值只用于结束后评价。

## 跨页面和响应式

诊断页：左上卫星表、左下检验证据、右侧天空图和卫星详情。实验与运行历史沿用相同控件和表格语法。1600px、1150px、900px、600px 宽度阈值及620px高度阈值沿用当前实现，准确的布局变化见 `DESIGN.md`。手机改为单列滚动，导航保留文字，表格只在自身区域横向滚动；极矮或窄窗口进入自然文档流。高级输入折叠，完成启动后关闭。

## 数据语义边界

数据密度高，右侧检查区在较矮桌面需要独立滚动；手机重在核验。真实 ENU 轨迹保持等比例，不加入虚构底图。四星无冗余、0/3星无效、TCP暂停、未知数据无绝对精度评分必须保留。界面和测试结果不能替代老师隐藏用例，也不能据此声称满分、工业定位精度或完好性保障。

## 参考与当前证据

本轮研究的官方来源：

- [Leica Infinity 官方产品与手册](https://leica-geosystems.com/products/gnss-systems/software/leica-infinity?sc_lang=en)
- [Topcon 官方软件手册](https://www.topconpositioning.com/content/dam/topcon_digital_asset_hub/collateral/ebooks/topcon_software_enGL23ebk.pdf)
- [Trimble Business Center 官方视图说明](https://help.fieldsystems.trimble.com/tbc/5455.htm)
- [Trimble Plan View 实际界面](https://help.fieldsystems.trimble.com/tbc/1891.png)

既有结构参考：

- [Emlid Studio GNSS 处理工作流](https://docs.emlid.com/emlid-studio/kinematic-processing-workflow/)
- [Felt 界面导览](https://help.felt.com/getting-started/tour-the-interface)
- [Foxglove Plot 面板](https://docs.foxglove.dev/docs/visualization/panels/plot)

完整研究解释、字体来源及已计算的对比度配对见 `docs/interface-research.md`；这些配对不等同于整站无障碍认证。当前界面证据位于 `.impeccable/review/industrial-desktop.jpg`、`industrial-user-1280.jpg`、`industrial-user-1414.jpg`、`industrial-mobile.jpg`、`industrial-diagnostics.jpg`、`industrial-mobile-diagnostics.jpg`、`industrial-experiments.jpg`、`industrial-mobile-experiments.jpg`、`industrial-empty.jpg`。README 示例截图由同轮真实界面更新，清单见 `docs/media/screenshots.json`。
