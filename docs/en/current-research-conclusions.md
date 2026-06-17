# OpenLocus Current Research Conclusions

Date: 2026-06-16

Scope: R0-R45, real-provider P1-P9, P8/P9 CI scale-up, L1/L2 real-provider large-repo-slice tests, P20-LS/P20-LS-A low-context LLM query-alias results, and the P21-G cross-model context-injection pivot.

Status: Research summary, not a promotion request.

## P52A Source Materialization / Local Verifier Prerequisite

P52A reads local source files only for bounded aggregate materialization prerequisite diagnostics. It stores no raw source, snippets, digests, paths, or spans. Source read is not Evidence, and materialized candidate is not Evidence. P52A does not validate EvidenceCore and does not produce verifier pass/fail or default/promotion claims. See the [P52A detailed report](p52a-source-materialization-prerequisite.md).

## P52B Source-Backed Local Verifier Feature Matrix

P52B reads local source files only for bounded aggregate source-shape heuristic diagnostics and source-feature risk buckets. It computes deterministic source-backed verifier feature diagnostics from bounded spans, using source-shape heuristics only and marking AST/query-dependent features as unavailable. P52B stores no raw source, snippets, digests, paths, or spans. Source-feature buckets are diagnostic only; they are not Evidence and do not admit candidates. P52B does not validate EvidenceCore, does not produce a verifier pass/fail score or a local verifier score, does not prove P51 quality, and does not send source to providers. It does not call an LLM, construct prompts, or make remote calls. See the [P52B detailed report](p52b-source-backed-local-verifier-feature-matrix.md).

## P52C Diagnostic Local Verifier Scoring Simulator

P52C is a deterministic, gold-free diagnostic scoring simulator over P52B/P52A/P52/P49/P48 features. It computes fixed diagnostic score buckets and aggregate retrospective correlations using bounded source-backed features when available and metadata-only fallback when source reads are unavailable. P52C does not produce a verifier pass/fail, evidence validity, admission/default/promotion, or quality-over-P25 claim. It emits only aggregate buckets (`diagnostic_score_high`, `diagnostic_score_medium`, `diagnostic_score_low`, `diagnostic_score_unavailable`) and binned score distributions, never raw candidate scores. Gold spans and outcomes are used only inside the explicitly-marked `score_phase_diagnostic_correlation` after score buckets are fixed. See the [P52C detailed report](p52c-local-verifier-scoring-simulator.md).

## P51 LLM Span Narrow 2.0 / Candidate Filter Diagnostic

P51 first tranche is a deterministic, no-LLM, no-remote, no-prompt-construction diagnostic scaffold. It selects candidate pools for a future span-narrow/filter/abstain phase using aggregate metadata, public task bucket/risk tags, and P49 contrast-pack feasibility only; P47/P48 RMC overlay availability is reported separately. It publishes prompt-blueprint metadata (pack shapes, source-line/context-char budgets, strategy/path-kind/risk-bucket mixes) and never constructs raw prompts. Existing P21 role outcomes are replayed only after selection and only when present; missing outcomes are reported as unavailable. P51 does not create Evidence, validate EvidenceCore, admit candidates, or change defaults. See the [P51 detailed report](p51-llm-span-narrow-2-diagnostic.md).

## P51-B LLM Opt-In Contract / Dry-Run Payload Validator

P51-B defines and dry-validates a future live LLM opt-in contract without provider calls, prompt construction, or persistent raw payloads.
 It computes aggregate eligibility and request-envelope blueprint metadata from P51 selection, P49 candidate metadata, and P52C source-backed availability, and validates synthetic role-output schemas fail-closed (`not_evidence=true`, role enum, no unknown fields, bounded candidate ref/line delta). Public artifacts contain no prompts, responses, snippets, source text, queries, paths, spans, digests, providers, models, or keys. `remote_calls_by_p51b=0`, `llm_calls_by_p51b=0`, `remote_requests_by_p51b=0`, `prompt_construction_by_p51b=false`, `dry_run_payload_validation_only=true`. It is not Evidence, not quality evidence, and not a live/default/promotion gate. See the [P51-B detailed report](p51b-llm-opt-in-contract.md).

## P51-C0 Live LLM Micro-Run Planner / Explicit Opt-In Gate

P51-C0 is a planner-only, explicit opt-in gate that validates whether a future P51-C live LLM micro-run may be manually launched. It consumes only the aggregate P61 pre-spend gate report and P51-B dry-run opt-in contract, performs no provider calls, constructs no prompts, reads no source, admits no Evidence, changes no defaults, and authorizes no spend. It requires an explicit `--p51c-live-opt-in` flag, a matching `I_UNDERSTAND_P51C_NOT_EVIDENCE` acknowledgement, `dataset=ci_smoke`, a repo in the public allowlist, a supported output mode (`json_schema_strict` or `tool_call`), P61 `micro_run_preconditions_met` with provider spend and authorization flags false, and a ready P51-B contract with source-backed eligibility, schema validity, redaction preconditions satisfied, and budget caps respected. It publishes only aggregate planning/gate information, using `repo_scope='public_ci_smoke_allowlist'` and never exposing raw repo identity, paths, spans, prompts, responses, providers, models, URLs, or keys. `remote_calls_by_p51c=0`, `llm_calls_by_p51c=0`, `remote_requests_by_p51c=0`, `prompt_construction_by_p51c=false`, `p51c_live_calls_disabled=true`, `provider_spend_authorized=false`, `live_run_authorized=false`. It is not Evidence, not quality evidence, not authorization, and not a live/default/promotion gate. See the [P51-C0 detailed report](p51c-live-micro-run-planner.md).

## P57 Generalization Gate v0

P57 is a deterministic, no-live-LLM, no-provider aggregate-only generalization-readiness gate that runs after P51B. It consumes only existing aggregate report JSON (P46, P47, P48, P49, P50, P52, P52A, P52B, P52C, optional P51, required P51B) and verifies upstream safety flags, completeness, and availability. It does not read source files, candidate pools, prompts, responses, or provider configs, and it publishes no paths, identifiers, spans, digests, or keys. For single-slice/self-test runs P57 reports `insufficient_matrix` by design; it is not quality evidence, not a promotion/default gate, and not live-readiness evidence. See the [P57 detailed report](p57-generalization-gate.md).

## P58 Source-Backed Verifier Calibration v0

P58 is a deterministic, no-live-LLM, no-provider aggregate-only calibration report that runs after P57. It consumes only the existing aggregate JSON from P48, P52C, P51B, and P57 (and optionally P52B/P52A/P49) and turns upstream availability/distributions into coarse planning/action-hint buckets. It is not a verifier, not admission, not Evidence, not default/promotion, and not live readiness. It does not read source files, candidate pools, tasks, prompts, responses, repo locks, or provider configs, and it emits only aggregate counts, rates, and calibration buckets. See the [P58 detailed report](p58-source-backed-verifier-calibration.md).

## P59 Contrastive Pack Coverage & Counterfactual Study v0

P59 is a deterministic, no-live-LLM, no-provider, aggregate-only pre-spend diagnostic that runs after P58. It rebuilds P49 contrastive candidate packs in memory from the same ephemeral P25 records and measures whether the frozen packs contain the prerequisite contrastive information a later LLM role would need, before any LLM spend. It is not a quality evaluator, not admission, not Evidence, not default/promotion, and not live readiness. Pack construction is gold-free and uses only candidate metadata; private labels are loaded only after packs are frozen, inside the explicitly-marked `score_phase_gold_coverage` block. It does not read source files, construct prompts, or call providers. See the [P59 detailed report](p59-contrastive-pack-coverage-counterfactual.md).

## P60 RMC Policy v2 v0

P60 is a deterministic, no-live-LLM, no-provider, aggregate-only diagnostic policy COMPARISON layer that advances `request_more_context` (RMC) from P47/P48 geometry/overlay into a comparable policy matrix. For the same frozen candidate/task inputs, each policy selects only the NEXT diagnostic action; P60 reports aggregate routing counts plus SCORE-phase gold reach / false cost diagnostics and labeled cost/latency ESTIMATES. RMC is not evidence/admission/default. P60 declares NO winner and recommends NO default. See the [P60 detailed report](p60-rmc-policy-v2.md).

