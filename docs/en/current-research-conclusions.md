# OpenLocus Current Research Conclusions

Date: 2026-06-24

Status: current research-conclusion memo. This is not a promotion request, not a default-policy change request, and not a benchmark leaderboard report.

Scope: empirical work through BEA-v1-P4K Exact Overlap Resolution & Locked Reservoir Audit, BEA-v1-P1 Actionability Audit, BEA-FD1/FD2-A/FD2-A1, BEA-5 fixed-protocol success-quota No-Go / near-miss, B16-F through B16-J live-provider atom ablations, C5 external benchmark retrieval smokes, F1 utility smokes, and D5-A automated calibration feature extraction/heldout validation.

## 0. Reading rule

This file is the concise current conclusion. It is not the full chronology.

- Full chronological record: [`research-log.md`](research-log.md)
- Long-form summary: [`research-summary.md`](research-summary.md)
- Detail docs: linked from [`../current-research-conclusions.md`](../current-research-conclusions.md)

The root `docs/current-research-conclusions.md` is only a bilingual index. Do not put status prose there.

## 1. Current bottom line

OpenLocus has crossed from control-plane scaffolding into real empirical work. The project now has external benchmark runs, live-provider coding-agent runs, private per-record SCORE/event traces, and aggregate-only public artifacts.

The strongest current conclusions are conservative:

1. **Context packs help live coding-agent behavior versus sparse prompts.** B16-F showed sparse control solved 0.25 while both same-budget BM25 and BEA v0.3 context packs solved 1.0 on the bounded live-provider smoke.
2. **BEA has not beaten same-budget BM25 downstream.** In B16-F, BEA v0.3 tied same-budget BM25 on solve/test outcomes and cost more tokens/latency.
3. **The support atom is causally important, but only after confounds were removed.** B16-G/H/I initially showed support-only sufficiency because support cues were too decisive. B16-J fixed role-bearing filename leakage and finally observed a bounded target+support conjunction signal: target+support solved 8/8, support-only solved 2/8, target-only solved 0/8.
4. **BEA v0.3 is mixed, not a winner.** BEA-2 improved file/MRR/success but hurt span/latency. BEA-3 mostly tied v0.2 with tiny span/quality-per-latency improvements. BEA-4 scaled the frozen v0.3 policy to 120 successful records and remained mixed.
5. **BEA-5 is complete as a fixed-protocol No-Go / near-miss.** The final fixed-protocol CI run `28003522632` failed closed with 119/120 successful records. A local exact rerun reproduced the artifact: 186 attempted, 119 successful, 67 excluded, ContextBench 82, RepoQA 37, private SCORE rows 833. This is failure-decomposition input, not a BEA-5 pass.
6. **BEA v1 is actionability-aware, but v1-A/P5 selector work is still not authorized.** BEA-FD2-A1 established that latency loss was non-actionable at candidate-selection time; BEA-v1-P1 found selector-only lower-bound recoverability of only 1/119 for `gold_file_absent`; BEA-v1-P2/P3/P4 showed retrieval-action scheduling can improve reach under cost gates on the same 119-record frame; BEA-v1-P4H failed disjoint validation at 73/80; BEA-v1-P4I confirmed the supported Python frame still has only 73/80 FD1-excluded reservoir records; BEA-v1-P4J found a 333-record cross-source upper-bound reservoir; BEA-v1-P4K resolved exact overlap and locked a 272/80 non-Python reservoir for locked-P4 validation design only.
7. **Automated E/S calibration is progressing, but human calibration is not claimed.** D5-A0/A1/A2 provide automated/proxy feature and heldout validation evidence; they do not establish human-calibrated E/S.

## 2. What is established vs not established

