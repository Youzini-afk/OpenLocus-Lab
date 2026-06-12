# R24 QuIVer/TDB/Dense Probe

**NOT a QuIVer bakeoff.** This is an availability + mock dense candidate-channel probe + TDB placeholder status check. QuIVer remains future work.

## Purpose

R24 answers three questions:

1. **Is QuIVer implemented?** No. QuIVer is not implemented. R24 scans for QuIVer implementation in Rust crates and dependencies and reports `quiver_implemented=false`. No fabricated QuIVer quality data is produced. All R24.1 diagnostic fields (BQ_overlap, quiver recall, quiver precision, etc.) are set to `unavailable`/`not_measured` with reason `quiver_not_implemented` and explicit `next_required_tests`. Numeric 0 is NEVER output as a quality result for QuIVer metrics.

2. **What is TDB's status?** TDB (TriviumDB) is a feature-gated metadata/chunk store behind the `tdb` Cargo feature. It is NOT an ANN index, NOT QuIVer, and NOT a vector retrieval backend. In the default build, TDB is a placeholder that returns `available=false`, `success=false`. R24 probes TDB status via `openlocus store status tdb --json` and reports the placeholder response. It does not claim retrieval quality. `tdb_stale_leak_count` is `not_applicable` unless actual TDB candidate search exists. R24 does not set 0 as proof if not tested.

3. **Can dense_mock serve as a candidate-channel safety/quality smoke?** Dense mock uses deterministic blake3-based vectors that do NOT capture semantic similarity. It is a candidate-channel integration/safety probe, not a semantic quality measurement. R24 runs `openlocus dense build --provider mock --experimental --json` and `openlocus dense search --provider mock --limit 10 --json <query>` for each R20 task in isolated repo roots, then scores against R20 labels. The scores measure whether the mock dense channel produces valid evidence and how its retrieval behavior interacts with the failure-surface benchmark — they do NOT measure semantic retrieval quality.

## Architecture

### Phase 1: RUN (public tasks only, no labels)

1. **Availability checks** (fail-closed evidence):
   - QuIVer implementation scan: no files/deps/symbols for QuIVer except eval/docs placeholders. Report `unavailable`, not run.
   - TDB default status via `openlocus store status tdb --json`: should be `available=false`/`success=false` or similar. No retrieval quality claimed.
   - Dense provider status: mock and disabled available; real provider unavailable.

2. **Dense mock candidate-channel probe**:
   - Use R20 repo lock source paths. Build isolated temp roots by allowlist-copying source files under `repo_id/` (like R21) and `.openlocus/policy.toml`.
   - For each repo, run `openlocus dense build --provider mock --experimental --json` once.
   - For R20 tasks, run `openlocus dense search --provider mock --limit 10 --json <query>` in that repo's isolated root.
   - Preserve `.openlocus/embeddings` and `.openlocus/audit` between build/search; only transient traces/context are cleaned during the run.
   - Produce R24-owned artifacts in `runs/`: dense_mock predictions/evidence/rejections/trace plus dense_mock_plus_rrf predictions/evidence/rejections/trace, and manifest JSON. Do NOT commit `runs/`.
   - Validate dense evidence through `openlocus citations validate --json` before cleanup. `citation_validity` must be 1.0 if evidence exists.
   - Scan `.openlocus/embeddings` and audit for canary tokens and query leaks. A non-secret dense path canary runs after dense build and fails closed if it cannot traverse the vector store and return evidence for non-empty stores. `success=false` task searches are recorded as candidate rejections, not as process failures, when the CLI exits cleanly with a block/no-hit reason.

3. **Optional fusion**: `dense_mock_plus_rrf` by RRF-fusing dense_mock with R21 rrf predictions, but only if dense evidence is citation-valid and no synthetic invalid channels. Score separately and report whether dense candidates actually contribute to fused output.

### Phase 2: SCORE (labels only, no CLI)

