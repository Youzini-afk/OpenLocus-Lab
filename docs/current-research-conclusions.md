# OpenLocus Current Research Conclusions / OpenLocus 当前研究结论

Date: 2026-06-21

This is the bilingual entry point for the current research-conclusion reports.
All language-specific reports now live under `docs/en/` and `docs/zh/` as mirrored files.

本页面为双语入口。当前研究结论报告已拆分到 `docs/en/` 与 `docs/zh/` 两个镜像目录。

- [English research conclusions](en/current-research-conclusions.md)
- [中文研究结论](zh/current-research-conclusions.md)

Latest status: C4 external benchmark readiness and the Step 6/D-series
dual-rubric control-plane harnesses are complete through the D4-series
rollup, and the trajectory has now pivoted into D5-A0 automated empirical
E/S calibration smoke, B16-A minimal deterministic/mock downstream
paired-agent empirical run, B16-B less-separable deterministic/mock
downstream paired-agent stress run, B16-C live-provider downstream paired
smoke, B16-D less-trivial live-provider downstream paired smoke, C5-A
ContextBench verified retrieval performance smoke, and C5-B ContextBench
verified retrieval method matrix smoke. D5-H / human-reference
calibration remains out of scope until human labels exist; the D5-A
automated/programmatic empirical path is active. B16-A is a deterministic
mock downstream smoke (no live LLM, no provider calls); it does NOT claim
downstream agent value. B16-B extends B16-A into a harder less-separable
multi-cue stress (no live LLM, no provider calls); it does NOT claim
downstream agent value, emits no
winner/best_arm/recommended_default/preferred_policy/promotion field, and
treatment is perfect by construction (harness/stress, not live result).
B16-C is the first live-provider B16-style downstream-agent smoke
(OpenAI-compatible live LLM only when --allow-remote +
OPENLOCUS_ALLOW_REMOTE=1 + provider env; structured edit action
allowlisted to target.py; real file edits + real subprocess tests; no
raw prompt/response/payload committed); manual CI run 27900913599 passed
with 2 synthetic tasks / 4 live provider calls and both arms solved all
tasks (solve-rate delta 0.0); it does NOT claim downstream agent value,
live agent generalization, external benchmark performance, real user
task, promotion, or default/policy/runtime/retriever/pack/backend/
EvidenceCore semantic change. B16-D extends B16-C with a harder
less-trivial multi-file task family (same-symbol distractor + support
relation required; treatment includes target file cue, target symbol
cue, support-relation cue, exact edit constraint; control lacks the
decisive cue; same live-provider gating; same aggregate-only safety
model; CI pass does NOT require treatment improvement); manual CI run
27901644438 passed with 4 synthetic tasks / 8 live provider calls,
control solve_rate=0.5, treatment solve_rate=1.0, solve-rate delta
`+0.5`, tests-pass delta `+0.5`, and
`context_pack_signal_observed=true`. This is a tiny synthetic smoke
signal, not downstream value proof; B16-D does NOT claim downstream
agent value, live agent generalization, external benchmark performance,
real user task, promotion, or default/policy/runtime/retriever/pack/
backend/EvidenceCore semantic change. B16-E broadens B16-D into a
heterogeneous synthetic task-family matrix with four fixed families
(`same_symbol_support_relation`, `operation_ambiguity`,
`boundary_condition`, `helper_dependency_choice`); manual CI run
27902925812 passed with 8 synthetic tasks / 16 live provider calls,
control solve_rate=0.125, treatment solve_rate=1.0, solve/test delta
`+0.875`, 4/4 families positive, and
`context_pack_signal_observed=true`; this is a broader but still tiny
synthetic smoke signal, not downstream value proof; B16-E does NOT
claim downstream agent value, live agent generalization, external
benchmark performance, real user task, promotion, or
default/policy/runtime/retriever/pack/backend/EvidenceCore semantic
change. F1-B is a retrieval-derived counterfactual utility smoke using
real ContextBench verified rows, transient /tmp clones, real OpenLocus
retrieval, and `eval/score.py` metrics (bm25,regex,symbol; 5 fixed
candidate-set variants; 4 fixed effects; no provider calls; no
winner/best/default fields; no E/S calibration notation); manual CI run
27903995230 passed with 5 rows fetched/successful, forbidden scan pass,
`bm25_topk` file_recall@10=0.4 / mrr=0.225 / span_f0.5@10=0.015905 /
success_rate=1.0, `regex_topk` and `symbol_topk` file_recall@10=0.0,
and `symbol_added_to_bm25` delta=0.0; this is NOT downstream utility,
NOT true E/S calibration, NOT an external benchmark performance claim,
NOT a leaderboard entry, and NOT promotion/default/runtime/retriever/
pack/backend/EvidenceCore semantic change. C5-A is an
external-benchmark-shaped retrieval performance smoke (bounded ContextBench
verified subset; transient /tmp clone + retrieval + score; aggregate-only
public artifact; no provider calls); it does NOT claim an external
benchmark result, leaderboard entry, performance claim, promotion, default
change, runtime/retriever/pack/backend/EvidenceCore semantic change, or
downstream agent value. C5-B extends C5-A into a bounded multi-method
matrix smoke (default bm25,regex,symbol; allowed bm25,regex,text,symbol;
fixed baseline_method=bm25; per-method aggregate records; aggregate-only
deltas vs bm25; no winner/best_method/recommended_default;
baseline_is_policy_candidate=false; default_should_change=false); it
likewise does NOT claim an external benchmark result, leaderboard entry,
performance claim, promotion, default change, runtime/retriever/pack/
backend/EvidenceCore semantic change, or downstream agent value. C5-C
scales C5-B up to a bounded 20-row method-matrix scale smoke
(bm25,regex,symbol only, no text; per-method aggregate records with
optional aggregate_runtime_seconds; aggregate-only deltas vs bm25;
input_summary block; status pass enum
contextbench_method_matrix_scale_smoke_pass; no winner/best_method/
recommended_default; baseline_is_policy_candidate=false;
default_should_change=false); it likewise does NOT claim an external
benchmark result, leaderboard entry, performance claim, promotion,
default change, runtime/retriever/pack/backend/EvidenceCore semantic
change, or downstream agent value. C5-D adds the first RepoQA-shaped
BM25 retrieval smoke: manual CI run 27906775008 passed with 5 RepoQA
Python needles seen/successful, forbidden scan pass, file_recall@10=0.6,
mrr=0.46, span_f0.5@10=0.041634, success_rate=1.0, provider_calls=0;
this is smoke-only, not a benchmark/performance/leaderboard/default
claim. C5-E extends RepoQA to a bm25/regex/symbol method matrix:
manual CI run 27907731742 passed with 5 RepoQA Python needles per
method, 3/3 methods successful, bm25 file_recall@10=0.6/mrr=0.46/
span_f0.5@10=0.041634/success_rate=1.0, regex/symbol file_recall@10=0.0,
provider_calls=0; this is smoke-only, not a method winner/default claim. C5-F extends RepoQA to a 10-needle method matrix scale smoke: manual CI run 27909885489 passed with 10 RepoQA Python needles per method, 3/3 methods successful, bm25 file_recall@10=0.5/mrr=0.369216/span_f0.5@10=0.020817/success_rate=1.0, regex/symbol file_recall@10=0.0, provider_calls=0, aggregate_runtime_seconds bm25=19.018/regex=18.181/symbol=28.251; this is smoke-only, not a method winner/default claim. F1-C is the cross-benchmark retrieval-derived utility smoke: it reruns real bounded external data (ContextBench verified 20-row + RepoQA 10-needle Python) over bm25,regex,symbol with a synthetic `empty_retrieval` zero baseline, computes a fixed retrieval-derived utility proxy (`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty` where `miss_penalty=0.25 if file_recall@10 == 0 else 0`), cross-benchmark weighted means, and 5 fixed counterfactual effects (`bm25_vs_empty`, `regex_vs_empty`, `symbol_vs_empty`, `regex_vs_bm25`, `symbol_vs_bm25`); local real-network run and manual CI run 27911651758 passed with 20 ContextBench rows fetched, 10 RepoQA needles seen, status `cross_benchmark_retrieval_utility_pass`, forbidden scan pass, provider_calls=0, bm25 cross-benchmark weighted-mean file_recall@10=0.4/mrr=0.218477/span_f0.5@10=0.020831/success_rate=1.0/retrieval_utility=0.465035, `bm25_vs_empty` retrieval_utility delta=+0.465035, `regex_vs_bm25` and `symbol_vs_bm25` retrieval_utility delta=-0.715035; this is smoke-only, not a method winner/default/benchmark/leaderboard/E_S-calibration/downstream-value claim. F1-D extends F1-C from point estimates to diagnostic paired-bootstrap confidence/sign-stability estimates; manual CI run 27913035117 passed: it reruns the same real bounded external data (ContextBench verified 20-row + RepoQA 10-needle Python), intercepts per-unit score metrics before aggregation (in memory or `/tmp` only), computes the same fixed retrieval-derived utility proxy (unchanged from F1-C), cross-benchmark weighted means, and paired bootstrap confidence/sign-stability statistics for effects `bm25_vs_empty`, `regex_vs_empty`, `symbol_vs_empty`, `regex_vs_bm25`, `symbol_vs_bm25` over metrics `retrieval_utility`, `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate` = 25 bootstrap effect records; cross-benchmark resampling preserves benchmark sample counts (ContextBench 20, RepoQA 10); bootstrap replicates default 1000 (hard cap 2000), fixed seed 20240621; local real-network run passed with 20 ContextBench rows fetched, 10 RepoQA needles seen, status `cross_benchmark_retrieval_robustness_pass`, forbidden scan pass, provider_calls=0, bootstrap_record_count=25; point estimates match F1-C deltas (`bm25_vs_empty` retrieval_utility = +0.465035, `regex_vs_bm25` = -0.715035); `bm25_vs_empty` retrieval_utility bootstrap CI=[+0.298938, +0.464512, +0.624026] sign_positive=1.0, `regex_vs_bm25` retrieval_utility CI=[-0.874026, -0.714511, -0.548938] sign_negative=1.0; the public artifact emits aggregate means and bootstrap statistics only (no per-unit metric arrays, no row/needle IDs, no repo URLs/commits/paths/spans/queries/gold/snippets/JSONL/evidence/stdout/stderr/clone-paths/hashes/provider/routing-prefix/winner/best/default fields, no F1-C container names); this is smoke-only, the bootstrap statistics are diagnostic robustness estimates NOT formal external benchmark confidence intervals, not a method winner/default/benchmark/leaderboard/E_S-calibration/downstream-value claim. D5-A1 moves from empirical smokes to calibration-ready weak-supervision features by machine-reading committed aggregate artifacts (F1-D/F1-C/C5-C/C5-F/B16-E required, D5-A0/B16-D optional if present and claim-safe); it validates schemas and claim flags fail-closed, extracts numeric aggregate signals (retrieval robustness from F1-D bm25_vs_empty/regex_vs_bm25/symbol_vs_bm25 point/CI/sign stability; external benchmark agreement/disagreement from C5-C+C5-F bm25 positive on both, regex/symbol negative on both, method agreement counts; live provider delta from B16-E context_pack_signal/solve_rate_delta/families positive/zero/negative), and computes deterministic calibration feature/bucket records (magnitude buckets, sign stability buckets, live provider delta bucket, family distribution bucket, cross-signal alignment label) and readiness buckets (`ready_for_manual_review`, `needs_more_live_downstream`, `retrieval_only_insufficient`, `conflicting_signals`, `insufficient_signal`); recommended next measurements are measurement-only (`manual_reference_audit`, `heldout_benchmark_scale`, `live_downstream_scale`), NOT policy/default/method winner; records-shaped lists only (`input_artifact_records`, `signal_records`, `calibration_feature_records`, `readiness_bucket_records`, `recommended_next_measurement_records`); no per-unit metric arrays, no raw input artifact paths/content, no B16 task text, no winner/best/default/calibrated-model/policy-recommendation fields; local feature extraction run passed with status `automated_calibration_feature_table_pass`, forbidden scan pass, 7 input artifacts loaded (5 required + 2 optional), 9 signals, 7 features, 5 bucket records, 2 measurements, cross_signal_alignment=`retrieval_robust_positive_plus_live_positive`, readiness_bucket=`ready_for_manual_review`; this is feature extraction, NOT calibration, NOT a calibrated model claim, NOT a policy/default recommendation, not a method winner/default/benchmark/leaderboard/E_S-calibration/downstream-value claim. D5-A2 validates whether D5-A1's retrieval-derived feature bucket reproduces on fresh heldout external retrieval samples: it loads the D5-A1 committed artifact as preregistered feature source (fail-closed on missing/schema-mismatch/unsafe-claim-flags), runs fresh heldout ContextBench verified Python rows 21-40 (fetch 40, evaluate slice [20,40)) and RepoQA Python needles 11-20 (parse 20, evaluate slice [10,20)) with methods bm25/regex/symbol, computes the same fixed retrieval-derived utility proxy, and checks 4 retrieval-feature validations (bm25_vs_empty magnitude/sign stability, regex/symbol_vs_bm25 sign stability); validation outcomes `retrieval_feature_validation_supported`/`mixed`/`not_supported`/`unavailable_with_reason`; records-shaped lists only (`d5a1_input_record`, `heldout_benchmark_method_records`, `validation_records`, `validation_summary_records`); no per-unit metric arrays, no row/needle IDs, no winner/default/calibration claims; local heldout run passed with status `heldout_feature_validation_pass`, `validation_outcome=retrieval_feature_validation_supported`, 20 rows fetched, 10 needles seen, all 4 D5-A1 retrieval features reproduce on heldout data (bm25_vs_empty heldout +0.727961 positive supported, bm25 sign stability heldout file_recall +0.6 positive supported, regex/symbol_vs_bm25 heldout -0.977961 negative supported); heldout bm25 file_recall@10=0.7 on ContextBench (vs 0.35 on original rows 1-20) confirms bm25 positive retrieval feature is supported on this heldout slice; this is heldout feature validation, NOT calibration, NOT policy/default, NOT method winner, NOT benchmark performance, NOT downstream value, NOT runtime/retriever/pack/backend/default-policy/EvidenceCore change; validates only retrieval-feature stability from D5-A1, NOT live-provider/downstream alignment; not a method winner/default/benchmark/leaderboard/E_S-calibration/downstream-value claim.
No runtime/default-policy/promotion/downstream-value claim is made.
BEA-0 is the first real algorithmic retrieval/acquisition experiment with
private per-record SCORE JSONL traces: it reruns fresh multi-method
retrieval (bm25/regex/symbol + optional rrf) over bounded real
ContextBench verified Python rows (default 10; hard cap 20) and RepoQA
Python needles (default 5; hard cap 10), runs the deterministic
`bea_v0_budgeted` policy under an evidence budget (default 10; hard cap
20) with action trace (`accept_candidate`/`skip_low_support`/
`rerank_by_agreement`/`stop_budget_exhausted` + optional
`expand_same_file`), writes private per-record SCORE JSONL ONLY to `/tmp`
(private SCORE path NEVER serialized in public artifact/docs/CI), and
publishes only aggregate per-arm metrics + baseline-vs-treatment deltas vs
`bm25_top10` (and `rrf_bm25_regex_symbol_top10` when rrf enabled). The
`bea_v0_budgeted` policy is runtime-clean (consumes only method source,
rank, score/normalized score, rank agreement across methods, duplicate
path/span overlap, candidate count, accepted coverage, budget remaining,
cheap path extension); verified invariant under synthetic
gold/label/row-id/model-family/previous-outcome tainting. Manual CI run
27934507148 (2026-06-21) with ContextBench 2 rows + RepoQA 1 needle, budget=5,
methods bm25/regex/symbol, rrf baseline enabled: 3 records successful,
forbidden scan pass, provider_calls=0, private_score_record_count=3
(matches records_successful), private_score_storage_class=tmp_private,
private_score_path_publicly_serialized=false; treatment `bea_v0_budgeted`
preserved file_recall@10 / mrr / success_rate parity with both baselines
while using roughly half the evidence budget (3.33 vs 6.67) and improved
span_f0.5@10 by +0.027662 and quality_per_candidate by +0.001384 vs
`bm25_top10`; aggregate_runtime_seconds=25.65. Schema
`bea0_budgeted_evidence_acquisition.v1`,
`claim_level=bea_v0_budgeted_acquisition_smoke_only`, phase `BEA-0`,
212/212 self-test checks pass. BEA-0 is NOT a benchmark result, NOT a
leaderboard entry, NOT a performance claim, NOT a method-winner claim,
NOT a calibration claim, NOT a promotion, NOT a default change, NOT a
runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a
downstream agent value claim. BEA-0 is NOT C3: C3 was replay-only and
selected among precomputed P21 outcomes; BEA-0 actually reruns retrieval
and acquires evidence under a budget, with private per-record SCORE
traces. No runtime/default-policy/promotion/method-winner/calibration/
downstream-value claim is made. BEA-1 is the mechanism ablation follow-up
to BEA-0: it reruns fresh bounded external ContextBench verified Python
rows (default 5; hard cap 20) + RepoQA Python needles (default 3; hard cap
10) over bm25/regex/symbol (+ optional rrf baseline), and runs 5 fixed arms
(`bm25_top10`, `bea_v0_budgeted`, `same_budget_bm25_prefix`,
`agreement_only_same_budget`, `seeded_random_same_budget`;
`rrf_bm25_regex_symbol_top10` when rrf enabled) on every record under a
paired denominator rule. Same-budget K exactly:
`K = min(len(bea_v0_budgeted.accepted_candidates), available_deduped_candidate_count)`.
Same-budget controls are runtime-clean and deterministic (BM25 prefix;
agreement-only sorted by agreement desc/min_rank asc/max_normalized_score
desc/stable order; seeded random with fixed public seed `20240621` over
stable-ordered deduped universe; no gold/labels/row IDs/provider/model
fields in seed or ordering). Bounded local run (2026-06-21) with
ContextBench 5 rows + RepoQA 3 needles, budget=5, methods
bm25/regex/symbol, rrf baseline enabled: 8 records successful,
`paired_exclusion_count=0`, forbidden scan pass, `provider_calls=0`,
`private_score_manifest.record_count=8` (matches records_successful),
`private_score_manifest.storage_class=tmp_private`,
`private_score_manifest.path_publicly_serialized=false`. Mechanism
contrasts (mrr, paired `record_count=8`):
`bea_vs_same_budget_bm25` delta(mrr)=0.0 (BEA ties same-budget BM25 prefix);
`bea_vs_agreement_only` delta(mrr)=0.0 (BEA ties agreement-only);
`bea_vs_seeded_random` delta(mrr)=+0.09375 (BEA beats seeded random). BEA
v0 and `agreement_only_same_budget` produce IDENTICAL
file_recall@10/mrr/span_f0.5@10/success_rate with the same
`evidence_budget_used=3.125`, suggesting BEA v0's gain over a pure
agreement-only rank under the same budget is zero on this bounded sample;
`seeded_random_same_budget` underperforms both, confirming deterministic
agreement-based selection beats random selection under the same budget.
Schema `bea1_mechanism_ablation.v1`,
`claim_level=bea_v0_mechanism_ablation_smoke_only`, phase `BEA-1`,
420/420 self-test checks pass. BEA-1 is NOT a benchmark result, NOT a
leaderboard entry, NOT a performance claim, NOT a method-winner claim, NOT
a calibration claim, NOT a promotion, NOT a default change, NOT a
runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a
downstream agent value claim. BEA-1 is NOT BEA-0: BEA-0 measured BEA v0
vs `bm25_top10` (and `rrf_bm25_regex_symbol_top10` when enabled); BEA-1
measures BEA v0 vs three same-budget controls that isolate whether BEA-0's
gains (if any) come from multi-source agreement / sequential budgeted
evidence acquisition rather than merely reading fewer candidates. BEA-1
does NOT bootstrap the BEA-0 aggregate artifact; it reruns fresh external
retrieval. No runtime/default-policy/promotion/method-winner/calibration/
downstream-value claim is made.

