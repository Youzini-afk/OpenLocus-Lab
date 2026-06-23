# BEA-5 冻结策略稳健性结果

日期：2026-06-22

状态：固定协议 BEA-5 success-quota run 已完成，结果是**严格 No-Go / near-miss**，不是 pass。

BEA-5 将 BEA v0.3 按 BEA-3/BEA-4 完全冻结，在更大的 disjoint external scan 上做显式 success-quota sampling。它**没有**修改 BEA v0.3 的权重或选择逻辑。

## 结果

固定协议 CI run `28003522632` fail-closed，因为它只得到 `records_successful=119`，比预声明的 `target_successful_records=120` 少 1 条。

本地 exact-protocol rerun 复现了 CI 结果，并生成已提交的 aggregate artifact：

- `status = partial`
- `quota_reached = false`
- `records_successful = 119`
- `records_attempted_total = 186`
- `records_excluded = 67`
- `contextbench_successful = 82`
- `repoqa_successful = 37`
- `private_score_manifest.record_count = 833`（`119 × 7 arms`）
- `private_attempt_manifest.record_count = 186`
- `failure_category_counts.retrieval_failed = 67`
- `failure_category_counts.rrf_required_but_missing = 0`
- `provider_calls = 0`
- `forbidden_scan.status = pass`

解释：BEA-5 没有满足严格 120-record scale gate。这是 near-miss dataset-yield / retrieval-yield No-Go，不是 BEA-5 pass，也不是 performance claim。

## 冻结策略

冻结 treatment arm：`bea_v0_3_anchor_span_latency`。

冻结权重与 BEA-3/BEA-4 一致：

- `anchor = 0.35`
- `span_tight = 0.15`
- `anchor_file_support = 0.10`
- `weak_support_penalty = -0.20`
- `early_stop_margin = 0.05`

绑定 flag：

- `algorithm_changed_during_bea5 = false`
- `weights_tuned_during_bea5 = false`

## 固定采样协议

- `sampling_mode = success_quota`
- `sampling_protocol_version = bea5_success_quota_disjoint_scan.v1`
- `sampling_frame_policy = full_available_python_excluding_bea2_bea3_bea4_windows`
- `target_successful_records = 120`
- ContextBench raw cap：480
- RepoQA raw cap：240
- 最低成功记录：ContextBench >= 40，RepoQA >= 20
- Methods：`bm25,regex,symbol`
- Budget：5
- RRF same-budget arm 必需
- 排除 BEA-2/3/4 窗口
- BEA-0/1 窗口不是 mandatory exclusion，但通过 `bea0_bea1_windows_excluded=false` 披露

早期 fixed-tail run `27984961904` 已被 supersede。它只得到 72 条成功记录，原因是 tail slice 中可检索的 Python rows/needles 产出不足。

## Arms

Artifact 包含 7 个固定 arm：

- `bea_v0_3_anchor_span_latency`
- `bea_v0_2_diversity_risk`
- `bea_v0`
- `bm25_prefix_same_budget`
- `agreement_only_same_budget`
- `rrf_same_budget`
- `seeded_random_same_budget`

不包含 BEA-3 ablations，也不包含 v0.31/v0.32 式权重微调。

## 119-record artifact 的关键 delta

`bea_v0_3_anchor_span_latency` vs `bea_v0_2_diversity_risk`：

- `file_recall@10`：+0.000000
- `mrr`：+0.000000
- `success_rate`：+0.000000
- `span_f0.5@10`：+0.004953
- `quality_per_latency`：+0.002853
- `latency_seconds`：+0.001086

`bea_v0_3_anchor_span_latency` vs `bm25_prefix_same_budget` 和 `agreement_only_same_budget`：

- `file_recall@10`：+0.184874
- `mrr`：+0.164566
- `success_rate`：+0.184874
- `span_f0.5@10`：+0.008345
- `quality_per_latency`：+0.059839
- `latency_seconds`：+3.818262

`bea_v0_3_anchor_span_latency` vs `rrf_same_budget`：

- `file_recall@10`：+0.184874
- `mrr`：+0.164566
- `success_rate`：+0.184874
- `span_f0.5@10`：+0.008345
- `quality_per_latency`：-0.033073
- `latency_seconds`：+1.871766

解释：在 119 条成功记录上，v0.3 在主要 recall/MRR/success 指标上仍与 v0.2 基本打平；相对 BM25/agreement/RRF 的 file/MRR/success 为正，但仍有 latency/quality-per-latency trade-off。由于严格 quota 少 1 条，本结果只能作为 failure decomposition 的 near-miss 证据，不能当作完成的 BEA-5 scale pass。

## 公开 artifact 合同

公开 artifact 是 records-only 且 aggregate-only：

- `benchmark_arm_metric_records`
- `delta_records`
- `win_tie_loss_records`
- `worst_slice_records`
- `mechanism_summary_records`
- `robustness_summary_records`
- `benchmark_attempt_records`
- aggregate-only `private_score_manifest`
- aggregate-only `private_attempt_manifest`

它不公开 raw queries、repo IDs、paths、commits、spans、snippets、prompts、provider payloads、gold labels、per-record SCORE rows 或 private attempt rows。

Counts-only self-test fields：

- `self_test_checks_total = 435`
- `self_test_checks_passed = 435`

## 结论

BEA-5 没有通过预声明的 120-record quota。正确下一步不是再改 sampling，也不是 v0.31 权重微调。119-record near-miss artifact 应进入 BEA-4/BEA-5 per-record failure decomposition，重点判断 BEA 的剩余问题来自 candidate-pool yield、span quality、budget allocation，还是缺少 target-support complementarity 建模。

## Claim boundary

BEA-5 仅是 eval/diagnostic。它不是 benchmark result、leaderboard result、performance claim、method-winner claim、calibration claim、promotion、default-policy 变更、runtime/retriever/backend/EvidenceCore 语义变更，也不是 downstream-value proof。
