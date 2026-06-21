# D5-A2 Heldout Feature Validation Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

D5-A2 validates whether D5-A1's retrieval-derived feature bucket
reproduces on **fresh heldout external retrieval samples**. D5-A2
loads the D5-A1 committed artifact as the preregistered feature
source, runs new heldout ContextBench verified Python rows 21-40 and
RepoQA Python needles 11-20 with methods bm25/regex/symbol, computes
the same retrieval-derived utility proxy, and checks whether the
heldout metrics support the D5-A1 feature buckets.

D5-A2 is explicitly **not** calibration, **not** a calibrated model
claim, **not** a policy/default recommendation, **not** a method
winner claim, **not** an external benchmark performance claim, **not**
a downstream agent value claim, **not** a leaderboard entry, and
**not** a runtime/retriever/pack/backend/default-policy/EvidenceCore
semantic change. It validates only the retrieval-feature stability
component from D5-A1; it does NOT validate live-provider/downstream
alignment. It makes NO provider calls and NO remote provider calls.

- Claim level: `heldout_retrieval_feature_validation_smoke_only`.
- Mode: `heldout_contextbench_repoqa_feature_validation`;
  phase `D5-A2`.
- Status enum: `heldout_feature_validation_pass` (all features
  reproduce); `partial` (mixed or not-supported but data was
  available); `unavailable_with_reason` (no heldout data);
  `fail_forbidden_scan`; `fail_schema_contract`.
- Validation outcomes (fixed allowlist):
  `retrieval_feature_validation_supported` (all reproduce),
  `retrieval_feature_validation_mixed` (some reproduce),
  `retrieval_feature_validation_not_supported` (none reproduce),
  `unavailable_with_reason`.

## D5-A1 input (preregistered feature source)

D5-A2 loads the D5-A1 committed artifact
(`artifacts/d5a1_automated_calibration_feature_table/d5a1_automated_calibration_feature_table_report.json`)
and extracts:

- `readiness_bucket` (e.g., `ready_for_manual_review`).
- `cross_signal_alignment` (e.g., `retrieval_robust_positive_plus_live_positive`).
- `calibration_feature_records` (preregistered feature buckets).

Fail-closed: D5-A1 missing, schema mismatch, status mismatch, unsafe
claim flags, or `forbidden_scan.status != pass` => status
`unavailable_with_reason` and nonzero CLI exit.

## Heldout measurement

D5-A2 runs fresh heldout retrieval measurements (NOT a reread of
existing C5/F1 artifacts):

- **ContextBench verified Python rows 21-40**: fetches
  (offset+limit)=40 rows from HF datasets-server, evaluates only the
  heldout slice [20, 40) for each method.
- **RepoQA Python needles 11-20**: parses (offset+limit)=20 needles
  from the RepoQA release asset, evaluates only the heldout slice
  [10, 20) for each method.
- Methods: `bm25,regex,symbol` only.
- No provider calls.

## Utility formula (fixed diagnostic proxy; unchanged from F1-C/F1-D)

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

## Validation rules

D5-A2 checks four retrieval-feature validations (records-shaped only):

1. **`bm25_vs_empty_retrieval_utility_magnitude`**: preregistered bucket
   `weak_positive`/`strong_positive` => heldout bm25
   retrieval_utility > 0 (empty is 0 by construction).
2. **`bm25_vs_empty_sign_stability`**: preregistered
   `stable_positive` => heldout bm25 file_recall@10 > 0 on both
   benchmarks.
3. **`regex_vs_bm25_sign_stability`**: preregistered
   `stable_negative` => heldout regex retrieval_utility < bm25
   retrieval_utility.
4. **`symbol_vs_bm25_sign_stability`**: preregistered
   `stable_negative` => heldout symbol retrieval_utility < bm25
   retrieval_utility.

Each record: `{feature_name, preregistered_bucket, heldout_metric,
heldout_direction, supported}`.

## Public artifact shape

Records-shaped lists only (no dynamic dict mirrors):

- `d5a1_input_record`: single record (schema, status, readiness
  bucket, cross-signal alignment, claim-safe, feature/signal counts).
- `heldout_benchmark_method_records`: list of fixed records
  `{benchmark, method, sample_count, metrics}`.
- `validation_records`: list of fixed records (fields above).
- `validation_summary_records`: list of fixed records
  `{outcome, outcome_count}` (one per outcome in the allowlist).

## CLI

```bash
python3 -m py_compile eval/d5a2_heldout_feature_validation.py
python3 eval/d5a2_heldout_feature_validation.py --self-test
python3 eval/d5a2_heldout_feature_validation.py \
    --contextbench-row-offset 20 --contextbench-row-limit 20 \
    --repoqa-needle-offset 10 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --out artifacts/d5a2_heldout_feature_validation/\
d5a2_heldout_feature_validation_report.json
```