## P61 Pre-Spend Gate v0

P61 is a deterministic, no-live-LLM, no-provider, aggregate-only pre-spend readiness gate that runs after P60. It consumes only existing aggregate reports (P57, P58, P59, P60, P51-B required; P52C optional) and emits a precondition-readiness decision about whether a future P51-C live LLM micro-run is worth considering. P61 does not call providers, construct prompts, read source/ephemeral records, admit Evidence, change defaults, promote, or authorize provider spend. It only reports preconditions; opening a live run remains a separate explicit workflow_dispatch or human decision. For single-slice/self-test runs, P61 reports `insufficient_inputs` or `self_test_only` by design. It is not quality evidence, not a promotion/default gate, and not live-readiness authorization. See the [P61 detailed report](p61-pre-spend-gate.md).

## P62 Generalization Matrix Aggregator v0

P62 is a deterministic, no-live-LLM, no-provider, aggregate-only generalization matrix aggregator that runs after P61. It consumes only the published aggregate reports from multiple slices (P57, P58, P59, P60, P51-B required) and combines each slice's aggregate report set into a >=4 distinct-slice generalization matrix. P62 does not read source files, gold labels, private labels, ephemeral records, candidate pools, prompts, responses, or provider configs; it does not call providers, construct prompts, admit Evidence, change defaults, or authorize provider spend. P62 builds a canonical sanitized summary per eligible slice and uses an internal SHA-256 signature to deduplicate slices so that the same slice repeated four times cannot inflate `slice_count`. P62 publishes only counts (`content_distinct_input_count`, `duplicate_input_count`, `eligible_distinct_slice_count`, `exact_duplicate_inputs_rejected_count`) and never repo identities, datasets, paths, digests, or signatures. When >=4 distinct eligible slices are present, P62 writes a P57-compatible `--input-matrix` JSON handoff containing only the P57-required report paths for P57 to consume. It is not quality evidence, not a promotion/default gate, and not live-readiness evidence. See the [P62 detailed report](p62-generalization-matrix-aggregator.md).

## P63 Cross-Run Slice Collector / Matrix Runner v0

P63 is a deterministic, offline, no-provider, no-live-LLM, aggregate-only cross-run slice collector and orchestrator that runs after P62. It accepts only already-downloaded local per-run artifact directories, validates that each directory contains only the allowlisted aggregate report JSON files, builds a P62 slice manifest, and then runs P62 -> P57 -> P61 offline. P63 does not fetch artifacts from a network, call providers, construct prompts, read source files, tasks, candidates, prompts, responses, traces, or ephemeral records, and it does not expose run, repo, dataset, or directory identity. It is not a fetcher, not quality evidence, not provider spend authorization, not repo or dataset diversity proof, and not a promotion/default gate or live-readiness authorization. P63 emits only aggregate counts and status enums; any future live provider run requires a separate workflow_dispatch or human decision. See the [P63 detailed report](p63-cross-run-slice-collector.md).

The first real cross-run dry-run used four successful `ci_smoke` runs with `max_tasks=6` and `round_robin_public_buckets` (`py_flask`, `js_express`, `go_gin`, `rust_ripgrep`). P63 accepted all four sanitized slice directories, P62 reported four distinct eligible slices, and P57 reached `diagnostic_matrix_complete` over 24 aggregate tasks (`positive=9`, `no_gold=15`). P61 initially blocked with `blocked_missing_actionability` because P59 reported `blocked_missing_hard_distractor`.

P59B then repaired the hard-distractor/actionability precondition using a gold-free `metadata_hard_distractor_proxy_v1` and stricter workflow gates; it did not relax P61 and did not use labels to construct packs. P51-B then added a redaction-policy precondition so P61 can distinguish `required_defined_satisfied` from missing redaction policy without constructing prompts or payloads. A second four-slice round-robin dry-run (`py_flask` 27643271948, `js_express` 27643273360, `go_gin` 27643274763, `rust_ripgrep` 27643276402) reached `P61 status=micro_run_preconditions_met` with reason `all_required_preconditions_present`. This is still only a precondition signal: it does not authorize live LLM spend, does not change defaults, does not promote any policy, and does not alter EvidenceCore. A true P51-C live micro-run remains a separate explicit workflow_dispatch or human decision.

---

## 0. Executive Research Thesis

The most important current finding is not that semantic retrieval is solved. It is that OpenLocus now has an evidence-gated research system for studying semantic retrieval, QuIVer, LLM-derived views, graph signals, and admission guards without weakening the evidence contract.

The research posture is now quality/efficiency first, with necessary safety boundaries rather than context starvation. On public corpora or explicit opt-in remote runs, rich code context is acceptable: raw snippets, path/symbol/signature metadata, neighbor windows, top-k local candidates, and retrieval scores should be available to models when that improves quality and speed.

The invariant remains:

```text
candidate != fact
candidate/supporting channels -> current source read -> content_sha/range validation -> EvidenceCore
```

Within that system, real embedding models now show **candidate/file-level recall signal**, but the L1/L2 large-slice tests also show that dense-only/global dense is unstable at larger scale, with low SpanF0.5 and high primary false-positive risk. P20-LS-A similarly shows that low-context/query-only LLM aliases are not enough. RRF remains the recall base, symbol/regex remain precision anchors, and `query_noise_plus_rrf_agree_min` remains the strongest current guard candidate. Dense, QuIVer, LLM-derived views, and graph signals must remain candidate/supporting/diagnostic layers for now, but P21-G should test cross-model context injection rather than continuing metadata-only model inputs or single-model token sweeps.

---

## 1. Evidence Strength

| Evidence tier | What it supports | What it does not support |
|---|---|---|
| **Strong: EvidenceCore, materialization gates, citation validation, CI privacy gates** | Fact authority is working: current-file validation, `content_sha`, strict line ranges, citation validity, RUN/SCORE separation, secret/private-label exclusion. | Does not prove any retrieval strategy should be default, and should not force low-context model inputs on public/opt-in runs. |
| **Strong for failure discovery: R29 on R26 auto-stress 1100 tasks** | RRF/symbol/guard/dense_mock/graph failure patterns are visible across broad stress buckets. | R26 labels are weak/mined/deterministic; not human promotion evidence. |
| **Moderate: real-provider P8/P9 CI scale-up** | Real embeddings show initial, repeatable file-level recall signal on bounded public repo slices; QuIVer BQ diagnostics are worth continuing. | Samples are small; span quality and default safety are not proven. |
| **Moderate-to-strong negative evidence: L1/L2 large-repo slices** | Dense-only/global dense is unstable on larger slices; all four L2 repos had PFP=`1.0`, and SpanF0.5 remained extremely low. | Still not a full-repo exhaustive benchmark; does not prove rich raw-code embedding views are useless. |
| **Directional: P1-P7 self-tests and bounded runs** | Provider, LLM status, local harness, and initial anchor-seeded hypotheses work mechanically. | Tiny/self-test outcomes can be contradicted by larger public corpus runs. |
| **Not quality evidence: dense_mock, LLM-generated stress, unavailable QuIVer/TDB** | Useful for failure discovery and plumbing. | Must not be used as semantic quality or promotion evidence. |

---

## 2. Main Research Conclusions

### 2.1 RRF is still the recall base

RRF remains the strongest recall channel on R26/R29: FileRecall@1 is about `0.803`, and FileRecall@5 is about `0.923`. This confirms that fusing local lexical/symbol channels improves coverage.

Its main risk is also clear: high primary false-positive rate, about `0.453` in R29. RRF is a strong recall base, but it should not directly become primary admission without guards, anchors, or an admission model.

### 2.2 Symbol and regex are precision anchors

Symbol search remains the precision anchor. In R29 it has SpanF0.5 around `0.291` and primary_false_positive_rate around `0.080`. Its weakness is high abstention and incomplete extraction coverage, not excessive noise. This makes symbol extraction repair a promising recall-safe improvement path.

