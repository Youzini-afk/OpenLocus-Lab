# 产品栈对比 — B2.2 Self-Hosted 执行设计

日期：2026-07-15

状态：`product_bakeoff_b22_runner_protocol_ready_no_runner_no_holdout_no_result`

B2.2 是在 B2.1 于低性能本地机器上两次停在同一 timeout 边界之后设计的全新确认性实验。本阶段不编写 holdout、不读取任何 B2.2 私有输入，也不执行任何 treatment arm。它实现强机资格门禁与手动 self-hosted GitHub Actions 路径，防止大型矩阵再次在不合格机器上启动。

可执行范围为：

- [`product_bakeoff_b22_protocol.py`](../../eval/product_bakeoff_b22_protocol.py)
- [`product_bakeoff_b22_runner_qualification.py`](../../eval/product_bakeoff_b22_runner_qualification.py)
- [`product-bakeoff-b22-runner.yml`](../../.github/workflows/product-bakeoff-b22-runner.yml)
- [`product_bakeoff_b22_protocol_report.json`](../../artifacts/product_bakeoff_b22_protocol/product_bakeoff_b22_protocol_report.json)

## 为什么完整锦标赛不在本地运行

小型合成测试仍在本地执行。公开编译、自检、故障注入、报告漂移和文档检查使用 GitHub-hosted CI。持续资格测试以及未来的私有锦标赛使用一台专用强力 self-hosted runner。

私有 holdout 不能提交到这个公开仓库，也不能复制到普通 hosted runner。这个隐私约束不等于必须使用当前工作站。正确边界是一台一次性 self-hosted runner：私有输入预置在 checkout 之外，只有经过验证的汇总产物可以离开机器。

## 实验设计边界

独立单位仍为一个逻辑任务（`n=48`）。仓库仍是嵌套 cluster。cache state 与四次 repetition 仍是技术重复测量。runner 机器被固定为 nuisance block：六种 treatment、全部 group 与最终分析必须使用同一台机器和同一个冻结 runtime。禁止跨多台 runner 按 group、仓库或 arm 分片，否则机器性能会与 treatment、cache 或运行顺序混杂。

随机完整任务区组、仓库 split-plot 生命周期、own-parent 双步策略、质量阈值、资源上限、同分策略以及零/一/多个 finalist 的合法结果均继续继承。不存在中途质量查看。

## 强机等级

runner 在压力执行前必须全部满足：

- Windows x64，至少 16 个逻辑 CPU；
- 至少 64 GiB 物理内存，任务开始时至少 40 GiB 可用；
- checkout 之外的固定本地 scratch 卷至少有 200 GiB 空闲空间；
- Git、Python、Rust、Cargo 与从当前 checkout 构建的 release OpenLocus 可用；
- 专用单任务 runner，并带自定义标签 `openlocus-b22-private`；
- 公开输出不得包含私有路径、精确硬件信息、runner 名称或机器标识。

顺序 I/O 资格测试写入并重读一个 512 MiB 文件，写入结束前执行 `fsync`，重读后核对 hash；读写速度都必须至少达到 150 MiB/s。精确观测速率保持私有。

## 持续资格工作负载

不能只信任硬件标签。profile 和 I/O 门禁通过后，资格器会确定性生成一个公开合成 TypeScript 语料：10,000 个文件、恰好 72 MiB 可见源码。随后使用全部六个 adapter、冻结 arm 轮换、真实 copy/index/query/support 生命周期以及继承的 30 秒阶段 timeout，连续运行三个真实 split-plot group。

必须得到 3/3 group、90/90 逻辑记录、全部正常记录 accepted、timeout 为 0、父收据错误为 0、terminal support 为 0、provider/网络调用为 0，且总墙钟时间不超过 45 分钟。该工作负载在读取任何私有 holdout 之前运行。由于资格测试没有 treatment 输出，不合格 runner 可以在私有输入读取前重新资格测试。

## 公开仓库的 self-hosted 安全

仓库是公开的，因此私有 job 永远不会由 `push` 或 `pull_request` 触发。它要求手动 `workflow_dispatch`、受保护环境 `b22-private-execution`、标签 `self-hosted`、`windows`、`x64` 和 `openlocus-b22-private`，并使用只处理一个 job、随后销毁或擦除的一次性 runner。GitHub 建议自动扩缩场景使用 ephemeral self-hosted runner，并警告公开仓库工作流可能让持久 self-hosted 机器暴露给不可信代码；因此 workflow 只在已审批手动作业期间让 runner 在线，并把外部 action 固定到完整 commit SHA。参见 GitHub 的 [self-hosted runner 参考](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)、[workflow 路由说明](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow) 与 [runner 访问警告](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access)。

job 只使用只读仓库权限，不保留 checkout 凭据，不使用 actions cache，只上传一个精确且已验证的汇总 JSON。按照 GitHub 建议，一次性运行前必须把 runner 诊断日志转发到受限外部存储。

## 操作实践

1. 创建受保护环境 `b22-private-execution` 并设置审批人。
2. 配置满足冻结资源等级的专用一次性 Windows x64 VM。
3. 把 scratch 放在固定本地 SSD，并在 runner 服务环境中设置 `OPENLOCUS_B22_SCRATCH_ROOT`；不得把私有数据放进 checkout。
4. 用自定义标签 `openlocus-b22-private` 和 ephemeral 模式注册 runner。
5. 把 runner 诊断日志转发到受限存储。
6. 从 `main` 手动 dispatch `product-bakeoff-b22-runner`，mode 选择 `runner_qualification`。
7. 只验证并提交上传的汇总资格结果。
8. 只有该结果为绿色后，才编写全新的 B2.2 holdout。

本检查点仓库中没有已注册 self-hosted runner，因此真实强机资格测试尚未执行。本地 profile-only 实践已在逻辑 CPU、总内存、可用内存和 scratch 空闲空间四项门禁上拒绝当前工作站；它正确跳过了 512 MiB I/O 测试与 72 MiB 压力语料，并报告 `private_input_read=false`。随后，允许在本地运行的小型真实生命周期实践使用六个实际 adapter 完成了 1/1 group 和 30/30 逻辑记录，timeout 与 provider/网络调用均为 0。

## 重试与未来执行策略

在读取私有输入前，可以重复合成 runner 资格测试。未来 B2.2 锦标赛在资格与冻结后只有一次尝试。一旦产生任何未来 arm 输出，完整重启、选择性重试、缺失单元插补、timeout 修改、任务/oracle 修改和跨 runner 迁移全部禁止。基础设施失败会把 B2.2 关闭为无结果。

未来 holdout 必须包含 12 个新仓库身份和 48 条新 task/oracle 行，并排除全部 B2、B2.1、真实预检与资格来源。不得复用任何 B2 或 B2.1 经验单元。

## 冻结标识

- B2.2 规格摘要：`b22spec_adf15e2598e9f7c4`
- B2.2 源码包摘要：`b22src_05d40bb6c20414aa8ec0972d087e53750d0af635f0a57857ceddd864b4b1ea47`
- B2.2 协议报告摘要：`b22protocol_a84b309cf327a81325eb38451682beb8077cd93e2e9a49b3befc65fc4219e425`

## 下一项已授权工作

配置并资格验证强力一次性 runner。在汇总 runner 资格结果提交并通过远端 CI 前，不得创建或读取 B2.2 私有 holdout，也不得执行任何 treatment arm。
