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
python3 eval/bea4_external_scale_smoke.py --self-test  => PASS (238/238 checks)
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

## 手动 CI scale 结果（run `27957586271`，2026-06-21）

手动 CI run `27957586271` 执行完整 BEA-4 scale 切片：ContextBench offset 80
limit 80 + RepoQA offset 40 limit 40，budget=5，方法 bm25/regex/symbol，
RRF baseline 必需并启用。

结果：`status=bea4_external_scale_smoke_pass`，120 条记录成功（ContextBench
80 + RepoQA 40），`paired_exclusion_count=0`，forbidden scan pass，
`provider_calls=0`，`network_calls=3`，
`private_score_manifest.record_count=840`（120×7 arm），
`private_score_storage_class=tmp_private`，
`private_score_path_publicly_serialized=false`，
`aggregate_runtime_seconds=864.538`。

BEA v0.3 按 benchmark 的指标：

- ContextBench：file_recall@10=0.225，mrr=0.151875，
  span_f0.5@10=0.013607，success_rate=0.225，latency_seconds=3.719746。
- RepoQA：file_recall@10=0.575，mrr=0.402917，
  span_f0.5@10=0.044761，success_rate=0.575，latency_seconds=0.50835。

`bea_v0_3_anchor_span_latency` 的 delta：

- vs `bea_v0_2_diversity_risk`：file_recall@10=0.0，mrr=0.0，
  span_f0.5@10=-0.000075，success_rate=0.0，latency_seconds=+0.000831，
  quality_per_latency=-0.000427。
- vs `bea_v0`：file_recall@10=+0.108334，mrr=+0.076945，
  span_f0.5@10=+0.001333，success_rate=+0.108334，latency_seconds=+0.000831，
  quality_per_latency=+0.000417。
- vs `bm25_prefix_same_budget` 和 `agreement_only_same_budget`：
  file_recall@10=+0.108334，mrr=+0.076945，span_f0.5@10=+0.001333，
  success_rate=+0.108334，latency_seconds=+2.649281，
  quality_per_latency=+0.053332。
- vs `rrf_same_budget`：file_recall@10=+0.108334，mrr=+0.076945，
  span_f0.5@10=+0.001333，success_rate=+0.108334，latency_seconds=+1.391673，
  quality_per_latency=-0.05038。
- vs `seeded_random_same_budget`：file_recall@10=+0.175，mrr=+0.139028，
  span_f0.5@10=+0.020195，success_rate=+0.175，latency_seconds=+2.649281，
  quality_per_latency=+0.053332。

Worst-slice records：发出 70 条跨 benchmark × arm × 固定 bucket context 的
聚合记录，无 row IDs、repos、paths、commits、queries、labels、candidate lists
或 gold/source snippets。

解释：BEA v0.3 作为冻结 diagnostic policy 可以在更大 scale 上运行；在该切片
上明显优于 BEA v0/random，也在 file_recall/MRR/success 上优于 same-budget
BM25、agreement-only 和 RRF，但 latency 与 quality-per-latency trade-off 混合，
并且基本与 BEA v0.2 持平。这是 scale smoke evidence，不是 method-winner、
benchmark-performance、default-policy、calibration、runtime/retriever/EvidenceCore
或 downstream-agent-value 声明。

## Caveats

- BEA-4 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法和权重与 BEA-3 完全一致（冻结）。
  `algorithm_changed_during_bea4=false`、
  `weights_tuned_during_bea4=false`（绑定）。
- 已提交 artifact 镜像手动 CI run `27957586271` 的完整 ContextBench 80 +
  RepoQA 40 scale 切片。上面的 3+2 命令仅作为本地验证保留，不作为结果证据。
- Network-enabled CI 仅用于 scale：若成功记录少于 75，或 ContextBench 与
  RepoQA 任一方没有非零记录，则 fail。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。
  BEA-0/BEA-1/BEA-2/BEA-3 语义未修改。
