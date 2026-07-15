# 产品栈对比 — B2.1 自有父目标 Holdout 协议

日期：2026-07-15

状态：`product_bakeoff_b21_protocol_frozen_no_execution_no_result`

B2.1 是新的确认性 holdout 锦标赛，不是对不完整 B2 矩阵的修补或续跑。B2 在评分前失败关闭，原因是某个双步任务的六个有效 context 输出没有落在同一条源码路径。B2.1 将这种目标差异保留为方法效果的一部分：每个 arm 的 support 步骤只跟随该 arm 自己在同一次执行中得到的 context 目标。

可执行协议与公开设计报告为：

- [`product_bakeoff_b21_protocol.py`](../../eval/product_bakeoff_b21_protocol.py)
- [`product_bakeoff_b21_protocol_report.json`](../../artifacts/product_bakeoff_b21_protocol/product_bakeoff_b21_protocol_report.json)

## 父级锁定与禁止复用边界

B2.1 绑定 B2 实现检查点 `55e0ebaaaf6f25c5c7d5c13ffc6ee58825e7d915` 和失败关闭收口检查点 `07bfd116622bd0ed9a2bc654abec3bb98a7f38df`。B2 已观察到的 24 条 context 记录保持未评分状态，不能恢复、修补、插补或复用。

新的经验任务框必须包含 12 个未出现在 B2 任务框中的仓库身份，以及 48 条全新编写的 task/oracle 行。B2 的任务边际和离线编写规则原样继承，因此不会利用失败结果调整任务 family、query 或标签。最终 holdout 任务在 B2.1 运行时冻结前不得由任何 arm 执行。

## 实验单位与生命周期

独立单位仍是一个逻辑任务（`n=48`）。仓库是嵌套 cluster。cache state 和四次重复都是技术重复测量，不会增加独立样本量。六个 S0–S5 栈在随机完整区组中运行每个任务，沿用仓库 split-plot 生命周期、轮换 cold 任务、288 次索引构建和 1,440 条逻辑记录。

## 自有父目标双步策略

每个双步任务先按冻结的 arm 顺序运行六个 context 步骤。正常 support 请求只绑定同一 arm、任务、重复和 episode 的已验收 context 目标。不同 arm 的路径和范围允许不同；禁止多数投票、求交、oracle 固定共同父目标或跨 arm 替换。

若一个已验收 context 结果没有提供恰好一个 `ready` 主目标，harness 会产生闭合的 `parent_unavailable` support-opportunity 记录。它计为 support 与任务失败，但不会中止完整矩阵。被拒绝、超时或格式错误的 context 仍属于基础设施无效运行并失败关闭。

公平门禁仍要求相同的任务 query、源码可见范围、预算、超时、cache 标签和 split-plot 生命周期。support 父目标字段只有在来自各 arm 自身 context 输出时才允许不同。context fingerprint 在 arm 间保持相同；support 使用排除 treatment-mediated 父字段的静态 fingerprint，并另行校验同 arm lineage。

## 评分与晋级

任务级质量、组件 earn-in 规则、非劣界限、资源上限、准入下限、同分处理以及零/一/多个决赛方案均继承 B2。双步任务只有在该 arm 的 context 目标通过 oracle 校验且同 arm support 输出命中冻结关系时才成功。终止型 support 机会计为失败并在 arm 汇总层报告；它们不进入 query latency 百分位，避免缺失父目标被奖励或伪装成实测查询。

禁止中途查看质量、提前淘汰、替换任务、选择性重跑或切换规则。只有完整逻辑矩阵、源码、lineage、资源、零网络、确定性和隐私门禁全部通过后才能加载评分。

## 隐私边界

仓库身份、任务文本、query、路径、范围、oracle 行、私有 manifest/freeze 摘要、逐任务分歧、逐单元资源和私有运行路径保持私有。公开输出只允许 arm 级与预声明分层的汇总。B2.1 CI 不接收任何私有 holdout 输入，只运行公开协议/实现测试和报告校验。

## 冻结标识

- B2.1 规格摘要：`b21spec_a4460a279280e872`
- B2.1 源码包摘要：`b21src_76e3433599291e9061c4449b32557b9a3ad2998cfc0a739f69a5632a4e47b7d3`
- B2.1 holdout-frame 摘要：`b21frame_f50eda42c3403eb877e46a07b257a8a0ce8930759422c7536963f7d96eee8571`
- B2.1 执行调度摘要：`b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.1 协议报告摘要：`b21protocol_f1c833bfe2bae7d0ca11c15b6ba5c62650adde88f399217b6171e7156a61d7b7`

## 下一项已授权工作

实现全新 holdout 准入覆盖层、同 arm lineage runner、终止型 support 记录、隔离 scorer 与仅汇总结果校验器。在物化最终 holdout 任务框前，通过合成测试、故障注入和未使用仓库上的真实源码预检。本检查点不存在 B2.1 经验结果。