Regex remains a foundational anchor too, but it needs normalization. User queries should not default to raw regex. The system needs separate modes for literal search, explicit regex search, identifier search, and path search. R39/R40 support continuing validation of `regex_hybrid_normalized`.

### 2.3 `query_noise_plus_rrf_agree_min` is the best current guard candidate

In R29, `query_noise_plus_rrf_agree_min` preserved RRF recall while reducing primary false-positive rate from about `0.453` to about `0.106`, with guard_recall_kill_rate around `0.003`. This is the clearest current guard signal.

It still cannot be promoted. R23 showed many bucket regressions, and R26/R29 are not human-reviewed promotion tiers. It is a strong guard candidate for continued study, not a default strategy.

### 2.4 Real embeddings help file recall but not span evidence yet

P8/P9 CI scale-up showed initial, repeatable file-level recall signal on bounded public corpus slices. For example, the bounded Flask P2 run achieved FileRecall@1=`0.800` and FileRecall@3=`1.000`; in the multilingual bge-m3 smoke, Go/Python were strong, Rust was moderate, and JavaScript Express was weaker.

The later L1/L2 large-slice tests weakened this optimistic signal. At 60 tasks / 1000 records / 2000 files, Django/Kubernetes dropped to roughly `0.25` FileRecall@1, Next.js/Deno were near `0`, all four repos had primary_false_positive_rate=`1.0`, and the best SpanF0.5 was only about `0.022`. Dense retrieval is currently a candidate-support channel, not a primary span-evidence channel.

### 2.5 Bigger embedding models did not dominate in the first slice

P9a compared `BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`, `Qwen/Qwen3-Embedding-4B`, and `Qwen/Qwen3-Embedding-8B` on the same Flask slice. In this small sample, the largest model did not dominate: bge-m3 and Qwen 0.6B/4B reached FileRecall@1=`1.000`, while 8B reached `0.800`.

This does not prove smaller models are better, but it is enough to avoid assuming the largest model is best without same-task bakeoffs. Future bakeoffs should compare models on the same tasks, corpus, caps, latency, and cost.

### 2.6 Anchor-seeded dense/QuIVer is promising but not safe yet

Early tiny/self-tests made anchor-seeded dense/QuIVer look promising: P4 once showed added_gold=`2` and added_false=`0`. But P8a on a real public Flask slice produced the opposite caution signal: FileRecall@1=`1.000`, but added_gold=`3` and added_false=`15`.

L1 P4 strengthened the block: on `py_django`, the best anchor strategy had added_gold=`0` and added_false=`40`; on `go_kubernetes`, it had added_gold=`5` and added_false=`44`.

This is exactly why the research harness matters: a small optimistic signal was constrained by a more realistic corpus slice. The conclusion is not that anchor-seeding is useless; it is that anchor-seeded dense/QuIVer must remain supporting-only while span targeting and false-span suppression are improved.

### 2.7 QuIVer is still diagnostic, but BQ signals are no longer empty

P3 ran BQ readiness diagnostics on real embeddings. On the Flask slice, BQ_overlap@10=`0.680`, BQ_overlap@50=`0.728`, BQ_vs_f32_MRR=`1.000`, and quiver_fit was marked `promising`. This means the BQ/QuIVer direction is worth continuing.

L1 P3 kept BQ diagnostics non-empty on larger slices: Django was marked `promising`, Kubernetes `mixed`. This remains BQ diagnostic evidence only, not QuIVer graph/ANN quality.

But the QuIVer graph/Vamana backend is not implemented, and no ANN graph quality claim exists yet. QuIVer remains diagnostic/prototype-only.

### 2.8 Graph expansion remains blocked

R25/R29/P6 support the same conclusion: graph is not safe as default expansion. In R29, graph_basic added_gold=`0` and added_false=`437`. Graph is more likely useful as an explainer, rerank feature, impact signal, or test selector than as default recall expansion.

### 2.9 LLM-derived views are useful for stress and hints, not facts

The real LLM provider has run successfully, and P5 generated derived/stress outputs. These outputs must remain `not_evidence=true`: the LLM must not generate Evidence, gold labels, citation verdicts, or promotion verdicts.

The useful role for LLMs is query aliases, symbol tags, intent views, candidate rerank/filter/span narrowing, and failure/stress generation. LLMs can expand the failure surface and help interpret rich candidate context, but they cannot replace EvidenceCore.

P20-LS makes this boundary executable: LS0 validates safety gates, LS1 generates `not_evidence=true` query aliases and evaluates them as candidate/supporting-only retrieval expansion, and LS3 writes only the public stress split by default. The initial offline slice was already a caution signal. P20-LS-A then ran the real LLM provider (`[mk]Kimi-K2.7-Code`) on self-test plus 9 real CI corpus runs. Schema/guardrail behavior was acceptable, but low-context/query-only alias quality failed completely: 0/9 real runs passed quality, added_gold_span=`289` vs added_false_span=`8312` (~28.8:1 false:gold), and average fabricated_identifier_rate was ~`0.459`. Therefore, scale-up is blocked for the low-context/query-only alias mode. This is not a verdict on rich-context LLM retrieval; future alias/retrieval research should use source snippets, candidate metadata, symbol/path inventories, and prompt/context matrices.

### 2.10 P21-G should study cross-model context injection effects

The next model phase should stop treating metadata-only remote inputs as the default research posture, but it should also avoid pretending that one model's best token budget is an OpenLocus-wide law. For public corpora and explicit opt-in remote runs, models should receive enough code facts to be useful: raw code snippets, path headers, signatures, symbol bodies, neighboring lines, local retrieval scores, hard distractors, and top-k candidate sets. Necessary boundaries remain: exclude secrets, ignored files, provider keys, and private labels/gold answers; keep EvidenceCore as final fact authority; do not use LLMs as promotion judges.

P21-G should compare context atoms and packs across embedding and LLM model profiles, query buckets, repo types, roles, and layouts. The primary variables are not fixed token caps but injected information: signatures, matched lines, source/test/doc flags, retrieval scores, body windows, neighbor symbols, related tests, hard distractors, candidate uncertainty, and inventory grounding. P21-G1E showed naked dense context atoms remain supporting-only: `pack2_evidence_sketch` had the best model-averaged SpanF0.5 and `atom_signature` the best FileRecall@5, but false spans dominated (`17924` vs `2876`). P21-G2E showed constrained dense has modest supporting value: `dense_atom_signature_rrf_file_constrained` averaged SpanF0.5 `0.163` vs RRF `0.1508`, PFP avg `0.0`, useful in `11/16` runs. Dense remains non-primary. P21-G3L showed LLM rich candidate roles can help but are model/repo specific: `llm_span_narrow` had avg ΔSpanF0.5 `+0.0418`, with strongest signal from Flash/Kimi on `py_flask`; filter/abstain reduced false spans but often killed gold; GLM-5.1 schema degradation blocks scale-up until prompt/schema repair. Every report must measure quality, efficiency, and cross-model generalization: SpanF0.5, added_gold/false, PFP, provider calls, input/output tokens/chars, p50/p95 latency, cost, model-averaged treatment effect, per-model effect, and effect variance.

P21-G3L-R is now the structured-output repair path for LLM roles. The rich-candidate harness supports `prompt_only`, `json_object`, `json_schema_strict`, and `tool_call` output modes, records provider-rejection fallback diagnostics, and allows one schema repair retry without another fallback ladder. The first GLM-focused smoke ran 4 output modes × 2 repos: `tool_call` is the preferred GLM mode so far (avg SpanNarrow Δ `+0.0677`, repair success `3/5`), `prompt_only` should be blocked, `json_object` remains insufficient, and `json_schema_strict` is mixed. A sequential low-concurrency `tool_call` rerun removed provider HTTP 429 noise and improved GLM SpanNarrow avg Δ to `+0.1361`; use GLM `tool_call` for the next bucketed P21-G3L run.

