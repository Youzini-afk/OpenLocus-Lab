# D2 Dual-Rubric Aggregate Calibration (Proxy Mappability Only)

## Scope and claim boundary

D2 is the bounded **proxy** aggregate calibration follow-on to D1. It
does NOT claim true E/S calibration. It operates in two strictly
separated modes:

- **D2a (default, committed)**: public aggregate mappability inventory.
  Reads committed C3/B12 public aggregate artifacts only; does NOT read
  private records. Claim level: `public_aggregate_mappability_only`.
- **D2b (opt-in, NOT committed)**: explicit local/private proxy
  calibration smoke. Requires
  `--allow-private-records --input <path> --limit N --out /tmp/...`.
  The `/tmp` `--out` path must be explicit; private mode refuses the
  committed artifact path. Never serializes the input path/basename/file
  size/mtime. Emits aggregate proxy bucket counts with small-cell
  suppression only.

D2 is **eval/diagnostic only**. It does NOT change runtime behavior,
retriever ranking, pack construction, model calls, backend storage,
default policy, or EvidenceCore semantics.

- Proxy scores (`proxy_e_score`, `proxy_s_score`) are NOT true E/S
  calibration, NOT improved retrieval, NOT downstream agent value, NOT
  a benchmark result, NOT a default change, and NOT a runtime-clean
  general algorithm claim.
- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D2 emits no EvidenceCore records and changes none of its
  semantics.
- D2 does NOT claim proxy calibration in D2a (default) mode:
  `proxy_calibration_claimed=false`,
  `true_e_s_calibration_claimed=false`.

## Proxy terminology

D2 uses **proxy** terminology throughout. It never claims true E/S
calibration.

- `proxy_e_score`: small-integer proxy semantic / direct-answer
  evidence score, mapped from P21 outcome metrics (`span_f0_5`,
  `added_gold_span`, `primary_false_positive_rate`) of the
  `candidate_baseline` strategy, IN MEMORY ONLY. Range 0..3.
- `proxy_s_score`: small-integer proxy dependency / support-structure
  evidence score, mapped from route features
  (`candidate_support_exists`, `local_anchor`, `rrf_backed_by_anchor`,
  `symbol_regex_agree`, `dense_support_present`), IN MEMORY ONLY.
  Range 0..5.
- `proxy_e_band` / `proxy_s_band`: `none` / `weak` / `high`.
- `proxy_bucket`: `proxy_primary_evidence` /
  `proxy_dependency_support` / `proxy_weak_candidates` /
  `proxy_abstained` / `proxy_unmappable`.

### Missing fields

Missing proxy fields become `proxy_unmappable`, NOT negative evidence.
A record with a missing `candidate_baseline` outcome or missing core
route features (`candidate_support_exists`, `local_anchor`) is classified
as `proxy_unmappable`, not as having zero evidence.

### Thresholds

- `PROXY_E_HIGH >= 2` (out of 3)
- `PROXY_S_HIGH >= 2` (out of 5)
- weak if proxy E or S is `>= 1` but below high.

### Classification order (fail-closed)

1. missing required proxy fields -> `proxy_unmappable`.
2. proxy E high -> `proxy_primary_evidence`.
3. proxy S high and proxy E below high -> `proxy_dependency_support`.
4. weak nonzero proxy E or S -> `proxy_weak_candidates`.
5. else -> `proxy_abstained`.

Proxy E-high beats proxy S-high: a record with both proxy E and S high
is `proxy_primary_evidence`, not `proxy_dependency_support`.

## D2a: public aggregate mappability inventory (default, committed)

The committed artifact at
`artifacts/d2_dual_rubric_aggregate_calibration/d2_dual_rubric_aggregate_calibration_report.json`
is the D2a default. It:

- checks committed C3/B12 public aggregate artifacts (generic labels
  `c3_public_aggregate`, `b12_public_aggregate` only; no filesystem
  paths serialized);
- reports whether public aggregates contain candidate-level proxy fields
  (they do NOT — they are aggregate-only by construction):
  `public_aggregates_have_candidate_level_proxy_fields=false`;
- reports `private_input_required_for_proxy_calibration=true`;
- does NOT read private records: `private_records_read=false`;
- does NOT claim proxy calibration:
  `proxy_calibration_claimed=false`;
- does NOT claim true E/S calibration:
  `true_e_s_calibration_claimed=false`.

### D2a artifact fields (aggregate only)

- `schema_version` = `d2_dual_rubric_aggregate_calibration.v1`
- `generated_by`, `generated_at`, `claim_level`, `rubric_version`,
  `status`, `mode`
- `artifact_classes_checked` = `["c3_public_aggregate",
  "b12_public_aggregate"]` (generic labels only)
- `public_artifacts_checked`, `public_artifact_status_counts`
- `public_aggregates_have_candidate_level_proxy_fields=false`
- `private_input_required_for_proxy_calibration=true`
- `proxy_calibration_claimed=false`,
  `true_e_s_calibration_claimed=false`
- `private_records_read=false`, `private_records_persisted=false`,
  `local_input_path_emitted=false`
- `proxy_field_terminology`, `proxy_e_signal_names`,
  `proxy_s_signal_names`, `proxy_bucket_names`
- `self_test_checks`, `self_test_passed`
- No-claim / safety flags (all change/leak booleans false; diagnostic
  booleans true)
- `forbidden_scan` summary

## D2b: opt-in private proxy calibration smoke (NOT committed)

D2b is available only with explicit opt-in:

```bash
python3 eval/d2_dual_rubric_aggregate_calibration.py \
    --allow-private-records --input /tmp/private.json \
    --limit 100 --out /tmp/d2b_proxy_smoke.json
```

D2b:

