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

## 全新 disjoint 更大切片（success-quota 采样）

BEA-5 使用 **success-quota 采样** 在更大 disjoint 原始扫描上运行。保持与
BEA-4 相同的 offset，但原始尝试上限更大，以在达到目标成功记录数时停止：

- ContextBench verified Python 行：offset 160、原始尝试上限 480（硬上限
  480）。
- RepoQA Python needle：offset 80、原始尝试上限 240（硬上限 240）。
- `target_successful_records = 120`。在两个 benchmark 中收集 120 条成功记录
  后停止评估。
- `sampling_mode = "success_quota"`。
- 要求 ContextBench + RepoQA 均有非零贡献；CI gate 要求
  `contextbench_successful >= 40` 且 `repoqa_successful >= 20`。
- `quota_reached` 布尔记录是否达到目标。
- 本地 smoke 可使用更小原始尝试上限以加速（如 3+2）；本地 debug artifact
  将如实显示 `status=partial` 和 `quota_reached=false`，直到手动 CI 达到
  目标。

此 success-quota 采样是在原始 disjoint 切片仅产出 72 条成功记录的 CI 失败
后的有界修复。它不是静默上限提升，也不是 No-Go；它显式采样更多原始尝试
以达到声明的 120 条成功记录目标。

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
- `benchmark_attempt_records`：natural key `(benchmark,)` — 每 benchmark
  的 attempted/successful/excluded 计数
- aggregate-only `private_score_manifest`：`{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`
- aggregate-only `private_attempt_manifest`：`{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`

无 dict mirror 如 `arm_metrics`、`deltas`、`aggregate_metrics` 或动态 method
map。

## Success-quota 公开字段

- `sampling_mode = "success_quota"`
- `target_successful_records = 120`
- `raw_attempt_cap_contextbench = 480`
- `raw_attempt_cap_repoqa = 240`
- `records_attempted_total`：两个 benchmark 的总尝试数
- `records_excluded`：总排除数（= `records_failed`）
- `quota_reached` 布尔
- `contextbench_attempted/successful/excluded`
- `repoqa_attempted/successful/excluded`
- `benchmark_attempt_records`：含每 benchmark 计数的 records 列表

## 私有轨迹

- 成功记录：私有 SCORE JSONL 行（`records_successful × 7 arm`）仅存于
  `/tmp`。
- 失败/排除尝试：单独的私有 attempt JSONL 仅存于 `/tmp`
  （`records_attempted_total` 行），每条尝试记录一行，含 `phase_run_id`、
  `benchmark`、`private_attempt_id`、`outcome_category`、`attempt_reason`。
  公开无原始 query/path/repo/gold。
- 公开 manifest 仅记录 count/hash/storage_class/path=false。

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
- `self_test_checks_total`：int（预期 385）
- `self_test_checks_passed`：int

禁止公开字段：`self_test_checks`、`self_test_details`、`self_test_list`、
`checks`、`check_list`。

## 验证

```text
python3 -m py_compile eval/bea5_frozen_policy_robustness.py  => PASS
python3 eval/bea5_frozen_policy_robustness.py --self-test  => PASS (385/385 checks)
python3 eval/bea5_frozen_policy_robustness.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 160 --contextbench-row-limit 3 \
  --repoqa-needle-offset 80 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol \
  --out artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json  => PASS
  (status: partial, 3 records successful,
   sampling_mode=success_quota, target_successful_records=120,
   quota_reached=false, records_attempted_total=5, records_excluded=2,
   contextbench_attempted=3, contextbench_successful=2, contextbench_excluded=1,
   repoqa_attempted=2, repoqa_successful=1, repoqa_excluded=1,
   private_score_manifest.record_count=21 (3×7 arms),
   private_attempt_manifest.record_count=5 (= records_attempted_total),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea5=false, weights_tuned_during_bea5=false,
   self_test_checks_total=385, self_test_checks_passed=385)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 真实有界本地 smoke 结果（2026-06-21，success-quota 修复）

有界本地 smoke（ContextBench offset 160 limit 3 + RepoQA offset 80
limit 2，budget=5，方法 bm25/regex/symbol）：这是一个小型本地 debug smoke，
`status=partial`，因为仅收集了 120 条目标成功记录中的 3 条。
`quota_reached=false`。`records_attempted_total=5`（3 ContextBench + 2
RepoQA），`records_successful=3`，`records_excluded=2`。
`contextbench_successful=2`，`repoqa_successful=1`。

`private_score_manifest.record_count=21`（3×7 arm），
`private_attempt_manifest.record_count=5`（= records_attempted_total），
`private_score_storage_class=tmp_private`，
`private_score_path_publicly_serialized=false`，
`algorithm_changed_during_bea5=false`，`weights_tuned_during_bea5=false`。

`benchmark_attempt_records`：
`contextbench: attempted=3, successful=2, excluded=1`；
`repoqa: attempted=2, successful=1, excluded=1`。

此本地 artifact 如实显示 success-quota 采样字段，不是 CI scale 结果。完整
success-quota CI 运行（原始尝试上限 480+240，目标 120 成功）待手动 CI；CI
将 fail-closed 除非 `records_successful >= 120`、`quota_reached=true`、
`contextbench_successful >= 40`、`repoqa_successful >= 20`、
`private_attempt_manifest.record_count == records_attempted_total`，以及
`private_score_manifest.record_count == records_successful × 7`。

## Caveats

- BEA-5 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法和权重与 BEA-3/BEA-4 完全一致（冻结）。
  `algorithm_changed_during_bea5=false`、
  `weights_tuned_during_bea5=false`（绑定）。
- 有界本地 smoke 使用 3+2 条记录以加速，如实显示 `status=partial`、
  `quota_reached=false`。完整 success-quota CI 运行（原始尝试上限 480+240，
  目标 120 成功）待手动 CI；已提交 artifact 仅反映本地 smoke。本地 debug
  可使用小上限，但绝不能记为 CI scale 证据。
- Success-quota 采样是在原始 disjoint 切片仅产出 72 条成功记录的 CI 失败
  后的显式有界修复。它不是静默上限提升，也不是 No-Go。
- RRF arm 必需；CI 在 RRF 禁用/缺失时失败。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。
  BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 语义未修改。