P21-G3B adds public-safe bucket sampling (`task_bucket` and `task_risk_tags`) and confirms that global LLM roles are unsafe across mixed buckets. In the 6-run bucketed smoke, LLM roles reduced PFP but frequently killed gold spans. `span_narrow` remains useful on likely-positive/high-confidence tasks, but it is not a cross-bucket default. `filter` and `abstain` should be routed only to negative/dense-false-positive/ambiguous buckets, not applied globally.

P22/P23 shifts the next phase from channel testing to evidence-seeking policy surfaces. The current freeze has two separate local, no-remote decision surfaces: `r20_positive` for positive candidate reach and `r26_guard` for no-gold guard stress. On the capped R20 positive slice, RRF remains the reach base (`Reach@5=0.975`, `SpanReach@5=0.95`), but symbol has the best local SpanF0.5 (`0.3169`), and `symbol_regex_union` is the best precision/reach experimental baseline candidate for P25/P30. On R26, BM25/RRF still create no-gold false primary (`0.2833`), while symbol/regex/union/guard abstain. This confirms P25/P30 must optimize policy surfaces separately: reach preservation, false-primary suppression, and EvidenceCore materialization are distinct success layers.

### 2.11 P25 bucket-routed LLM role policy evaluator is ready

`eval/p25_bucket_policy.py` is a deterministic, no-remote policy evaluator. The
committed report is a sanitized self-test scaffold (`status=self_test_only`,
`not_quality_evidence=true`), not quality evidence. Real P25 evaluation now
requires ephemeral SCORE-phase records from
`eval/p21_llm_rich_candidate.py --p25-policy-records-out`; those records remain
under runner temp and are not uploaded, while P25 uploads aggregate metrics only.
The `bucket_routed_v0` policy routes by allowlisted public `task_bucket`/
`task_risk_tags`: `llm_span_narrow` for likely-positive/high-confidence buckets,
fixed a-priori `llm_filter`/`llm_abstain_filter` for negative/
dense-false-positive/ambiguous buckets, skips LLM for exact-symbol-plus-unique
anchors, and otherwise falls back to the candidate baseline. Aggregate P21
summaries and non-ephemeral schemas are rejected with
`status=insufficient_task_detail`. This provides a scaffold for future P25/P30
evidence-seeking policy surfaces, not a promotion claim.

The first real P25 remote smoke used this safe P21→P25 ephemeral handoff on six
successful aggregate runs (`Flash/Kimi/GLM × py_flask/js_express`, 18
bucket-sampled tasks each). `bucket_routed_v0` reduced added false spans
`108 -> 28` and mean PFP by about `0.0926`, but also reduced added gold spans
`24 -> 21`; mean SpanF0.5 delta was only slightly positive (`+0.0026`) and
repo/model-dependent. Therefore P25 is useful as a false-primary reducer signal
for P30 Admission V3, not a default policy.

### 2.12 P30 Admission Model V3 scaffold is ready

`eval/p30_admission_model_v3.py` is a deterministic, no-remote admission model
research harness (schema `p30-admission-v3-report-v1`). The committed
self-test artifact is a sanitized synthetic scaffold
(`status=self_test_only`, `not_quality_evidence=true`), not a quality result.
Real P30 evaluation requires the same ephemeral
`p25-policy-records-ephemeral-v1` records produced by
`eval/p21_llm_rich_candidate.py --p25-policy-records-out`; those records stay
under runner temp and are not uploaded, while P30 uploads aggregate metrics
only.

P30 routes only from RUN-phase public/observable features: public
`task_bucket`, `task_risk_tags`, and `route_features`. `score_group`,
`has_gold`, gold spans, private labels, and outcome metrics are used only for
aggregate scoring after actions are chosen. Allowed actions are `abstain`,
`admit_symbol_regex_union`, `admit_rrf_primary`, `admit_llm_span_narrow`,
`apply_llm_filter`, `supporting_only`, and `weak_candidate_only`. The
`admission_v3` scorecard combines explainable monotonic feature scores (query
noise, exact/unique symbol anchor, symbol/regex/local anchors, RRF backed by
anchor, LLM span-narrow validity/within candidate) with hard guards for
negative/ambiguous/dense-false-positive buckets. Dense and graph signals are
allowed only as supporting features; they cannot invent primary evidence.

The evaluator compares `candidate_baseline`, `llm_span_narrow`, `llm_filter`,
`llm_abstain_filter`, `bucket_routed_v0` (reused from P25), and
`admission_v3`. It reports task count, SpanF0.5, PFP, added gold/false spans,
filter gold kill rate, abstain rate, action counts, score bands,
selective risk proxy, mean deltas versus the candidate baseline and
`bucket_routed_v0`, and explicit outcome-fallback counters for actions that do
not have measured outcomes in a given ephemeral record. Public output is
recursively scanned for forbidden keys
(raw query/snippet/prompt/response/gold/gold_spans/private labels/provider
keys). `promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`external_calls=0`.

P30 is not a promotion candidate. The next step is to run it against real P25
ephemeral smoke records and compare the scorecard to P25 `bucket_routed_v0`
and the P22/P23 evidence-seeking guard surfaces.

The first real P30 remote smoke completed six successful runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each). It
confirmed that the current `admission_v3` scaffold is too conservative:
baseline produced `27/102` added gold/false spans, P25 `bucket_routed_v0`
produced `19/39`, and P30 `admission_v3` produced `17/41`. P30 matched the mean
PFP reduction (`-0.0833`) but had worse mean SpanF0.5 delta than
`bucket_routed_v0` (`-0.0102` vs `+0.0010`). Non-zero fallback counts show the
current ephemeral handoff lacks measured outcomes/features for the richer local
admission actions. Next: extend P21/P22 handoff with measured
`symbol_regex_union` / `rrf_primary` outcomes and safe route features before
rerunning P30.

P30-H1 implemented that handoff repair. It succeeded as measurement repair but
failed as policy improvement. Six real runs produced zero selected-action
fallback for `admission_v3_h1`, so the comparison is now quality-comparable.
However, P25 `bucket_routed_v0` remained better: `20/37` added gold/false with
mean ΔSpanF0.5 `+0.0020`, versus P30-H1 `18/87` with mean ΔSpanF0.5 `-0.0350`.
The new conclusion is that missing handoff was masking a scorecard problem:
`admit_symbol_regex_union` is too broad and admits many false spans. Next P30-H2
should make local-anchor admission stricter instead of adding more channels.

P30-H2 made local-anchor admission stricter, but this also failed as a quality
repair. It stayed fallback-free and quality-comparable, but produced `15/90`
added gold/false versus H1 `18/87` and P25 `bucket_routed_v0` `16/36`; mean
ΔSpanF0.5 was `-0.0370` for H2 versus `-0.0346` for H1 and `-0.0052` for P25.
The updated diagnosis is that primary-admission breadth was not the only issue:
weak/supporting/filter actions still preserve too much span-level false cost.
P30-H3 now models action-specific span cost and false-span budgets as a
score-phase-only, diagnostic accounting layer. It does not change admission
routes; it derives per-action cost from the existing `bucket_routed_v0`,
`admission_v3_h1`, `admission_v3_h2`, and baseline comparison policies, and emits
a dedicated `artifacts/p30_admission_v3/p30_h3_span_cost_report.json` artifact
with schema `p30-h3-action-span-cost-report-v1`.

The real P30-H3 smoke (6 successful runs, 108 tasks) explains the P30 failure
mode more precisely. Baseline was `27/102` added gold/false spans; P25
`bucket_routed_v0` remained the strongest reference at `19/45`; P30-H1 was
`18/88`; P30-H2 was `15/90`. H3 shows P30-H1/H2 false-span cost is dominated
by primary local-admit actions (`admit_symbol_regex_union`, and H2
`admit_rrf_primary`), while `supporting_only` mainly costs recall by killing
gold rather than adding false spans. Therefore P30-H4 should use explicit
action budgets for primary local-admit actions instead of globally tightening
all non-primary actions.

### 2.13 P31 Candidate Reach Ceiling Study scaffold is ready

`eval/p31_candidate_reach_ceiling.py` is a deterministic, no-remote diagnostic
scaffold (schema `p31-candidate-reach-ceiling-report-v1`). The committed
self-test artifact is sanitized synthetic data (`status=self_test_only`,
`not_quality_evidence=true`), not quality evidence. P31 is SCORE-phase-only:
labels are loaded only after RUN and are used only for aggregate metrics. It
does not influence routing or admission decisions.

P31 measures whether candidate evidence alone reaches the gold label before any
routing or admission. Inputs are the same ephemeral
`p25-policy-records-ephemeral-v1` records used by P25/P30. When records do not
yet carry candidate evidence pools, P31 reports
`candidate_pool_availability=missing_candidate_pool` and
`reach_metrics_available=false`, then computes outcome-only fallback metrics
rather than fabricating reach zeros. When pools are present, it reports
aggregate `GoldFileReach@K`, `GoldSpanReach@K`, `GoldSpanExactReach@K`,
`CandidateAbsentRate@K`, and `FileRightSpanWrongRate@K` for K=1/3/5/10/20, plus
`ModelMissGivenGoldPresent@K` against `candidate_baseline`, action/strategy
diagnostics (`FilterKillGoldRate`, `AdmissionFalsePrimaryRate`,
`AdmissionFalseSpanPerNoGoldTask`), `EvidenceCoreRejectRate` (`not_measured`
when rejection fields are not present), and a K=5 failure funnel with
`funnel_sums_to_positive_tasks=true`.

P31-H1 extends the P21 rich-candidate handoff so ephemeral records now carry
lightweight candidate pools (`p31_candidate_pools`) and private SCORE-phase gold
spans (`p31_score_gold`), tagged with `p31_h1_candidate_reach_handoff=true` and
`p31_h1_schema_version="p31-h1-candidate-reach-handoff-v1"`. Pool items keep only
`rank`, `path`, `start_line`, `end_line`, plus optional `content_sha`, `score`,
and `channels`; no snippets, raw queries, prompts, responses, or provider fields.

P31-H2 adds a strategy-level reach matrix across `candidate_baseline`,
`rrf_primary`, `symbol_regex_union`, `llm_span_narrow`, `llm_filter`, and
`llm_abstain_filter`. It reports reach@K per strategy and, when H1 pools are
present, aggregate reach by public repo and task bucket, unique reach share,
pairwise file/span overlap and Jaccard span, marginal gain in both directions,
and union reach for fixed strategy combinations. Missing strategy pools are
reported as `availability=missing_pool`, not fake zeros.

Public artifacts are aggregate-only: no per-task rows, raw queries, snippets,
prompts, responses, candidate paths/spans, gold spans, private labels, or
provider fields. Safety flags are locked: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`candidate_not_fact=true`, `remote_calls_by_p31=0`,
`score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.

