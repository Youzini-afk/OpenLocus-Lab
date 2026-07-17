# Product Bakeoff B3 未来锦标赛预注册

日期：2026-07-17

状态：`product_bakeoff_b3_protocol_frozen_no_runtime_no_holdout_no_execution_no_result`

B3 是一项全新的未来实验。它不会重开、重试、恢复、评分、排名或重新解释 B2.5。B2.5 的终态 `failed_closed_no_result` 聚合仍然是权威结论，任何 B2.5 治疗输出、私有留出集或启动授权都不得复用。

公开预注册见 [`product_bakeoff_b3_protocol_report.json`](../../artifacts/product_bakeoff_b3_protocol/product_bakeoff_b3_protocol_report.json)。可执行协议见 [`product_bakeoff_b3_protocol.py`](../../eval/product_bakeoff_b3_protocol.py)，门槛与评分共用的重复性策略见 [`product_bakeoff_b3_repeatability.py`](../../eval/product_bakeoff_b3_repeatability.py)。

本阶段不读取私有留出集、不产生治疗输出，也不授予执行权限。租用的 Linux 服务器可以继续保持关机。

## 在任何新输出之前冻结的设计修正

B3 在不改变任何历史结果的前提下修正四个设计薄弱点：

1. 不再把 48 个逻辑任务描述为 48 个独立仓库。它们嵌套在 12 个冻结仓库快照内。任务仍是成对质量分析单位，仓库则是相关性簇，也是外推边界。
2. 六个实验臂采用六序列 Williams 设计，同时平衡实验臂位置和一阶前序效应；历史循环轮换只显式平衡了位置。
3. 评分前重复性门槛与评分端规范化调用同一份实现。整组缺失、重复 repetition 或错误 cache 签名不能再被普通分组过程掩盖。
4. 正式尝试边界绑定到第一条持久化治疗观测——无论是 accepted 还是 rejected 的运行记录或输出——而不是仅仅创建 launch release。边界前经审计确认的零观测交接失败可以修复；边界后的任何失败仍然终止且不可重试。

## 实验结构

| 层级 | 数量 | 含义 |
| --- | ---: | --- |
| 冻结仓库快照 | 12 | 分层固定框架中的相关性簇，不是随机总体样本 |
| 逻辑任务 | 48 | 主要成对质量分析单位，每个仓库嵌套 4 个任务 |
| 治疗栈 | 6 | 每个任务都接受全部六个栈，构成完整任务内区组 |
| 技术重复 | 4 | 1 次 cold、3 次 warm；不增加质量样本量 |
| 冻结调度行 | 192 | 实验臂展开前的任务/repetition 行 |
| 逻辑评分组 | 360 | 288 个 context 组，加 72 个两步 support 组 |
| 适配器观测 | 1,440 | 资源与重复性观测，不是 1,440 个独立实验 |

主要结论范围是对这个精确冻结框架作产品决策。B3 不预注册总体假设检验，并禁止把任务错误地当作相互独立后计算未经调整的 p 值。重复性门槛通过后，每个逻辑任务只评分一次。技术观测仍可用于资源测量，但不会增加质量样本量。

完全相同的结果继续按同分处理。相同质量向量和相同资源向量使用共享竞赛排名，例如 `1, 1, 3`；B3 不强制产生唯一赢家，决策等价的实验臂可以共同晋级。

## Williams 随机化与 split-plot 生命周期

公开随机种子为 `openlocus-b3-20260717-williams6-splitplot-v1`。

六个治疗对应六条 Williams 排列。在一套完整的六序列中：

- 每个实验臂在每个位置恰好出现一次；
- 每一对不同实验臂作为相邻的“前序—后序”恰好出现一次；
- 不会出现实验臂紧跟自身的情况。

192 条任务/repetition 行用冻结的语言、规模、角色和 repetition 系数分配这些序列。验证要求：

- 全局的序列、实验臂位置和有向前序关系完全平衡；
- 每个 repetition、规模层和任务角色内完全平衡；
- 语言层保持在 10 到 12 次的受控序列范围；
- 每个仓库/repetition 生命周期恰有 1 个 cold 任务和 3 个 warm 任务；
- 每个任务恰好轮到 1 次 cold、3 次 warm。

仓库/实验臂/repetition 的索引生命周期仍是 split plot。cold/warm 观测共享声明的仓库状态，是技术重复测量，不是独立的索引构建实验。

## 门槛与评分共用一个重复性定义

