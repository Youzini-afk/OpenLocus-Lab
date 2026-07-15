# 产品栈对比 — B2.3 Runner 资格结果

日期：2026-07-15

状态：`product_bakeoff_b23_runner_qualified_no_private_input_read`

受限 Linux runner 已在下列精确源码包上通过冻结的 B2.3 公开合成资格测试。本检查点使同一机器实例取得后续 B2.3 工作资格，并且只授权下一项私有 holdout 编写阶段。它不授权锦标赛执行，不公开硬件身份，也不选择产品栈。

经过验证的公开汇总为 [`product_bakeoff_b23_runner_qualification.json`](../../artifacts/product_bakeoff_b23_runner_qualification/product_bakeoff_b23_runner_qualification.json)，其 SHA-256 为 `b22229479ed3744321a4a6b09e454d06dc873f08d366069c738e6109c72a7e95`。

## 冻结结果

- profile 准入通过；
- 压力测试后的 profile 复检已执行并通过；
- 512 MiB 写入、`fsync`、重读与 hash 校验 I/O 门禁通过；
- 3/3 个持续 group 完成；
- 90/90 个逻辑记录均为正常且 accepted；
- timeout、terminal support、父回执错误及 provider/网络调用计数全部为零；
- 满足六小时 wall-clock 上限；
- 未读取任何私有输入。

精确吞吐量、cgroup 观测、硬件身份、挂载源、路径及 runner 名称只保留在私有回执中。

## 审计链

- B2.3 规格摘要：`b23spec_b9281d2e323f8103`
- B2.3 源码包摘要：`b23src_c674402a50183c6d3bb6eec0d855900dbfe7822929eb9656965077f9336057eb`
- 资格摘要：`b23qual_0ba839c5e02c96a7c8c879532ad354f19a6405cd6dd3f9885baa2ea3c1a499a1`
- 最终受保护 CI：[29415970142](https://github.com/Youzini-afk/OpenLocus-Lab/actions/runs/29415970142)

较早的一次运行已经通过资格与汇总验证门禁，但仅在经过服务商私有 CA 上传 artifact 时失败。workflow 随后改为在不关闭 TLS 校验的前提下信任 Linux 系统 CA 证书包，源码包重新冻结，并从头重跑完整资格测试。最终运行的全部 job step 均通过，经过验证的汇总成功上传，一次性 runner 注册也已自动移除。

## 授权范围

`future_holdout_authoring_authorized=true` 只允许下一阶段按照预注册排除规则编写并冻结新的 12 仓库、48 任务私有 holdout。`future_tournament_execution_authorized=false` 仍然具有约束力。在 holdout 完成独立审计且后续检查点明确授权一次性锦标赛前，不得执行任何 treatment arm。
