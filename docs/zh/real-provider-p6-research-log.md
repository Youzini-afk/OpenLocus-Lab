# Real Provider P6 Research Log

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# Real Provider P6 Research Log

## Scope

P6 replayed the R39-R42 repair/admission harnesses and validated the P5 generated stress corpus remains failure-discovery only.

- R39/R40: symbol extraction repair and regex normalization replay
- R41/R42: graph role and admission_v2_rules replay
- P5 stress: 24 public tasks + 24 private labels, deterministic failure-discovery only

## Results

R39/R40:

- best_regex_mode: `regex_hybrid_normalized`
- symbol_FileRecall_delta: `+0.2`
- symbol_false_primary_delta: `0.0`
- promotion_ready: `false`

R41/R42:

- graph_expansion_blocked: `true`
- graph_pollution_ratio: `0.5`
- selective_risk: `0.0`
- coverage: `0.3333`
- promotion_ready: `false`

P5 stress validation:

- public tasks contain only public fields
- private labels remain separate
- label quality is `deterministic_validated_failure_discovery`
- not human-verified / not promotion evidence

## Decision

Regex normalization and symbol repair remain promising repair tracks, but broad R26/R38 validation is still required. Graph remains supporting/explainer-only. Admission v2 remains research-only and does not change defaults.

