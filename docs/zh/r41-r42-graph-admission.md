# R41-R42 Graph Role and Admission Model v2

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R41-R42 Graph Role and Admission Model v2

R41 evaluates graph as supporting/rerank/explainer only. R42 introduces an explainable rule-based admission model without promoting it.

## Safety

- promotion_ready: `False`
- default_should_change: `False`
- evidencecore_semantics_changed: `False`
- graph_default_expansion_allowed: `False`
- graph_role_recommendation: `supporting_or_explainer_only`
- learned_calibrator_default_allowed: `False`

## Metrics

- selective_risk: `0.0`
- coverage: `0.3333333333333333`
- FileRecall@1: `0.0`
- SpanF0.5: `0.1923076923076923`
- graph_added_gold_span: `1`
- graph_added_false_span: `1`
- graph_expansion_blocked: `True`

## Admission Actions

- abstain: `2`
- admit_primary: `1`

## Decision

- Graph expansion remains blocked; graph can continue as supporting/explainer research.
- `admission_v2_rules` is explainable research only; no learned router/default promotion.

