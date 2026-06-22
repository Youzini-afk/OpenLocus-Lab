# BEA-2 Policy v0.2 Diversity/Risk Mechanism Smoke

Date: 2026-06-21 (BEA-2 policy v0.2 diversity/risk mechanism smoke over fresh
heldout ContextBench verified Python rows + RepoQA Python needles, with private
per-record SCORE JSONL traces in `/tmp` and records-shaped aggregate-only
public artifact)

BEA-2 is the **policy v0.2 diversity/risk mechanism smoke** follow-up to
BEA-1. It implements a real algorithmic policy change — BEA v0.2
diversity/risk-aware acquisition — and tests it against BEA v0 and same-budget
controls on fresh heldout external records. BEA v0.2 is structurally
different from v0 (BEA-0) and from agreement-only (BEA-1): it computes a
per-candidate priority score that combines cross-method agreement, normalized
BM25 score, diversity bonus for new file/dir, query-token/path-token overlap
scalar, risk penalty for test/docs/generated/vendor/lock/config path buckets,
and duplication penalty for same-file/overlapping span already selected, then
greedily selects by descending priority under the budget with priority
recomputation after each selection.

BEA-2 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change. It
does NOT emit `winner`, `best_method`, `recommended_default`,
`method_winner`, `calibration`, or anything implying a policy/default
decision.

> **Important claim boundary.** BEA-2 emits `claim_level =
> bea_v02_policy_smoke_only`. All no-claim / no-runtime-change flags are
> false.

## BEA v0.2 policy (deterministic, runtime-clean)

The v0.2 policy consumes ONLY runtime-clean candidate features:

- **cross-method support / agreement**, weighted by method mix (bm25=1.0,
  symbol=0.8, rrf=0.9, regex=0.6);
- **normalized BM25 score** (max normalized score in [0, 1] within method);
- **diversity bonus** for new file/dir (1.0 if both new file and new dir;
  0.5 if new file only; 0.25 if new dir only; 0.0 otherwise);
- **query-token/path-token overlap scalar** (Jaccard-like overlap in [0, 1]
  between query tokens and path tokens);
- **risk penalty** for test/docs/generated/vendor/lock/config-like path
  buckets (-1.0 if risk_penalty bucket; 0.0 otherwise);
- **duplication penalty** for same-file/overlapping span already selected
  (-1.0 if overlapping span; -0.5 if same file only; 0.0 otherwise).

Frozen priority weights (NOT tuned from outcomes):
`agreement=0.30`, `bm25_norm=0.20`, `diversity=0.20`,
`query_path_overlap=0.15`, `risk_penalty=-0.25`,
`duplication_penalty=-0.30`.

Forbidden policy features: gold files/lines, benchmark labels, row/needle
IDs, outcome history, repo URL/name/commit, source snippets unless
explicitly acquired inside budget, provider/model identity, private SCORE
outcomes.

## Fixed policy arms

- `bm25_prefix_same_budget`: first K deduped BM25 candidates (same-budget K).
- `agreement_only_same_budget`: sort by agreement desc / min_rank asc /
  max_norm_score desc / stable order, take first K.
- `bea_v0`: BEA-0 deterministic policy (accept/skip/rerank/stop).
- `bea_v0_2_diversity_risk`: v0.2 priority-scored greedy selection with
  diversity/risk/duplication-aware recomputation.
- `seeded_random_same_budget`: deterministic PRNG with fixed public seed
  `20240621` over stable-ordered deduped universe.
- `rrf_same_budget` (optional): first K deduped RRF candidates.

## Same-budget K

`K = min(len(bea_v0_2_diversity_risk.accepted_candidates), available_deduped_candidate_count)`.
If v0.2 accepts zero candidates, K=0; all same-budget controls also select
zero.

## Fresh heldout slice

- ContextBench verified Python rows offset 40, limit 20 (rows 41-60).
- RepoQA Python needles offset 20, limit 10 (needles 21-30).

## Public artifact shape

Records only (no dynamic arm dicts):

- `benchmark_arm_metric_records`: `{benchmark, arm, metric, value, record_count}`.
- `delta_records`: `{baseline_arm, treatment_arm, metric, delta}` (v0.2 vs
  each control arm, with v0 as the fixed baseline).
- `mechanism_contrast_records`: `{contrast, baseline_arm, treatment_arm,
  metric, delta, record_count}` for `v02_vs_v0`,
  `v02_vs_same_budget_bm25`, `v02_vs_agreement_only`,
  `v02_vs_seeded_random` on the paired denominator.
- `win_tie_loss_records`: `{baseline_arm, treatment_arm, metric, win, tie,
  loss, record_count}` for v0.2 vs each control on primary metrics
  (`file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`).
- `private_score_manifest`: `{records_written, record_count,
  schema_version, manifest_hash, storage_class,
  path_publicly_serialized=false}`.

## Validation

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

## Manual CI result (2026-06-21)

Manual CI run `27938484585` (`bea2-policy-v02`, external benchmark network
enabled, ContextBench offset 40 limit 20 + RepoQA offset 20 limit 10,
budget=5, methods bm25/regex/symbol, RRF baseline enabled) completed
successfully: 30 records successful, `paired_exclusion_count=0`, forbidden
scan pass, `provider_calls=0`, `private_score_manifest.record_count=180`
(30 records × 6 arms), `private_score_manifest.storage_class=tmp_private`,
`private_score_manifest.path_publicly_serialized=false`,
`aggregate_runtime_seconds=386.3`. The committed artifact mirrors this
sanitzed aggregate CI report.

BEA v0.2 vs BEA v0 / same-budget BM25 / agreement-only / RRF on primary
metrics (same deltas because those controls tied on this slice):
`file_recall@10` delta=+0.033334, `mrr` delta=+0.081667,
`span_f0.5@10` delta=-0.012947, `success_rate` delta=+0.033334,
`latency_seconds` delta=+8.188547, `evidence_budget_used` delta=0.0.
Win/tie/loss for v0.2 vs v0 (n=30): `file_recall@10` win=3 tie=25 loss=2;
`mrr` win=7 tie=21 loss=2; `span_f0.5@10` win=0 tie=28 loss=2;
`success_rate` win=3 tie=25 loss=2.

Against seeded random, v0.2 had stronger positive deltas (`file_recall@10`
+0.233334, `mrr` +0.326667, `span_f0.5@10` +0.019687, `success_rate`
+0.233334), but it still increased latency. This is a mixed smoke-level
mechanism result: v0.2 improved file recall/MRR/success over v0 and same-budget
controls on this bounded CI slice, but reduced span metric and cost more latency.
It is not a method-winner, default-policy, benchmark-performance, or calibration
claim.

## Caveats

- BEA-2 is eval/diagnostic only. NOT a benchmark result, NOT a leaderboard
  entry, NOT a performance claim, NOT a method-winner claim, NOT a calibration
  claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/
  backend/EvidenceCore semantic change, NOT a downstream agent value claim.
- BEA-2 does NOT emit `winner`, `best_method`, `recommended_default`,
  `method_winner`, `calibration`.
- BEA-2 runs NO provider calls. `provider_calls=0`.
- BEA-2 uses a bounded heldout sample (default ContextBench 20 rows / RepoQA
  10 needles; local run may use smaller bounds for speed). Aggregate metrics
  are point estimates over a bounded sample.
- BEA-2 writes private per-record SCORE JSONL ONLY under `/tmp`. The private
  SCORE path is NEVER serialized in the public artifact, docs, or CI
  artifacts.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  remain true. EvidenceCore semantics are unchanged.