4. Score dense_mock using R20 labels with the following metrics:
   - FileRecall@1/3/5, MRR, SpanF0.5, SpanPrecision, SpanRecall
   - token_waste, no_gold_nonempty_rate
   - primary_false_positive_rate
   - must_not_primary_violation_rate
   - abstain_rate, weak_candidate_rate
   - hard_distractor_hit_rate
   - Bucket metrics for: query_category, risk_tags, expected_behavior, repo_id, language
   - Dense semantic trap / proper_name / config/API buckets separately summarized

5. TDB stale/materialization smoke:
   - Default build TDB is unavailable placeholder. `store status tdb` confirms. Do not enable feature unless cheap.
   - If not run feature build, report `tdb_feature_probe_not_run` with reason.
   - `tdb_stale_leak_count` is `not_applicable` unless actual TDB candidate search exists.

6. QuIVer diagnostic fields (R24.1):
   - BQ_overlap, quiver recall, quiver precision, quiver MRR, quiver F0.5: all `unavailable`/`not_measured` with reason `quiver_not_implemented` and `next_required_tests`.

## Safety gates

- Labels not loaded until after dense run complete
- Citation validator pass for dense artifacts
- Artifact manifest path/sha/bytes/lines verified
- Dense mock must produce non-empty materialized candidates; otherwise R24 fails as a vacuous candidate-channel probe
- Non-secret dense path canary must return evidence for non-empty dense stores; raw canary/query text must not appear in stdout/stderr or artifacts
- Canary/no label leakage: public tasks only in run phase; labels only score
- No promotion/dense real/QuIVer quality claims
- Runs artifacts gitignored
- Private field scan: no gold_spans/expected_behavior/query_category in R24 artifacts
- Canary token scan: no canary tokens in R24 artifacts

## Output JSON schema r24-v1

```json
{
  "schema_version": "r24-v1",
  "promotion_ready": false,
  "not_promotion_evidence": true,
  "core_changes": false,
  "remote_calls": 0,
  "dense_or_llm_claims": false,
  "quiver_implemented": false,
  "availability_checks": {
    "quiver_implementation_scan": { "quiver_implemented": false, ... },
    "tdb_status": { "available": false, "success": false, ... },
    "dense_provider_status": { "mock_available": true, "real_available": false, ... }
  },
  "dense_mock_probe": { "metrics": {...}, "bucket_metrics": {...}, ... },
  "dense_mock_plus_rrf": { "status": "completed|not_run|...", ... },
  "tdb_probe": { "status": "tdb_feature_probe_not_run", "reason": "..." },
  "tdb_stale_leak_count": "not_applicable",
  "quiver_diagnostics": {
    "BQ_overlap": { "status": "unavailable", "reason": "quiver_not_implemented", ... },
    ...
  },
  ...
}
```

## Caveats

- Dense mock scores are NOT semantic quality metrics. They measure candidate-channel integration safety on the R20 failure-surface benchmark.
- Full-run dense_mock produced 5,264 citation-valid candidates, but quality is intentionally poor for failure discovery: FileRecall@1 0.024, MRR 0.073, SpanF0.5 ~0.000, token_waste 0.850, primary_false_positive_rate 0.878.
- Full-run dense_mock recorded 99 candidate rejections (`candidate_rejection_rate` 0.134), mostly expected block/no-hit outcomes surfaced explicitly rather than hidden as empty successes.
- Canary hardening is non-vacuous: 8 non-empty dense stores checked, 1 empty store skipped, path canary returned 66 evidence items, query canaries returned 132 evidence items, and raw canary/query leakage count was 0.
- Full-run dense_mock_plus_rrf confirms dense contribution but mostly adds noise: FileRecall@1 0.134, MRR 0.451, token_waste 0.928, primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215.
- dense_mock_plus_rrf is not a recommended strategy; it is a noise/amplification failure-surface probe.
- QuIVer is not implemented. No numeric quality data is fabricated for QuIVer.
- TDB is a metadata/chunk store, not an ANN/QuIVer backend. No retrieval quality claim.
- Dense real provider is unavailable. Only mock (deterministic blake3 vectors) is tested.
- R20 labels are weak/mined; not promotion evidence.
- promotion_ready is always false.
