# 产品栈对比 — B2 内部锦标赛协议冻结

日期：2026-07-15

状态：`product_bakeoff_b2_execution_failed_closed_no_result`

B2 仍是已预注册的有界内部产品决策锦标赛。实现与私有的 12 仓库/48 任务框已冻结，源码检查点通过了跨平台 CI，正式的 1,440 条记录矩阵也已启动。随后运行在 support 执行和评分之前按规则失败关闭：某个双步任务的六个 context 输出虽然全部验收通过，但没有落在同一条规范源码路径，因此冻结的共同父范围规则无法构造共享 support 父目标。停止时共有 24 条 context 记录和 24 份父进程回执验收通过，provider/网络调用为 0。不存在锦标赛分数、排名、决赛方案或产品默认结果。

可执行实现表面与闭合公开协议报告为：

- [`product_bakeoff_b2_protocol.py`](../../eval/product_bakeoff_b2_protocol.py)
- [`product_bakeoff_b2_corpus.py`](../../eval/product_bakeoff_b2_corpus.py)
- [`product_bakeoff_b2_author.py`](../../eval/product_bakeoff_b2_author.py)
- [`product_bakeoff_b2_oracle.py`](../../eval/product_bakeoff_b2_oracle.py)
- [`product_bakeoff_b2_adapters.py`](../../eval/product_bakeoff_b2_adapters.py)
- [`product_bakeoff_b2_runner.py`](../../eval/product_bakeoff_b2_runner.py)
- [`product_bakeoff_b2_scorer.py`](../../eval/product_bakeoff_b2_scorer.py)
- [`product_bakeoff_b2_cli.py`](../../eval/product_bakeoff_b2_cli.py)
- [`product_bakeoff_b2_protocol_report.json`](../../artifacts/product_bakeoff_b2_protocol/product_bakeoff_b2_protocol_report.json)
- [`product_bakeoff_b2_failed_closed_aggregate.json`](../../artifacts/product_bakeoff_b2/product_bakeoff_b2_failed_closed_aggregate.json)

## 失败关闭执行检查点

这不是超时、坏记录、缺失回执、资源故障或网络故障。已产生的 24 条记录全部通过验收与父进程校验；停止条件来自预注册的跨 arm 父路径收敛规则本身。由于 arm 输出已经存在，B2 不能修补任务、放宽规则、填充缺失单元或选择性重跑。同一冻结包下的确定性重试会再次触发相同停止条件，因此不获授权。

## 父级锁定

B2 绑定到已正式收口的 B1 机械能力包：

- B1 源码检查点：`0b6f2e13b1dbc679eb1f827c28a8abd5403dcd58`
- B1 收口检查点：`617b452cf24ac7294b49133caf18ee8f279e1dfe`
- B1 源码包：`b1src_fa5b30ca188d08a491206e13acfe3faa9a5070a68be2222ba349392101b136d2`
- B1 收口运行使用的运行时包：`b1run_01c1fdcfe6d77f3d1f8101f66a90191a1f4a620d43e39a139b686149e0b2a896`

如果 B1 机械能力表面发生任何改变，经验执行前必须显式重新冻结 B2。

## 实验单位与阻断

独立实验单位是一个逻辑任务，因此锦标赛样本量精确为 48。六个 S0–S5 栈都运行每个任务，所以每个任务本身就是完整对照块。仓库、语言和规模是已知干扰因素。重复、冷/热观测、context/support 步骤、候选、证据 span 和资源样本都是重复或嵌套测量，不能增加独立任务数。

私有经验任务框必须包含 12 个冻结仓库快照：

- 语言：Rust、Python、TypeScript；
- 可见源码规模：small、medium、large、xlarge；
- 每个语言 × 规模组合恰好一个仓库；
- 每个仓库 4 个任务，分别对应 direct、relational、workflow、restraint。

这样共得到 48 个任务。精确公开边际为：

- 每种语言 16 个任务；
- 每个规模档 12 个任务；
- 每种任务角色 12 个任务；
- 36 个单步任务、12 个双步任务；
- 36 个 deterministic、6 个 ambiguous multi-target、6 个 no-answer；
- 九种可回答任务 family 各 4 个任务；ambiguous_target 与 no_answer 各 6 个。

真实仓库身份、任务文本、查询、oracle 行和标签保持私有。公开报告只暴露冻结的槽位结构及其摘要。

## Split-plot 生命周期与运行顺序

索引构建是难切换因素。因此 B2 使用仓库块内 split-plot 生命周期，而不是为每个任务重新构建索引：

- 四次技术重复；
- 每个仓库 × arm × repetition 只新建一次索引；
- 随后该仓库的 4 个任务复用这份状态；
- 恰好 1 个任务承担 cold 观测，其余 3 个是 warm reuse；
- cold 角色轮换，使每个任务恰好 cold 一次、warm 三次。

完整设计需要 288 次索引构建和 1,440 条已校验记录：864 条单步记录，加 576 条 context/support 记录。技术重复用于提高资源与确定性测量质量，但不会把独立样本量从 `n=48` 变大。

基础 arm 顺序由固定种子生成。正交循环轮换使每个 arm 在规模、任务角色和 repetition 分层内精确均衡地出现在各执行位置。每种语言有 64 行调度，无法被 6 个位置整除，因此每个 arm-position 计数被限制在 10–12。

