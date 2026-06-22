# BEA-5 Frozen-Policy Larger/Cross-Slice Robustness Smoke

日期：2026-06-21（BEA-5 冻结 BEA v0.3 策略的更大/跨切片稳健性 smoke，基于
全新 disjoint 更大 external 切片——ContextBench verified Python 行 offset
160 + RepoQA Python needle offset 80——私有 per-record SCORE JSONL 存于
`/tmp`，公开产物为 records 形态的仅聚合，含 robustness summary）

BEA-5 是冻结 BEA v0.3 策略的 **frozen-policy 稳健性 smoke**。它在全新
disjoint 更大/跨切片 external 稳健性 smoke 上运行（ContextBench verified
Python 行 offset 160 limit 240，RepoQA Python needle offset 80 limit 120），
测试 BEA-4 结论在任何 BEA v0.4 调优前是否稳定。**v0.3 算法和权重与
BEA-3/BEA-4 完全一致（冻结）；本阶段是稳健性度量，不是新算法。**

BEA-5 明确**不是** benchmark 结果，**不是** leaderboard 条目，**不是**
性能声明，**不是** method-winner 声明，**不是** calibration 声明，**不是**
promotion，**不是** default/policy 变更，**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更，且**不是**算法变更。
`algorithm_changed_during_bea5` 和 `weights_tuned_during_bea5` flag 均为
`false`（绑定）。

> `claim_level = bea_v03_frozen_policy_robustness_smoke_only`。所有 no-claim
> / no-runtime-change flag 均为 false。

## 冻结策略

`bea_v0_3_anchor_span_latency` 与 BEA-3/BEA-4 完全相同（冻结权重：
anchor=0.35、span_tight=0.15、anchor_file_support=0.10、
weak_support_penalty=-0.20、early_stop_margin=0.05）。BEA-5 期间无算法/权重
变更。

## 必需 arm（7 个；RRF 必需，从不可选）

- `bea_v0_3_anchor_span_latency`（treatment）
- `bea_v0_2_diversity_risk`
- `bea_v0`
- `bm25_prefix_same_budget`
- `agreement_only_same_budget`
- `rrf_same_budget`（必需；CI 在 RRF 禁用/缺失时失败）
- `seeded_random_same_budget`

BEA-3 的消融（`bea_v0_3_no_anchor`、`bea_v0_3_no_early_stop`）**不**在
BEA-5 固定 arm 中。BEA-5 无 `--enable-rrf-baseline` CLI flag；RRF 始终必需。

## 全新 disjoint 更大切片

- ContextBench verified Python 行：offset 160、limit 240（硬上限 240）。
- RepoQA Python needle：offset 80、limit 120（硬上限 120）。
- 本地 smoke 可使用更小边界以加速（如 2+2）；CI 要求 >=120 records_successful
  且 ContextBench + RepoQA 均有非零贡献。

## 公开 artifact 形态

仅 records（无动态 arm dict）。所有 record 表必须按其 natural key 唯一：

- `benchmark_arm_metric_records`：natural key `(benchmark, arm, metric)`
- `delta_records`：natural key `(baseline_arm, treatment_arm, metric)`
- `win_tie_loss_records`：natural key `(baseline_arm, treatment_arm, metric)`
- `worst_slice_records`：natural key `(benchmark, arm, query_length_bucket,
  candidate_pool_size_bucket, budget_exhaustion_bucket, file_kind_mix_bucket,
  method_agreement_bucket, rank_gap_bucket)`
- `mechanism_summary_records`：natural key `(mechanism_field,)`
- `robustness_summary_records`：natural key `(robustness_field,)`
- aggregate-only `private_score_manifest`：`{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`

无 dict mirror 如 `arm_metrics`、`deltas`、`aggregate_metrics` 或动态 method
map。

## Robustness summary 字段

每条 record：`{robustness_field, value, record_count}`。

- `cross_slice_v03_vs_v02_mrr_delta`：v0.3-v0.2 跨 paired record 的平均 mrr delta
- `cross_slice_v03_vs_v0_mrr_delta`
- `cross_slice_v03_vs_v02_file_recall_delta`
- `cross_slice_v03_vs_v0_file_recall_delta`
- `v03_vs_v02_sign_stability_mrr`：paired record 中 v0.3 >= v0.2 on mrr 的比例
- `v03_vs_v0_sign_stability_mrr`
- `v03_vs_v02_sign_stability_file_recall`
- `v03_vs_v0_sign_stability_file_recall`
- `v03_quality_per_latency_mean`
- `rrf_quality_per_latency_mean`
- `v03_vs_rrf_quality_per_latency_delta`
- `worst_slice_cluster_<bucket_field>_<bucket_value>`：每个 bucket 值的 worst slice 计数（覆盖 6 个非 benchmark bucket 字段）

