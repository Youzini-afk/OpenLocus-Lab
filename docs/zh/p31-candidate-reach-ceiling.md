# P31 Candidate Reach Ceiling Study

> 中文译本待补充。当前文件先作为 `docs/en/p31-candidate-reach-ceiling.md` 的 1:1 中文镜像，保留英文原文以保证内容不丢失和链接可回溯。

## English source / 英文原文

# P31 Candidate Reach Ceiling Study

- Schema: `p31-candidate-reach-ceiling-report-v1`
- Generated: 2026-06-14T15:52:29.359187+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P31: 0

- Candidate pool availability: `partial`
- Reach metrics available: True
- P31-H1 handoff detected: True
- Tasks: 5 positive=4 positive_with_gold_spans=4 no_gold=1

## P31-H1 handoff

P31-H1 extends the P21 rich-candidate ephemeral handoff with lightweight
`p31_candidate_pools` and private SCORE-phase `p31_score_gold`. When the handoff
is present, P31 computes real reach metrics; when absent, it falls back to
outcome-only metrics with `candidate_pool_availability=missing_candidate_pool`
and `reach_metrics_available=false`.

## Reach metrics by K

| K | GoldFileReach | GoldSpanReach | GoldSpanExactReach | CandidateAbsent | FileRightSpanWrong |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.6667 | 0.3333 | 0.3333 | 0.3333 | 0.5000 |
| 3 | 0.6667 | 0.3333 | 0.3333 | 0.3333 | 0.5000 |
| 5 | 0.6667 | 0.3333 | 0.3333 | 0.3333 | 0.5000 |
| 10 | 0.6667 | 0.3333 | 0.3333 | 0.3333 | 0.5000 |
| 20 | 0.6667 | 0.3333 | 0.3333 | 0.3333 | 0.5000 |

## Reach numerators/denominators by K

| K | GoldFile | GoldSpan | GoldSpanExact | CandidateAbsent | FileRightSpanWrong |
|---:|---:|---:|---:|---:|---:|
| 1 | 2/3 | 1/3 | 1/3 | 1/3 | 1/2 |
| 3 | 2/3 | 1/3 | 1/3 | 1/3 | 1/2 |
| 5 | 2/3 | 1/3 | 1/3 | 1/3 | 1/2 |
| 10 | 2/3 | 1/3 | 1/3 | 1/3 | 1/2 |
| 20 | 2/3 | 1/3 | 1/3 | 1/3 | 1/2 |

## Strategy miss given gold present@K=5

| Strategy | miss | denominator | rate |
|---|---:|---:|---:|
| llm_span_narrow | 0 | 1 | 0.0000 |
| llm_filter | 0 | 1 | 0.0000 |
| llm_abstain_filter | 1 | 1 | 1.0000 |
| symbol_regex_union | 0 | 1 | 0.0000 |
| rrf_primary | 0 | 1 | 0.0000 |
| bucket_routed_v0 | 0 | 0 | n/a |
| admission_v3 | 0 | 0 | n/a |
| admission_v3_h1 | 0 | 0 | n/a |
| admission_v3_h2 | 0 | 0 | n/a |

## Action/strategy diagnostics

- FilterKillGoldRate: 1.0 (3/3)
- AdmissionFalsePrimaryRate: not_measured (0/0)
  - Reason: selected_admission_action_rows_unavailable
- AdmissionFalseSpanPerNoGoldTask: n/a (0/0)
- EvidenceCoreRejectRate: `not_measured` 

## Failure funnel at K=5

| Stage | Count |
|---|---:|
| evaluated | 4 |
| has_candidate_pool | 3 |
| no_candidate_pool | 1 |
| pool_but_no_candidate_at_5 | 0 |
| candidate_present_no_file | 1 |
| file_reach_no_span | 1 |
| span_reached | 1 |
| span_exact_reached | 1 |
| model_output_loses_gold | 1 |
- funnel_sums_to_positive_tasks: True

## Conclusion

- Self-test-only scaffold evaluated 5 synthetic tasks; this is not quality evidence.
- Reach@5: GoldFile=0.666667, GoldSpan=0.333333, ExactSpan=0.333333, CandidateAbsent=0.333333, FileRightSpanWrong=0.5.
- Reach metrics measure whether candidate evidence alone reaches the gold before routing/admission; they are not a promotion claim and are independent of any policy decision.
- P31 is diagnostic-only and SCORE-phase-only; it does not influence routing or admission.
- FilterKillGoldRate=1.0; AdmissionFalsePrimaryRate=not_measured; AdmissionFalseSpanPerNoGoldTask=None; EvidenceCoreRejectRate=not_measured.
- No policy is promotion-ready or default-ready.
- Next: run P31 against ephemeral records that include candidate evidence pools and compare reach ceilings across candidate_baseline, transformed strategies, and admission policies.

## Safety notes

- No remote model calls were made during P31 evaluation.
- Labels are loaded only after RUN for aggregate SCORE-phase metrics.
- This report contains only aggregate metrics and public task metadata.
- Raw queries, snippets, prompts, responses, gold spans, private labels, candidate paths/spans, and provider fields are not stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p31=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.
