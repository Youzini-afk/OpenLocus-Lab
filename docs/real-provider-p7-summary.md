# Real Provider P7 Summary

P7 summarizes P1-P6 real-provider tests. No provider URL or key is committed.

## Main Findings

- Embedding smoke status: `ok`
- LLM smoke status: `ok`
- P2 dense FileRecall@3: `0.6666666666666666` with primary_false_positive_rate `1.0`
- P3 QuIVer fit: `mixed`; graph implemented: `False`
- P4 best anchored strategy: `flat_f32__source_vs_test_split__anchor_regex` with added_gold `2` and added_false `0`
- P5 stress tasks: `24` public / `24` private labels
- P6 best regex mode: `regex_hybrid_normalized`; graph expansion blocked: `True`

## Decision

- `promotion_ready=false`
- `default_should_change=false`
- dense remains supporting-only and preferably anchor-seeded
- QuIVer remains diagnostic-only; no global default
- LLM-derived/stress remains not Evidence and not promotion evidence
- graph remains supporting/explainer-only

## Next Required Tests

- run P2/P3/P4 on CI smoke public corpus with repo/file caps
- add remote-safe repo/file cap before running R26/R38 large locks
- compare Qwen3-Embedding-8B/4B/0.6B and bge-m3 on the same capped corpus
- validate anchored dense/quiver against P5 stress traps
- run admission_v2_rules with real dense support features
