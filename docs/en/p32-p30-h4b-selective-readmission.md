# P32 / P30-H4B Selective Primary Re-Admission Diagnostic

## Status

- Stage: P32/P30-H4B diagnostic lane
- Artifact: `eval/p30_admission_model_v3.py` (policy `admission_v3_h4b`)
- External calls: 0
- Promotion ready: false
- Default should change: false
- EvidenceCore semantics changed: false
- Selective readmission: true

## Purpose

P32/P30-H4B is an even narrower sibling of P32/P30-H4. While H4 tests budgeted
**demotion**, H4B tests whether an extremely strict subset of P33-B subtype
evidence can ever justify a primary-admit action. It is explicitly a
non-promotional diagnostic; almost all tasks remain hard-guarded or demoted.

H4B uses only RUN-phase public task metadata (`task_bucket`, `task_risk_tags`,
`route_features`) and the private P33-B subtype handoff
(`p33b_anchor_subtypes`, `p33b_anchor_subtypes_schema`). It does not use
labels, gold spans, or outcome metrics during routing.

## P33-B motivation

P33-B showed that even the best anchor subtype bucket (`span_overlap`) is not
primary-safe in aggregate. H4B asks: is there a *very small* cell inside that
bucket that *might* be primary-safe? To qualify, a task must satisfy every
criterion in a strict conjunction, not just one strong signal.

## Strict primary re-admission gate

`admit_symbol_regex_union` is selected only when ALL of the following hold:

- P33-B handoff is present.
- The best/top subtype row is `source_class == symbol_regex_fusion`,
  `agreement_class == span_overlap`, and `rrf_backing == true`.
- `local_anchor == true`.
- `symbol_regex_agree_span == true`.
- `query_noise <= 0.1`.
- Public bucket/tags are in a low-risk positive set
  (`exact_symbol_unique`, `exact_symbol`, `high_confidence`, `route_handler`,
  `config`, `positive`, `likely_positive`) and contain no negative, dense,
  hard-distractor, ambiguous, or hallucination-risk tags.
- At least one of `exact_unique_symbol_anchor` or `rrf_anchor_agree_span` holds.

If the same gate also has `rrf_backed_by_anchor == true` and
`rrf_anchor_agree_span == true`, H4B may optionally select `admit_rrf_primary`
instead, but the gate itself does not change.

## Hard guards and demotions

Everything else is routed to non-primary actions:

- Missing P33-B handoff -> `weak_candidate_only`/`apply_llm_filter`.
- `regex_only`, `same_file_only`, `disagree`, or `single_source` best subtype ->
  `apply_llm_filter` / `weak_candidate_only`.
- Negative, dense, hard-distractor, ambiguous, hallucination-risk, or
  `query_noise > 0.2` -> `apply_llm_filter` / `weak_candidate_only`.
- `span_overlap` `symbol_regex_fusion` that fails the strict gate ->
  `supporting_only` if RRF-backed and low-risk; else `weak_candidate_only` or
  `apply_llm_filter`.

H4B never introduces new action names.

## Report flags

Top-level flags:

- `h4b_available`: true when at least one task carries a P33-B subtype handoff.
- `h4b_budget_overlay`: true.
- `h4b_selective_readmission`: true.
- `p33b_handoff_detected`: true when P33-B subtype metadata is present.
- `promotion_ready`: false.
- `default_should_change`: false.

Per-policy fields:

- `rule_counts`: strict_union_re_admit, strict_rrf_re_admit, hard_guard,
  missing_handoff, demote_span_overlap, demote_same_file,
  filter_dangerous_subtype, other.
- `h4b_primary_opportunity_count`: strict_union + strict_rrf counts.
- `false_per_gold` and `net_span_value_2x` from aggregate added gold/false spans.
- `span_cost_summary` from P30-H3 action accounting.
- `quality_comparable`, `selected_action_fallback_rate`, `policy_action_counts`.

## Safety

- No remote model calls.
- Private handoff fields are in-memory only and never emitted publicly.
- Aggregate-only public artifacts: no per-task rows, candidate paths/spans,
  subtype rows, gold spans, or private labels are stored.
- `candidate_not_fact=true`, `external_calls=0`.
