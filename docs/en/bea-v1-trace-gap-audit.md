# BEA-v1 Trace Gap Audit

Date: 2026-06-27

BEA-v1-P0-1 is a scanner-validated trace-gap audit over the committed FD1, P1, FD2-A1, P4L, N2, and N3 artifacts. It does not run new retrieval, does not call providers, does not implement a policy, and does not authorize P5, BEA-v1-A, selector/reranker work, runtime promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

The purpose is to convert the post-N3 research state into explicit trace requirements for follow-up research agents. It follows the updated artifact rule: public output may include sanitized per-gap records when no raw paths, snippets, ranks, candidate lists, prompts, provider payloads, private paths, or source-linkable private data are exposed.

## Inputs

The audit reads committed public artifacts only:

- FD1 failure decomposition: `bea_fd1_decomposition_pass`.
- BEA-v1-P1 actionability audit: `no_go_retrieval_availability_limit`.
- FD2-A1 attribution replay: `bea_fd2a1_attribution_replay_pass`.
- P4L locked non-Python scheduler validation: `bea_v1_p4l_locked_non_python_scheduler_validation_pass`.
- N2 rank/pack decomposition: `n2_rank_pack_actionability_decomposition_pass`.
- N3 merge-order design simulation: `n3_merge_order_design_inconclusive`.

## Result

```text
status: trace_gap_audit_pass
trace gaps audited: 12 FD1 categories
forbidden scan: pass
self-test: 5 / 5
```

Trace availability summary:

```text
sanitized_available:                         3
private_only_needs_public_export:            3
missing_label:                               3
missing_trace:                               2
aggregate_only_insufficient_for_deep_research: 1
```

Priority gap summary:

```text
P0 unresolved/public-export gaps: 8
P1 unresolved/public-export gaps: 1
```

## Main finding

The N2/N3 rank-pack line already provides sanitized per-record rows for rank/pack and merge-order review, but the broader BEA-v1 mechanism surface is still trace-incomplete for deep research agents.

The immediate blockers are:

- `action_cost_trace`: available in private manifests from scheduler phases, but not yet exported as sanitized per-record scheduler rows.
- `support_link_trace`: missing support/target relation labels for support counterfactual work.
- `same_file_redundancy_trace`: FD1 marks redundancy as missing trace.
- `risk_penalty_trace`: FD1 marks risk-removed-gold as missing trace.
- `ordered_prefix_stop_trace`: only aggregate evidence is currently available for early-stop diagnosis.

## Authorized next work

This phase authorizes only trace/data-surface work:

- build an actionability matrix refresh using the explicit trace-gap rows;
- export a scanner-validated sanitized P4/P4L scheduler dataset;
- design support-link labeling/counterfactual inputs;
- preserve or export redundancy, risk-penalty, and ordered-prefix stop trace fields before new policy experiments.

It does not authorize implementation of a new retrieval policy, selector/reranker execution, P5, BEA-v1-A, runtime/default promotion, frozen P4 reruns, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_trace_gap_audit.py`
- Report: `artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json`

