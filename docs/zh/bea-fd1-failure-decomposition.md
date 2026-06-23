# BEA-FD1: BEA-4/5 冻结重放失败分解

日期：2026-06-22（BEA-FD1 失败分解——通过子进程精确重放冻结 BEA-4 和 BEA-5
协议，解析私有 SCORE JSONL 文件，将 v0.3 treatment 结果分类到固定 12 类别
enum，发布 records-only 聚合分解表）

BEA-FD1 精确重放两个最终协议：BEA-4（CI `27957586271`，预期 120/840）和
BEA-5（CI `28003522632`，预期 119/833）。不更改 BEA v0.3、采样、gate、arm
或权重。不实现 v0.4。

> `claim_level = bea_fd1_failure_decomposition_smoke_only`。所有 no-claim /
> no-runtime-change flag 为 false。

## 重放协议

网络启用的 BEA-FD1 通过子进程运行 `eval/bea4_external_scale_smoke.py` 和
`eval/bea5_frozen_policy_robustness.py`，使用精确协议输入和
`--private-score-dir` 指向 BEA-FD1 临时私有目录。解析生成的
`bea4.private.jsonl` 和 `bea5.private.jsonl` 文件及临时公开 artifact 以计算
聚合分解。

- BEA-4：ContextBench offset 80 limit 80，RepoQA offset 40 limit 40，budget 5，
  methods bm25,regex,symbol，RRF 必需。预期 120 成功 / 840 私有 SCORE 行。
- BEA-5：ContextBench offset 0 limit 480，RepoQA offset 0 limit 240，budget 5，
  methods bm25,regex,symbol。预期 119 成功 / 833 私有 SCORE 行。

若重放计数与预期不匹配，状态为 partial/unavailable，不是 pass。

## 必需对比

v0.3 treatment vs：v0.2、v0、bm25_prefix_same_budget、
agreement_only_same_budget、rrf_same_budget。

## 固定类别 enum（12）

`gold_file_absent`、`gold_span_absent`、`correct_file_wrong_span`、
`redundant_same_file_candidates`、`too_many_anchor_slots`、
`missing_support_candidate`、`support_selected_without_target`、
`target_selected_without_support`、`risk_penalty_removed_gold`、
`early_stop_too_early`、`budget_spent_on_low_marginal_gain`、
`latency_without_quality_gain`。

## 可用 vs 不可用类别

- **可用**：`gold_file_absent`（file_recall==0）、
  `correct_file_wrong_span`（文件命中但 span==0）、
  `too_many_anchor_slots`（anchor_slots>2）、
  `early_stop_too_early`（early_stop 触发且 quality<=baseline）、
  `budget_spent_on_low_marginal_gain`（满预算且 quality<=baseline）、
  `latency_without_quality_gain`（latency>baseline 且 quality delta<=0）。
- **unavailable_missing_trace**：`redundant_same_file_candidates`、
  `risk_penalty_removed_gold`。
- **unavailable_no_support_label**：`missing_support_candidate`、
  `support_selected_without_target`、`target_selected_without_support`。

## 公开 artifact 表（仅 records，natural key）

- `source_run_records`：`(source_phase, source_ci_run_id)`
- `category_summary_records`：`(source_phase, benchmark, category, category_availability)`
- `category_metric_loss_records`：`(source_phase, benchmark, category, baseline_arm, treatment_arm, metric)`
- `category_win_tie_loss_records`：`(source_phase, benchmark, category, baseline_arm, treatment_arm, metric)`
- `bucket_category_records`：`(source_phase, benchmark, bucket_type, bucket_value, category)`
- `candidate_source_category_records`：`(source_phase, benchmark, candidate_source_bucket, category)`
- `availability_records`：`(source_phase, benchmark, category, category_availability)`
- `private_decomposition_manifest`：仅聚合（count/hash/storage/path=false）

## 指标损失

- 质量指标：`loss = max(0, baseline_metric - treatment_metric)`。
- 延迟：`loss = max(0, treatment_latency - baseline_latency)`。
- 记录含 `loss_sum`、`loss_mean`、`delta_mean`、`record_count`。

## 验证

```text
python3 -m py_compile eval/bea_fd1_failure_decomposition.py  => PASS
python3 eval/bea_fd1_failure_decomposition.py --self-test  => PASS (174/174 checks)
python3 eval/bea_fd1_failure_decomposition.py \
  --out artifacts/bea_fd1_failure_decomposition/bea_fd1_failure_decomposition_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_fd1=false, weights_tuned_during_bea_fd1=false,
   self_test_checks_total=174, self_test_checks_passed=174)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```


## Manual CI 结果

Manual CI run `28011901294` 通过，用时 54m52s。公开聚合 artifact 已替换为 CI 结果：

- `status = bea_fd1_decomposition_pass`
- `records_decomposed = 239`（BEA-4 120 + BEA-5 119）
- `private_decomposition_manifest.record_count = 86040`
- `source_run_records`：BEA-4 replay 匹配 run `27957586271`（120/840）；BEA-5 replay 匹配 run `28003522632`（119/833）
- Run `28011901294` 取代较早 FD1 run `28008602265`；后者的公开 `source_run_records` 曾把 BEA-4 benchmark contribution counts 误写为 0/0。
- 聚合表规模：category_summary=16，category_metric_loss=480，category_win_tie_loss=480，bucket_category=16，candidate_source_category=16，availability=48
- 最强聚合类别是 budget spent on low marginal gain、latency without quality gain、gold file absent、correct file / wrong span；support-target 类别仍为 unavailable，因为当前私有 SCORE schema 没有 support/target 标签。

这是用于 v0.4 设计的 failure-mechanism evidence，不是 benchmark performance、winner、default、calibration 或 downstream-value 声明。

## 限制

- BEA-FD1 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法/权重冻结；`algorithm_changed_during_bea_fd1=false`。
- 固定协议：无 budget/methods CLI 输入；使用精确 BEA-4/5 默认值。
- Manual CI run `28011901294` 已完成完整 BEA-4/BEA-5 replay：status `bea_fd1_decomposition_pass`，records_decomposed=239，private_decomposition_manifest.record_count=86040，forbidden_scan=pass。
- `redundant_same_file_candidates` 和 `risk_penalty_removed_gold` 标记为
  `unavailable_missing_trace`。
- `missing_support_candidate`、`support_selected_without_target`、
  `target_selected_without_support` 标记为 `unavailable_no_support_label`
  （不发明 support/target 标签）。