The real P33-B subtype smoke (6 successful runs, 108 task observations: 36
positive and 72 no-gold) confirms the P33 result at finer granularity: no
observed subtype bucket is primary-safe. `span_overlap` is the best coarse
agreement class (`GoldSpanReach=1.0`, `false_per_gold≈1.78`) but remains
net-negative under a 2x false-span penalty. `symbol_regex_fusion` also has
perfect subtype span reach in this smoke but still costs `24/66` added
gold/false (`false_per_gold=2.75`). `same_file_only` is weaker
(`false_per_gold≈2.18`), and `disagree` / `single_source` buckets are dominated
by false-span cost. RRF backing helps but does not make anchors safe
(`rrf_yes false_per_gold≈4.67`). P33-B subtype buckets should therefore feed
P32/P30-H4 action budgets, not primary admission.


The first real P31-H1 reach smoke completed six successful runs
(`Flash/Kimi/GLM × py_flask/js_express`, 108 total tasks, 48 positive tasks).
H1 handoff was detected in every run and reach metrics were available in every
run. Candidate baseline reached only `24/48` positive tasks at both file and
span level at K=5 (`GoldFileReach@5=0.5000`, `GoldSpanReach@5=0.5000`), while
`FileRightSpanWrongRate@5=0/24`. This points to candidate absence as the first
bottleneck in this smoke, not within-file span localization. P25
`bucket_routed_v0` still had lower false-span cost than P30-H1/H2 on the same
runs (`20/46` added gold/false vs H1 `18/87`, H2 `15/90`), but P31 shows
admission tuning alone cannot recover the missing half of positive tasks.

The P31-H2 strategy reach matrix rerun shows why the next repair should target
anchors, not another LLM role. At K=5, `candidate_baseline` reaches `24/48`
positive spans, `rrf_primary` reaches `21/48`, and `symbol_regex_union` reaches
`42/48`. `symbol_regex_union` contributes `18/48` unique span hits, while
`candidate_baseline + rrf_primary` and `candidate_baseline + llm_span_narrow`
remain at `24/48`. Therefore `symbol_regex_union` is a high-reach candidate
expansion source, but P30-H3 already showed it is unsafe when admitted directly
as primary. The next steps are P33 anchor repair/calibration and P32/P30-H4
action budgets before local-anchor primary admission.

The first real P33 anchor precision smoke confirms that no observed anchor
bucket is primary-safe yet. The strongest calibration cell (`a3_r0_s2`: span
agreement, low-risk, RRF-span-backed) reaches `42/48` positive spans, but has
`false_per_gold≈8.69` and `net_span_value_2x=-786`. `symbol_regex_agree_span`
reaches `9/9` positives in its bucket, but still has `false_per_gold=4.0`;
`symbol_regex_disagree` reaches `27/30` but has `false_per_gold≈13.44`, and
`regex_only` is worse (`false_per_gold=22.5`). Therefore P33 preserves the
P31-H2 conclusion that anchors are the main reach lever, while strengthening
the P30-H3 conclusion that anchor primary admission must be budgeted. P33-B
should now repair/calibrate symbol and regex subtypes; P32/P30-H4 should not
promote any local-anchor bucket without held-out budget validation.

### 2.14 P33 Reach-Preserving Precision Anchor Repair scaffold is ready

`eval/p33_anchor_precision_repair.py` is a deterministic, no-remote diagnostic
scaffold (schema `p33-anchor-precision-repair-report-v1`). It consumes the same
P21/P31-H1 ephemeral records that P31 uses: it needs `p31_candidate_pools`,
`p31_score_gold`, public `task_bucket`/`task_risk_tags`, and pre-SCORE
`route_features`. Labels and gold spans are used only in the SCORE phase for
aggregate metrics. When candidate pools or gold spans are missing, P33 reports
`availability=missing_pool`/`not_measured` rather than fabricating zeros.

P33 defines an anchor taxonomy v1 with buckets such as
`exact_unique_symbol_anchor`, `unique_symbol_anchor`, `symbol_anchor_only`,
`regex_anchor_only`, `symbol_regex_agree_span`/`agree_file`/`disagree`,
`rrf_anchor_agree_span`/`agree_file`/`unbacked`, public buckets
(`positive`/`ambiguous`/`negative`), risk tags (`hard_distractor`,
`dense_false_positive`), query-noise levels, and bounded composites like
`symbol_regex_agree_span_low_risk`, `rrf_span_backed`, and
`negative_or_ambiguous_with_anchor`. For each bucket it reports task counts,
positive/no-gold counts, `GoldFileReach@5`, `GoldSpanReach@5`,
`FileRightSpanWrongRate@5`, span cost aggregates (`added_gold_span`,
`added_false_span`, `false_per_gold`, `gold_per_false`, `net_span_value_1x/2x`),
mean `SpanF0.5` and mean `primary_false_positive_rate`, and a diagnostic class
(`primary_candidate_safe_observed`, `supporting_only_observed`,
`needs_budget_guard`, `blocked_high_false_cost`, or
`insufficient_denominator`).