| Area | Established | Not established |
|---|---|---|
| External retrieval benchmarks | ContextBench and RepoQA smoke/matrix/scale runs execute in CI with aggregate-only artifacts. | No benchmark leaderboard or general performance claim. |
| BEA algorithm | BEA policies run on real external benchmark data with private SCORE traces. BEA v0.3 has mixed evidence. | No winner/default/promotion claim. |
| BEA v1 actionability | FD1 failure categories are mapped to action layers; FD1 private replay supports an honest file-selector lower bound; P2/P3/P4 show retrieval-action scheduling can improve same-frame reach under cost gates; P4J shows cross-source frames contain a 333-record file-miss upper-bound reservoir; P4K resolves exact overlap and locks a 272/80 non-Python reservoir for design. | BEA-v1-A selector, P5 selector/reranker, naive broad retrieval expansion, locked/frozen P4 validation execution, and runtime promotion are not authorized; P4K authorizes only design of a later locked-denominator P4 validation phase. |
| Downstream live-provider behavior | Context packs improve bounded synthetic coding-agent tasks versus sparse prompts. B16-J isolates a target+support conjunction signal after removing confounds. | No real-user downstream value proof. No BEA-over-BM25 downstream advantage. |
| Automated calibration | Automated/proxy calibration artifacts and heldout feature checks exist. | No human-calibrated E/S claim. |
| Privacy/artifact discipline | Public artifacts are aggregate-only; private SCORE/event traces stay under `/tmp` or ignored locations. | No raw prompts, responses, paths, snippets, provider payloads, gold labels, or per-record rows are public. |

## 3. BEA conclusions

### 3.1 BEA-0 and BEA-1

BEA-0 established the real run pattern: external benchmark/retrieval run, deterministic BEA policy, private SCORE JSONL, and records-only public artifact.

BEA-1 mechanism ablation showed BEA v0 did not beat same-budget BM25/agreement controls, but did beat seeded random. This means the mechanism is not merely random budget reduction, but also not yet superior to strong same-budget lexical controls.

### 3.2 BEA-2 and BEA-3

BEA-2 introduced diversity/risk scoring. It improved file recall, MRR, and success rate on the bounded slice, but regressed span_f0.5 and latency.

BEA-3 added anchor/span/latency-aware scoring. On the fixed CI run `27942492278`, v0.3 mostly tied v0.2 on file/MRR/success and produced only tiny span and quality-per-latency improvements. This is weak/mixed evidence.

### 3.3 BEA-4

BEA-4 froze BEA v0.3 and ran a larger external scale smoke. The valid result is fixed CI run `27957586271`; earlier run `27955873768` is superseded because its public `delta_records` shape had duplicates.

BEA-4 produced 120 successful records and 840 private SCORE rows. It showed v0.3 can run at larger scale with required RRF and unique public record tables, but the outcome remains mixed. This is robustness evidence, not a default-policy decision.

### 3.4 BEA-5

BEA-5 is complete as a strict fixed-protocol No-Go / near-miss. Earlier attempts failed closed before the final protocol:

- `27962009344`: only 72 successful records and nonzero RRF-missing classification.
- `27964243698`: still 72 successful records because evaluator hard caps were lower than workflow requests.
- `27966269054`: RRF-missing fixed, but still 72 successful records, below the 120-record scale gate.
- `27984961904`: fixed-tail success-quota still yielded only 72/120.
- `28003522632`: fixed-protocol recovery scan yielded 119/120 and failed closed.

The final protocol used explicit success-quota sampling over a full available Python frame excluding BEA-2/3/4 windows:

- sampling mode: `success_quota`
- raw caps: ContextBench 480, RepoQA 240
- target successful records: 120
- minimum benchmark contribution gates: ContextBench >= 40, RepoQA >= 20
- public artifact must report attempted/success/excluded aggregate counts
- private SCORE rows remain `records_successful × 7`
- private attempt/exclusion rows are private and only manifest counts are public

Final artifact summary: `status=partial`, `quota_reached=false`, `records_successful=119`, `records_attempted_total=186`, `records_excluded=67`, `contextbench_successful=82`, `repoqa_successful=37`, `private_score_manifest.record_count=833`, `private_attempt_manifest.record_count=186`, `rrf_required_but_missing=0`, `forbidden_scan.status=pass`.

Conclusion: BEA-5 did not pass the strict 120-record gate. The 119-record near-miss artifact should feed BEA-4/5 failure decomposition; do not keep tuning sampling or make v0.31 weight tweaks.

## 4. B16 downstream/context-pack conclusions

### 4.1 B16-F

B16-F compared sparse, same-budget BM25 context pack, and BEA v0.3 context pack in a live-provider paired smoke (`27945253824`). Context packs helped strongly over sparse, but BEA tied BM25.

Conclusion: context helps; BEA selection superiority is not shown.

### 4.2 B16-G and B16-H

