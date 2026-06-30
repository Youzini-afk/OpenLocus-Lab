# BEA-v1-N10EM Difference-Aware Winner Public Replication Package

Date: 2026-06-30

BEA-v1-N10EM packages the public N10EK/N10EL chain. It reads only public artifacts and does not read private rows, recompute the transform, run retrieval, execute OpenLocus, generate candidates, use network, or change runtime/default behavior.

## Result

```text
status: difference_aware_winner_public_replication_package_complete_n10en_authorized
self-test: 8 / 8
forbidden scan: pass
N10EK winner top10/top20/top50/top100: 13 / 16 / 20 / 26
N10EL audit top10/top20/top50/top100: 13 / 16 / 20 / 26
lost baseline top10: 0
chain consistent: true
```

## Packaged policy boundary

- frozen rule: `if top5_novel_candidate_item_count >= 4 then guarded_top5_novel_distinct else full_novel_first`
- threshold counts top-5 candidate items, not distinct files
- old-pool membership is used to define novelty
- gold is not used for policy
- full/guard outcome membership is not used for policy
- N10EK transform code is not called by the N10EL audit

## Meaning

N10EM confirms that the same-source N10EK experiment and N10EL independent audit agree. This is a strong same-row replication package for the difference-aware rule. It is still not a runtime/default recommendation, method-winner claim, downstream-value claim, or heldout/generalization claim.

## Handoff

N10EM itself remains a public-only package and performs no private reads, recompute, retrieval, OpenLocus execution, network access, or candidate generation.

Its handoff authorizes only N10EN bounded CI-validation actions: manual GitHub Actions canary over manifest-listed public repositories, public GitHub clone/fetch, local OpenLocus CLI build, local OpenLocus search against cloned public repos, temporary public candidate materialization in runner temp space, score-phase label generation after RUN outputs are fixed, and upload of a sanitized aggregate-only report.

This does not authorize provider/model network calls, remote embeddings, private assets, external benchmark downloads, raw candidate/label/query/path upload, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, heldout/generalization claims, scaled retrieval claims, or production retrieval changes.

## Artifact

- Script: `eval/bea_v1_n10em_difference_aware_winner_public_replication_package.py`
- Report: `artifacts/bea_v1_n10em_difference_aware_winner_public_replication_package/bea_v1_n10em_difference_aware_winner_public_replication_package_report.json`
