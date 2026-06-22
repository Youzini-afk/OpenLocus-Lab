# BEA-2 Policy v0.2 Diversity/Risk 机制消融 Smoke

日期：2026-06-21（BEA-2 policy v0.2 diversity/risk 机制消融 smoke，基于全新
heldout ContextBench verified Python 行 + RepoQA Python needle，私有
per-record SCORE JSONL 轨迹存于 `/tmp`，公开产物为 records 形态的仅聚合）

BEA-2 是 BEA-1 的 **policy v0.2 diversity/risk 机制消融 smoke** 后续。它实现
了一个真正的算法策略变更——BEA v0.2 diversity/risk-aware 采集——并在全新
heldout external 记录上将其与 BEA v0 和同预算控制进行对比测试。BEA v0.2
在结构上与 v0（BEA-0）和 agreement-only（BEA-1）不同：它计算每候选优先级
分数，结合跨方法 agreement、归一化 BM25 分数、新文件/目录的 diversity
bonus、query-token/path-token 重叠标量、test/docs/generated/vendor/lock/
config 路径 bucket 的风险惩罚，以及已选同文件/重叠 span 的重复惩罚，然后
按优先级降序在预算下贪心选择，每次选择后重新计算优先级。

BEA-2 明确**不是** benchmark 结果，**不是** leaderboard 条目，**不是**
性能声明，**不是** method-winner 声明，**不是** calibration 声明，**不是**
promotion，**不是** default/policy 变更，且**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。它不会输出
`winner`、`best_method`、`recommended_default`、`method_winner`、
`calibration`，或任何暗示 policy/default 决策的字段。

> **重要 claim 边界**。BEA-2 输出 `claim_level =
> bea_v02_policy_smoke_only`。所有 no-claim / no-runtime-change flag 均为
> false。

## BEA v0.2 策略（确定性，runtime-clean）

v0.2 策略只消费 runtime-clean 候选特征：

- **跨方法 support/agreement**，按 method mix 加权（bm25=1.0、symbol=0.8、
  rrf=0.9、regex=0.6）；
- **归一化 BM25 分数**（max normalized score 在 [0, 1] 内，method 内）；
- **新文件/目录的 diversity bonus**（新文件+新目录=1.0；仅新文件=0.5；
  仅新目录=0.25；否则=0.0）；
- **query-token/path-token 重叠标量**（query token 与 path token 的类
  Jaccard 重叠，在 [0, 1] 内）；
- **test/docs/generated/vendor/lock/config 路径 bucket 的风险惩罚**
  （risk_penalty bucket=-1.0；否则=0.0）；
- **已选同文件/重叠 span 的重复惩罚**（重叠 span=-1.0；仅同文件=-0.5；
  否则=0.0）。

冻结优先级权重（不从 outcomes 调优）：
`agreement=0.30`、`bm25_norm=0.20`、`diversity=0.20`、
`query_path_overlap=0.15`、`risk_penalty=-0.25`、
`duplication_penalty=-0.30`。

禁止策略特征：gold files/lines、benchmark labels、row/needle IDs、outcome
history、repo URL/name/commit、source snippets（除非在预算内显式采集）、
provider/model identity、私有 SCORE outcomes。

## 固定策略 arm

- `bm25_prefix_same_budget`：去重后前 K 个 BM25 候选（同预算 K）。
- `agreement_only_same_budget`：按 agreement desc / min_rank asc /
  max_norm_score desc / 稳定顺序排序，取前 K。
- `bea_v0`：BEA-0 确定性策略（accept/skip/rerank/stop）。
- `bea_v0_2_diversity_risk`：v0.2 优先级评分贪心选择，含
  diversity/risk/duplication-aware 重计算。
- `seeded_random_same_budget`：确定性 PRNG，固定公开种子 `20240621`，在
  稳定排序后的去重宇宙上采样。
- `rrf_same_budget`（可选）：去重后前 K 个 RRF 候选。

## 同预算 K

`K = min(len(bea_v0_2_diversity_risk.accepted_candidates), available_deduped_candidate_count)`。
若 v0.2 接受零候选，K=0；所有同预算控制也选择零。

## 全新 heldout 切片

- ContextBench verified Python 行 offset 40、limit 20（行 41-60）。
- RepoQA Python needle offset 20、limit 10（needle 21-30）。

