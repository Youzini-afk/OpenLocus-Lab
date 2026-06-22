# BEA-4 External Scale Smoke

日期：2026-06-21（BEA-4 冻结 BEA v0.3 策略的外部 scale smoke，基于更大全新
external 切片——ContextBench verified Python 行 offset 80 + RepoQA Python
needle offset 40——私有 per-record SCORE JSONL 存于 `/tmp`，公开产物为
records 形态的仅聚合，含 worst-slice 可见性）

BEA-4 是冻结 BEA v0.3 策略的 **external scale smoke**。它在一个更大的全新
external 切片上度量 v0.3 + 同预算控制的 scale 行为，并发布 records-only
聚合输出，含 worst-slice 可见性。**v0.3 算法和权重与 BEA-3 完全一致（冻
结）；本阶段是 scale 度量，不是新算法。**

BEA-4 明确**不是** benchmark 结果，**不是** leaderboard 条目，**不是**
性能声明，**不是** method-winner 声明，**不是** calibration 声明，**不是**
promotion，**不是** default/policy 变更，**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更，且**不是**算法变更。
`algorithm_changed_during_bea4` 和 `weights_tuned_during_bea4` flag 均为
`false`（绑定）。

> `claim_level = bea_v03_external_scale_smoke_only`。所有 no-claim /
> no-runtime-change flag 均为 false。

## 冻结策略

`bea_v0_3_anchor_span_latency` 与 BEA-3 完全相同（冻结权重：anchor=0.35、
span_tight=0.15、anchor_file_support=0.10、weak_support_penalty=-0.20、
early_stop_margin=0.05）。BEA-4 期间无算法/权重变更。

## 必需 arm（无消融）

- `bm25_prefix_same_budget`
- `agreement_only_same_budget`
- `rrf_same_budget`（必需）
- `bea_v0`
- `bea_v0_2_diversity_risk`
- `bea_v0_3_anchor_span_latency`（treatment）
- `seeded_random_same_budget`

BEA-3 的消融（`bea_v0_3_no_anchor`、`bea_v0_3_no_early_stop`）**不**在
BEA-4 固定 arm 中（scale 度量，非消融）。

## 全新 primary 切片

- ContextBench verified Python 行：offset 80、limit 80（硬上限 80）。
- RepoQA Python needle：offset 40、limit 40（硬上限 40）。
- 本地 smoke 可使用更小边界以加速；手动 CI 使用完整 scale 切片（或在
  runtime 顾虑时回退 ContextBench 50 + RepoQA 25，绝不是另一个 20 + 10
  却称为 scale）。

## 公开 artifact 形态

仅 records（无动态 arm dict）：

- `benchmark_arm_metric_records`：`{benchmark, arm, metric, value, record_count}`
- `delta_records`：`{baseline_arm, treatment_arm, metric, delta}`（v0.3 vs
  bm25、agreement、rrf、v0.2、v0、random；v0 为固定 baseline arm）
- `win_tie_loss_records`：`{baseline_arm, treatment_arm, metric, win, tie,
  loss, record_count}`（paired denominator；v0.3 vs 每条控制）
- `worst_slice_records`：`{benchmark, arm, query_length_bucket,
  candidate_pool_size_bucket, budget_exhaustion_bucket, file_kind_mix_bucket,
  method_agreement_bucket, rank_gap_bucket, record_count, file_recall@10,
  mrr, span_f0.5@10, success_rate, evidence_budget_used, latency_seconds,
  quality_per_candidate, quality_per_latency}`（每 benchmark × arm 取最差
  N=5，按 span_f0.5@10 升序）
- `mechanism_summary_records`：`{mechanism_field, value, record_count}`
- aggregate-only `private_score_manifest`：`{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`

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

## 验证

```text
python3 -m py_compile eval/bea4_external_scale_smoke.py  => PASS
python3 eval/bea4_external_scale_smoke.py --self-test  => PASS (237/237 checks)
python3 eval/bea4_external_scale_smoke.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 80 --contextbench-row-limit 3 \
  --repoqa-needle-offset 40 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea4_external_scale_smoke/bea4_external_scale_smoke_report.json  => PASS
  (status: bea4_external_scale_smoke_pass, 5 records successful,
   private_score_manifest.record_count=35 (5×7 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea4=false, weights_tuned_during_bea4=false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 真实有界本地 smoke 结果（2026-06-21）

有界本地 smoke（ContextBench offset 80 limit 3 + RepoQA offset 40
limit 2，budget=5，方法 bm25/regex/symbol，必需并启用 rrf baseline）：5 条记录成
功，`paired_exclusion_count=0`，forbidden scan pass，`provider_calls=0`，
`private_score_manifest.record_count=35`（5×7 arm），
`private_score_storage_class=tmp_private`，
`private_score_path_publicly_serialized=false`。

Win/tie/loss（v0.3 vs v0，n=5）：file_recall@10 win=1 tie=4 loss=0；mrr
win=2 tie=3 loss=0；span_f0.5@10 win=1 tie=3 loss=1；success_rate win=1
tie=4 loss=0。

Delta records（v0.3 vs 控制）：vs `bea_v0_2_diversity_risk` 所有 delta
0.0（v0.3 在此有界样本上与 v0.2 在所有 primary 指标上持平）；vs
`bea_v0`/`agreement_only`/`bm25_prefix`/`rrf_same_budget` file_recall@10
+0.2 / mrr +0.2 / success_rate +0.2 / span_f0.5@10 -0.020628；vs
`seeded_random` file_recall@10 +0.4 / mrr +0.266667 / span_f0.5@10
+0.038277 / success_rate +0.4。

机制摘要：anchor_used_rate=1.0、early_stop_rate=0.0、
mean_budget_used=5.0、mean_latency_seconds=6.3926、
mean_span_extent=5.0、span_proxy_bucket_tight=25。

Worst-slice records：跨（benchmark × arm）组合发出 27 个 slice，每个
`record_count >= 1`，按 span_f0.5@10 升序。所有 bucket 标签为固定公开聚
合标签；无 row IDs、repos、paths、commits、queries、labels、candidate
lists 或 gold/source snippets。

这是诚实的 smoke 级 scale 结果，不是 method-winner、calibration、
default、promotion、runtime/retriever/EvidenceCore 或 downstream-agent-value
声明。完整 scale 切片（ContextBench 80 + RepoQA 40）待手动 CI 运行。

## Caveats

- BEA-4 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法和权重与 BEA-3 完全一致（冻结）。
  `algorithm_changed_during_bea4=false`、
  `weights_tuned_during_bea4=false`（绑定）。
- 有界本地 smoke 使用 3+2 条记录以加速。完整 scale 切片（ContextBench
  80 + RepoQA 40）待手动 CI 运行；已提交 artifact 仅反映本地 smoke。
- Network-enabled CI 仅用于 scale：若成功记录少于 75，或 ContextBench 与
  RepoQA 任一方没有非零记录，则 fail。3+2 小样本只用于本地验证，不作为
  CI result evidence。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。
  BEA-0/BEA-1/BEA-2/BEA-3 语义未修改。
