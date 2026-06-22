# BEA-3 Anchor/Span/Latency-Aware 策略 Smoke

日期：2026-06-21（BEA-3 anchor/span/latency-aware 策略 smoke，基于全新
heldout ContextBench verified Python 行 offset 60 + RepoQA Python needle
offset 30，私有 per-record SCORE JSONL 存于 `/tmp`，公开产物为 records
形态的仅聚合）

BEA-3 实现了一个**冻结 BEA v0.3 算法策略**，针对 BEA-2 的混合结果：在保
持 file/MRR/success 增益的同时减少 span_f0.5 和 latency 回归。v0.3 为
BM25/agreement anchor 预留 anchor slot，对剩余预算应用 diversity/risk
评分，添加 runtime-clean span/latency 代理（更紧的 line-span bonus、
同文件-as-anchor 支持 bonus、风险 bucket 惩罚、weak-support + low-BM25
惩罚、anchor 后固定边际优先级 early stop），并在全新 heldout 记录上与
v0.2、v0 和同预算控制进行对比。

BEA-3 明确**不是** benchmark 结果，**不是** leaderboard 条目，**不是**
性能声明，**不是** method-winner 声明，**不是** calibration 声明，**不是**
promotion，**不是** default/policy 变更，且**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。

> `claim_level = bea_v03_policy_smoke_only`。所有 no-claim /
> no-runtime-change flag 均为 false。

## v0.3 冻结策略

`bea_v0_3_anchor_span_latency`：

- 为 BM25/agreement anchor 预留前 `anchor_count=min(2,budget)` 个 slot；
- 仅对剩余预算应用 diversity/risk 评分；
- 添加 runtime-clean span/latency 代理：更紧的 line-span bonus、
  same-file-as-anchor 支持 bonus、风险 bucket 惩罚、weak-support +
  low-BM25 惩罚、anchor 后固定边际优先级 early stop；
- 从不使用 gold labels/spans/files、row/needle IDs、repo identity、
  outcome history、provider/model identity 或 benchmark-only labels。

冻结权重：`anchor=0.35`、`span_tight=0.15`、
`anchor_file_support=0.10`、`weak_support_penalty=-0.20`、
`early_stop_margin=0.05`。这些不从 outcomes 调优。

必需消融：`v0_3_no_anchor`（无 anchor 预留）、`v0_3_no_early_stop`
（无边际优先级 early stop）。

## 必需 arm

`bea_v0_3_anchor_span_latency`、`bea_v0_3_no_anchor`、
`bea_v0_3_no_early_stop`、`bea_v0_2_diversity_risk`、`bea_v0`、
`bm25_prefix_same_budget`、`agreement_only_same_budget`、
`seeded_random_same_budget`、可用时 `rrf_same_budget`。

## 全新 primary 切片

ContextBench offset 60、limit 20。RepoQA offset 30、limit 10。本地 smoke
使用更小边界（3+2）以加速；CI 使用完整 20+10。

## 公开 artifact 形态

仅 records（无动态 arm dict）：

- `benchmark_arm_metric_records`：`{benchmark, arm, metric, value, record_count}`
- `delta_records`：`{baseline_arm, treatment_arm, metric, delta}`
- `mechanism_contrast_records`：`{contrast, baseline_arm, treatment_arm, metric, delta, record_count}`
- `win_tie_loss_records`：`{baseline_arm, treatment_arm, metric, win, tie, loss, record_count}`
- `mechanism_summary_records`：`{mechanism_field, value, record_count}`（anchor_used_rate、early_stop_rate、mean_budget_used、mean_latency_seconds、mean_span_extent、span_proxy_bucket 计数）
- aggregate-only `private_score_manifest`

指标：`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`、
`evidence_budget_used`、`candidate_count_read`、`latency_seconds`、
`quality_per_candidate`、`quality_per_latency`。

## 延迟归因

所有 arm 共享候选收集延迟（公平归因）。v0.3 还获得增量策略时间。控制获
得 0.0（进程内，无检索）。

## 验证

```text
python3 -m py_compile eval/bea3_anchor_span_latency.py  => PASS
python3 eval/bea3_anchor_span_latency.py --self-test  => PASS (224/224 checks)
python3 eval/bea3_anchor_span_latency.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 60 --contextbench-row-limit 3 \
  --repoqa-needle-offset 30 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea3_anchor_span_latency/bea3_anchor_span_latency_report.json  => PASS
  (status: bea3_anchor_span_latency_pass, 5 records successful,
   private_score_manifest.record_count=45 (5×9 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 真实有界本地运行结果（2026-06-21）

5 条记录成功（ContextBench 3 + RepoQA 2）。45 行私有 SCORE
（5 × 9 arm）。Win/tie/loss（v0.3 vs v0.2，n=5）：file_recall@10 win=0
tie=5 loss=0；mrr win=0 tie=5 loss=0；span_f0.5@10 win=0 tie=5 loss=0；
success_rate win=0 tie=5 loss=0。v0.3 在此有界样本上与 v0.2 在所有 primary
指标上持平。

机制摘要：anchor_used_rate=1.0、early_stop_rate=0.0、
mean_budget_used=5.0、mean_latency_seconds=6.8976、
mean_span_extent=4.88、span_proxy_bucket_tight=25。

## Caveats

- BEA-3 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 权重为冻结常量，不从 outcomes 调优。
- 有界样本（5 条记录）。smoke，非严格评估。
- v0.3 在此有界样本上与 v0.2 在所有 primary 指标上持平——
  anchor/span/latency 代理未改变 accepted set（所有候选均为 tight-span、
  low-risk、BM25-backed）。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。
  BEA-0/BEA-1/BEA-2 语义未修改。
