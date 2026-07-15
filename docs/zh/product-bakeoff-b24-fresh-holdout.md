# 产品栈 Bakeoff — B2.4 全新合格机器盲测协议

日期：2026-07-15

状态：`product_bakeoff_b24_private_holdout_frozen_no_treatment_output_no_result`

B2.4 是一个新的验证性锦标赛外壳：B2.1 已按失败关闭，B2.3 的受限 Linux 机器已经通过公开资格验证。B2.4 私有盲测集和精确运行时现已冻结，而仓库身份、任务文本、查询、判定记录和私有摘要继续保持私有。本检查点不包含任何方案输出、评分、排名、短名单或产品默认项结论。

可执行的公开契约包括：

- [`product_bakeoff_b24_protocol.py`](../../eval/product_bakeoff_b24_protocol.py)
- [`product_bakeoff_b24_corpus.py`](../../eval/product_bakeoff_b24_corpus.py)
- [`product_bakeoff_b24_runner.py`](../../eval/product_bakeoff_b24_runner.py)
- [`product_bakeoff_b24_scorer.py`](../../eval/product_bakeoff_b24_scorer.py)
- [`product_bakeoff_b24_readiness.py`](../../eval/product_bakeoff_b24_readiness.py)
- [`product_bakeoff_b24_cli.py`](../../eval/product_bakeoff_b24_cli.py)
- [`product_bakeoff_b24_linux_longrun.sh`](../../scripts/product_bakeoff_b24_linux_longrun.sh)
- [`product-bakeoff-b24-holdout.yml`](../../.github/workflows/product-bakeoff-b24-holdout.yml)
- [`product_bakeoff_b24_protocol_report.json`](../../artifacts/product_bakeoff_b24_protocol/product_bakeoff_b24_protocol_report.json)
- [`product_bakeoff_b24_holdout_readiness.json`](../../artifacts/product_bakeoff_b24_readiness/product_bakeoff_b24_holdout_readiness.json)

## 上游锁定

B2.4 锁定 B2.1 的聚合失败关闭结果，包括两次不完整尝试、没有评分、没有锦标赛结论。它也锁定 B2.3 已通过的精确机器资格汇总。该汇总允许编写新的盲测集，但明确不允许直接执行锦标赛。

未来锦标赛必须复用同一台已认证机器。机器的精确配置、标识和存储位置保持私有。执行前会重新核验私有资格回执；稳定字段发生变化时，启动会失败关闭。

## 全新盲测边界

最终私有样本包含 12 个仓库快照和 48 个新编写的逻辑任务：Rust、Python、TypeScript 与 small、medium、large、xlarge 四个可见源码规模交叉，每个仓库四种任务角色。每个入选仓库的 slug 和 `(slug, commit)` 身份都必须同时不出现在 B2、B2.1 实证样本及封闭的预检/资格排除表中。

12 个槽位中的每一个都至少预先冻结两个候选仓库及其顺序和预期许可证。候选切换只能发生在任何方案输出之前。查询和判定标准继续由冻结的 B2 离线出题器生成，不使用任何检索方案输出。在仓库、任务、判定标准、源码、运行时、超时和机器资格全部冻结前，任何最终任务都不得交给方案执行。

## 聚合就绪检查点

私有出题与冻结已经在同一台合格机器上完成。聚合检查点确认最终选入 12 个仓库快照、48 个逻辑任务和 48 条判定记录；与 24 个历史实证仓库及封闭排除表的重叠均为 0。公开文件只给出排除仓库总数 24 和被排除合成源总数 1，不发布仓库身份、候选顺序、切换细节、任务文本、查询、路径、判定记录或私有摘要。

任务边际与预注册完全一致：每种语言 16 个任务、每个规模档 12 个、每种角色 12 个；36 个 one-shot 和 12 个 two-step；判定类型为 36 个 deterministic、6 个 multi-target 和 6 个 abstain。方案输出、逻辑记录、提供方网络调用、评分、排名和公开结果计数全部为 0。在本就绪检查点提交并通过公开 CI 之前，锦标赛执行仍未获授权。

## 实验设计

独立实验单位仍是一个逻辑任务（`n=48`）。仓库是嵌套聚类；四次重复和冷/热缓存观测只是技术重复，不增加独立样本量。六个 S0–S5 方案在同一台合格机器上完整运行每个任务，形成随机完整任务区组，并继承固定随机种子和仓库 split-plot 生命周期。

不允许按方案或任务组分片，不允许中途查看质量、不允许自适应淘汰、替换任务、选择性重跑、补齐缺失单元或迁移到另一台机器。质量向量或资源向量完全相同时使用并列竞赛排名，不强行选出唯一第一名。

## 长跑超时桥接

B2.1 两次都在同一个短超时边界失败。B2.3 把外层阶段上限提高到 600 秒，但继承的底层命令仍保留旧的 25 秒限制。B2.4 现在把两层都明确冻结：请求/工作进程上限为 600 秒，内部 prepare、index、query 命令上限为 570 秒。内部上限仍小于外层上限，因此父级测试框架仍能保持失败关闭控制。

这个桥接对所有方案及 prepare、index、context、support 操作完全相同，并且在私有出题前冻结。一旦产生任何方案输出，就不能再修改超时。

## 执行与监控

未来锦标赛使用 `nohup` 或 `screen` 下的单个独立进程，不在 GitHub Actions 私有作业中运行。必须先提交只含聚合信息的公开就绪检查点并让 CI 通过，之后才可创建一个私有启动授权回执，把该就绪提交和 CI 运行绑定到冻结的私有输入与运行时。

锦标赛只有一次尝试。一旦产生任何方案输出，进程或机器重启、恢复执行、完整重跑、选择性重跑、重新计算、修改超时或修改任务/判定标准都会让 B2.4 无结果关闭。监控只允许查看进程状态、已完成任务组数、逻辑记录数和最终退出状态，不允许查看任何中途方案、质量、资源或排名指标。

## 隐私与发布

仓库身份、候选顺序与切换、任务文本、查询、路径、范围、判定标准、私有清单、冻结/运行时/启动摘要、逐任务输出、精确机器配置和私有位置全部保持私有。盲测就绪文件只能发布预注册计数和布尔门槛。只有完整 1,440 条逻辑记录和所有评分前门槛全部通过后，才允许发布锦标赛结果；即使发布，也只能包含方案级和预注册分层的聚合信息。

## 冻结的公开标识

- B2.4 规范摘要：`b24spec_d64f8821238a58ec`
- B2.4 源码包摘要：`b24src_191a8ca7d4a61e7f29564b5079776632bd1c147dcce1aedf11fe10a54b91e0bd`
- B2.4 盲测框架摘要：`b24frame_429a87368330b5c33c8c30a771fd5f62c2f445d9408598bf25cbf0d0fad64d07`
- 继承的执行调度摘要：`b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.4 协议报告摘要：`b24protocol_94b395f9e6b12fc37ca473077ab15fcf4716c3e63928a996c7678f57e41455a5`
- B2.4 就绪摘要：`b24ready_94ef3cc33a025a523825ce0a88f20819694975600c0be6afc9fe959f20bd1596`
- 协议检查点与 CI：`c2891cd3f8eb6880b6edd263914c1582629c44e5`，运行 `29423106660`（`success`）

## 下一项获准工作

提交这个仅含聚合信息的就绪检查点并取得公开 CI 通过。之后把就绪提交和 CI 运行绑定进唯一的私有启动授权回执，重新核验合格机器配置与冻结运行时，然后启动且只启动一次独立锦标赛。在这些门槛全部通过前不得执行任何方案。