A 3D calibration matrix over `anchor_strength` (0=none, 1=symbol_or_regex_only,
2=file_agreement, 3=span_agreement, 4=exact_unique_symbol_span_agreement),
`risk_level` (0=low/positive, 1=ambiguous, 2=negative/high risk), and
`rrf_backing_level` (0=none, 1=file-only, 2=span) reports the same aggregate
diagnostics and flags monotonic-sanity violations. A `p33_to_p32_handoff` section
groups budget candidates by diagnostic class, with `frozen_policy=false`.

Public artifacts are aggregate-only: no per-task rows, task IDs, raw queries,
snippets, prompts, responses, route features, candidate paths/spans, gold spans,
private labels, or provider fields. Safety flags are locked:
`promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`remote_calls_by_p33=0`, `score_phase_only_metrics=true`,
`aggregate_only_public_artifact=true`.

### 2.15 P33-B Anchor Subtype Calibration scaffold is ready

`eval/p33b_anchor_subtype_calibration.py` is a deterministic, no-remote diagnostic
scaffold (schema `p33b-anchor-subtype-calibration-v1`). It extends the P21
ephemeral handoff with private per-candidate subtype metadata
(`p33b_anchor_subtypes`, schema `p33b-anchor-subtypes-v1`) describing each
`symbol_regex_union` candidate as `symbol_only`, `regex_only`, or
`symbol_regex_fusion`, with agreement classes (`single_source`, `same_file_only`,
`span_overlap`, `disagree`), `rank_bin`, `candidate_count_bin`,
`span_width_bin`, and per-candidate `rrf_backing`. The handoff also adds
`symbol_primary` and `regex_primary` candidate pools for P31 reach studies.

P33-B consumes those ephemeral records, joins private subtype rows to the
`symbol_regex_union` candidates, and uses `p31_score_gold` and strategy outcomes
only in the SCORE phase for aggregate metrics. It reports bounded subtype-bucket
diagnostics: task counts, positive/no-gold counts, `SubtypeGoldFileReach@5`,
`SubtypeGoldSpanReach@5`, `FileRightSpanWrongRate@5`,
`UniqueSubtypeSpanReach@5`, span cost aggregates with coarse task-level
attribution, `delta_vs_candidate_baseline`, and diagnostic classes with minimum
denominator gating. A 3D calibration matrix over `source_strength` (0=regex_only,
1=symbol_only, 2=symbol_regex_fusion), `match_quality` (0=disagree,
1=same_file_only, 2=span_overlap_unbacked, 3=span_overlap_rrf_backed), and
`risk_level` reports the same diagnostics plus monotonic-sanity checks. A
`p33b_to_p32_handoff` groups budget candidates by diagnostic class, with
`frozen_policy=false`.

Public artifacts remain aggregate-only: no per-task rows, task IDs, raw queries,
snippets, prompts, responses, candidate paths/spans, gold spans, private labels,
route features, subtype rows, or provider fields. Safety flags are locked:
`promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`remote_calls_by_p33b=0`, `score_phase_only_metrics=true`,
`aggregate_only_public_artifact=true`.

### 2.16 P32 / P30-H4 deterministic budget overlay is ready

`eval/p30_admission_model_v3.py` now implements `admission_v3_h4`, a P32/P30-H4
budget-overlay policy. H4 is deterministic, no-remote, and diagnostic-only. It
reads private P33-B subtype metadata from the P21 ephemeral handoff
(`p33b_anchor_subtypes`, `p33b_anchor_subtypes_schema`) and uses it, together
with RUN-phase public features, to test budgeted demotion. It does not change
Rust/EvidenceCore semantics, the default pipeline strategy, or any production
admission route.

P33-B showed that no subtype is primary-safe: even the best `span_overlap`
bucket has `false_per_gold≈1.78` and negative `net_span_value_2x`, while
`disagree` and `single_source` are dangerous and `same_file_only` is weaker.
Consequently H4 never selects `admit_symbol_regex_union`, `admit_rrf_primary`,
or `admit_llm_span_narrow` from subtype evidence alone. Its actions are limited
to `apply_llm_filter`, `supporting_only`, `weak_candidate_only`, and `abstain`.
Rules are conservative: negative/dense/ambiguous tasks are filtered or
abstained; `span_overlap` in low-risk public buckets becomes `supporting_only`
when RRF-backed and `weak_candidate_only` otherwise; `same_file_only` becomes
`weak_candidate_only` only in clearly positive buckets; `disagree`/
`single_source` are filtered unless the public bucket is strongly positive and
query noise is low. Missing subtype metadata degrades to a `bucket_routed_v0`-
like conservative fallback.

The normalized in-memory task carries the private P31/P33-B handoff fields
(`p31_candidate_pools`, `p31_score_gold`, `p33b_anchor_subtypes`,
`p33b_anchor_subtypes_schema`) for SCORE-phase use, but these keys are never
emitted in public P30 artifacts. Report flags are locked to
`h4_budget_overlay=true`, `promotion_ready=false`,
`default_should_change=false`, and, when P33-B records are present,
`h4_available=true` / `p33b_handoff_detected=true`. H4 reports
`quality_comparable`, `blocked_by_missing_action_outcomes`, and
`selected_action_fallback_rate` like H1/H2, and the real-provider CI gate now
requires H4 to exist and, on `p21_llm_rich` records, to be quality-comparable
with zero selected-action fallback.

The first real P30-H4 remote smoke completed 6 successful runs. It was
quality-comparable and fallback-free, but it was too conservative: H4 produced
`0` added gold spans and `0` added false spans, with mean SpanF0.5 `0.0000`.
P25 `bucket_routed_v0` remains the best reference on the same runs (`27/34`
added gold/false, mean SpanF0.5 `0.0768`). H4 is therefore a safety lower bound
and useful negative result, not a deployable admission policy. The next H4
iteration should test budgeted selective re-admission or `request_more_context`,
not all-demotion.

### 2.17 P32 / P30-H4B selective primary re-admission is ready

`eval/p30_admission_model_v3.py` now also implements `admission_v3_h4b`, a P32/P30-H4B
selective primary re-admission diagnostic. H4B is deterministic, no-remote, and
diagnostic-only. It uses the same private P33-B subtype handoff and RUN-phase
public features as H4, but tests an extremely narrow strict conjunction for
primary-admit actions rather than demoting everything.

The strict gate selects `admit_symbol_regex_union` only when the best subtype is
`symbol_regex_fusion` + `span_overlap` + `rrf_backing`, `local_anchor` and
`symbol_regex_agree_span` are true, `query_noise <= 0.1`, the public bucket/tag is
in a low-risk positive set, and either `exact_unique_symbol_anchor` or
`rrf_anchor_agree_span` holds. If `rrf_backed_by_anchor` and
`rrf_anchor_agree_span` also hold, H4B may optionally select `admit_rrf_primary`
instead. All other tasks are hard-guarded or demoted, including negative/dense/
ambiguous/hallucination/high-noise cases and any best subtype that is
`regex_only`, `same_file_only`, `disagree`, or `single_source`.

Public outputs include `h4b_available`, `h4b_budget_overlay=true`,
`h4b_selective_readmission=true`, `h4b_primary_opportunity_count`, and rule
aggregate counts (`strict_union_re_admit`, `strict_rrf_re_admit`, `hard_guard`,
`missing_handoff`, `demote_span_overlap`, `demote_same_file`,
`filter_dangerous_subtype`). H4B also reports `quality_comparable`,
`selected_action_fallback_rate`, `false_per_gold`, `net_span_value_2x`, and a
span-cost summary from P30-H3 accounting. On synthetic self-test it is
quality-comparable and fallback-free, and fires a small number of strict primary
opportunities. The real H4B smoke completed 6 successful provider runs: H4B is
quality-comparable and fallback-free, and it escapes H4A's all-demotion failure
(`0/0 -> 24/41` added gold/false). It still does not beat P25
`bucket_routed_v0` (`25/30` added gold/false, mean SpanF0.5 `0.0683` vs H4B
`0.0433`), so H4B is a promising research direction but not a promotion
candidate. The next iteration should tighten strict RRF re-admission or use
`request_more_context` before primary admission.

---

## 3. Current Hypotheses