B3 共用策略不读取 oracle，但保留所有可能改变冻结质量评分或同臂 support 路由的输出特征。

对 context 观测保留：

- 已接纳且可评分的结果类别；
- 候选集合为空或非空；
- pack 状态；
- evidence 的路径/行并集；
- target 的路径/行并集；
- target 数量类别：空、单个或多个；
- support 集合为空或非空。

对 support 观测保留已接纳且可评分的类别，以及按 relation kind、parent target id、路径和行区间归并的 support 并集。终止型 support 观测保留已验证终止类别、终止原因和完整的 context 评分/路由投影。

target 数量不会被故意丢弃。一个 ready 的单 target 允许执行同臂 support 并获得 support 得分；两个重复 target 对象则不允许，即使它们的行并集与一个 target 完全相同。evidence 和 support 在评分原子并集不变时可以合并分段，但 target 的单个与多个会改变路由，因此在科学含义上并不等价。

当候选仍为非空时，候选原生分数与顺序、evidence/support 重复分段、excerpt、channel、解释、状态原因文本、精确 pack 序列化和诊断 receipt 都不进入质量投影。它们的精确诊断 hash 可以私下记录。纯诊断漂移不会让质量门槛失败，但也不会被悄悄抹掉。

调用方必须提供完整预期观测计划。共用核心会核对全部 360 个逻辑组、repetition 1 到 4，以及精确的 1 cold/3 warm 签名，然后才选择最低 repetition 的代表进行质量评分。资源观测不会被规范化，也不要求相等。

source currentness、记录验证与可评分性、工作区严格性、split-plot 生命周期、同臂父级 lineage、跨臂静态公平性和 provider 网络调用为零，仍然是相互独立的强制门槛。

## 尝试边界与恢复策略

仅创建私有 launch release 不会消耗唯一一次有结果意义的尝试。在第一条持久化治疗观测之前，只有同时满足以下审计条件才允许恢复：

- 不存在持久化治疗记录或输出，也没有治疗 payload 对操作者可见；
- 冻结协议、留出集、query 和 oracle 完全未改变；
- 所有工作状态都被丢弃并重新创建；
- 如果更换 runner，必须重新完成公开 qualification 和 readiness checkpoint 后才能启动。

第一条持久化治疗观测会跨越尝试边界，其中也包括 rejected 运行记录。从此只有一次尝试：不得完整重启、在进程或机器丢失后恢复、选择性重跑 cell、填补缺失 cell，或重新计算已完成 cell。边界后失败将以“无锦标赛结果”关闭。

这个边界既保证在证据出现后不能适应性调整，也不会把已经证明零输出的 launcher 或交接故障错误地当作科学数据。

## 冻结阶段顺序

必须按以下顺序推进：

1. 公开冻结 B3 协议和重复性策略；
2. 在本地完成 B3 runner/scorer 集成与合成故障测试；
3. 通过公开 CI；
4. 在未来使用的机器上完成精确 Linux runtime qualification；
5. 创作并冻结全新的私有留出集；
6. 提交仅含聚合信息的公开 readiness，并等待 CI 通过；
7. 创建一次私有 launch authorization 和 release；
8. 执行一次完整锦标赛尝试并终态关闭。

当前 readiness 只完成到第 1 步。B3 runner 和 scorer 尚未集成，runtime 尚未 qualification，私有留出集不存在，执行也未获授权。下一本地阶段应先完成这些实现面与故障测试，再启动服务器进行精确 runtime qualification。

## 公开验证

协议自检覆盖 192 条调度行、360 个完整逻辑组和 1,440 个预期观测。它检查 Williams 位置与前序平衡、仓库聚类表述、门槛/评分共用策略、target 数量路由、同分处理、父终态锁，以及零输出与边界后失败的区分。故障注入会拒绝整组缺失、重复 repetition、评分相关漂移、target 数量漂移、父锁漂移、伪重复表述、关闭前序平衡、边界后重试、扩大隐私公开、过度授权执行和 digest 漂移。

公开协议 digest 为 `b3protocol_d823432f1db3dedbf51e344dee25eddf41d67fd4ce33f0f284cae5fed66a3a92`；spec digest 为 `b3spec_bee900dd30fe0ce7`。

## 剩余限制

B3 目前只是预注册设计，不是锦标赛结果。它不改变产品默认值，也不提出任何实验臂实证结论。在本地 runner/scorer 集成和公开合成 qualification 完成且 CI 通过之前，服务器应继续保持关闭。
