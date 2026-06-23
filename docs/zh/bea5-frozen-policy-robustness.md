# BEA-5 Frozen-Policy Larger/Cross-Slice Robustness Smoke

日期：2026-06-21（BEA-5 冻结 BEA v0.3 策略的更大/跨切片稳健性 smoke，基于
全新 disjoint 更大 external 切片，使用 **recovery success-quota 采样**——
扫描全可用 Python benchmark frame，排除 BEA-2/3/4 先前窗口——私有
per-record SCORE JSONL 存于 `/tmp`，公开产物为 records 形态的仅聚合，含
robustness summary）

BEA-5 是冻结 BEA v0.3 策略的 **frozen-policy 稳健性 smoke**。它运行全新
disjoint 更大/跨切片 external 稳健性 smoke，测试 BEA-4 结论在任何 BEA v0.4
调优前是否稳定。**v0.3 算法和权重与 BEA-3/BEA-4 完全一致（冻结）；本阶段
是稳健性度量，不是新算法。**

Fixed-tail CI run `27984961904` 因数据集产出不足而未达配额：72 成功 / 126
尝试；ContextBench 53 成功；RepoQA 19 成功；所有失败为
`retrieval_failed`；`rrf_required_but_missing=0`；无隐私/schema/RRF 失败。
这**不是** BEA v0.3 算法失败，也**不是** BEA-5 结果声明。Recovery 采样修订
扫描全可用 Python frame，排除 BEA-2/3/4 窗口，使 RepoQA 能达到其 20 条最
小值。

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

## 全新 disjoint 更大切片（recovery success-quota 采样）

BEA-5 使用 **recovery success-quota 采样** 扫描全可用 Python benchmark
frame，排除强制 BEA-2/3/4 先前窗口。这取代了在 CI run `27984961904` 中
耗尽可用 Python 行的 fixed-tail 采样。

- `sampling_mode = "success_quota"`
- `sampling_protocol_version = "bea5_success_quota_disjoint_scan.v1"`
- `sampling_frame_policy =
  "full_available_python_excluding_bea2_bea3_bea4_windows"`
- `excluded_prior_windows_policy =
  "mandatory_bea2_bea3_bea4; bea0_bea1_best_effort_or_disclosed"`
- `bea0_bea1_windows_excluded = false`
- `bea0_bea1_overlap_policy =
  "not_excluded; disclosed; BEA-0 and BEA-1 were small early smoke slices,
  not frozen-v0.3 BEA-2 to BEA-4 windows"`
- ContextBench：扫描全可用 Python frame（offset 0，原始尝试上限 480），
  排除强制窗口 `[40,160)`（BEA-2 `[40,60)`、BEA-3 `[60,80)`、BEA-4
  `[80,160)`）。
- RepoQA：扫描全可用 Python frame（offset 0，原始尝试上限 240），排除
  强制窗口 `[20,80)`（BEA-2 `[20,30)`、BEA-3 `[30,40)`、BEA-4
  `[40,80)`）。
- Python-only 过滤保留。
- 稳定确定性顺序（每个 benchmark 内按原始 index 顺序）。
- **确定性交错**：以 round-robin 方式处理 ContextBench 和 RepoQA，使
  RepoQA 能在 ContextBench 达到 40 条配额后仍能达到其 20 条最小值。
- 仅在 `total successful >= 120 AND contextbench_successful >= 40 AND
  repoqa_successful >= 20` 后停止。
- `quota_reached` 布尔记录是否达到目标。
- 原始上限 480/240 为每 benchmark 最大尝试数。
- BEA-5 recovery 是固定协议：CLI/workflow 输入必须严格为 offset 0、cap
  480/240、budget 5、methods `bm25,regex,symbol`。较小 debug cap 会被拒绝，
  以避免 public requested fields 与实际采样 frame 漂移。

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
- `sampling_protocol_version = "bea5_success_quota_disjoint_scan.v1"`
- `sampling_frame_policy =
  "full_available_python_excluding_bea2_bea3_bea4_windows"`
- `excluded_prior_windows_policy =
  "mandatory_bea2_bea3_bea4; bea0_bea1_best_effort_or_disclosed"`
- `bea0_bea1_windows_excluded = false`
- `bea0_bea1_overlap_policy`：说明 BEA-0/1 没有作为 mandatory exclusion
  的聚合披露字符串
- `target_successful_records = 120`
- `raw_attempt_cap_contextbench = 480`
- `raw_attempt_cap_repoqa = 240`
- `records_attempted_total`：两个 benchmark 的总尝试数
- `records_excluded`：总排除数（= `records_failed`）
- `quota_reached` 布尔
- `contextbench_attempted/successful/excluded`
- `repoqa_attempted/successful/excluded`
- `contextbench_excluded_prior_window_count`：被强制 BEA-2/3/4 窗口排除的
  行数
- `repoqa_excluded_prior_window_count`：被强制 BEA-2/3/4 窗口排除的
  needle 数
- `contextbench_eligible_count`：排除过滤后的行数
- `repoqa_eligible_count`：排除过滤后的 needle 数
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
- `self_test_checks_total`：int（预期 435）
- `self_test_checks_passed`：int

禁止公开字段：`self_test_checks`、`self_test_details`、`self_test_list`、
`checks`、`check_list`。

## 验证

```text
python3 -m py_compile eval/bea5_frozen_policy_robustness.py  => PASS
python3 eval/bea5_frozen_policy_robustness.py --self-test  => PASS (435/435 checks)
python3 eval/bea5_frozen_policy_robustness.py \
  --out artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   sampling_mode=success_quota,
   sampling_protocol_version=bea5_success_quota_disjoint_scan.v1,
   sampling_frame_policy=full_available_python_excluding_bea2_bea3_bea4_windows,
   quota_reached=false, records_attempted_total=0,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea5=false, weights_tuned_during_bea5=false,
   self_test_checks_total=435, self_test_checks_passed=435)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 先前 CI run 与 recovery 采样

Fixed-tail CI run `27984961904` 因数据集产出不足而未达配额：
`records_successful=72`、`records_attempted_total=126`、
`contextbench_successful=53`、`repoqa_successful=19`、
`retrieval_failed=54`、`rrf_required_but_missing=0`。所有失败为
`retrieval_failed`（tail 切片上的 repo clone/materialization 失败）；无隐
私/schema/RRF 失败。这**不是** BEA v0.3 算法失败，也**不是** BEA-5 结果
声明。

Recovery 采样修订扫描全可用 Python frame，排除 BEA-2/3/4 先前窗口，使用
确定性交错使 RepoQA 能达到其 20 条最小值。完整 success-quota CI 运行
（原始尝试上限 480+240，目标 120 成功，每 benchmark 最小 40/20）待手动 CI。

## Caveats

- BEA-5 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法和权重与 BEA-3/BEA-4 完全一致（冻结）。
  `algorithm_changed_during_bea5=false`、
  `weights_tuned_during_bea5=false`（绑定）。
- Fixed-tail CI run `27984961904` 因数据集产出不足而未达配额（72 成功 /
  126 尝试），不是算法或 schema 失败。Recovery 采样修订扫描全可用 Python
  frame，排除 BEA-2/3/4 窗口，使用确定性交错。
- 完整 success-quota CI 运行（原始尝试上限 480+240，目标 120 成功，每
  benchmark 最小 40/20）待手动 CI；已提交 artifact 仅反映 no-network
  unavailable 状态。
- RRF arm 必需；CI 在 RRF 禁用/缺失时失败。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。
  BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 语义未修改。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。
  BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 语义未修改。
