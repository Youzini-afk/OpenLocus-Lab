# BEA-v1-N6X-FR Explicit Full-Frozen Candidate-Pool Reconstruction Capture

Date: 2026-06-28

BEA-v1-N6X-FR is the first explicitly broader full-frozen reconstruction boundary after N6XR. It is preflight-only by default. It verifies committed public artifacts and local prerequisite buckets for a future full-frozen candidate-pool reconstruction capture, but it does not run network access, repository clones, the OpenLocus binary, P4L/N1/N2/N3 reruns, retrieval, selector/reranker execution, counterfactuals, candidate-pool generation, or materialization.

## Result

```text
status: no_go_n6xfr_local_prerequisites_unavailable
self-test: 18 / 18
forbidden scan: pass
openlocus binary available: false
FD1 private decomposition available: false
P4L private source available: false
local prerequisites available: false
execution attempted: false
```

## What was checked

N6X-FR loads the public N4, N5, N6, N6F, N6G, N6XR, P4L, and N2 artifacts and verifies their expected statuses. It then checks prerequisite buckets without reading private file contents or serializing private paths/names:

- OpenLocus release binary availability;
- explicit FD1 private decomposition availability;
- P4L private source availability;
- whether canary or full-40 execution was explicitly requested;
- whether private output boundaries remain ignored and scanner-safe.

The default local run has missing prerequisites, so it stops before canary reconstruction.

## Execution flags

The CLI accepts future checkpoint flags `--execute-canary`, `--execute-full-40`, `--openlocus`, `--fd1-private-decomposition-jsonl`, and `--private-output-root`. In this checkpoint they are safe no-op/preflight inputs: if prerequisites are unavailable, no network, clone, binary execution, or replay is attempted.

## Decision

N6X-FR does not indicate method failure; it indicates capture prerequisites are unavailable locally under the explicit full-frozen boundary. The next allowed phase is `none_until_full_frozen_reconstruction_prerequisites_are_available`. N6X-FR does not authorize N7, canary execution, full-40 capture, retrieval, full rerun, network/git clone, private reads, P5, BEA-v1-A, selector/reranker execution, counterfactuals, runtime/default changes, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture.py`
- Report: `artifacts/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture_report.json`