- requires `--allow-private-records` AND `--input`; either alone exits
  non-zero (exit code 2);
- requires an explicit `--out` under `/tmp`; private mode rejects the
  committed artifact path and any non-`/tmp` output;
- reads private records transiently (in memory only) using the C1
  adapter (`c1_private_records.load_private_records`);
- suppresses loader exception details so malformed private inputs cannot
  leak the input path or basename through stderr;
- NEVER serializes the input path, basename, file size, or mtime;
- emits aggregate proxy bucket counts, proxy E/S band counts, and a
  small-cell-suppressed proxy E x S band crosstab only;
- writes output to `/tmp` only — D2b output is NEVER committed;
- claim level: `dual_rubric_proxy_calibration_smoke_only`;
- `proxy_calibration_claimed=true` (smoke ran), but
  `true_e_s_calibration_claimed=false` (proxy, not true E/S).

### Small-cell suppression

Private aggregate crosstabs use small-cell suppression with `k_min`
(default 5, configurable via `--k-min`). Cells with count < `k_min` are
omitted from the crosstab. `small_cells_suppressed=true` when any cell
is suppressed; `suppressed_cell_count` reports the number of suppressed
cells (NOT their individual counts).

## Public artifact contract (aggregate-only)

Both D2a and D2b artifacts are aggregate-only. They NEVER emit:

- task IDs, repo IDs/names, paths/spans/snippets, line or byte ranges;
- content hashes, raw candidate text, prompts/responses;
- raw private records, labels/qrels, per-record diagnostics;
- row-level derived hashes, private bucket rows;
- the local input path, basename, file size, or mtime.

A strict forbidden-output scanner runs fail-closed before any artifact
is written. It rejects forbidden dict keys (`path`, `span`,
`content_sha`, `snippet`, `query`, `task_id`, `repo_id`, `repo`,
`label`, `qrels`, `gold`, `prompt`, `response`, `private_record_hash`,
`p31_score_gold`, etc.) and forbidden value patterns (URLs, 32/40/64-char
hex digests, secret-like strings, path-like `src/foo.py`,
`/private/foo.jsonl`, multiline strings, raw JSON fragments, raw line
ranges `12-34`).

### No-claim / safety flags

- `aggregate_only_public_artifact=true`, `diagnostic_only=true`,
  `not_evidence=true`.
- `runtime_behavior_changed=false`, `retriever_changed=false`,
  `pack_builder_changed=false`, `model_calls_changed=false`,
  `backend_changed=false`, `default_policy_changed=false`.
- `promotion_ready=false`, `default_should_change=false`,
  `evidencecore_semantics_changed=false`,
  `runtime_clean_general_algorithm_claimed=false`,
  `downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
  `quiver_systems_supported=false`.
- `candidate_text_emitted=false`, `paths_or_spans_emitted=false`,
  `content_sha_emitted=false`,
  `raw_private_records_read=false` in committed D2a (`true` only in
  explicit `/tmp` D2b smoke),
  `raw_private_records_persisted=false`,
  `row_level_hashes_emitted=false`,
  `per_candidate_rows_emitted=false`.

## Validation

```text
python3 -m py_compile eval/d2_dual_rubric_aggregate_calibration.py   => PASS
python3 eval/d2_dual_rubric_aggregate_calibration.py --self-test     => PASS (78/78 checks)
python3 eval/d2_dual_rubric_aggregate_calibration.py \
  --out artifacts/d2_dual_rubric_aggregate_calibration/\
d2_dual_rubric_aggregate_calibration_report.json                     => PASS
  (status: public_aggregate_mappability_only,
   forbidden_scan: pass, self_test_passed: true,
   proxy_calibration_claimed: false,
   true_e_s_calibration_claimed: false,
   private_records_read: false)
# CLI guard: --input without --allow-private-records exits non-zero   => PASS (exit 2)
# CLI guard: --allow-private-records without --input exits non-zero  => PASS (exit 2)
# CLI guard: private mode without explicit /tmp --out exits non-zero  => PASS (exit 2)
# CLI guard: private mode with committed artifact --out exits non-zero=> PASS (exit 2)
# CLI guard: private load errors suppress path/basename details       => PASS
# D2b smoke (--allow-private-records --input /tmp/... --out /tmp/...) => PASS (/tmp only, not committed)
python3 scripts/validate_docs_i18n.py                                 => PASS
git diff --check                                                      => PASS
```

## Caveats

- D2 is eval/diagnostic only. It does NOT change runtime, retriever,
  pack, model, backend, or default policy; it does NOT change
  EvidenceCore semantics. It is NOT a benchmark result, NOT a downstream
  agent value claim, NOT a runtime-clean general algorithm claim, NOT an
  OOD temporal claim, and NOT a QuIVer systems claim.
- Proxy scores are NOT true E/S calibration, NOT improved retrieval, NOT
  downstream agent value, NOT a benchmark result, and NOT a default
  change.
- D2a (default) is public aggregate mappability only, NOT proxy
  calibration. It does NOT read private records.
- D2b (opt-in) is a private proxy calibration smoke only. Its output goes
  to `/tmp` only and is NEVER committed. It does NOT claim true E/S
  calibration. It records `raw_private_records_read=true` only in that
  explicit local/private mode, while `raw_private_records_persisted=false`
  remains false.
- Missing proxy fields become `proxy_unmappable`, NOT negative evidence.
- Small-cell suppression (`k_min`) omits rare crosstab cells; the
  suppressed cell counts are never emitted.
- Existing mode-only dirty files (`eval/ci_clone_and_lock_repo.py`,
  `eval/ci_make_repo_matrix.py`,
  `eval/p59_contrastive_pack_coverage_counterfactual.py`) were NOT
  touched.
