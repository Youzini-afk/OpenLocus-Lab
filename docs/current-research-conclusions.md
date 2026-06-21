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
change, or downstream agent value. No
runtime/default-policy/promotion/downstream-value claim is made.

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
EvidenceCore 语义变更或下游 agent 价值。C5-C manual CI run 27905621090 已在 fail-closed workflow 下通过：20 行抓取，3/3 方法成功，bm25 file_recall@10=0.35 / mrr=0.143107 / span_f0.5@10=0.020838 / success_rate=1.0，regex 与 symbol file_recall@10=0.0；较早 run 27905321437 的绿色 unavailable 被视为 fail-open 并已修复；这仍只是 smoke 诊断，不是外部 benchmark 性能/default-policy 声明。当前不作
runtime/default-policy/promotion/downstream-value 声明。

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
- `ci-research-harness.md`: [en](en/ci-research-harness.md) · [zh](zh/ci-research-harness.md)
- `current-research-conclusions.md`: [en](en/current-research-conclusions.md) · [zh](zh/current-research-conclusions.md)
- `d5a-automated-es-calibration.md`: [en](en/d5a-automated-es-calibration.md) · [zh](zh/d5a-automated-es-calibration.md)
- `b16a-minimal-mock-agent-paired-run.md`: [en](en/b16a-minimal-mock-agent-paired-run.md) · [zh](zh/b16a-minimal-mock-agent-paired-run.md)
- `b16b-less-separable-mock-paired-run.md`: [en](en/b16b-less-separable-mock-paired-run.md) · [zh](zh/b16b-less-separable-mock-paired-run.md)
- `b16c-live-provider-paired-smoke.md`: [en](en/b16c-live-provider-paired-smoke.md) · [zh](zh/b16c-live-provider-paired-smoke.md)
- `b16d-less-trivial-live-provider-paired-smoke.md`: [en](en/b16d-less-trivial-live-provider-paired-smoke.md) · [zh](zh/b16d-less-trivial-live-provider-paired-smoke.md)
- `b16e-broader-live-provider-paired-smoke.md`: [en](en/b16e-broader-live-provider-paired-smoke.md) · [zh](zh/b16e-broader-live-provider-paired-smoke.md)
- `f1-counterfactual-evidence-utility.md`: [en](en/f1-counterfactual-evidence-utility.md) · [zh](zh/f1-counterfactual-evidence-utility.md)
- `f1b-retrieval-derived-counterfactual-utility.md`: [en](en/f1b-retrieval-derived-counterfactual-utility.md) · [zh](zh/f1b-retrieval-derived-counterfactual-utility.md)
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