## Worst-slice bucket 标签（固定公开聚合）

仅这 7 个固定公开聚合 bucket 标签；无 row IDs、repos、paths、commits、
queries、labels、candidate lists 或 gold/source snippets：

- `benchmark`：contextbench | repoqa
- `query_length_bucket`：short | medium | long | empty
- `candidate_pool_size_bucket`：small | medium | large | empty
- `budget_exhaustion_bucket`：full | partial | empty
- `file_kind_mix_bucket`：pure_python | mixed | non_python | empty
- `method_agreement_bucket`：high | medium | low | empty
- `rank_gap_bucket`：narrow | medium | wide | empty

## Counts-only self-test 摘要

公开 artifact 仅记录计数，不记录 self-test 详情列表：

- `self_test_passed`：bool
- `self_test_checks_total`：int（预期 285）
- `self_test_checks_passed`：int

禁止公开字段：`self_test_checks`、`self_test_details`、`self_test_list`、
`checks`、`check_list`。

## 验证

```text
python3 -m py_compile eval/bea5_frozen_policy_robustness.py  => PASS
python3 eval/bea5_frozen_policy_robustness.py --self-test  => PASS (285/285 checks)
python3 eval/bea5_frozen_policy_robustness.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 160 --contextbench-row-limit 2 \
  --repoqa-needle-offset 81 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol \
  --out artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json  => PASS
  (status: bea5_frozen_policy_robustness_pass, 4 records successful,
   private_score_manifest.record_count=28 (4×7 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea5=false, weights_tuned_during_bea5=false,
   self_test_checks_total=285, self_test_checks_passed=285)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 真实有界本地 smoke 结果（2026-06-21）

有界本地 smoke（ContextBench offset 160 limit 2 + RepoQA offset 81
limit 2，budget=5，方法 bm25/regex/symbol）：4 条记录成功，
`paired_exclusion_count=0`，forbidden scan pass，`provider_calls=0`，
`private_score_manifest.record_count=28`（4×7 arm），
`private_score_storage_class=tmp_private`，
`private_score_path_publicly_serialized=false`，
`algorithm_changed_during_bea5=false`，`weights_tuned_during_bea5=false`。

Win/tie/loss（v0.3 vs v0，n=4）：file_recall@10 win=2 tie=2 loss=0；mrr
win=2 tie=1 loss=1；span_f0.5@10 win=2 tie=2 loss=0；success_rate win=2
tie=2 loss=0。

Delta records（v0.3 vs 控制，mrr）：vs `bea_v0_2_diversity_risk` delta=0.0
（v0.3 与 v0.2 在 mrr 上持平）；vs `bea_v0`/`agreement_only`/`bm25_prefix`/
`rrf_same_budget` mrr delta=+0.070833；vs `seeded_random` mrr delta=+0.1125。

Robustness summary（精选）：`cross_slice_v03_vs_v02_mrr_delta=0.0`、
`cross_slice_v03_vs_v0_mrr_delta=0.070833`、
`cross_slice_v03_vs_v0_file_recall_delta=0.5`、
`v03_vs_v02_sign_stability_mrr=1.0`、
`v03_vs_v0_sign_stability_mrr=0.75`、
`v03_quality_per_latency_mean=0.058183`、
`rrf_quality_per_latency_mean=0.011407`、
`v03_vs_rrf_quality_per_latency_delta=0.046776`。

公开 record 表：140 `benchmark_arm_metric_records`、60 `delta_records`、
24 `win_tie_loss_records`、22 `worst_slice_records`、6
`mechanism_summary_records`、20 `robustness_summary_records`。所有 record 表
均通过 natural key 唯一性验证。

这是诚实的 smoke 级稳健性结果，不是 method-winner、calibration、default、
promotion、runtime/retriever/EvidenceCore 或 downstream-agent-value 声明。
完整 scale 切片（ContextBench 240 + RepoQA 120）待手动 CI 运行；已提交
artifact 仅反映本地 smoke。

## Caveats

- BEA-5 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法和权重与 BEA-3/BEA-4 完全一致（冻结）。
  `algorithm_changed_during_bea5=false`、
  `weights_tuned_during_bea5=false`（绑定）。
- 有界本地 smoke 使用 2+2 条记录以加速。完整稳健性切片（ContextBench
  240 + RepoQA 120）待手动 CI 运行；已提交 artifact 仅反映本地 smoke。
  本地 debug 可使用 2+2，但绝不能记为 CI scale 证据。
- RRF arm 必需；CI 在 RRF 禁用/缺失时失败。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。
  BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 语义未修改。
