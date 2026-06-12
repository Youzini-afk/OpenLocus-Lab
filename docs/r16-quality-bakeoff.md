# R16 Multi-Method Quality Bakeoff

**This is a lexical/symbol/RRF quality bakeoff. No provider/dense/LLM claims are made.**

Date: 2026-06-12

## Summary

R16 runs the R14-S, R15-M, and R15-stress benchmark matrices across four retrieval methods (regex, BM25, symbol, RRF) and aggregates results into a cross-matrix quality comparison. All safety gates passed across all matrices. No method is promoted to universal default.

## Safety Checks: All Passed

- R14-S: safety_passed=true, citation_validity=1.0 for all methods, citation_hash_checked=true, canary_retrieval.passed=true
- R15-M: safety_passed=true, citation_validity=1.0 for all methods, citation_hash_checked=true, canary_retrieval.passed=true
- R15-stress: safety_passed=true, citation_validity=1.0 for all methods, citation_hash_checked=true, canary_retrieval.passed=true
- No remote calls in any benchmark run
- Citation hash checked in R14/R15 reports via Rust validator in isolated roots

## R14-S Matrix (regex, bm25, symbol, rrf)

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| file_recall@1 | 0.457 | 0.696 | 0.674 | 0.543 |
| file_recall@5 | 0.587 | 0.870 | 0.717 | 0.870 |
| file_recall@10 | 0.630 | 0.870 | 0.717 | 0.870 |
| mrr | 0.518 | 0.770 | 0.684 | 0.660 |
| span_f0.5@10 | 0.068 | 0.064 | 0.199 | 0.084 |
| hard_negative_hit_rate@10 | 0.152 | 0.196 | 0.043 | 0.152 |
| negative_nonempty_rate@10 | 0.000 | 0.000 | 0.000 | 0.000 |

## R15-M Matrix (regex, bm25, symbol, rrf)

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| file_recall@1 | 0.852 | 0.548 | 0.807 | 0.933 |
| file_recall@5 | 0.956 | 0.719 | 0.830 | 0.993 |
| file_recall@10 | 0.970 | 0.741 | 0.844 | 0.993 |
| mrr | 0.889 | 0.623 | 0.820 | 0.959 |
| span_f0.5@10 | 0.263 | 0.188 | 0.310 | 0.253 |
| hard_negative_hit_rate@10 | 0.289 | 0.230 | 0.052 | 0.259 |
| negative_nonempty_rate@10 | 0.000 | 0.645 | 0.000 | 0.645 |

## R15-stress Matrix (regex, bm25, symbol, rrf)

Stress tier contains only negative tasks; recall/MRR/SpanF metrics are not applicable.

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| negative_nonempty_rate@10 | 0.474 | 0.684 | 0.105 | 0.684 |

## Winners per Metric

### R14-S

| Metric | Winner | Notes |
|---|---|---|
| file_recall@1 | bm25 | BM25 dominates top-1 on self-referential fixture |
| file_recall@5 | bm25, rrf | Tied at 0.870 |
| file_recall@10 | bm25, rrf | Tied at 0.870 |
| mrr | bm25 | 0.770 vs next-best 0.684 (symbol) |
| span_f0.5@10 | symbol | 0.199 — best span precision by far |
| hard_negative_hit_rate@10 | symbol | 0.043 — lowest hard-negative contamination |
| negative_nonempty_rate@10 | all | 0.000 — no false positives on negatives |

### R15-M

| Metric | Winner | Notes |
|---|---|---|
| file_recall@1 | rrf | 0.933 — RRF fusion dominates recall |
| file_recall@5 | rrf | 0.993 |
| file_recall@10 | rrf | 0.993 |
| mrr | rrf | 0.959 |
| span_f0.5@10 | symbol | 0.310 — best span precision |
| hard_negative_hit_rate@10 | symbol | 0.052 — lowest contamination |
| negative_nonempty_rate@10 | regex, symbol | 0.000 — no false positives on negatives |

### R15-stress

| Metric | Winner | Notes |
|---|---|---|
| negative_nonempty_rate@10 | symbol | 0.105 — lowest false-positive rate on stress negatives |

## Conclusions

1. **RRF wins R15-M recall/MRR (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative false positive behavior** (negative_nonempty@10 0.645 on R15-M and 0.684 on stress), so it is not safe as default for precision-sensitive tasks without negative gating or query intent routing.

2. **Symbol has best span precision/hard-negative profile on R15-M** (SpanF0.5 0.310, hard_negative_hit_rate 0.052, negative_nonempty 0.000) but lower recall than RRF, so it is ideal as precision anchor, not sole retriever.

3. **Regex is surprisingly strong on mined exact-symbol external tasks** (R15-M FileRecall@1 0.852, negative_nonempty 0.000), but this reflects task distribution and exact-string bias; not a general natural-language conclusion.

4. **BM25 strong in R14-S but weak and false-positive-heavy in R15-M/stress**; needs query intent routing or threshold/negative guard.

5. **No promotion of any method to universal default from R16**; next research should be query intent router / negative guard / method fusion policy, not raw channel addition.

## Caveats

- R16 is a multi-method quality bakeoff across R14-S/R15-M/R15-stress matrices; not a universal quality conclusion.
- Mined labels are not human-verified; line ranges may be imprecise.
- Hard negatives are first-class data measuring precision under ambiguity.
- Citation validity is a safety gate, not a quality metric.
- No provider/dense/LLM quality claims are made.
- RRF negative_nonempty_rate reflects BM25 false-positive inheritance; not a retrieval quality win.
- R15-M RRF FileRecall@1 can vary slightly with benchmark implementation details; the committed value is from the strict R16 aggregate run.
- R14-S uses self-referential OpenLocus workspace data; not generalizable.
- R15 uses 9 external local repos which are workspace snapshots; not modified.
