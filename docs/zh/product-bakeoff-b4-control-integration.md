# 产品栈对比 B4 离线控制面集成

日期：2026-07-18

状态：`product_bakeoff_b4_offline_control_plane_complete_server_required_next_for_exact_linux_qualification`

B4 原始仓库执行适配器和离线控制面现已实现并通过故障测试；本检查点没有读取私有留出集，也没有产生治疗输出。聚合机器可读检查点为 [`product_bakeoff_b4_control_integration.json`](../../artifacts/product_bakeoff_b4_control_integration/product_bakeoff_b4_control_integration.json)。

## 原始执行适配器

十二个面板分别在全新的子进程中复用既有 B2.1 执行门槛和 B2.4 超时外壳。窄作用域 override 只在该子进程内把历史表面改为三个实验臂、每个“仓库 × 实验臂”一个生命周期、一次重复、冻结的面板调度、180 个原始操作组和 36 次索引构建；无论成功还是异常，历史函数、超时、适配器注册表、调度函数和常量都会恢复。

RUN 阶段开始前不允许导入 author、oracle 或 scorer。此前会传递导入 scorer/oracle 的历史 B3 校验依赖已改为在原始子进程导入面之外惰性加载。只有面板原始矩阵和评分前门槛全部完成后，子进程才加载冻结 oracle 与历史任务评分器，投影出 144 个不含身份的任务结果，并以独占、原子、耐久方式写入一个私有面板报告。十二个有效报告最终组装为分析引擎要求的 1,728 个任务结果、2,160 条逻辑记录和 432 次索引构建。

## 私有语料构造与冻结

作者控制器在十二个仓库槽位和十二个互不重叠的面板间共用一份候选目录。它排除 B2、B2.1、B2.4、B2.5、B3 五个历史帧中的全部 60 个仓库，以及显式排除注册表。每个槽位的候选顺序是确定的；候选失败只推进对应槽位，已完成仓库检查点和已完成面板不会重做。

恢复时，控制器会重放每个已完成面板的候选计划和游标，重新校验选中 Git checkout、任务/oracle 清单，重建仅基于源码的查询兼容门，并重建精确面板绑定。缓存根目录会相对于整个私有根统一规范化。淘汰的 clone 依据冻结的 `clone_root` 字段清理，选中的源码目录保持不动。只有十二个面板合计包含 144 个互异仓库身份、576 个任务、有效查询/oracle 绑定、精确 qualification runtime 与 CLI 字节，并且治疗输出为零时，才允许冻结。

公开内容只有聚合 readiness。另有一份私有 readiness-binding receipt 把公开 readiness 的精确文件字节绑定到精确 global private freeze；launch authorization 必须同时验证两者，从而在不公开私有摘要的前提下阻断 freeze 漂移。仓库、候选、任务、查询、oracle、源码位置、私有路径、端点和私有摘要均保持私有。

## Runtime 与存储策略

下一步服务器工作是使用生产 CLI 和公开合成 runtime 用例做精确 Linux qualification。非存储门槛沿用既有专用 Linux runner 类，包括至少 8 个有效 CPU 核、至少 32 GiB 的有限内存上限、admission 时至少 24 GiB 的有效可用内存、活动 swap 为零、checkout 外的本地非旋转 scratch，以及冻结的 Rust/Python 工具链约束。不需要 GPU。

B4 不继承任意固定磁盘预留。free-scratch 门槛由最大允许可见仓库、一个串行生命周期中的三个实验臂快照、索引/渲染展开、控制 receipt 和文件系统余量计算得出，最终 admission 阈值为 5,100,273,664 字节（约 4.75 GiB）。已冻结源码占用已经体现在当前空闲空间中；面板与仓库生命周期串行执行，可丢弃工作树会在使用后删除。

## 启动、中断与尝试边界

Runtime qualification 必须先提交并通过公开 CI。之后私有 authoring 与 freeze 生成聚合 readiness 及其私有 freeze-binding receipt；公开 readiness 也必须提交并通过 CI，才能创建私有 launch authorization。

Linux launcher 使用独立进程组、耐久 PID 身份、私有日志与退出码、worker-entry/runner-admission 握手和单独的 launch release。冻结 CLI 路径会显式绑定到历史 runner 查询的 `OPENLOCUS_CLI`。若在 release 前、零观测条件下 admission 失败，确认 worker 已停止后，可用窄范围 reset 仅删除 PID/admission/envelope 状态；只要 release、耐久观测、面板结果、边界 receipt、终态或公开 closeout 中任一存在，该 reset 就被禁止。

仅写入 launch release 不消耗尝试。第一条耐久写入的普通或 terminal 原始观测会先同步文件及目录，再创建私有尝试边界 receipt；若进程在观测落盘后、receipt 写入前崩溃，系统会从耐久清单保守重建。跨越边界后仍禁止重启、恢复、选择性重试、填补和重算。失败进度按精确耐久观测数统计，包含当前未完成面板，而不再用“完整面板数”粗略估算。

## 验证与当前边界

本地 self-test 与 fault-test 覆盖十二套调度、真实嵌套 runtime override、异常后的完整恢复、独占耐久面板输出、重复键/非有限 JSON 拒绝、不含身份的投影、完整聚合组装、候选耗尽与历史重叠、确定性恢复、选中/淘汰 clone 清理、计算型资源 admission、readiness 隐私、launch release 分离、观测/receipt 崩溃窗口协调、精确聚合进度，以及零观测且 release 前的 reset。Linux 脚本另行演练 detached 握手与 PID 身份路径。CI 会在 Linux 和 Windows 上重复控制测试，并检查原始导入围栏、父协议/引擎漂移、公开隐私、双语文档和 shell 启动行为。

本检查点尚未完成精确 Linux runtime qualification；没有创建或冻结私有 B4 留出集；不存在 launch authorization、release、治疗观测、评分、排名或 B4 实证结果。只有在本控制面检查点提交且 CI 变绿后，才需要开启算力服务器。
