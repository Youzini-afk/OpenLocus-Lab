# Product Bakeoff B3 Runner/Scorer 引擎集成

日期：2026-07-17

状态：`product_bakeoff_b3_runner_scorer_integration_complete_no_runtime_no_holdout_no_execution_no_result`

本阶段把 B3 预注册落实成可执行的 runner/scorer 机械路径，同时不修改任何历史 B2、B2.1、B2.4 或 B2.5 模块。它不 qualification runtime、不创作私有留出集、不授权执行、不产生治疗输出、不进行锦标赛评分，也不改变 B2.5 的终态 `failed_closed_no_result`。

公开聚合见 [`product_bakeoff_b3_engine_integration.json`](../../artifacts/product_bakeoff_b3_engine_integration/product_bakeoff_b3_engine_integration.json)。实现分别位于 [`product_bakeoff_b3_runner.py`](../../eval/product_bakeoff_b3_runner.py) 和 [`product_bakeoff_b3_scorer.py`](../../eval/product_bakeoff_b3_scorer.py)。

在本集成阶段开始前，父协议检查点 `291c5a0041d94224a6dfff10838c6ed50110ddb4` 已通过跨平台 CI `29565270451`。

## Runner 集成

B3 runner 复用冻结的 B2.1 执行循环，因为该循环已经实现成本高且安全关键的机械逻辑：

- 隔离的六臂执行；
- source currentness 和 writable-state-root 检查；
- 记录验证与可评分性；
- 仓库 split-plot 生命周期和精确索引构建数；
- 同臂 own-parent support lineage；
- 跨臂静态公平性；
- provider/网络调用为零；
- scorer/oracle 导入隔离。

只在一个有界的单进程上下文中替换两个历史 hook：

1. 用预注册的 B3 Williams 调度替换历史调度工厂和 digest；
2. 用 B3 共用的评分/路由重复性门槛替换历史 exact semantic gate。

B2.4 长跑 envelope 继续提供已设计的长跑适配器以及 request/child-command 双层超时。未来 B3 外层启动层必须先提供一个闭合的 freeze-receipt validator，才能调用此引擎。

每个被注入的函数在替换前都检查对象身份，并在 `finally` 中恢复，即使内部运行抛出异常也一样。嵌套覆盖或预先存在的覆盖会 fail closed。历史文件的字节没有变化。

B2.1 的 execution-key 门槛仍会核对精确有序的 1,440 条记录列表。该列表在注入 B3 调度时构建，因此实验臂顺序、任务顺序、repetition、cache state、operation 顺序和组完整性仍绑定到 Williams 调度，而不只是绑定到重复性投影。

## Scorer 集成

B3 scorer 直接调用 `product_bakeoff_b3_repeatability.canonicalize_for_scoring`，不会调用任何一个历史 B2.1 exact-hash canonicalizer。

共用 canonicalizer 验证全部 360 个逻辑组并为每组选择一个质量代表后，scorer 只复用以下冻结机械逻辑：

- B2 oracle/任务评分；
- B2.1 own-parent 终止型 support 评分；
- 实验臂级计数与定点聚合；
- warm query、RSS、cold index 和 index-state 百分位；
- 组件 earned-inclusion 门槛；
- 相互独立的质量与资源竞赛排名；
- 共享完全同分和决策等价共同入围。

如果 runner 的全部门槛尚未通过、1,440 条逻辑矩阵不完整，或仓库/任务/freeze/oracle 绑定缺失或漂移，scorer 会拒绝运行。公开锦标赛结果构建器仍刻意不实现，直到 readiness 和 launch authorization 冻结。

## 隐藏的旧门槛已经消失的证明

合成端到端 fixture 包含全部 360 个逻辑评分组和 1,440 个观测。每组的四次 repetition 都故意使用不同的历史诊断 semantic hash，同时保持 B3 评分/路由投影不变。

对完全相同的 fixture：

- 冻结的历史 B2.1 semantic gate 会失败；
- B3 runner 门槛会通过全部 360 组，并私下计数 360 个诊断漂移组；
- B3 scorer 通过同一个 canonicalization 核心为全部 360 组选择 repetition 1；
- 历史 B2.1 scorer canonicalizer 被替换成“一旦调用就立即抛错”的函数，但 B3 scorer 规范化仍然通过；
- 与原 target 行并集完全相同的第二个重复 target 会被拒绝，因为它改变单 target support 路由；
- 整组缺失或错误的 repetition/cache 签名会被拒绝。

这是行为级集成证明。runner 和 scorer 不再只是文字上声称共用策略；测试会让旧 exact-hash 路径不可用，并验证 B3 路径仍然工作。

## 质量与资源分离

共用 canonicalizer 只为逻辑质量评分选择一个代表，不会折叠资源观测，也不要求资源观测相等。所有有效 cold/warm/repetition 计时和内存测量继续进入冻结的 B2.1 资源总体。

当评分/路由语义一致时，诊断序列化漂移可以私下计数，但不能改变质量结果。source、公平性、lineage、provider 隔离、完整性和 runtime 测量仍是独立门槛，绝不会从投影中推断。

## 验证

本地验证覆盖：

- 360 个预期组和 1,440 个预期观测签名；
- 调度/门槛注入与恢复成功；
- 注入异常后仍然恢复；
- 拒绝嵌套覆盖、缺失任务、重复任务身份、target 数量漂移、逻辑组缺失和门槛前评分；
- 继承的 B2.1 runner/scorer 自检与故障测试；
- 证明不会调用的“下毒”历史 scorer canonicalization 路径。

公开 integration digest 为 `b3engine_a61e54a2fe426f00ac081345ce379300b4cf8c59bdbcc43eca99f9f104579535`。

## 剩余工作与服务器状态

服务器应继续保持关闭。下一个离线阶段必须实现并完成故障测试：

1. B3 私有 freeze 和仅聚合公开的 readiness 契约；
2. launch admission 和第一条持久化治疗观测边界 receipt；
3. CLI 与断线安全 launcher；
4. 公开合成 runtime qualification 和启动握手；
5. 最终公开结果/失败关闭边界。

只有这些本地实现面冻结并通过 CI 后，才应启动服务器进行精确 Linux runtime qualification。当前尚无私有留出集，执行仍未获授权。
