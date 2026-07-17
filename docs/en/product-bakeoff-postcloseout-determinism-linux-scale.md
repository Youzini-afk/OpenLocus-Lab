# Product Bakeoff Post-closeout Determinism Linux Scale Closure

Date: 2026-07-17

Status: `product_bakeoff_postcloseout_determinism_linux_scale_complete_no_tournament_authorization`

This closes the production-scale synthetic Linux validation requested by the post-B2.5 determinism repair. It does not reopen B2.5, reclassify its failed-closed decision, score or rank its matrix, reuse its launch authorization, change the product default, or authorize another tournament.

The public aggregate is [`product_bakeoff_postcloseout_determinism_linux_scale.json`](../../artifacts/product_bakeoff_determinism_linux_scale/product_bakeoff_postcloseout_determinism_linux_scale.json). Its digest is `detlinux_b82d0262881b5f2623b866e3f9ea504e68cc591b1c23ac43c20349816af7bcfc`.

## Final review finding

The comprehensive review found one residual issue on the actual bakeoff path. Core RRF had already been repaired to divide a wider vote evenly across several incomparable minimal descendants, but bakeoff input normalization still selected one descendant before RRF saw the ambiguity. That earlier selection could recreate a positional winner even though core RRF itself was deterministic.

The repaired behavior now distinguishes two cases:

- one unique minimal descendant: canonicalize the wider cell to that descendant;
- several incomparable minimal descendants: retain the wider cell and let production RRF split its contribution evenly across all minimal descendants.

Small regression tests cover both cases. The Linux scale harness also exercises the full bakeoff normalization-to-RRF path, not only the RRF helper in isolation.

## Linux synthetic scale validation

All runs used release-profile Rust tests, synthetic temporary inputs only, no ignored `runs/` input, no provider/model/network call, and the exact source checkpoint that passed cross-platform CI.

| Tier | Synthetic files | Ambiguous spans | Fresh process iterations | Test invocations per process | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Default production scale | 20,000 | 4,096 | 3 | 4 | pass |
| Elevated scale | 50,000 | 8,192 | 2 | 4 | pass |
| Declared parameter ceiling | 100,000 | 20,000 | 1 | 4 | pass |

Each process iteration covered:

1. persistent BM25 complete equal-score boundary collection;
2. temporary BM25 complete equal-score boundary collection;
3. core RRF ambiguous-overlap score conservation;
4. bakeoff pre-fusion ambiguous-overlap normalization followed by production RRF.

Across the three tiers, six fresh process iterations and 24 stress-test invocations passed. The final tier exercised the maximum file and span counts accepted by the stress tests.

## Comprehensive review scope

The review followed the exact B2 through B2.5 frozen tournament component path: persistent and temporary BM25; literal, symbol, and AST caps; graph build, expansion, support ordering, and caps; bakeoff component canonicalization; pre-fusion overlap handling; RRF ties, exact cells, containment, and final ordering; adapter candidate order and two-step support projection; the future scorer-equivalent comparability projection; and terminal public-archive validation.

No known order-dependent cap remains in that reviewed tournament path. This is deliberately not a claim that every unrelated product or laboratory surface in the entire repository is deterministic.

## Interpretation and remaining limits

The earlier research-design conclusion still holds: an exact semantic repeatability hash is broader than the frozen scorer in principle, so a future pre-score gate should compare the same oracle-blind scorer-equivalent projection that the future scorer uses for repeated cells. Source currentness, scoreability, lineage, fairness, and provider isolation remain separate mandatory gates.

B2.5 remains the authoritative `failed_closed_no_result` closeout. Its failure is not reclassified as diagnostic-only, and no B2.5 score or rank exists.

Production-scale Linux stress is now complete. A future tournament still requires a separately preregistered gate/scorer projection, qualification of the exact future runtime, and a fresh holdout that reuses neither B2.5 treatment output nor its launch authorization.
