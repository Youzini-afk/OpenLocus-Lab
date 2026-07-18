# 产品栈对比 B4 分析与发布引擎集成

日期：2026-07-18

状态：`product_bakeoff_b4_analysis_publication_engine_complete_no_runtime_no_holdout_no_execution`

本检查点在选择任何仓库、产生任何治疗输出之前，实现并故障测试 B4 的比较分析表面。机器可读聚合为 [`product_bakeoff_b4_engine_integration.json`](../../artifacts/product_bakeoff_b4_engine_integration/product_bakeoff_b4_engine_integration.json)。

## 闭合矩阵契约

runner 契约只接受恰好 1,728 个不含身份的任务结果，即 576 个配对任务乘以三个实验臂。每个结果都必须绑定公开的面板/任务调度，并与冻结的任务角色和冷热分配完全一致；重复或缺失 cell 会被拒绝；2,160 个原始操作组、432 次索引构建、闭合的评分前门槛集合以及 provider/网络调用为零也必须全部满足。该表面不含仓库 slug、任务 slug、查询、oracle 行、源码位置、excerpt 或原始输出。

这还不是原始仓库执行适配器。Phase 3 仍需把通过验证的私有执行 receipt 转换为该闭合矩阵，并用合成 fixture 与 Linux qualification fixture 证明转换正确。

## 仓库簇分析与决策行为

scorer 把 144 个仓库视为配对簇，计算任务成功、任务效用、状态/目标、context F0.5 和有害证据效应；普通 95% 与同时 97.5% 区间；十二面板方向计数；配对 warm-query 与 peak-RSS 比率区间；质量/资源 competition rank；以及 Pareto frontier。

有害证据门槛不会把“观测到零事件”误写成“零不确定性”。除配对风险差估计外，它还对候选独有的有害事件使用保守的同时 Wilson 上界。排名始终先于部署门槛完成；完全同分共享名次，安全或资源门槛失败也不能删除效应、排名或 Pareto 结果。

## 聚合发布

成功 schema 始终包含三个实验臂的聚合、两个预定比较、两种区间、面板方向、质量/资源排名、Pareto 成员、门槛结果和 Phase C shortlist。失败关闭 schema 只包含安全的聚合进度与失败类别；边界前失败不得发布治疗计数，边界后失败不得授权重启、恢复、重试或重算。

合成测试覆盖可进入 shortlist 的比较结果、三臂完全同分、资源门槛失败、有害证据失败、矩阵缺失/重复、调度漂移、bool-as-int 污染、发布篡改和私有 key 注入。在完全同分场景中，所有实验臂共享第 1 名，Pareto frontier 仍然存在，shortlist 为空，但比较结果不会消失。

## 当前边界

当前没有已 qualification 的 runtime，不存在私有仓库/任务/oracle 留出集，正式执行也未获授权。下一个本地 Phase 是原始仓库执行适配器，以及离线 source、runtime、corpus、readiness、尝试边界和断线安全控制面。在该 Phase 通过 CI 前仍不需要开启算力服务器。