B16-G and B16-H found support-only could solve all tasks. B16-H removed the target-file-only action constraint, yet support-only still solved 8/8. This showed the synthetic support cue itself was too decisive.

Conclusion: those runs diagnose task/cue design, not a real target+support mechanism.

### 4.3 B16-I

B16-I attempted a non-decisive support cue but still observed support-only 8/8. The design intent failed.

Conclusion: the support cue still leaked enough problem information.

### 4.4 B16-J

B16-J used role-neutral candidate filenames and full-prompt leakage tests. CI run `27953321504` finally observed the intended bounded conjunction pattern:

- target+support: 8/8
- support-only: 2/8
- target-only: 0/8
- conjunction-required count: 6/8

Conclusion: after removing filename/role leakage and overly decisive support text, the live-provider smoke supports a target+support conjunction mechanism. This is still bounded synthetic evidence, not proof of real-user downstream value.

## 5. External benchmark and utility conclusions

C5 and F1 phases established that the project can run real external retrieval/utility smokes in CI:

- ContextBench and RepoQA retrieval matrix/scale phases produced aggregate retrieval metrics.
- F1-C and F1-D connected retrieval-derived utility across benchmarks and bootstrap robustness.
- These phases support empirical evaluation infrastructure and bounded findings.

They do not establish leaderboard performance or default-policy readiness.

## 6. D5-A automated calibration conclusions

D5-A is no longer blocked by missing human labels. The automated path is valid if claims remain explicit.

- D5-A0: automated E/S calibration smoke.
- D5-A1: deterministic feature extraction from committed empirical artifacts.
- D5-A2: heldout validation on ContextBench rows 21–40 and RepoQA needles 11–20.

Current claim: automated/proxy calibration evidence exists. Human-calibrated E/S is not claimed.

## 7. Current guardrails

The following remain false unless a future phase explicitly validates them:

- promotion_ready
- default_should_change
- method_winner_claimed
- benchmark_performance_claimed
- downstream_agent_value_proven
- human_e_s_calibration_claimed
- evidencecore_semantics_changed
- runtime_clean_general_algorithm_claimed
- ood_temporal_supported
- quiver_systems_supported

## 8. Current next work

BEA-v0.4-P1 setwise role-proxy smoke is complete as a valid P1 No-Go / weak negative. Manual CI run `28017063082` passed fail-closed with 38 successful records (ContextBench 20, RepoQA 18), but status was `no_go_proxy_unavailable`: target_proxy_available_rate=0.0 and setwise_selection_diff_rate_vs_v03=0.105263 (<0.25). Quality did not catastrophically regress, but v0.4-P1 did not improve over v0.3. See `docs/en/bea-v04-p1-setwise-role-proxy-smoke.md`.

BEA-v0.4-P2 target-role proxy repair smoke is also complete as a valid No-Go. Manual CI run `28020331024` passed fail-closed with 38 successful records. P2 repaired target_proxy_available_rate from 0.0 to 1.0, but support_proxy_available_rate fell to 0.0, P2-vs-P1 selection difference was 0.0, and P2-vs-v0.3 selection difference stayed 0.105263 (<0.25). Quality safety held, but P2 does not justify full v0.4 matrix entry. See `docs/en/bea-v04-p2-target-role-proxy-repair-smoke.md`.

BEA-v0.4-P3 support/complementarity proxy repair smoke is complete as the final bounded role-proxy No-Go. Manual CI run `28022595796` passed fail-closed with 38 successful records and status `no_go_support_proxy_degenerate`: P3 made target/support/pair availability and selection all reach 1.0 and materially changed selection (diff vs v0.3=0.5), but support was over-broad (mean 18.289474 support candidates/record) and quality regressed versus v0.3 (file_recall@10 -0.052632, MRR -0.155263). This triggers the role-proxy stop rule: do not run legacy role-proxy P4/P5, do not enter the full v0.4 matrix from the role-proxy design, and do not tune v0.31/v0.32. See `docs/en/bea-v04-p3-support-complementarity-repair-smoke.md`.

BEA-FD1 failure decomposition is complete. Manual CI run `28011901294` replayed BEA-4 and BEA-5 exactly, decomposed 239 successful records, wrote 86040 private decomposition rows, and published records-only aggregate tables. See `docs/en/bea-fd1-failure-decomposition.md`.

