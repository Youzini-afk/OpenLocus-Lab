# R30 Baseline Freeze

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R30 Baseline Freeze

R30 freezes the R29 × R26 stress-matrix baseline for later real-model retrieval experiments. It is a control artifact only: no retrieval was run, no remote provider was called, no EvidenceCore semantics changed, and no strategy is promoted.

## Frozen Baseline

- schema_version: `r30-baseline-freeze-v1`
- baseline_name: `r29_r26_stress_matrix`
- baseline_source: `runs/r29-r26-stress-matrix-report.json`
- implemented_strategies: 16
- unavailable_strategies: 5 (reason-only, no fake metrics)
- promotion_ready: false
- default_should_change: false
- core_changes: false
- evidencecore_semantics_changed: false
- remote_calls: 0

## Control Strategies

| Strategy | Role | FileRecall@1 | SpanF0.5 | primary_false_positive_rate | abstain_rate | guard_recall_kill_rate |
|---|---|---:|---:|---:|---:|---:|
| rrf | best recall channel | 0.8032786885245902 | 0.2500956437429835 | 0.453030303030303 | 0.3427272727272727 | None |
| query_noise_plus_rrf_agree_min | best guard candidate | 0.8032786885245902 | 0.24976691373202803 | 0.10606060606060606 | 0.5881818181818181 | 0.002785515320334262 |
| symbol | precision anchor | 0.6857923497267759 | 0.2911193523175293 | 0.0803030303030303 | 0.6709090909090909 | None |

## R30 Required Deltas for Future Phases

Every later real-model experiment must report:

- `delta_vs_r29_rrf`
- `delta_vs_r29_query_noise_guard`
- `delta_vs_r29_symbol`

## Main Frozen Facts

1. RRF remains the strongest recall channel, but primary false-positive risk is high.
2. `query_noise_plus_rrf_agree_min` preserves RRF recall on R26 while reducing false-primary, but prior bucket-regression evidence still blocks promotion.
3. Symbol remains the precision anchor: low false-primary, higher abstain.
4. Dense mock is a safety/noise probe, not semantic-quality evidence.
5. Graph expansion remains blocked by added false spans > added gold spans.
6. QuIVer/TDB remain unavailable for quality; no fabricated metrics are allowed.

## Runtime Artifact Inventory

- runtime_artifacts_available: true
- note: Runtime R29 artifacts were hashed and inventoried.

## Safety Gate Freeze

- promotion_ready: `False`
- default_should_change: `False`
- not_promotion_evidence: `True`
- core_changes: `False`
- evidencecore_semantics_changed: `False`
- remote_calls: `0`
- dense_or_llm_claims: `False`
- run_phase_public_only: `True`
- score_phase_labels_only: `True`
- labels_loaded_after_run: `True`
- r26_public_tasks_public_only: `True`
- citation_validity_all_strategies: `1.0`
- artifact_manifest_verified_if_present: `True`
- unavailable_strategies_reason_only: `True`

