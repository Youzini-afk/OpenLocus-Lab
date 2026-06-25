# BEA-v1-P4L：锁定非 Python P4 调度器验证

日期：2026-06-25。BEA-v1-P4L 是在 BEA-v1-P4K 结果（checkpoint `dccfb64`，CI
`28151914531`，`cross_source_locked_reservoir_ready_for_locked_p4_validation_design`，
锁定非 Python 分母 272）之后进行的有限**调度器验证阶段**。它验证 frozen
BEA-v1-P4 检索动作调度器是否能从原始同 frame Python 分母泛化到 P4K 锁定的、
all-prior-disjoint 非 Python 跨来源蓄水池。

这是仅调度器验证阶段。它**不是** P5、不是 BEA-v1-A、不是 selector/reranker
工作、不是 runtime/default 提升、不是 method-winner 主张、不是参数调优、不是
阈值搜索、不是新 arm、不是 broad retrieval 扩展、不是在旧 Python 分母上的
frozen P4 重跑、也不是 latency-in-relevance 评分。

> `claim_level = bea_v1_p4l_locked_non_python_scheduler_validation_only`。
> `provider_calls_made=false`、`latency_in_candidate_relevance=false`、
> `selector_or_reranker_executed=false`、`p5_authorized=false`、
> `v1_a_authorized=false`、`frozen_p4_rerun_authorized=false`、
> `future_locked_p4_validation_authorized=false`、`locked_p4_validation_authorized=false`、
> `parameter_tuning_executed=false`、`threshold_search_executed=false`、
> `new_arms_added=false` 均为 binding。

## 固定分母

P4K 锁定蓄水池完全一致：

- P4K 结果 checkpoint：`dccfb64`
- P4K CI 运行：`28151914531`
- 必需的重建计数：P4H 73/73、P4I 73/73、P4J 333/333（61 Python + 272 非
  Python）、P4J 与 P4H/P4I 重叠：61、锁定分母：272，全部非 Python。

实现在运行任何调度器臂之前重建锁定分母。它必须复现完整 P4J/P4K split（333
total、61 Python、272 non-Python）以及 locked non-Python denominator（272）。如果
这些计数不匹配，状态为 `no_go_p4l_locked_denominator_unavailable` 或
`fail_schema_contract`；它**不**能静默更改分母。

## 允许的 frozen 臂

仅运行这 4 个臂，定义 frozen 自先前已提交的 P2/P3/P4 代码：

1. `baseline_current_candidate_pool`（depth=1，无 query anchor）
2. `p2_depth_only_reference`（depth=4，无 query anchor）
3. `p3_constrained_depth_policy_reference`（约束 depth 策略）
4. `p4_latency_aware_action_scheduler_frozen`（frozen P4 调度器）

不允许新臂、selector、reranker、评分策略、参数搜索、阈值搜索或权重调优。

## Frozen 阈值（无事后调优）

- P4 retained-gain ratio ≥ 0.75（P4 相对 baseline 的提升 / P2 相对 baseline
  的提升）
- P4 延迟比率 vs P3 ≤ 2.0
- P4 延迟降低 vs P3 ≥ 0.10
- P4 池增长比率 ≤ 4.0
- P4 treatment 硬上限违规 = 0；reference arms 的硬上限违规只报告，不决定 P4 treatment gate

## 状态

- `bea_v1_p4l_locked_non_python_scheduler_validation_pass` — 精确分母重建
  （333/61/272，locked non-Python denominator 272）、调度器臂已执行、P4 相对
  baseline 提升 reach、P4 保留 ≥ 0.75 的 P2 reach 增益、P4 延迟低于 frozen P3
  阈值、池增长在 frozen 上限内、P4 treatment 硬上限违规为零、子组 guard 通过。
  Reference-arm 硬上限违规会报告，但不决定 P4 treatment gate。
- `no_go_p4l_locked_non_python_scheduler_validation_failed` — 分母精确但 P4 未通过
  一个或多个 frozen 门。
- `no_go_p4l_locked_denominator_unavailable` — 锁定分母无法精确重建为 272。
- `unavailable_with_reason` — 默认无网络 artifact（诚实，非 pass）。
- `fail_schema_contract` / `fail_forbidden_scan` — 隐私/schema/provenance 失败。
  任何 `fail_*` 状态对网络-enabled 的真实运行都不是 CI-valid。

## 公开 artifact 契约

必需的 aggregate-only 记录表（records-only；无动态 dict）：