BEA-FD2-A direct FD1-objective setwise acquisition smoke is complete as a bounded No-Go. Manual CI run `28025382422` passed fail-closed with 38 successful records and status `no_go_no_fd1_loss_reduction`: the FD1-weighted treatment changed selection strongly (diff vs v0.3=0.710526), but increased composite FD1 loss (0.756181 vs v0.3 0.397802 and coverage-only 0.748783) and regressed file_recall@10/MRR versus v0.3. Do not run FD2-B from this objective. See `docs/en/bea-fd2a-direct-fd1-objective-setwise-smoke.md`.

BEA-FD2-A1 failure attribution replay is complete. Manual CI run `28027342996` replayed FD2-A and attributed 38/38 regressed records. The dominant mechanism was `latency_category_non_actionable_or_dominating` on 38/38 records; candidate availability was not limiting (`candidate_availability_limit=0/38`, better candidates existed for 38/38). See `docs/en/bea-fd2a1-failure-attribution-replay.md`.

BEA-v1-P1 Actionability Audit is complete. Manual CI run `28076434237` regenerated and validated FD1 private decomposition (86040 rows, 239 composite record groups) and published status `no_go_retrieval_availability_limit`. The audit mapped all 12 FD1 categories over 6 action layers and computed the file-selector ceiling from private replay: `gold_file_absent` denominator=119, lower-bound recoverable count=1, lower-bound rate=0.004184, unrecoverable candidate-unavailable lower-bound count=118, retrieval-availability rate=0.991597. Do not start BEA-v1-A coverage-preserving selector from this evidence.

BEA-v1-P2 Candidate Availability / Retrieval Reach Smoke is complete. Manual CI run `28093864524` regenerated FD1 private replay and ran 4 retrieval-reach arms over the 119-record file-miss denominator. Status is `no_go_retrieval_reach_latency_or_pool_cost`: runtime-clean expansion can recover additional files, but broad expansion is too costly. Baseline reached 32/119; depth-only reached 59/119 (+27, lift 0.226891, pool 3.41×, latency 1.18×); query-anchor reached 60/119 (+28) but exceeded cost; combined depth+query reached 81/119 (+49, lift 0.411765) but violated pool/latency safety (10.13× pool, 3.89× latency).

Immediate next work is no longer proxy repair, direct aggregate-FD1-loss weighting, FD2-A diagnosis, selector-only v1-A, or naive broad retrieval expansion. FD2-A1 explains the latency-objective failure, v1-P1 shows selector-only file coverage is under-justified, v1-P2 shows candidate availability can improve only if retrieval expansion is constrained, and BEA-v1-P3 showed the next bottleneck was retrieval-action latency rather than candidate relevance scoring.

BEA-v1-P4 Latency-Aware Retrieval Action Scheduler Smoke is complete. Manual CI run `28118888584` passed fail-closed after regenerating FD1 private replay and running 4 fixed arms on the 119-record file-miss denominator. Status is `bea_v1_p4_latency_aware_retrieval_scheduler_pass`: P4 reached 56/119 (+24), preserving >=75% of P2 depth-only gain, with pool 2.056×, latency 1.750×, 19.38% lower latency than P3, zero hard-cap violations, and fewer actions on 119/119 records. This validates retrieval-action scheduling as a runtime-clean candidate-availability lever, but not a default-policy/method-winner/runtime-promotion claim; selector relevance remains unresolved (mean first-gold rank 25.625, 48 records above budget). See `docs/en/bea-v1-p4-latency-aware-retrieval-scheduler-smoke.md`.

BEA-v1-P4H Disjoint Scheduler Validation is complete as a No-Go. Manual CI run `28132121958` passed fail-closed after the full-frame disjoint scan fix `0dfeb27`, but status is `no_go_p4h_insufficient_denominator`: exact BEA-4/5 raw-key exclusion removed 239 prior records, the scan fetched 266 ContextBench and 100 RepoQA rows, attempted 127 non-prior candidate rows, and found only 73 baseline file-miss heldout records (61 ContextBench, 12 RepoQA), below the fixed 80-record gate. Scheduler arms were not executed (`retrieval_policy_executed=false`, `private_scheduler_rows=0`). This does not contradict the P4 same-frame pass, but it means P4 is not validated on a disjoint heldout denominator and does not authorize P5 selector/reranker work, BEA-v1-A, or runtime promotion. See `docs/en/bea-v1-p4h-disjoint-scheduler-validation.md`.