| Hypothesis | Current state | What would confirm it |
|---|---|---|
| RRF should remain the recall base. | Strongly supported by R29, but needs guard. | Stable recall under guard across human-reviewed and stress tiers. |
| Symbol/regex should be precision anchors. | Strongly supported. | Broader symbol repair validation without PFP increase. |
| Dense should remain supporting-only for now. | Current L1/L2 evidence blocks dense-only/global dense as primary/default. | Rich raw-code/snippet views add gold more than false spans with low PFP and acceptable latency/cost. |
| Anchor-seeded dense/QuIVer may be safer than global dense. | Plausible but mixed. | P4-like tests on multiple repos show repeatable false-span suppression. |
| BQ diagnostics may be compatible with current code-embedding distributions. | Diagnostic signal promising on Flask. | Sharded BQ/proto graph beats flat f32 or improves latency without false-span growth. |
| Smaller embedding models may be enough. | Initial P9 supports continued bakeoff. | Same-task model bakeoff across more repos with latency/cost. |
| LLM-derived views can expand failures safely. | Mechanically supported, not quality-proven. | Rich context derived views add gold or stress coverage without inducing primary hallucinations. |
| LLM query aliases can improve anchors without pollution. | Low-context P20-LS-A query aliases are blocked for `[mk]Kimi-K2.7-Code`: 0/9 real quality pass, false:gold span ≈28.8:1, avg fabricated identifier rate≈0.459. | A grounded variant succeeds: aliases selected from repo inventories or top-k candidate context, `alias_added_gold > alias_added_false`, no PFP increase, low fabricated identifier rate. |
| Context atoms can generalize across model families. | Planned P21-G hypothesis. | Signature/matched-lines/scores/flags/body-window atoms show positive model-averaged treatment effect with low model variance and no PFP increase. |
| Rich LLM candidate support can improve span targeting. | Planned P21-G role hypothesis. | Rerank/filter/span-narrow over snippet-backed local candidates improves SpanF0.5 and reduces false spans at acceptable latency/cost. |

---

## 4. Contradictions and Negative Results

These negative results are among the most valuable findings because they prevent premature optimism:

1. **P4 tiny optimism weakened by P8a**: tiny self-test had added_false=`0`; the public Flask slice had added_false=`15`.
2. **Dense file recall and span quality diverge**: P8/P9 show good FileRecall but low SpanF0.5.
3. **RRF recall is coupled with false-primary risk**: raw recall is not enough; admission is critical.
4. **Graph expansion is repeatedly net-negative**: graph_basic mostly adds false spans and almost no gold.
5. **Larger embedding models did not win the first bakeoff**: 8B did not dominate 0.6B/4B/bge-m3.
6. **JS Express underperformed Go/Python/Rust**: embedding quality varies across language/framework buckets.
7. **P20-LS low-context alias expansion failed real-provider scale-up**: all guardrails passed, but query-only aliases produced far more false spans than gold spans (8312 vs 289 on real CI runs), with high fabricated identifier rates. This blocks low-context LLM alias scale-up, not rich-context LLM retrieval.

---

## 5. Current Quality and Boundary Policy

The new research priority is quality and efficiency. Boundaries should protect the fact layer and secrets, not starve the model of useful public-code context. All conclusions depend on preserving these necessary boundaries:

- `EvidenceCore` remains the only authoritative fact layer.
- Dense, QuIVer, graph, and LLM-derived outputs remain candidate/supporting/diagnostic, not Evidence.
- Evidence must come from reading current source files and validating `content_sha` plus line ranges.
- RUN phase must not read private labels; SCORE phase reads labels only after run artifacts exist.
- Real providers run only under `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1`.
- Reports and artifacts must not upload provider URLs/keys, private labels, or gold answers. Raw snippets may be sent to providers in explicit public/opt-in rich-context runs, but should not be committed as artifacts unless intentionally documented.
- Unavailable strategies must be reason-only and must not emit fake quality numbers.

Allowed in quality-first public/opt-in remote runs:

- raw code snippets/chunks after secret and ignore filtering;
- path, symbol, signature, doc heading, and neighbor-line context;
- top-k local candidate metadata and retrieval scores;
- prompt/context matrices that trade quality, cost, and latency.

---

## 6. What the Research Has Actually Established

The research has established four things with reasonable confidence:

1. **The fact-layer safety constraints are executable**: EvidenceCore, materialization, and citation validation are implemented across local retrieval, store, graph, dense, and CI runner paths.
2. **Local lexical/symbol/RRF remain the backbone**: real models did not replace RRF/symbol/regex; they made anchors and guards more important.
3. **Real models are useful but context-sensitive**: embeddings have file-level signal, LLMs can expand stress/derived views, and QuIVer BQ deserves continuation; none should directly become facts, but future tests should give models richer code context.
4. **The experiment system can find counterexamples**: the P4 → P8a and P20-LS offline → remote scale-up shifts show that the harness can challenge tiny optimistic or merely schema-safe results with realistic corpus slices.

---

## 7. Stage Summary Index

The detailed phase reports are preserved. This section is an index, not a replacement.

### R0-R13: Local evidence kernel and safety scaffolds

- R0/R1: local evidence kernel, read/scan/search, trace, citation validation.
- R2: regex/BM25/symbol/RRF local bakeoff.
- R3: StoreHit materialization gate and conservative store.
- R4: DerivedIndexView safety scaffold; derived views are not Evidence.
- R5: deterministic graph scaffold; graph output is not direct Evidence.
- R6: deterministic fast-context orchestration scaffold.
- R7-R10: persistent BM25, AST chunking, quality bakeoff, incremental index.
- R11: TDB Level0 adapter probe; metadata/chunks only, no retrieval quality claim.
- R12: real-repo incremental robustness bench.
- R13: provider/dense safety scaffold with mock embeddings and no remote quality claim.

### R14-R29: Benchmark/failure-surface expansion

- R14-R16: scaled benchmark foundation, external multi-repo expansion, multi-method bakeoff.
- R17-R19: query router, guard calibration, large/stress guard generalization.
- R20-R23: auto-wide failure-surface dataset, strategy matrix, failure attribution, guard sweep.
- R24-R25: QuIVer/TDB availability probe, dense_mock/graph ablation; graph/dense default expansion blocked.
- R26: auto-stress-1000 static dataset.
- R28: conservative promotion candidate report; no default change.
- R29: R26 strategy matrix; RRF recall strong, symbol precision anchor, query-noise guard promising, graph/dense blocked.

### R30-R45: Real-model readiness and diagnostic expansion

- R30: freeze R29 baseline.
- R31: real embedding provider smoke and safety gates.
- R32: embedding view bakeoff harness.
- R33: QuIVer BQ readiness diagnostics.
- R34-R36: QuIVer/BQ prototype and anchor-seeded dense/quiver experiments.
- R37-R38: LLM-derived views and stress expansion; not Evidence.
- R39-R40: symbol extraction and regex normalization repair tracks.
- R41-R42: graph role research and admission model v2 rules.
- R43-R45: integrated long-run report; no promotion.

### P1-P9: Real-provider and CI scale-up

- P1: real embedding and LLM smoke, provider access validated.
- P2: bounded real embedding view bakeoff.
- P3: real embedding QuIVer BQ readiness.
- P4: real embedding anchor prototype.
- P5: LLM-derived/stress harness with not-evidence boundary.
- P6: repair/admission replay.
- P7: real-provider summary.
- P8/P9: GitHub Actions public corpus scale-up, model bakeoff, and multilingual smoke.

### P20-P25/P30: LLM scale-up, policy routing, and explainable admission

