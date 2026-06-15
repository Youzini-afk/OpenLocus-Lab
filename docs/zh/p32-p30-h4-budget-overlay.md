# P32 / P30-H4 确定性预算覆盖层

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P32 / P30-H4 Deterministic Budget Overlay

## Status

- Stage: P32/P30-H4 diagnostic overlay
- Artifact: `eval/p30_admission_model_v3.py` (policy `admission_v3_h4`)
- External calls: 0
- Promotion ready: false
- Default should change: false
- EvidenceCore semantics changed: false

## Purpose

P32/P30-H4 is a deterministic diagnostic lane that tests whether P33-B anchor-subtype metadata can be used to budget-demote admission decisions without changing Rust/EvidenceCore or the default pipeline strategy. It is explicitly **not** a promotion candidate.

H4 consumes only RUN-phase public features (`task_bucket`, `task_risk_tags`, `route_features`) and the private P33-B handoff fields (`p33b_anchor_subtypes`, `p33b_anchor_subtypes_schema`). It never uses labels, gold spans, or outcome metrics during routing. The private handoff fields are copied into the normalized in-memory task and are never emitted into public reports or workflow artifacts.

## P33-B conclusions that drive H4

- No subtype is primary-safe.
- `span_overlap` is the best subtype but still carries approximately `false_per_gold ≈ 1.78` and negative `net_span_value_2x`.
- `symbol_regex_fusion` has high reach but 24/66 gold-to-false ratio.
- `same_file_only` is weaker; `disagree` and `single_source` are dangerous.
- RRF backing improves precision but is not sufficient for primary promotion.

Therefore H4 tests budgeted **demotion**, not primary promotion.

## Routing summary

| Situation | H4 action |
|---|---|
| Negative / dense / hard-distractor / deeply penalized | `supporting_only` if dense/graph support; else `abstain` or `apply_llm_filter` |
| Ambiguous / hallucination-risk | `weak_candidate_only` or `supporting_only` for span-overlap cases without negative tags; otherwise `apply_llm_filter` |
| Best subtype `span_overlap` in low-risk public bucket | `supporting_only` if RRF-backed, else `weak_candidate_only` |
| `same_file_only` in low-risk public bucket | `weak_candidate_only`; otherwise `apply_llm_filter` |
| `disagree` / `single_source` | `weak_candidate_only` only in clearly positive/low-noise buckets; otherwise `apply_llm_filter` |
| Exact/unique-symbol signal | treated as budget diagnostic non-primary (`weak_candidate_only` / filter) |
| Missing P33-B subtype metadata | conservative `bucket_routed_v0`-like fallback using existing non-primary actions |

H4 never selects `admit_symbol_regex_union`, `admit_rrf_primary`, or `admit_llm_span_narrow` based solely on local anchor subtype evidence.

## Report flags

A P30 report that includes H4 must set:

- `h4_available`: true when at least one task carries a P33-B subtype handoff.
- `h4_budget_overlay`: true.
- `p33b_handoff_detected`: true when P33-B subtype metadata is present.
- `promotion_ready`: false.
- `default_should_change`: false.

## Quality comparability

`admission_v3_h4` reports `quality_comparable`, `blocked_by_missing_action_outcomes`, and `selected_action_fallback_rate` like H1/H2. On real `p21_llm_rich` records, H4 is expected to be quality-comparable with a zero selected-action fallback rate because it only selects actions that must have measured outcomes in the P33-B handoff.

## Safety

- No remote model calls.
- Private labels and gold spans are used only for aggregate scoring after actions are fixed.
- Private P31 / P33-B handoff fields are not written to public artifacts.
- `candidate_not_fact=true`, `external_calls=0`.