BEA-v1-P4I Disjoint Denominator Reservoir Audit is complete as a No-Go. Manual CI run `28137455572` passed fail-closed, but status is `no_go_disjoint_denominator_reservoir_insufficient`: the audit fetched 366 raw rows, excluded 239 exact BEA-4/5 prior raw keys from FD1, attempted 127 non-prior rows, observed 54 baseline-reached rows, and found only 73 FD1-excluded file-miss reservoir records. `reservoir_upper_bound_count=73`, `qualified_denominator_reservoir_count=0`, and `p4h_overlap_resolved=false`. This confirms the P4H blocker is a current-source reservoir limitation in the supported ContextBench/RepoQA Python frame, not just fixed-tail sampling. Do not run frozen P4H rerun, P5 selector/reranker, BEA-v1-A, or broad retrieval expansion from P4I. See `docs/en/bea-v1-p4i-disjoint-denominator-reservoir-audit.md`.

BEA-v1-P4J Cross-Source File-Miss Reservoir Unlock Audit is complete as an unqualified No-Go. Manual CI run `28146407493` passed fail-closed after diagnostic patch `18126f4`, but status is `no_go_cross_source_reservoir_unqualified`: P4J found a large cross-source FD1-excluded upper-bound reservoir (`denominator_count=333`, `reservoir_upper_bound_count=333`, `cross_source_non_python_reservoir_count=272`, `cross_source_python_reservoir_count=61`) after fetching 780 rows and attempting 618 rows. However `qualified_cross_source_reservoir_count=0` and `p4h_p4i_overlap_resolved=false`, so the 333 records are not a locked all-prior-disjoint denominator. P4J proves the source story is broader than the Python frame, but still does not authorize locked-P4 validation, frozen P4 rerun, P5 selector/reranker, BEA-v1-A, runtime promotion, or broad retrieval expansion. See `docs/en/bea-v1-p4j-cross-source-reservoir-unlock-audit.md`.

BEA-v1-P4K Exact Overlap Resolution & Locked Reservoir Audit is complete as design-ready only. Manual CI run `28151914531` passed fail-closed with status `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`: P4K reconstructed P4H `73/73`, P4I `73/73`, and P4J `333/333` with split 61 Python + 272 non-Python, found overlap of 61 with P4H/P4I, and locked a post-overlap cross-source reservoir of 272/80, entirely non-Python. `locked_p4_validation_design_authorized=true` appears only in `stop_go_records`; `scheduler_validation_authorized=false`, `locked_p4_validation_executed=false`, `frozen_p4_rerun_authorized=false`, `p5_authorized=false`, and `v1_a_authorized=false`. P4K resolves the P4J blocker but authorizes only designing a later locked-denominator P4 validation phase, not executing validation or selector work. See `docs/en/bea-v1-p4k-exact-overlap-resolution-locked-reservoir-audit.md`.

Do not run B16-K, legacy role-proxy P4/P5, FD2-B from the failed FD2-A objective, v0.31/v0.32 weight tweaks, D5-A readiness expansions, QuIVer/dense/graph quality experiments, another BEA scale smoke, BEA-v1-A selector-only implementation, P5 selector/reranker from P4H/P4I/P4J/P4K, locked/frozen P4 validation execution without a separate locked-denominator validation phase, or unconstrained broad retrieval expansion.

## 9. One-sentence conclusion

OpenLocus now has real empirical evidence pipelines and a bounded target+support downstream signal, but BEA is still mixed and not a default/winner; BEA-5 missed the fixed quota by one record, BEA-FD1 decomposed BEA-4/5 failures, P1/P2/P3 closed the role-proxy line, FD2-A/FD2-A1 closed direct FD1-loss weighting, BEA-v1-P1 rejects selector-only v1-A, P2/P3/P4 show retrieval-action scheduling can improve candidate availability under cost gates, P4H/P4I show the supported Python frame lacks enough disjoint file-miss reservoir, P4J shows a cross-source reservoir exists, and P4K resolves exact overlap into a 272/80 locked non-Python reservoir for validation-design only.