- P20-LS/P20-LS-A: low-context/query-only LLM aliases safety-passed but quality-failed; direct low-context alias scale-up blocked.
- P21-G: cross-model context-injection phase using context atoms, context packs, candidate metadata, model profiles, roles, layouts, and latency/cost accounting. P21-G1E found useful file/span signal (`pack2_evidence_sketch`, `atom_signature`) but naked dense false spans dominated. P21-G2E found constrained dense has modest supporting value (`dense_atom_signature_rrf_file_constrained`) while dense-only remains diagnostic/non-primary. P21-G3L found LLM span narrowing has promising but model/repo-specific signal; filter/abstain need prompt/bucket routing and GLM needs schema repair.
- P25: bucket-routed LLM role policy evaluator. Deterministic, no-remote, routes by public `task_bucket`/`task_risk_tags`; reduces false primary but also some gold spans; useful as a P30 input, not default.
- P30: Admission Model V3 research harness. Deterministic explainable scorecard with hard guards, routes only from pre-SCORE public features, compares baselines plus `admission_v3`/`admission_v3_h1`/`admission_v3_h2`, reports score bands/selective risk/deltas, action-specific span-cost accounting (P30-H3), and scans public output for forbidden keys. P30-H1 fixed missing outcomes; P30-H2 stricter local-anchor admission still underperforms P25; P30-H3 now provides diagnostic action-cost accounting without changing routes.
- P48: Diagnostic Policy Simulator / Request-More-Context Overlay. Deterministic, SCORE-phase-only route simulator that overlays the P47 span-geometry gate on P25 `bucket_routed_v0` and P30-H4B `admission_v3_h4b`. It counts how many risky candidate-derived primary actions would be replaced by `request_more_context`, reports measured primary cost for existing actions only, and emits geometry-only diagnostics with explicit not-evidence flags. It does not change defaults or EvidenceCore.
- P49: Contrastive Candidate Pack Scaffold. Deterministic, SCORE-phase-only pack-shape diagnostic that builds candidate packs from candidate metadata only (rank, score, channels, subtype axes, path-kind). It reports aggregate pack-build, contrast, provenance-completeness, and SCORE-phase diagnostics per public task bucket and risk tag. It does not call an LLM, does not create evidence, does not admit spans, does not read source files, does not validate content_sha, and does not change defaults or EvidenceCore.
- P52: Metadata-Only Local Verifier Scaffold. Deterministic, SCORE-phase-only feature-availability and candidate-risk-bucket inventory that runs before any source-read or LLM span-narrow phase. It consumes the same ephemeral P25-policy records as P46/P49, classifies candidates into metadata-risk buckets using only public metadata, and reports aggregate availability/checkability/risk diagnostics by pack strategy, public bucket, and risk tag. It does not verify source text, does not read files, does not call an LLM, does not construct prompts, does not validate EvidenceCore, does not produce evidence, does not produce a verifier pass/fail score, and does not prove P51/P53 quality. See `docs/en/p52-metadata-local-verifier-scaffold.md`.
- P52B: Source-Backed Local Verifier Feature Matrix. Deterministic, SCORE-phase-only source-shape feature diagnostics computed from bounded local source reads. It consumes the same ephemeral P25-policy records and the P52A materialization outcome, extracts source-shape heuristics from bounded candidate spans, classifies candidates into source-feature risk buckets, and reports aggregate diagnostics by pack strategy and safe public dimensions. It does not produce evidence, does not produce a verifier pass/fail or local-verifier score, does not admit candidates, does not change defaults, does not prove P51 quality, and does not send source to providers. See `docs/en/p52b-source-backed-local-verifier-feature-matrix.md`.
- P52C: Diagnostic Local Verifier Scoring Simulator. Deterministic, gold-free diagnostic score-bucket simulator over P52B/P52A/P52/P49/P48 features. It computes fixed `p52c_diagnostic_score_v0` score buckets and aggregate retrospective correlations; scores are not Evidence, not a verifier pass/fail, and not an admission/default/promotion claim. See `docs/en/p52c-local-verifier-scoring-simulator.md`.

Key detailed reports:

- `docs/final-research-report.md` — long R0-R29 historical report.
- `docs/research-summary.md` — stage-by-stage status summary.
- `docs/r29-r26-stress-matrix.md` — R29 matrix and failure clusters.
- `docs/r45-promotion-candidate-report.md` — R30-R45 conclusion checkpoint.
- `docs/real-provider-p7-summary.md` — P1-P6 real-provider summary.
- `docs/real-provider-ci-scale-p8-p9.md` — first CI scale-up results.
- `docs/en/real-provider-ci-large-scale.md` — L1/L2 real-provider large-scale results.
- `docs/p20-llm-large-scale.md` — P20-LS-A low-context LLM alias scale-up result.
- `docs/p21-g-cross-model-context-injection.md` — P21-G cross-model context-injection plan.
- `docs/p25-bucket-routed-policy.md` — P25 bucket-routed LLM role policy.
- `docs/p30-admission-model-v3.md` — P30 Admission Model V3 report.
- `docs/p30-admission-model-v3-remote-smoke.md` — first P30 real remote smoke.
- `docs/p30-h1-remote-smoke.md` — P30-H1 enriched handoff real remote smoke.
- `docs/p30-h2-remote-smoke.md` — P30-H2 stricter local-anchor admission real remote smoke.
- `docs/p30-h3-span-cost-accounting.md` — P30-H3 action-specific span-cost accounting (diagnostic-only, score-phase-only, no route change).
- `docs/p30-h3-remote-smoke.md` — P30-H3 real remote smoke action-cost diagnosis.
- `docs/en/p48-diagnostic-policy-simulator.md` — P48 diagnostic policy simulator / request-more-context overlay (not evidence, not admission, not default).
- `docs/en/p49-contrastive-candidate-pack-scaffold.md` — P49 contrastive candidate pack scaffold (not evidence, not admission, not default, metadata-only pack construction).
- `docs/en/p52-metadata-local-verifier-scaffold.md` — P52 metadata-only local verifier scaffold (not evidence, not admission, not default, source/query features unavailable, candidate-risk diagnostics only).
- `docs/en/p52b-source-backed-local-verifier-feature-matrix.md` — P52B source-backed local verifier feature matrix (not evidence, not admission, not default, source-shape heuristic diagnostics only, AST/query features unavailable).

---

## 8. Next Research Questions

The next step is not promotion. It is larger, more granular, more reproducible validation:

1. Freeze the L2 task set into a reproducible suite to avoid task-generation drift.
2. Run P21-G context atom screening on public/opt-in corpora: signatures, matched lines, retrieval scores, flags, body windows, neighbors, related tests, and hard distractors.
3. Extend P3/P4 beyond Django/Kubernetes only after false-span analysis.
4. Continue bge-m3 vs Qwen 0.6B/4B/8B bakeoffs on identical task sets, including latency/cost.
5. Feed P5 stress traps into anchored dense/QuIVer validation and measure whether added_gold consistently exceeds added_false.
6. Re-validate symbol repair and regex normalization on R26/R38, focusing on bucket regressions.
7. Add real dense support scores to admission_v2 research, but only as supporting features.
8. Continue QuIVer sharding/prototype work; do not claim QuIVer quality until graph/ANN backend evidence exists.
9. If LLM query aliases are revisited, test only grounded variants: inventory-selected aliases or aliases derived after seeing top-k local candidate snippets.
10. Run P21-G rich LLM candidate support: rerank/filter/span-narrow/abstain/inventory_alias over snippet-backed local candidates, record model-averaged and per-model effects, and report quality, latency, token, and cost trade-offs.
11. P30-H3: add action-specific span-cost accounting and false-span budgets for weak/supporting/filter outcomes before further route tuning.

---

## 9. Current Bottom Line

OpenLocus has established a quality-and-evidence-gated research direction: local lexical/symbol/RRF retrieval is the backbone, while real embeddings, QuIVer, LLM-derived views, and graph signals are valuable only when grounded and validated. L1/L2 shows dense-only/global dense cannot be primary/default, and P20-LS-A shows low-context/query-only LLM aliases cannot be scaled as-is. P22/P23 now frames the next phase as evidence-seeking retrieval policy research: preserve local recall, use precision anchors and guard surfaces to suppress false primary, route dense/LLM roles only where the bucket/candidate surface supports them, and let EvidenceCore remain the only fact authority. P30 provides a deterministic, explainable admission scaffold to compare these policy surfaces.