- `source_run_records`
- `arm_metrics_records`
- `subgroup_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

`self_test_checks_total` 和 `self_test_checks_passed` 仅计数（int）；不存在
`self_test_checks` 列表字段。不序列化任何私有 row ID、raw key、仓库 URL、
base commit、query、候选路径、gold 路径、snippet 或 provider payload。私有
per-record 臂结果和调度器 trace 仅写入 `/tmp`，`path_publicly_serialized=false`。

## Workflow

手动 workflow
`bea-v1-p4l-locked-non-python-scheduler-validation.yml` 仅通过
`workflow_dispatch` 运行，接受 `enable_external_benchmark_network`。它构建
OpenLocus release CLI，运行 self-test，在 `/tmp` 下重新生成 FD1 private
decomposition，验证 239/86040 replay，重建 P4K 锁定非 Python 分母，运行 4 个
frozen 调度器臂，fail-closed 验证报告，并上传 aggregate 报告。在验证器之前上传
prevalidation artifact（始终，用于诊断）而不影响最终 fail-closed 门。私有目录使用
`/tmp`，不使用 `$RUNNER_TEMP`。

## 本地验证

```text
python3 -m py_compile eval/bea_v1_p4l_locked_non_python_scheduler_validation.py  => PASS
python3 eval/bea_v1_p4l_locked_non_python_scheduler_validation.py --self-test  => PASS (122/122 checks)
python3 eval/bea_v1_p4l_locked_non_python_scheduler_validation.py \
  --out artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json  => PASS
  (默认无网络 status: unavailable_with_reason,
   forbidden_scan=pass, locked_denominator_count=0,
   scheduler_arms_executed=false,
   self_test_checks_total=122, self_test_checks_passed=122)
```

## CI 结果

Manual network-enabled CI run `28184096209` 在 heartbeat workflow patch `e98839b`
之后绿色完成（2h33m08s）。早期尝试均被 supersede：

- `28160078060` 暴露了一个 false No-Go：reference-arm hard-cap violations 被错误
  加到 P4 treatment gate。
- `28166304912` 在修正 classifier 后，将 live reconstruction drift 正确报告为
  denominator No-Go。
- `28175852713` 在 P4L 前置阶段失败，因为 FD1 replay 只重建 215/239 groups。
- `28178712989` 成功重新生成 FD1，但 evaluator step 没有产出 artifact；因此
  `e98839b` 加入 CI heartbeat wrapper，未改变 validator。

最终 status：`bea_v1_p4l_locked_non_python_scheduler_validation_pass`。

最终 artifact 精确重建 P4J/P4K（`333/61/272`）以及 locked non-Python denominator
（`272`）。所有 scheduler arms 均执行，private arm outcomes 仅写入 `/tmp`
（`record_count=1088`）。公开聚合 metrics：

| Arm | Reach | Mean pool | Mean latency | Hard-cap violations |
|---|---:|---:|---:|---:|
| baseline current pool | 0/272 | 13.871324 | 2.059338s | 0 |
| P2 depth-only reference | 55/272 | 53.084559 | 1.863294s | 3 |
| P3 constrained reference | 55/272 | 31.058824 | 3.626279s | 0 |
| frozen P4 latency-aware scheduler | 52/272 | 30.194853 | 2.381607s | 0 |

P4 保留 P2 depth-only reach gain 的 `0.945455`，相对 baseline 提升 52 条 reach，
相对 P3 降低 latency `0.343237`（`p4_vs_p3_latency_ratio=0.656763`），pool growth
在 cap 内（`2.176782`），并且 P4-treatment hard-cap violations 为 0。P2 上的 3 次
hard-cap violations 只是 reference-arm diagnostics。`forbidden_scan.status=pass`。

## 注意事项

- P4L 是调度器验证阶段。它不是 benchmark/leaderboard、default-policy、
  method-winner、runtime-promotion、downstream-value、P5、BEA-v1-A、检索扩展、
  selector/reranker、参数调优、阈值搜索、新臂或 runtime/default 提升授权主张。
- pass 状态表示本 P4L locked scheduler validation 已在 272-record non-Python
  denominator 上运行并通过 frozen gates。它**不**授权 P5、BEA-v1-A、runtime 提升、
  method-winner 主张、broad retrieval 扩展、selector/reranker 执行、frozen P4 rerun
  或任何未来 locked-P4 promotion/default step。
- frozen 阈值来自先前 P4；无事后调优。
- Gold/private label 仅用于评估/scoring 文件缺失。