最新状态：C4 外部 benchmark readiness 与 Step 6/D 系列 dual-rubric 控制面
harness 已推进到 D4-series rollup 并收束，研究已转入 D5-A0 自动实证 E/S
校准 smoke、B16-A 最小确定性/mock 下游 paired-agent 实证 run、B16-B
less-separable 确定性/mock 下游 paired-agent 压力测试 run、B16-C
live-provider 下游 paired smoke、B16-D less-trivial live-provider 下游 paired
smoke、C5-A ContextBench verified 检索性能
smoke，以及 C5-B ContextBench verified 检索方法矩阵 smoke。D5-H / 人工
参考校准在人工标签存在前仍属 out of scope；D5-A 自动/程序化实证路径已激
活。B16-A 是确定性 mock 下游 smoke（无 live LLM、无 provider 调用）；它
**不**声明下游 agent 价值。B16-B 将 B16-A 扩展为更难的 less-separable
多线索压力测试（无 live LLM、无 provider 调用）；它**不**声明下游 agent
价值，不输出 winner/best_arm/recommended_default/preferred_policy/
promotion 字段，且 treatment 按构造完美（harness/stress，非 live 结果）。
B16-C 是首个 live-provider B16 风格下游 agent smoke（仅当 --allow-remote
+ OPENLOCUS_ALLOW_REMOTE=1 + provider env 时使用 OpenAI 兼容 live LLM；
结构化 edit action 白名单限 target.py；真实文件编辑 + 真实子进程测试；
不提交 raw prompt/response/payload）；manual CI run 27900913599 已通过，覆盖
2 个合成任务 / 4 次 live provider calls，两个 arm 都解出（solve-rate delta
0.0）；它**不**声明下游 agent 价值、live agent 泛化、外部基准测试性能、
真实用户任务、promotion 或 default/policy/runtime/retriever/pack/backend/
EvidenceCore 语义变更。B16-D 扩展 B16-C 为更难的 less-trivial 多文件
任务族（同符号 distractor + 需要 support relation；treatment 含 target
file cue、target symbol cue、support-relation cue、exact edit
constraint；control 缺少决定性 cue；相同 live-provider gating；相同仅
聚合安全模型；CI 通过**不**要求 treatment 改善）；manual CI run
27901644438 已通过，覆盖 4 个合成任务 / 8 次 live provider calls，control
solve_rate=0.5、treatment solve_rate=1.0、solve-rate delta `+0.5`、
tests-pass delta `+0.5`，且 `context_pack_signal_observed=true`。这是微型合成
smoke 信号，不是下游价值证明；B16-D **不**声明下游 agent 价值、live agent
泛化、外部基准测试性能、真实用户任务、promotion 或
default/policy/runtime/retriever/pack/backend/EvidenceCore 语义变更。B16-E
将 B16-D 扩展为含四个固定族的异构合成任务族矩阵
（`same_symbol_support_relation`、`operation_ambiguity`、
`boundary_condition`、`helper_dependency_choice`）；manual CI run 27902925812
已通过，覆盖 8 个合成任务 / 16 次 live provider calls，control
solve_rate=0.125、treatment solve_rate=1.0、solve/test delta `+0.875`，
4/4 families positive，且 `context_pack_signal_observed=true`；这是更广但仍微型
的合成 smoke 信号，不是下游价值证明；B16-E **不**声明下游 agent 价值、
live agent 泛化、外部基准测试性能、真实用户任务、promotion 或
default/policy/runtime/retriever/pack/backend/EvidenceCore 语义变更。F1-B 是
retrieval-derived counterfactual utility smoke，使用真实 ContextBench verified
rows、临时 /tmp clones、真实 OpenLocus retrieval 与 `eval/score.py` 指标
（bm25,regex,symbol；5 个固定 candidate-set variants；4 个固定 effects；无
provider 调用；无 winner/best/default 字段；无 E/S 校准记法）；manual CI run
27903995230 已通过，5 行抓取/成功，forbidden scan pass，`bm25_topk`
file_recall@10=0.4 / mrr=0.225 / span_f0.5@10=0.015905 / success_rate=1.0，
`regex_topk` 与 `symbol_topk` file_recall@10=0.0，`symbol_added_to_bm25`
delta=0.0；这**不是**下游效用、**不是** true E/S 校准、**不是**外部基准测试性能
声明、**不是** leaderboard 条目，也**不是** promotion/default/runtime/retriever/
pack/backend/EvidenceCore 语义变更。C5-A 是外部-benchmark-形态
的检索性能 smoke（有界 ContextBench verified subset；临时 /tmp clone +
retrieval + score；aggregate-only 公共 artifact；无 provider 调用）；它
**不**声称外部 benchmark 结果、leaderboard 条目、性能、promotion、默认变更、
runtime/retriever/pack/backend/EvidenceCore 语义变更或下游 agent 价值。C5-B
将 C5-A 扩展为有界多方法矩阵 smoke（默认 bm25,regex,symbol；允许
bm25,regex,text,symbol；固定 baseline_method=bm25；每方法 aggregate 记录；
仅 aggregate 的与 bm25 的 delta；无 winner/best_method/recommended_default；
baseline_is_policy_candidate=false；default_should_change=false）；它同样
**不**声称外部 benchmark 结果、leaderboard 条目、性能、promotion、默认变更、
runtime/retriever/pack/backend/EvidenceCore 语义变更或下游 agent 价值。C5-C
将 C5-B 扩展为有界 20 行方法矩阵 scale smoke（仅 bm25,regex,symbol，无 text；
每方法 aggregate 记录带可选 aggregate_runtime_seconds；仅 aggregate 的与
bm25 的 delta；input_summary 块；status pass 枚举
contextbench_method_matrix_scale_smoke_pass；无 winner/best_method/
recommended_default；baseline_is_policy_candidate=false；
default_should_change=false）；它同样**不**声称外部 benchmark 结果、
leaderboard 条目、性能、promotion、默认变更、runtime/retriever/pack/backend/
EvidenceCore 语义变更或下游 agent 价值。C5-C manual CI run 27905621090 已在 fail-closed workflow 下通过：20 行抓取，3/3 方法成功，bm25 file_recall@10=0.35 / mrr=0.143107 / span_f0.5@10=0.020838 / success_rate=1.0，regex 与 symbol file_recall@10=0.0；较早 run 27905321437 的绿色 unavailable 被视为 fail-open 并已修复；这仍只是 smoke 诊断，不是外部 benchmark 性能/default-policy 声明。C5-D 增加第一个 RepoQA 形态的 BM25 检索 smoke：manual CI run 27906775008 已通过，5 个 RepoQA Python needle seen/successful，forbidden scan pass，file_recall@10=0.6，mrr=0.46，span_f0.5@10=0.041634，success_rate=1.0，provider_calls=0；这只是 smoke，不是 benchmark/performance/leaderboard/default 声明。C5-E 将 RepoQA 扩展到 bm25/regex/symbol 方法矩阵：manual CI run 27907731742 已通过，每方法 5 个 RepoQA Python needle，3/3 方法成功，bm25 file_recall@10=0.6/mrr=0.46/span_f0.5@10=0.041634/success_rate=1.0，regex/symbol file_recall@10=0.0，provider_calls=0；这只是 smoke，不是方法 winner/default 声明。C5-F 将 RepoQA 扩展到 10-needle 方法矩阵 scale smoke：manual CI run 27909885489 已通过，每方法 10 个 RepoQA Python needle，3/3 方法成功，bm25 file_recall@10=0.5/mrr=0.369216/span_f0.5@10=0.020817/success_rate=1.0，regex/symbol file_recall@10=0.0，provider_calls=0，aggregate_runtime_seconds bm25=19.018/regex=18.181/symbol=28.251；这只是 smoke，不是方法 winner/default 声明。F1-C 是跨基准 retrieval-derived utility smoke：对两个基准（ContextBench verified 20 行 + RepoQA 10 needle Python）**重新运行真实有界外部数据**，方法 bm25,regex,symbol + 合成 `empty_retrieval` 零基线，计算固定 retrieval-derived utility proxy（`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty`，其中 `miss_penalty=0.25 if file_recall@10 == 0 else 0`）、跨基准加权均值与 5 个固定 counterfactual effects（`bm25_vs_empty`、`regex_vs_empty`、`symbol_vs_empty`、`regex_vs_bm25`、`symbol_vs_bm25`）；本地真实网络 run 与 manual CI run 27911651758 已通过：20 行 ContextBench 抓取，10 个 RepoQA needle 见到，status `cross_benchmark_retrieval_utility_pass`，forbidden scan pass，provider_calls=0，bm25 跨基准加权均值 file_recall@10=0.4/mrr=0.218477/span_f0.5@10=0.020831/success_rate=1.0/retrieval_utility=0.465035，`bm25_vs_empty` retrieval_utility delta=+0.465035，`regex_vs_bm25` 与 `symbol_vs_bm25` retrieval_utility delta=-0.715035；这只是 smoke，不是方法 winner/default/benchmark/leaderboard/E_S 校准/下游价值声明。当前不作 runtime/default-policy/promotion/downstream-value 声明。

