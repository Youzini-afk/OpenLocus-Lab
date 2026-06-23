# BEA-5 Frozen-Policy Robustness Result

Date: 2026-06-22

Status: fixed-protocol BEA-5 success-quota run completed as a **strict No-Go / near-miss**, not a pass.

BEA-5 froze BEA v0.3 exactly as in BEA-3/BEA-4 and tested a larger disjoint external scan with explicit success-quota sampling. It did **not** change BEA v0.3 weights or selection logic.

## Result

The fixed-protocol CI run `28003522632` failed closed because it produced `records_successful=119`, one short of the required `target_successful_records=120`.

A local exact-protocol rerun reproduced the CI result and generated the committed aggregate artifact:

- `status = partial`
- `quota_reached = false`
- `records_successful = 119`
- `records_attempted_total = 186`
- `records_excluded = 67`
- `contextbench_successful = 82`
- `repoqa_successful = 37`
- `private_score_manifest.record_count = 833` (`119 × 7 arms`)
- `private_attempt_manifest.record_count = 186`
- `failure_category_counts.retrieval_failed = 67`
- `failure_category_counts.rrf_required_but_missing = 0`
- `provider_calls = 0`
- `forbidden_scan.status = pass`

Interpretation: BEA-5 did not satisfy the strict 120-record scale gate. The result is a near-miss dataset-yield / retrieval-yield No-Go, not a BEA-5 pass and not a performance claim.

## Fixed policy

Frozen treatment arm: `bea_v0_3_anchor_span_latency`.

Frozen weights match BEA-3/BEA-4:

- `anchor = 0.35`
- `span_tight = 0.15`
- `anchor_file_support = 0.10`
- `weak_support_penalty = -0.20`
- `early_stop_margin = 0.05`

Binding flags:

- `algorithm_changed_during_bea5 = false`
- `weights_tuned_during_bea5 = false`

## Fixed sampling protocol

- `sampling_mode = success_quota`
- `sampling_protocol_version = bea5_success_quota_disjoint_scan.v1`
- `sampling_frame_policy = full_available_python_excluding_bea2_bea3_bea4_windows`
- `target_successful_records = 120`
- ContextBench raw cap: 480
- RepoQA raw cap: 240
- Minimum successful records: ContextBench >= 40, RepoQA >= 20
- Methods: `bm25,regex,symbol`
- Budget: 5
- RRF same-budget arm required
- BEA-2/3/4 windows excluded
- BEA-0/1 windows not mandatory exclusions, but disclosed via `bea0_bea1_windows_excluded=false`

Earlier fixed-tail run `27984961904` is superseded. It produced only 72 successful records because the tail slice had insufficient retrievable Python rows/needles.

## Arms

The artifact includes 7 fixed arms:

- `bea_v0_3_anchor_span_latency`
- `bea_v0_2_diversity_risk`
- `bea_v0`
- `bm25_prefix_same_budget`
- `agreement_only_same_budget`
- `rrf_same_budget`
- `seeded_random_same_budget`

No BEA-3 ablations and no v0.31/v0.32-style weight tweaks are included.

## Selected deltas from the 119-record artifact

`bea_v0_3_anchor_span_latency` vs `bea_v0_2_diversity_risk`:

- `file_recall@10`: +0.000000
- `mrr`: +0.000000
- `success_rate`: +0.000000
- `span_f0.5@10`: +0.004953
- `quality_per_latency`: +0.002853
- `latency_seconds`: +0.001086

`bea_v0_3_anchor_span_latency` vs `bm25_prefix_same_budget` and `agreement_only_same_budget`:

- `file_recall@10`: +0.184874
- `mrr`: +0.164566
- `success_rate`: +0.184874
- `span_f0.5@10`: +0.008345
- `quality_per_latency`: +0.059839
- `latency_seconds`: +3.818262

`bea_v0_3_anchor_span_latency` vs `rrf_same_budget`:

- `file_recall@10`: +0.184874
- `mrr`: +0.164566
- `success_rate`: +0.184874
- `span_f0.5@10`: +0.008345
- `quality_per_latency`: -0.033073
- `latency_seconds`: +1.871766

Interpretation: on the 119 successful records, v0.3 remains effectively tied with v0.2 on primary recall/MRR/success metrics, improves over BM25/agreement/RRF on file/MRR/success, but still carries latency/quality-per-latency trade-offs. Because the strict quota missed by one record, this remains near-miss evidence for failure decomposition, not a completed BEA-5 scale pass.

## Public artifact contract

The public artifact is records-only and aggregate-only:

- `benchmark_arm_metric_records`
- `delta_records`
- `win_tie_loss_records`
- `worst_slice_records`
- `mechanism_summary_records`
- `robustness_summary_records`
- `benchmark_attempt_records`
- aggregate-only `private_score_manifest`
- aggregate-only `private_attempt_manifest`

It does not publish raw queries, repo IDs, paths, commits, spans, snippets, prompts, provider payloads, gold labels, per-record SCORE rows, or private attempt rows.

Counts-only self-test fields:

- `self_test_checks_total = 435`
- `self_test_checks_passed = 435`

## Conclusion

BEA-5 did not pass the predeclared 120-record quota. The correct next step is not another sampling tweak and not a v0.31 weight adjustment. The 119-record near-miss artifact should feed BEA-4/BEA-5 per-record failure decomposition, especially to determine whether BEA's remaining gap is candidate-pool yield, span quality, budget allocation, or missing target-support complementarity.

## Claim boundary

BEA-5 is eval/diagnostic only. It is not a benchmark result, leaderboard result, performance claim, method-winner claim, calibration claim, promotion, default-policy change, runtime/retriever/backend/EvidenceCore semantic change, or downstream-value proof.