双步任务先按冻结的 arm 顺序运行六个 context 步骤。六个主目标必须位于同一规范路径，且行范围存在非空交集；这个精确交集成为六个 support 请求共同的父范围，随后再按相同的冻结 arm 顺序运行 support。若路径分叉或交集为空，完整运行直接失败关闭，不允许不同 arm 得到不同的父问题。

## 任务准入与评分

在任何 arm 输出出现前，私有仓库、任务和 oracle manifest 必须冻结并计算摘要。不得使用适配器输出创建或修改任务。查询不得暴露仓库身份、源码路径或行号。

Deterministic 任务恰好有 1 个正目标 span；ambiguous 任务至少有 2 个不同正目标 span；no-answer 没有正目标。每个任务至少有 2 个不同的冻结负 span，正负 span 必须不相交并通过当前源码校验。双步任务至少需要 1 条有效支持关系。

上下文质量按去重后的 `(canonical path, line)` 原子评分。Precision、recall 和 F0.5 使用精确有理数计算，向下取整为整数百万分数，并在 42 个可回答任务上求和。排名使用未舍入总和，绝不使用舍入后的平均值。如果任何已选择证据行与冻结负 span 相交，该任务记为 harmful。

只有在 cache state 和 repetition 之间的质量语义完全一致后，scorer 才能把技术测量折叠为一个任务级结果。

当前私有准备轮次在不公开仓库身份、任务文本、路径或 oracle 行的前提下，匹配全部公开边际：12 个仓库、48 个任务；三种语言各 4 个仓库；四个规模档各 3 个仓库；36 个单步任务加 12 个双步任务；48 个正 span、96 个负 span 和 12 条支持关系。这仍只是冻结前审计；没有使用任何最终任务的 arm 输出来创建或修改任务框。

## 产品门禁与晋级轨道

所有经验结果必须先通过完整矩阵、当前 citation、源码不可变、确定性、资源完整、零网络、scorer 隔离和隐私门禁。缺失单元永不插补。

S0 保留为必需的控制和回退比较，但不会自动晋级。S4 与 S5 是默认候选轨；S1、S2、S3 是可选能力候选。

冻结门禁包括：

- 候选准入至少 34/48 个成功任务、30/36 个成功单步任务；
- 至少 34/42 个可回答目标成功；
- ambiguous 决策至少 5/6 正确，no-answer 至少 5/6 正确；
- 预声明的语言、规模和任务角色下限；
- 包含 harmful evidence 的可回答任务不超过 4 个；
- 默认候选轨还要求至少 36/48 个任务成功、9/12 个 support 成功；
- 相对 S0 的质量非劣与有界 warm latency、RSS、cold-index 时间和持久状态大小。

每个新增组件都必须相对直接比较栈赚取纳入资格。Literal 和 symbol 需要预声明子集上的成功增益或上下文质量增益。Graph 需要更大的 graph 子集增益并满足更严格的成本限制。Support 必须提高真实 support success；仅仅上下文变好不能让 support “赚到”资格。S5 还必须单独证明 graph 相对 S4 的价值，因此 graph 不能藏在 support 栈中而不承担增量成本。

## 同分与合法结果

质量排名和资源排名分开。质量使用精确整数计数和定点总和。完全相同的质量向量共享竞赛排名，例如 `1, 1, 3`。协议禁止强行产生唯一获胜者。

0 个、1 个或多个决赛方案都是合法结果。若多个合格 arm 落在冻结的决策等价边界内，它们都可以晋级 Phase C；不设决赛方案数量上限。当至少一个默认候选轨 arm 通过时，shortlist 从该轨道产生；否则协议可以返回可选轨 shortlist 或无决赛方案。

## 反适应与隐私边界

任何 arm 输出出现后，B2 禁止增删替换任务、修改 query 或 oracle、改变阈值/权重/顺序、设置 arm 专属预算、阶段性淘汰、选择性重跑和缺失单元插补。基础设施无效的运行必须整体作废，并以新的私有运行身份完整重启。

经验锦标赛在 Git 忽略的本地目录中运行。CI 只运行公开的 B2 编译、实现自检、实现故障注入、协议自检与故障注入、报告校验、漂移检查、包回归测试和文档校验；它不会接收私有候选计划、仓库、任务或 oracle 行。公开经验输出只允许 aggregate-only：不得公开任务/仓库行、查询、候选、路径、范围、摘录、私有内容 hash 或冻结 manifest 摘要、标签、逐单元资源、私有运行路径、provider payload 或密钥。公开协议摘要和汇总产物自身摘要仍可保留。

## 冻结标识

- B2 规格摘要：`b2spec_358b77c924fbe3f1`
- B2 源码包摘要：`b2src_c129273f4078d484401e4e255a110b926a0cce7f513fe2f1455415f6309f2ea0`
- 任务槽摘要：`b2slots_a92720057d2f931e1f84c2b3d49af5a4e2efe08661d7c49e375e8835a80149ff`
- 执行调度摘要：`b2sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- 协议报告摘要：`b2protocol_9057cbb85bb11f84377424a96ea2de55e7bff80314520b89b3c0c1e35340b679`

## 下一项已授权工作

将 B2 收口为 `failed_closed_no_result`。任何后续产品锦标赛都必须使用新的 holdout 任务框单独预注册，并在产生任何新 arm 输出前论证新的父目标绑定策略；不得恢复、选择性修补或把这份不完整矩阵当作有效结果复用。