## 公开 artifact 形态

仅 records（无动态 arm dict）：

- `benchmark_arm_metric_records`：`{benchmark, arm, metric, value,
  record_count}`。
- `delta_records`：`{baseline_arm, treatment_arm, metric, delta}`（v0.2 vs
  每条控制 arm，v0 为固定 baseline）。
- `mechanism_contrast_records`：`{contrast, baseline_arm, treatment_arm,
  metric, delta, record_count}`，对 `v02_vs_v0`、
  `v02_vs_same_budget_bm25`、`v02_vs_agreement_only`、
  `v02_vs_seeded_random`，在 paired denominator 上。
- `win_tie_loss_records`：`{baseline_arm, treatment_arm, metric, win, tie,
  loss, record_count}`，v0.2 vs 每条控制，在 primary metrics
  （`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`）上。
- `private_score_manifest`：`{records_written, record_count,
  schema_version, manifest_hash, storage_class,
  path_publicly_serialized=false}`。

## 验证

```text
python3 -m py_compile eval/bea2_policy_v02.py  => PASS
python3 eval/bea2_policy_v02.py --self-test  => PASS (321/321 checks)
python3 eval/bea2_policy_v02.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 40 --contextbench-row-limit 3 \
  --repoqa-needle-offset 20 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea2_policy_v02/bea2_policy_v02_report.json  => PASS
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 手动 CI 结果（2026-06-21）

手动 CI run `27938484585`（`bea2-policy-v02`，启用 external benchmark network，
ContextBench offset 40 limit 20 + RepoQA offset 20 limit 10，budget=5，方法
bm25/regex/symbol，启用 RRF baseline）成功完成：30 条记录成功，
`paired_exclusion_count=0`，forbidden scan pass，`provider_calls=0`，
`private_score_manifest.record_count=180`（30 条记录 × 6 arm），
`private_score_manifest.storage_class=tmp_private`，
`private_score_manifest.path_publicly_serialized=false`，
`aggregate_runtime_seconds=386.3`。已提交 artifact 镜像该 sanitized aggregate CI report。

BEA v0.2 相对 BEA v0 / same-budget BM25 / agreement-only / RRF 的 primary
metrics（这些 control 在此 slice 上相同）：`file_recall@10` delta=+0.033334，
`mrr` delta=+0.081667，`span_f0.5@10` delta=-0.012947，`success_rate`
delta=+0.033334，`latency_seconds` delta=+8.188547，`evidence_budget_used`
delta=0.0。v0.2 vs v0 的 win/tie/loss（n=30）：`file_recall@10` win=3
tie=25 loss=2；`mrr` win=7 tie=21 loss=2；`span_f0.5@10` win=0 tie=28
loss=2；`success_rate` win=3 tie=25 loss=2。

相对 seeded random，v0.2 有更强正 delta（`file_recall@10` +0.233334，
`mrr` +0.326667，`span_f0.5@10` +0.019687，`success_rate` +0.233334），
但仍增加 latency。这是 mixed smoke-level 机制结果：v0.2 在该 bounded CI slice
上相对 v0 和 same-budget controls 提升 file recall/MRR/success，但降低 span metric
并带来更多 latency。它不是 method-winner、default-policy、benchmark-performance
或 calibration 声明。

## Caveats

- BEA-2 是 eval/diagnostic only。不是 benchmark 结果、不是 leaderboard
  条目、不是性能声明、不是 method-winner 声明、不是 calibration 声明、不是
  promotion、不是 default 变更、不是 runtime/retriever/pack/backend/
  EvidenceCore 语义变更、不是 downstream agent 价值声明。
- BEA-2 不输出 `winner`、`best_method`、`recommended_default`、
  `method_winner`、`calibration`。
- BEA-2 不运行 provider 调用。`provider_calls=0`。
- BEA-2 使用有界 heldout 样本（默认 ContextBench 20 行 / RepoQA 10 needle；
  本地运行可使用更小边界以加速）。聚合指标为有界样本上的点估计。
- BEA-2 仅在 `/tmp` 写入私有 per-record SCORE JSONL。私有 SCORE 路径绝不
  序列化到公开 artifact、docs 或 CI artifact。
- 所有 no-claim / no-runtime-change flag 保持 false；diagnostic flag 保持
  true。EvidenceCore 语义不变。