## Mirror convention / 镜像约定

For every `<report>.md` under `docs/en/` there is a matching `docs/zh/<report>.md`.
If a Chinese translation is complete, `docs/zh/<report>.md` contains the translation.
If the Chinese translation is still pending, the `docs/zh/<report>.md` file starts with a
Chinese 'translation pending' notice and then preserves the English source under a section
`## English source / 英文原文` so no content is lost.

`docs/en/` 下的每份 `<report>.md` 都在 `docs/zh/` 下有同名镜像。中文已完成时，
`docs/zh/<report>.md` 为中文译文；中文待补充时，文件开头会标注“中文译本待补充”，
然后在 `## English source / 英文原文` 中保留英文原文，避免内容丢失。

## Report mirror index / 报告镜像索引

- `AGENTS.md`: [en](en/AGENTS.md) · [zh](zh/AGENTS.md)
- `b1-live-llm-rich-candidate-run.md`: [en](en/b1-live-llm-rich-candidate-run.md) · [zh](zh/b1-live-llm-rich-candidate-run.md)
- `b1c-cross-model-rich-candidate-rerun.md`: [en](en/b1c-cross-model-rich-candidate-rerun.md) · [zh](zh/b1c-cross-model-rich-candidate-rerun.md)
- `b2-contrastive-pack-quality-experiment.md`: [en](en/b2-contrastive-pack-quality-experiment.md) · [zh](zh/b2-contrastive-pack-quality-experiment.md)
- `b3-rmc-quality-experiment.md`: [en](en/b3-rmc-quality-experiment.md) · [zh](zh/b3-rmc-quality-experiment.md)
- `b4-b9-model-robust-evidence-conversion.md`: [en](en/b4-b9-model-robust-evidence-conversion.md) · [zh](zh/b4-b9-model-robust-evidence-conversion.md)
- `b6-lite-interpretable-policy-search.md`: [en](en/b6-lite-interpretable-policy-search.md) · [zh](zh/b6-lite-interpretable-policy-search.md)
- `b6b-combined-policy-search.md`: [en](en/b6b-combined-policy-search.md) · [zh](zh/b6b-combined-policy-search.md)
- `b6c-frozen-policy-validation.md`: [en](en/b6c-frozen-policy-validation.md) · [zh](zh/b6c-frozen-policy-validation.md)
- `b6d-cross-adapter-frozen-validation.md`: [en](en/b6d-cross-adapter-frozen-validation.md) · [zh](zh/b6d-cross-adapter-frozen-validation.md)
- `b10-runtime-feature-audit.md`: [en](en/b10-runtime-feature-audit.md) · [zh](zh/b10-runtime-feature-audit.md)
- `b10b-runtime-shadow-replay.md`: [en](en/b10b-runtime-shadow-replay.md) · [zh](zh/b10b-runtime-shadow-replay.md)
- `b11-prospective-blind-validation.md`: [en](en/b11-prospective-blind-validation.md) · [zh](zh/b11-prospective-blind-validation.md)
- `b12-mechanism-decomposition.md`: [en](en/b12-mechanism-decomposition.md) · [zh](zh/b12-mechanism-decomposition.md)
- `b13-distributionally-robust-policy-search.md`: [en](en/b13-distributionally-robust-policy-search.md) · [zh](zh/b13-distributionally-robust-policy-search.md)
- `b8-lite-medium-matrix-combiner.md`: [en](en/b8-lite-medium-matrix-combiner.md) · [zh](zh/b8-lite-medium-matrix-combiner.md)
- `b9a-adapter-health-report.md`: [en](en/b9a-adapter-health-report.md) · [zh](zh/b9a-adapter-health-report.md)
- `b9b-qwen-low-volume-quality-follow-up.md`: [en](en/b9b-qwen-low-volume-quality-follow-up.md) · [zh](zh/b9b-qwen-low-volume-quality-follow-up.md)
- `b9c-qwen-frozen-policy-validation.md`: [en](en/b9c-qwen-frozen-policy-validation.md) · [zh](zh/b9c-qwen-frozen-policy-validation.md)
- `b9d-deepseek-glm-participation-screen.md`: [en](en/b9d-deepseek-glm-participation-screen.md) · [zh](zh/b9d-deepseek-glm-participation-screen.md)
- `c4-external-benchmark-adapters.md`: [en](en/c4-external-benchmark-adapters.md) · [zh](zh/c4-external-benchmark-adapters.md)
- `c5-contextbench-verified-performance-smoke.md`: [en](en/c5-contextbench-verified-performance-smoke.md) · [zh](zh/c5-contextbench-verified-performance-smoke.md)
- `c5b-contextbench-verified-method-matrix-smoke.md`: [en](en/c5b-contextbench-verified-method-matrix-smoke.md) · [zh](zh/c5b-contextbench-verified-method-matrix-smoke.md)
- `c5c-contextbench-method-matrix-scale-smoke.md`: [en](en/c5c-contextbench-method-matrix-scale-smoke.md) · [zh](zh/c5c-contextbench-method-matrix-scale-smoke.md)
- `c5d-repoqa-bm25-retrieval-smoke.md`: [en](en/c5d-repoqa-bm25-retrieval-smoke.md) · [zh](zh/c5d-repoqa-bm25-retrieval-smoke.md)
- `c5e-repoqa-method-matrix-smoke.md`: [en](en/c5e-repoqa-method-matrix-smoke.md) · [zh](zh/c5e-repoqa-method-matrix-smoke.md)
- `c5f-repoqa-method-matrix-scale-smoke.md`: [en](en/c5f-repoqa-method-matrix-scale-smoke.md) · [zh](zh/c5f-repoqa-method-matrix-scale-smoke.md)
- `ci-research-harness.md`: [en](en/ci-research-harness.md) · [zh](zh/ci-research-harness.md)
- `current-research-conclusions.md`: [en](en/current-research-conclusions.md) · [zh](zh/current-research-conclusions.md)
- `d5a-automated-es-calibration.md`: [en](en/d5a-automated-es-calibration.md) · [zh](zh/d5a-automated-es-calibration.md)
- `b16a-minimal-mock-agent-paired-run.md`: [en](en/b16a-minimal-mock-agent-paired-run.md) · [zh](zh/b16a-minimal-mock-agent-paired-run.md)
- `b16b-less-separable-mock-paired-run.md`: [en](en/b16b-less-separable-mock-paired-run.md) · [zh](zh/b16b-less-separable-mock-paired-run.md)
- `b16c-live-provider-paired-smoke.md`: [en](en/b16c-live-provider-paired-smoke.md) · [zh](zh/b16c-live-provider-paired-smoke.md)
- `b16d-less-trivial-live-provider-paired-smoke.md`: [en](en/b16d-less-trivial-live-provider-paired-smoke.md) · [zh](zh/b16d-less-trivial-live-provider-paired-smoke.md)
- `b16e-broader-live-provider-paired-smoke.md`: [en](en/b16e-broader-live-provider-paired-smoke.md) · [zh](zh/b16e-broader-live-provider-paired-smoke.md)
- `bea0-budgeted-evidence-acquisition.md`: [en](en/bea0-budgeted-evidence-acquisition.md) · [zh](zh/bea0-budgeted-evidence-acquisition.md)
- `bea1-mechanism-ablation.md`: [en](en/bea1-mechanism-ablation.md) · [zh](zh/bea1-mechanism-ablation.md)
- `f1-counterfactual-evidence-utility.md`: [en](en/f1-counterfactual-evidence-utility.md) · [zh](zh/f1-counterfactual-evidence-utility.md)
- `f1b-retrieval-derived-counterfactual-utility.md`: [en](en/f1b-retrieval-derived-counterfactual-utility.md) · [zh](zh/f1b-retrieval-derived-counterfactual-utility.md)
- `f1c-cross-benchmark-retrieval-utility.md`: [en](en/f1c-cross-benchmark-retrieval-utility.md) · [zh](zh/f1c-cross-benchmark-retrieval-utility.md)
- `final-research-report.md`: [en](en/final-research-report.md) · [zh](zh/final-research-report.md)
- `p20-llm-large-scale.md`: [en](en/p20-llm-large-scale.md) · [zh](zh/p20-llm-large-scale.md)
- `p21-g-cross-model-context-injection.md`: [en](en/p21-g-cross-model-context-injection.md) · [zh](zh/p21-g-cross-model-context-injection.md)
- `p21-g-dense-hybrid.md`: [en](en/p21-g-dense-hybrid.md) · [zh](zh/p21-g-dense-hybrid.md)
- `p21-g-dense-hybrid-remote-smoke.md`: [en](en/p21-g-dense-hybrid-remote-smoke.md) · [zh](zh/p21-g-dense-hybrid-remote-smoke.md)
- `p21-g-embedding-context.md`: [en](en/p21-g-embedding-context.md) · [zh](zh/p21-g-embedding-context.md)
- `p21-g-embedding-context-remote-smoke.md`: [en](en/p21-g-embedding-context-remote-smoke.md) · [zh](zh/p21-g-embedding-context-remote-smoke.md)
- `p21-g-llm-bucketed-role-remote-smoke.md`: [en](en/p21-g-llm-bucketed-role-remote-smoke.md) · [zh](zh/p21-g-llm-bucketed-role-remote-smoke.md)
- `p21-g-llm-rich-candidate.md`: [en](en/p21-g-llm-rich-candidate.md) · [zh](zh/p21-g-llm-rich-candidate.md)
- `p21-g-llm-rich-candidate-remote-smoke.md`: [en](en/p21-g-llm-rich-candidate-remote-smoke.md) · [zh](zh/p21-g-llm-rich-candidate-remote-smoke.md)
- `p21-g-llm-structured-output-remote-smoke.md`: [en](en/p21-g-llm-structured-output-remote-smoke.md) · [zh](zh/p21-g-llm-structured-output-remote-smoke.md)
- `p22-p23-policy-surface.md`: [en](en/p22-p23-policy-surface.md) · [zh](zh/p22-p23-policy-surface.md)
- `p22-p23-policy-surface-r20-positive.md`: [en](en/p22-p23-policy-surface-r20-positive.md) · [zh](zh/p22-p23-policy-surface-r20-positive.md)
- `p22-p23-policy-surface-r26-guard.md`: [en](en/p22-p23-policy-surface-r26-guard.md) · [zh](zh/p22-p23-policy-surface-r26-guard.md)
- `p25-bucket-routed-policy.md`: [en](en/p25-bucket-routed-policy.md) · [zh](zh/p25-bucket-routed-policy.md)
- `p25-bucket-routed-policy-remote-smoke.md`: [en](en/p25-bucket-routed-policy-remote-smoke.md) · [zh](zh/p25-bucket-routed-policy-remote-smoke.md)
- `p30-admission-model-v3.md`: [en](en/p30-admission-model-v3.md) · [zh](zh/p30-admission-model-v3.md)
- `p30-admission-model-v3-remote-smoke.md`: [en](en/p30-admission-model-v3-remote-smoke.md) · [zh](zh/p30-admission-model-v3-remote-smoke.md)
- `p30-h1-remote-smoke.md`: [en](en/p30-h1-remote-smoke.md) · [zh](zh/p30-h1-remote-smoke.md)
- `p30-h2-remote-smoke.md`: [en](en/p30-h2-remote-smoke.md) · [zh](zh/p30-h2-remote-smoke.md)
- `p30-h3-span-cost-accounting.md`: [en](en/p30-h3-span-cost-accounting.md) · [zh](zh/p30-h3-span-cost-accounting.md)
- `p30-h3-remote-smoke.md`: [en](en/p30-h3-remote-smoke.md) · [zh](zh/p30-h3-remote-smoke.md)
- `p32-p30-h4-budget-overlay.md`: [en](en/p32-p30-h4-budget-overlay.md) · [zh](zh/p32-p30-h4-budget-overlay.md)
- `p32-p30-h4b-selective-readmission.md`: [en](en/p32-p30-h4b-selective-readmission.md) · [zh](zh/p32-p30-h4b-selective-readmission.md)
- `p32-p30-h4b-remote-smoke.md`: [en](en/p32-p30-h4b-remote-smoke.md) · [zh](zh/p32-p30-h4b-remote-smoke.md)
- `p32-p30-h4-remote-smoke.md`: [en](en/p32-p30-h4-remote-smoke.md) · [zh](zh/p32-p30-h4-remote-smoke.md)
- `p31-candidate-reach-ceiling.md`: [en](en/p31-candidate-reach-ceiling.md) · [zh](zh/p31-candidate-reach-ceiling.md)
- `p31-h1-remote-smoke.md`: [en](en/p31-h1-remote-smoke.md) · [zh](zh/p31-h1-remote-smoke.md)
- `p31-h2-strategy-reach-remote-smoke.md`: [en](en/p31-h2-strategy-reach-remote-smoke.md) · [zh](zh/p31-h2-strategy-reach-remote-smoke.md)
- `p33-anchor-precision-repair.md`: [en](en/p33-anchor-precision-repair.md) · [zh](zh/p33-anchor-precision-repair.md)
- `p33-anchor-precision-repair-remote-smoke.md`: [en](en/p33-anchor-precision-repair-remote-smoke.md) · [zh](zh/p33-anchor-precision-repair-remote-smoke.md)
- `p33b-anchor-subtype-calibration.md`: [en](en/p33b-anchor-subtype-calibration.md) · [zh](zh/p33b-anchor-subtype-calibration.md)
- `p33b-anchor-subtype-remote-smoke.md`: [en](en/p33b-anchor-subtype-remote-smoke.md) · [zh](zh/p33b-anchor-subtype-remote-smoke.md)
- `p46-candidate-reach-cost-map.md`: [en](en/p46-candidate-reach-cost-map.md) · [zh](zh/p46-candidate-reach-cost-map.md)
- `p47-request-more-context.md`: [en](en/p47-request-more-context.md) · [zh](zh/p47-request-more-context.md)
- `p48-diagnostic-policy-simulator.md`: [en](en/p48-diagnostic-policy-simulator.md) · [zh](zh/p48-diagnostic-policy-simulator.md)
- `p49-contrastive-candidate-pack-scaffold.md`: [en](en/p49-contrastive-candidate-pack-scaffold.md) · [zh](zh/p49-contrastive-candidate-pack-scaffold.md)
- `p50-fixed-suite-validation.md`: [en](en/p50-fixed-suite-validation.md) · [zh](zh/p50-fixed-suite-validation.md)
- `p52-metadata-local-verifier-scaffold.md`: [en](en/p52-metadata-local-verifier-scaffold.md) · [zh](zh/p52-metadata-local-verifier-scaffold.md)
- `p52a-source-materialization-prerequisite.md`: [en](en/p52a-source-materialization-prerequisite.md) · [zh](zh/p52a-source-materialization-prerequisite.md)
- `p52b-source-backed-local-verifier-feature-matrix.md`: [en](en/p52b-source-backed-local-verifier-feature-matrix.md) · [zh](zh/p52b-source-backed-local-verifier-feature-matrix.md)
- `p52c-local-verifier-scoring-simulator.md`: [en](en/p52c-local-verifier-scoring-simulator.md) · [zh](zh/p52c-local-verifier-scoring-simulator.md)
- `p51-llm-span-narrow-2-diagnostic.md`: [en](en/p51-llm-span-narrow-2-diagnostic.md) · [zh](zh/p51-llm-span-narrow-2-diagnostic.md)
- `p51b-llm-opt-in-contract.md`: [en](en/p51b-llm-opt-in-contract.md) · [zh](zh/p51b-llm-opt-in-contract.md)
- `p57-generalization-gate.md`: [en](en/p57-generalization-gate.md) · [zh](zh/p57-generalization-gate.md)
- `p58-source-backed-verifier-calibration.md`: [en](en/p58-source-backed-verifier-calibration.md) · [zh](zh/p58-source-backed-verifier-calibration.md)
- `p59-contrastive-pack-coverage-counterfactual.md`: [en](en/p59-contrastive-pack-coverage-counterfactual.md) · [zh](zh/p59-contrastive-pack-coverage-counterfactual.md)
- `p60-rmc-policy-v2.md`: [en](en/p60-rmc-policy-v2.md) · [zh](zh/p60-rmc-policy-v2.md)
- `p61-pre-spend-gate.md`: [en](en/p61-pre-spend-gate.md) · [zh](zh/p61-pre-spend-gate.md)
- `p51c-live-micro-run-planner.md`: [en](en/p51c-live-micro-run-planner.md) · [zh](zh/p51c-live-micro-run-planner.md)
- p62-generalization-matrix-aggregator.md: [en](en/p62-generalization-matrix-aggregator.md) · [zh](zh/p62-generalization-matrix-aggregator.md)
- p63-cross-run-slice-collector.md: [en](en/p63-cross-run-slice-collector.md) · [zh](zh/p63-cross-run-slice-collector.md)
- `r16-quality-bakeoff.md`: [en](en/r16-quality-bakeoff.md) · [zh](zh/r16-quality-bakeoff.md)
- `r17-router-guard.md`: [en](en/r17-router-guard.md) · [zh](zh/r17-router-guard.md)
- `r18-calibration-sweep.md`: [en](en/r18-calibration-sweep.md) · [zh](zh/r18-calibration-sweep.md)
- `r19-large-guard-validation.md`: [en](en/r19-large-guard-validation.md) · [zh](zh/r19-large-guard-validation.md)
- `r20-auto-wide.md`: [en](en/r20-auto-wide.md) · [zh](zh/r20-auto-wide.md)
- `r21-auto-wide-matrix.md`: [en](en/r21-auto-wide-matrix.md) · [zh](zh/r21-auto-wide-matrix.md)
- `r22-r27-failure-attribution.md`: [en](en/r22-r27-failure-attribution.md) · [zh](zh/r22-r27-failure-attribution.md)
- `r23-guard-sweep.md`: [en](en/r23-guard-sweep.md) · [zh](zh/r23-guard-sweep.md)
- `r24-quiver-tdb-probe.md`: [en](en/r24-quiver-tdb-probe.md) · [zh](zh/r24-quiver-tdb-probe.md)
- `r25-graph-dense-ablation.md`: [en](en/r25-graph-dense-ablation.md) · [zh](zh/r25-graph-dense-ablation.md)
- `r26-auto-stress.md`: [en](en/r26-auto-stress.md) · [zh](zh/r26-auto-stress.md)
- `r28-promotion-candidate-report.md`: [en](en/r28-promotion-candidate-report.md) · [zh](zh/r28-promotion-candidate-report.md)
- `r29-r26-stress-matrix.md`: [en](en/r29-r26-stress-matrix.md) · [zh](zh/r29-r26-stress-matrix.md)
- `r30-baseline-freeze.md`: [en](en/r30-baseline-freeze.md) · [zh](zh/r30-baseline-freeze.md)
- `r31-real-embedding-provider.md`: [en](en/r31-real-embedding-provider.md) · [zh](zh/r31-real-embedding-provider.md)
- `r32-embedding-view-bakeoff.md`: [en](en/r32-embedding-view-bakeoff.md) · [zh](zh/r32-embedding-view-bakeoff.md)
- `r33-quiver-readiness.md`: [en](en/r33-quiver-readiness.md) · [zh](zh/r33-quiver-readiness.md)
- `r34-r36-quiver-anchor-proto.md`: [en](en/r34-r36-quiver-anchor-proto.md) · [zh](zh/r34-r36-quiver-anchor-proto.md)
- `r37-r38-llm-derived-stress.md`: [en](en/r37-r38-llm-derived-stress.md) · [zh](zh/r37-r38-llm-derived-stress.md)
- `r39-r40-symbol-regex-repair.md`: [en](en/r39-r40-symbol-regex-repair.md) · [zh](zh/r39-r40-symbol-regex-repair.md)
- `r41-r42-graph-admission.md`: [en](en/r41-r42-graph-admission.md) · [zh](zh/r41-r42-graph-admission.md)
- `r43-real-model-full-matrix.md`: [en](en/r43-real-model-full-matrix.md) · [zh](zh/r43-real-model-full-matrix.md)
- `r44-failure-clusters.md`: [en](en/r44-failure-clusters.md) · [zh](zh/r44-failure-clusters.md)
- `r45-promotion-candidate-report.md`: [en](en/r45-promotion-candidate-report.md) · [zh](zh/r45-promotion-candidate-report.md)
- `real-provider-ci-all-smoke.md`: [en](en/real-provider-ci-all-smoke.md) · [zh](zh/real-provider-ci-all-smoke.md)
- `real-provider-ci-large-scale.md`: [en](en/real-provider-ci-large-scale.md) · [zh](zh/real-provider-ci-large-scale.md)
- `real-provider-ci-p2-smoke.md`: [en](en/real-provider-ci-p2-smoke.md) · [zh](zh/real-provider-ci-p2-smoke.md)
- `real-provider-ci-scale-p8-p9.md`: [en](en/real-provider-ci-scale-p8-p9.md) · [zh](zh/real-provider-ci-scale-p8-p9.md)
- `real-provider-p1-embedding-smoke.md`: [en](en/real-provider-p1-embedding-smoke.md) · [zh](zh/real-provider-p1-embedding-smoke.md)
- `real-provider-p1-llm-smoke.md`: [en](en/real-provider-p1-llm-smoke.md) · [zh](zh/real-provider-p1-llm-smoke.md)
- `real-provider-p1-research-log.md`: [en](en/real-provider-p1-research-log.md) · [zh](zh/real-provider-p1-research-log.md)
- `real-provider-p2-research-log.md`: [en](en/real-provider-p2-research-log.md) · [zh](zh/real-provider-p2-research-log.md)
- `real-provider-p2-view-bakeoff-bounded.md`: [en](en/real-provider-p2-view-bakeoff-bounded.md) · [zh](zh/real-provider-p2-view-bakeoff-bounded.md)
- `real-provider-p2-view-bakeoff-selftest.md`: [en](en/real-provider-p2-view-bakeoff-selftest.md) · [zh](zh/real-provider-p2-view-bakeoff-selftest.md)
- `real-provider-p3-quiver-readiness.md`: [en](en/real-provider-p3-quiver-readiness.md) · [zh](zh/real-provider-p3-quiver-readiness.md)
- `real-provider-p3-research-log.md`: [en](en/real-provider-p3-research-log.md) · [zh](zh/real-provider-p3-research-log.md)
- `real-provider-p4-quiver-anchor-proto.md`: [en](en/real-provider-p4-quiver-anchor-proto.md) · [zh](zh/real-provider-p4-quiver-anchor-proto.md)
- `real-provider-p4-research-log.md`: [en](en/real-provider-p4-research-log.md) · [zh](zh/real-provider-p4-research-log.md)
- `real-provider-p5-llm-derived-stress.md`: [en](en/real-provider-p5-llm-derived-stress.md) · [zh](zh/real-provider-p5-llm-derived-stress.md)
- `real-provider-p5-research-log.md`: [en](en/real-provider-p5-research-log.md) · [zh](zh/real-provider-p5-research-log.md)
- `real-provider-p6-graph-admission.md`: [en](en/real-provider-p6-graph-admission.md) · [zh](zh/real-provider-p6-graph-admission.md)
- `real-provider-p6-replay-summary.md`: [en](en/real-provider-p6-replay-summary.md) · [zh](zh/real-provider-p6-replay-summary.md)
- `real-provider-p6-research-log.md`: [en](en/real-provider-p6-research-log.md) · [zh](zh/real-provider-p6-research-log.md)
- `real-provider-p6-symbol-regex-repair.md`: [en](en/real-provider-p6-symbol-regex-repair.md) · [zh](zh/real-provider-p6-symbol-regex-repair.md)
- `real-provider-p7-summary.md`: [en](en/real-provider-p7-summary.md) · [zh](zh/real-provider-p7-summary.md)
- `research-log.md`: [en](en/research-log.md) · [zh](zh/research-log.md)
- `research-summary.md`: [en](en/research-summary.md) · [zh](zh/research-summary.md)