## Validation

```text
python3 -m py_compile eval/d5a2_heldout_feature_validation.py  => PASS
python3 eval/d5a2_heldout_feature_validation.py --self-test  => PASS (88/88 checks)
python3 eval/d5a2_heldout_feature_validation.py \
  --contextbench-row-offset 20 --contextbench-row-limit 20 \
  --repoqa-needle-offset 10 --repoqa-needle-limit 10 \
  --methods bm25,regex,symbol \
  --out artifacts/d5a2_heldout_feature_validation/\
d5a2_heldout_feature_validation_report.json  => PASS
  (status: heldout_feature_validation_pass,
   forbidden_scan: pass, self_test_passed: true,
   validation_outcome: retrieval_feature_validation_supported,
   contextbench_rows_fetched: 20, repoqa_needles_seen: 10,
   network_calls: 2, provider_calls: 0,
   heldout_feature_validation_executed: true,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   calibrated_model_claimed: false,
   policy_recommendation_claimed: false,
   method_winner_claimed: false,
   external_benchmark_performance_claimed: false,
   promotion_ready: false,
   default_should_change: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

Local heldout run and manual CI run `27915252367` produced the following aggregate records (no
row/needle IDs/repo URLs/commits/queries/paths/spans/snippets/JSONL/
evidence/per-unit metrics/hashes/stdout/stderr/clone paths/provider
fields/winner/default/calibration claims committed):

```text
status: heldout_feature_validation_pass
validation_outcome: retrieval_feature_validation_supported
contextbench_rows_fetched: 20
repoqa_needles_seen: 10
network_calls: 2
forbidden_scan: pass
provider_calls: 0
d5a1_input_record:
  readiness_bucket: ready_for_manual_review
  cross_signal_alignment: retrieval_robust_positive_plus_live_positive
  feature_count: 7, signal_count: 9
heldout_benchmark_method_records:
  contextbench/bm25: sample_count=20, file_recall@10=0.7, retrieval_utility=0.815104
  contextbench/regex: sample_count=20, file_recall@10=0.0, retrieval_utility=-0.25
  contextbench/symbol: sample_count=20, file_recall@10=0.0, retrieval_utility=-0.25
  repoqa/bm25: sample_count=10, file_recall@10=0.5, retrieval_utility=0.553674
  repoqa/regex: sample_count=10, file_recall@10=0.0, retrieval_utility=-0.25
  repoqa/symbol: sample_count=10, file_recall@10=0.0, retrieval_utility=-0.25
validation_records:
  bm25_vs_empty_retrieval_utility_magnitude: prereg=weak_positive, heldout=+0.727961, dir=positive, supported=True
  bm25_vs_empty_sign_stability: prereg=stable_positive, heldout=+0.6, dir=positive, supported=True
  regex_vs_bm25_sign_stability: prereg=stable_negative, heldout=-0.977961, dir=negative, supported=True
  symbol_vs_bm25_sign_stability: prereg=stable_negative, heldout=-0.977961, dir=negative, supported=True
validation_summary_records:
  retrieval_feature_validation_supported: count=4
  retrieval_feature_validation_mixed: count=0
  retrieval_feature_validation_not_supported: count=0
  unavailable_with_reason: count=0
```

All 4 D5-A1 retrieval features reproduce on heldout data
(`retrieval_feature_validation_supported`, supported count=4/4).

## Caveats

- D5-A2 is the public aggregate-only heldout feature validation smoke
  artifact. It is eval/diagnostic only. It is NOT calibration, NOT a
  calibrated model claim, NOT a policy/default recommendation, NOT a
  benchmark result, NOT downstream utility, NOT true E/S calibration,
  NOT an external benchmark performance claim, NOT a leaderboard entry,
  NOT a method winner, and NOT a promotion.
- D5-A2 validates only the retrieval-feature stability component from
  D5-A1. It does NOT validate live-provider/downstream alignment.
- D5-A2 runs fresh heldout retrieval measurements (rows 21-40, needles
  11-20). It does NOT reread existing C5/F1 artifacts.
- D5-A2 makes NO provider calls and NO remote provider calls. All
  transient data stays in memory or under `/tmp` only.
- The heldout run found bm25 file_recall@10=0.7 on ContextBench heldout
  (vs 0.35 on the original D5-A1 rows 1-20), supporting the bm25
  positive retrieval feature on this heldout slice (and it is stronger
  on this slice).
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  remain true; `heldout_feature_validation_executed=true` only when a
  real heldout run actually executed.
