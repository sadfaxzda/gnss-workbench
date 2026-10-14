# GNSS Workbench

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

武汉大学 GNSS 课程小组：在 macOS 上开发，通过浏览器进行计算、故障分析与课堂演示。教师按给定模型、数据契约和实验结果验收。

## Product Purpose

从 GPS L1 C1 伪距和广播星历逐历元计算独立普通解与改进解，解释故障处置依据，保存可复现的输入、参数与输出。

## Operating Context

以桌面分析为主，支持手机查看。提供文件与 TCP 输入、历史运行、受控故障实验、自定义观测导入和 CSV/日志导出。轨迹、残差、卫星和统计量必须对应同一选中历元。

## Capabilities and Constraints

等权 LS 基线；最多两星共识排除为默认方法，单星 FDE 和论文启发的 GNC 为对照方法。真值仅用于事后评价，不能进入解算。所有无效状态、数据过期提示、四星无冗余提示和算法边界必须保留。D01 无独立真值，不报告其绝对精度。不得发明地图地理位置、定位指标、完好性保障或成绩承诺。

## Brand Commitments

用户要求可靠、稳重的测绘工具感，并明确要求摆脱通用 AI 后台模板。已授权参考长期使用的测绘企业软件重构配色：本轮依据 Leica Infinity、Topcon MAGNET Office、Trimble Business Center 的官方界面研究，建立石墨框架、设备灰工具层、白色数据纸面和深色轨迹区的职责分工；设备黄用于主要运行动作与导航标记，蓝色用于数据和次级交互。已确认的紧凑操作、数据主视图、按需检查和统一时间回放继续保留。中文为主要界面语言；用户指定中文统一使用微软雅黑，英文与数字使用 Times New Roman，关闭字体合成，读取本机400/700字体且不分发字体二进制。该要求优先于此前的系统字体及等宽字体选择。保留 GNSS Workbench 名称，不复制参考产品的品牌资产或声称厂商认证。

## Evidence on Hand

fixtures/course 为原始课程资料。docs/requirements-matrix.md 为要求矩阵；docs/validation.md 与 tests 保存验收证据。web/e2e 覆盖实际运行、故障、导入、TCP 与消融。实际成员分工与答辩尚需成员完成。

## Product Principles

- 信息优先级由当前分析任务决定。
- 异常与失效状态必须可见，结果可追溯。
- 每一个交互操作作用于明确的数据集、运行或历元。
- 保留真实数值，不以平滑、历史位置或装饰隐瞒计算失败。
