# OpenLocus Current Research Conclusions

Date: 2026-06-22

Status: current research-conclusion memo. This is not a promotion request, not a default-policy change request, and not a benchmark leaderboard report.

Scope: empirical work through BEA-5 quota-sampling implementation in progress, B16-F through B16-J live-provider atom ablations, C5 external benchmark retrieval smokes, F1 utility smokes, and D5-A automated calibration feature extraction/heldout validation.

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
5. **BEA-5 is not complete.** Raw disjoint scale attempts failed closed because only 72 successful/evaluable records were found under the previous raw-slice design. The current fix is explicit success-quota sampling with aggregate yield/exclusion reporting. No BEA-5 scale result is claimed yet.
6. **Automated E/S calibration is progressing, but human calibration is not claimed.** D5-A0/A1/A2 provide automated/proxy feature and heldout validation evidence; they do not establish human-calibrated E/S.

## 2. What is established vs not established

| Area | Established | Not established |
|---|---|---|
| External retrieval benchmarks | ContextBench and RepoQA smoke/matrix/scale runs execute in CI with aggregate-only artifacts. | No benchmark leaderboard or general performance claim. |
| BEA algorithm | BEA policies run on real external benchmark data with private SCORE traces. BEA v0.3 has mixed evidence. | No winner/default/promotion claim. |
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

BEA-5 is currently in progress. Three full CI attempts failed closed before result writeback:

- `27962009344`: only 72 successful records and nonzero RRF-missing classification.
- `27964243698`: still 72 successful records because evaluator hard caps were lower than workflow requests.
- `27966269054`: RRF-missing fixed, but still 72 successful records, below the 120-record scale gate.

The current design is explicit success-quota sampling over a larger disjoint raw scan:

- sampling mode: `success_quota`
- raw caps: ContextBench 480, RepoQA 240
- target successful records: 120
- minimum benchmark contribution gates: ContextBench >= 40, RepoQA >= 20
- public artifact must report attempted/success/excluded aggregate counts
- private SCORE rows remain `records_successful × 7`
- private attempt/exclusion rows are private and only manifest counts are public

No BEA-5 scale conclusion exists until this quota CI passes.

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

Immediate next work is BEA-5 quota-sampling completion:

1. Finish local verification of the quota-sampling implementation.
2. Get @oracle review.
3. Commit the quota fix.
4. Run full BEA-5 quota CI.
5. If it passes, write back the result with aggregate yield/exclusion counts.
6. If it fails, record the failure honestly; do not weaken the gate.

After BEA-5, choose between:

- broader external robustness with the frozen policy,
- a v0.4 algorithm change targeted at observed BEA failure modes,
- or another downstream smoke only if it tests a new mechanism rather than repeats B16-J.

## 9. One-sentence conclusion

OpenLocus now has real empirical evidence pipelines and a bounded target+support downstream signal, but BEA is still mixed and not a default/winner; the immediate research problem is whether frozen BEA v0.3 remains robust under explicit success-quota external sampling.
