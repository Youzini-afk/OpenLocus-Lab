# 产品栈对比 — B2.3 受限 Linux 长跑设计

日期：2026-07-15

状态：`product_bakeoff_b23_linux_longrun_protocol_ready_no_runner_qualification_no_holdout_no_result`

B2.3 保留 B2.2 作为未执行的强机设计检查点，并为专用、受配额限制的 Linux 容器建立新的执行环境契约。本检查点不编写或读取私有 holdout，不执行 treatment arm，不进行锦标赛评分，也不选择默认方案。

公开可执行表面为：

- [`product_bakeoff_b23_protocol.py`](../../eval/product_bakeoff_b23_protocol.py)
- [`product_bakeoff_b23_runner_qualification.py`](../../eval/product_bakeoff_b23_runner_qualification.py)
- [`product_bakeoff_b23_linux_bootstrap.sh`](../../scripts/product_bakeoff_b23_linux_bootstrap.sh)
- [`product-bakeoff-b23-linux.yml`](../../.github/workflows/product-bakeoff-b23-linux.yml)
- [`product_bakeoff_b23_protocol_report.json`](../../artifacts/product_bakeoff_b23_protocol/product_bakeoff_b23_protocol_report.json)

## 为什么 B2.3 是新检查点

B2.2 在没有注册或资格验证任何 runner 前冻结了 Windows x64 强机等级。直接改写这些门槛会抹掉审计链，因此 B2.3 在跨平台换行归一化后锁定 B2.2 报告的仓库字节，并锁定其语义摘要，只改变执行环境设计。不存在任何 B2.2 私有输入或 treatment 输出。

只要所有 arm 使用同一台合格机器，并在每个逻辑任务区组内保留冻结的完整 arm 轮换，机器较慢本身不会成为 treatment 混杂因素。服务商宿主机竞争仍是不可控干扰，因此性能结论只能限定在这一台合格机器内，禁止跨机器推广。

## 实验设计边界

独立单位仍为一个逻辑任务（`n=48`）。仓库仍是嵌套 cluster。cache state 与四次 repetition 仍是技术重复测量。每个任务区组都包含完整六 arm 轮换，继承随机完整区组与仓库 split-plot 日程。禁止按仓库、group 或 arm 跨机器分片。

不存在中途质量查看、arm 淘汰、timeout 修改、任务修改或根据结果决定的暂停。未来完整矩阵结束后只能进行一次最终分析。

## 受限 Linux runner 等级

资格器读取容器的实际有效配额，而不是相信宿主机级 `/proc` 总量，同时支持 cgroup v1 与 v2。执行工作负载前，容器必须满足：

- Linux x64；
- 有限且有效的 CPU 配额至少为 8 核；
- 有限的 cgroup 内存上限至少为 32 GiB，且该上限内至少有 24 GiB 可用；
- 没有启用的 swap；
- checkout 之外的非旋转本地块存储至少有 300 GiB 空闲；
- 准入采样期间 cgroup 空闲 CPU 使用率不超过 250 millicore；
- 文件句柄软上限至少为 65,535；
- Python 3.10 或更新版本、Git、Rust 1.95.0、Cargo 1.95.0 与 release OpenLocus 可用；
- 没有并发用户工作负载。

精确 cgroup 文件、硬件信息、挂载源、路径、runner 名称与机器标识只保留在私有回执中。

## I/O 与持续资格测试

I/O 门禁写入 512 MiB，执行 `fsync`，重新读取并校验 hash。顺序写入与读取速度都必须至少达到 150 MiB/s，精确观测值保持私有。

profile 与 I/O 门禁通过后，资格器确定性生成一个公开合成 TypeScript 仓库：10,000 个文件、恰好 72 MiB 可见源码。随后使用全部六个 adapter、继承的 copy/index/query/support 生命周期与 arm 轮换，连续执行三个真实 split-plot group。每个生命周期阶段使用预先声明的 600 秒 timeout，整个压力门禁上限为六小时。

通过条件为 3/3 group、90/90 逻辑记录、全部正常记录 accepted、timeout 为 0、terminal support 为 0、父收据错误为 0、provider/网络调用为 0。

压力门禁结束后，资格器会再次采集 runner profile。CPU 与内存限制、挂载标识、工具版本、文件句柄限制及 release OpenLocus 二进制摘要必须保持稳定，而且所有容量门禁仍须通过。复检失败或任一稳定字段漂移都会 fail closed。私有回执与公开汇总会作为新原子文件写入每次尝试独有的资格目录；已有输出永不覆盖。

## 资格测试与未来锦标赛

公开契约检查使用 GitHub-hosted Linux。持续资格测试是一个经过人工审批的手动作业，只路由到受限 Linux 机器上的一次性 GitHub runner 注册。该单一 job 完成后注销注册，机器随后不再连接 GitHub。

未来私有锦标赛不会作为 GitHub Actions job 运行。它将作为一个独立进程，在 `screen` 或 `nohup` 下跨 SSH 断线持续运行，因为长时间确认性执行不能依赖会过期的 workflow token。在 runner 资格汇总提交并远端变绿前，未来 launcher 与 holdout 均未获授权。

一旦未来产生任何 arm 输出，进程或机器重启都会把 B2.3 关闭为无结果。已完成 cell 不得重算；完整重启、选择性重试、缺失 cell 插补、跨 runner 迁移与 timeout 修改全部禁止。

## Bootstrap 与隐私

bootstrap 会把冻结的 Rust 1.95 工具链安装到调用者提供的私有数据盘根目录。Rustup 1.29.0 从官方归档下载，并使用其公开 SHA-256 文件校验。脚本不会注册 runner、克隆私有 holdout 或启动资格测试。

仓库是公开的。pull request 与 push 不能启动私有资格 job。job 只有只读仓库权限，不保留 checkout 凭据，不使用 Actions cache，把外部 action 固定到完整 commit SHA，并且只上传经过严格验证的汇总 JSON。GitHub 建议使用一次性 self-hosted runner，并把 runner 诊断日志保存在外部受限存储；参见 [self-hosted runner 参考](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)。

## 本地验证边界

本地工作站只允许运行编译、协议自检、故障注入、cgroup 解析器 fixture、公开报告验证、bootstrap 语法检查，以及此前已限制规模的单 group 生命周期微测试。512 MiB I/O 资格门禁、72 MiB 三 group 压力门禁与未来私有锦标赛只能在租用的 Linux runner 上运行。

## 冻结标识

- B2.3 规格摘要：`b23spec_b9281d2e323f8103`
- B2.3 源码包摘要：`b23src_f79e7ef4e18b71d61494075bdb0670647e26be87cdf3264195523d89d4094702`
- B2.3 协议报告摘要：`b23protocol_d238873449f91768aa85970a825be095b80bad9c0d44ac208955ccf8a118461c`

## 下一项已授权工作

bootstrap 受限 Linux 容器，配置受保护的一次性资格 runner 注册，并且只执行公开合成资格测试。在公开资格汇总提交并远端变绿前，不得创建或读取 B2.3 私有 holdout，也不得执行 treatment arm。
