# D4f D4b Bundle Validation / Gate-Check Harness (Public Harness / No-Validation Artifact)

## Scope and claim boundary

D4f is the **D4b true-label bundle validation / gate-check harness**
public artifact. D4f is the last useful harness before real labels exist:
D4e proves filled packets can become a D4b bundle locally; D4f proves a
D4b bundle can be validated and gate-checked locally without publishing
labels, exact counts, or metrics. The default committed artifact is a
**public harness / no-validation artifact**, NOT a real D4b bundle
validation run, NOT gate-check pass, NOT calibration, NOT agreement/CI
computation, and NOT a D5 unblock.

The D4f bridge is:

```text
D3 dual-rubric -> D4c annotation packets -> human annotation runbook (D4d) -> D4e converter -> D4b true-label bundle -> D4f validator -> D5 aggregate release candidate
```

D4f **does not** read a private D4b bundle by default, **does not**
validate a private D4b bundle by default, **does not** persist any
private bundle by default, **does not** emit labels / raw label rows /
exact counts / bucket counts / cell counts / agreement metric values /
CI numeric values in any committed artifact, **does not** accept packet
refs / task IDs / repo IDs / paths / spans / snippets / content hashes /
query / candidate text / rater IDs / model outputs / provider payloads
in any committed artifact, **does not** compute calibration / inter-rater
agreement / confidence intervals, **does not** pass any public-release
gate, **does not** unblock D5, **does not** claim true E/S calibration,
**does not** perform model/LLM labeling, and **does not** change runtime
behavior, retriever, pack, model, backend, default policy, or
EvidenceCore semantics.

- Claim level: `d4b_bundle_validation_gate_harness_only`.
- D4b bundle schema source: `d4b_true_label_bundle_v1`.
- D4e converter source: `d4e_filled_packet_converter_harness.v1`.
- D4d runbook protocol: `d4d_human_annotation_runbook.v1`.
- Status: `blocked_no_private_bundle_available_or_no_validation_run`;
  mode `public_harness_no_private_bundle_no_validation`; phase `D4f`.

D4f is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
downstream agent value claim, NOT a runtime-clean general algorithm
claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D4f emits no EvidenceCore records and changes none of its
  semantics.
- D4f default reads no D4b bundle and runs no validation:
  `private_bundle_read=false`,
  `private_bundle_validated=false`,
  `private_bundle_persisted=false`,
  `bundle_validation_run=false`, `labels_read=false`,
  `labels_persisted=false`, `raw_label_rows_emitted=false`,
  `exact_private_counts_emitted=false`, `bucket_counts_emitted=false`,
  `cell_counts_emitted=false`, `task_ids_emitted=false`,
  `repo_ids_emitted=false`, `paths_or_spans_emitted=false`,
  `snippets_emitted=false`, `content_sha_emitted=false`,
  `query_or_candidate_text_emitted=false`, `rater_ids_emitted=false`,
  `private_input_path_emitted=false`,
  `private_output_path_emitted=false`.
- D4f computes no metrics, performs no model labeling, and passes no
  release gate:
  `calibration_metrics_computed=false`,
  `inter_rater_agreement_computed=false`,
  `inter_rater_agreement_measured=false`,
  `agreement_metric_values_emitted=false`,
  `confidence_intervals_computed=false`,
  `confidence_interval_values_emitted=false`,
  `model_or_llm_labeling_performed=false`,
  `model_assisted_labels_allowed=false`,
  `true_e_s_calibration_claimed=false`,
  `public_release_gate_passed=false`, `d5_unblocked=false`.

## Core boundary: D4f is a validator harness with a blocked public artifact

- The **default committed D4f artifact** is a public harness /
  no-validation artifact. Its status is
  `blocked_no_private_bundle_available_or_no_validation_run`. It reads
  NO private D4b bundle, validates NO bundle, persists NO private bundle,
  reads NO labels, emits NO labels / counts / metrics / paths / IDs /
  snippets / rater IDs, computes NO calibration / agreement / CI,
  performs NO model/LLM labeling, and passes NO public-release gate. D5
  remains blocked.
- D4f has a private validator mode (opt-in, NOT committed) for
  local-only `/tmp` runs. Private output is never committed.
- The validator consumes the D4e D4b bundle output shape only; it
  rejects packet refs / paths / snippets / content_sha / query text /
  candidate text / rater IDs / provider payloads / API secrets / model
  outputs / raw agreement/CI values / per-row hashes / unknown keys. It
  does not need source context and should not accept it.

### D4e -> D4f -> D5 relation

D4e produces a `d4b_true_label_bundle_v1`-shaped bundle (locally, under
`/tmp`, never committed). D4f consumes that bundle, validates its schema,
and runs the gate checks (schema, label_source, rater_count, agreement
availability, CI availability, min-N band, k-min band). D4f is a
validator harness with a blocked public artifact: by default it runs NO
validation and emits NO gate report. A private local-only run (under
`/tmp`, never committed) may validate a D4b bundle and emit a private
gate report with gate booleans and bands ONLY (no labels, no exact
counts, no metrics).

## CLI

```bash
python3 -m py_compile eval/d4f_bundle_validation_gate.py
python3 eval/d4f_bundle_validation_gate.py --self-test
python3 eval/d4f_bundle_validation_gate.py \
    --out artifacts/d4f_bundle_validation_gate/\
d4f_bundle_validation_gate_report.json
# D4f private validator (NOT committed; /tmp only):
python3 eval/d4f_bundle_validation_gate.py \
    --allow-private-bundle \
    --input-bundle /local/private/d4b_bundle.json \
    --out /tmp/d4f_bundle_validation_report.json
# D4f synthetic harness self-test (NOT committed; /tmp only):
python3 eval/d4f_bundle_validation_gate.py \
    --allow-private-bundle --synthetic-harness-test \
    --input-bundle /tmp/synthetic_d4b_bundle.json \
    --out /tmp/d4f_synthetic_validation.json
```

Default mode: writes the committed public harness / no-validation
artifact (default out path if `--out` omitted).

CLI arguments: `--self-test`, `--out`, `--allow-private-bundle`,
`--input-bundle`, `--synthetic-harness-test`. Unknown/private-looking
arguments are rejected with a generic `invalid arguments` message that
does not echo private paths or basenames (SafeArgumentParser pattern).

### Guard requirements

1. No private read by default.
2. `--input-bundle` without `--allow-private-bundle` exits 2.
3. `--allow-private-bundle` without `--input-bundle` exits 2.
4. Private mode requires explicit `--out`.
5. Committed artifact path rejected before any private input read.
6. Non-`/tmp` private `--out` rejected before any private input read.
7. Resolved `/tmp` guard: parent symlink escape rejected; existing
   output symlink rejected; resolved target must stay under `/tmp`.
8. Validate CLI/output guards before opening/stat'ing input.
9. Sanitized load/parse/schema/privacy errors:
   `error: failed to load private bundle (schema/privacy/parse error; details suppressed)`.
10. Success stdout must not include exact input path, output path,
    basename, counts, or metrics.
11. Private output is never committed.

## Private D4b bundle input contract

D4f consumes the D4e D4b bundle output shape. D4f should not need packet
refs, source context, or model outputs and should reject them.

Required input bundle shape:

```json
{
  "schema": "d4b_true_label_bundle_v1",
  "label_source": "human_manual_true_e_s",
  "rater_count": 2,
  "agreement_available": true,
  "confidence_intervals_available": true,
  "synthetic_harness_test": false,
  "local_private_conversion_executed": true,
  "real_human_labels_converted": true,
  "labels": [
    {
      "e_score": "E0|E1|E2",
      "s_score": "S0|S1|S2",
      "bucket": "primary_evidence|dependency_support|weak_candidates|abstained",
      "citation_valid": true,
      "rater_pair_present": true,
      "adjudicated": true
    }
  ]
}
```

Allowed input keys:

- bundle: `schema`, `label_source`, `rater_count`,
  `agreement_available`, `confidence_intervals_available`,
  `synthetic_harness_test`, `local_private_conversion_executed`,
  `real_human_labels_converted`, `labels`.
- label: `e_score`, `s_score`, `bucket`, `citation_valid`,
  `rater_pair_present`, `adjudicated`.

Rejected input keys/values: packet refs; task/repo IDs; paths/spans/
snippets; content_sha; query/candidate text; rater IDs/names;
prompts/responses/model outputs/provider payloads/API keys; raw
agreement metric values; CI numeric values; per-row hashes; unknown
keys. D4f validates schema and gate availability only; it does not
compute metrics.

## Private `/tmp` output contract

Private output under `/tmp` may contain gate booleans and bands ONLY
(no labels, no exact counts, no metrics). It is local-only and never
committed.

Recommended private report:

```json
{
  "schema_version": "d4f_bundle_validation_gate_private_report.v1",
  "private_validation_report": true,
  "public_artifact": false,
  "do_not_commit": true,
  "synthetic_harness_test": false,
  "synthetic_bundle_validated_for_harness_only": false,
  "local_private_bundle_validation_run": true,
  "real_human_bundle_validated": true,
  "schema_gate_passed": true,
  "label_source_gate_passed": true,
  "rater_count_gate_passed": true,
  "agreement_availability_gate_passed": true,
  "ci_availability_gate_passed": true,
  "min_total_labels_gate_band": "met|not_met|not_evaluated",
  "k_min_gate_band": "met|not_met|not_evaluated",
  "small_cell_suppression_required": true,
  "exact_private_counts_emitted": false,
  "bucket_counts_emitted": false,
  "cell_counts_emitted": false,
  "agreement_metric_values_emitted": false,
  "confidence_interval_values_emitted": false,
  "public_release_gate_passed": false,
  "d5_unblocked": false
}
```

For `--synthetic-harness-test`, output must clearly mark:

- `synthetic_harness_test=true`
- `synthetic_bundle_validated_for_harness_only=true`
- `local_private_bundle_validation_run=false`
- `real_human_bundle_validated=false`

For real local private runs, `local_private_bundle_validation_run=true`
and `real_human_bundle_validated=true` may be true only if not
synthetic-marked, label_source is human manual, the D4e real-conversion
flags (`local_private_conversion_executed=true`,
`real_human_labels_converted=true`) are true in the input bundle, input
schema passes, and `/tmp` guard passes. Docs must say a local real-mode
flag-path test over a synthetic fixture is not evidence that real labels
exist. Even if all gates pass locally, the report always keeps
`public_release_gate_passed=false` and `d5_unblocked=false`.

If the min-N and k-min gates are tested internally, D4f computes the
exact N and per-bucket counts internally but emits ONLY the bands
(`met`, `not_met`, or `not_evaluated`); never exact N or cell counts.

Private output must not include labels list/label rows, exact counts,
agreement/CI numeric values, packet refs, task/repo IDs, paths/spans,
snippets, content_sha, query/candidate text, rater IDs, provider
payloads, API secrets, model outputs, exact input/output paths, or
basenames.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d4f_bundle_validation_gate/d4f_bundle_validation_gate_report.json`
is the public harness / no-validation artifact. Identity / boundary
fields:

- `schema_version` = `d4f_bundle_validation_gate_harness.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `d4b_bundle_schema_source`, `d4e_converter_source`,
  `d4d_runbook_protocol`
- Default false flags (all false): `private_bundle_read`,
  `private_bundle_validated`, `private_bundle_persisted`,
  `bundle_validation_run`, `labels_read`, `labels_persisted`,
  `raw_label_rows_emitted`, `exact_private_counts_emitted`,
  `bucket_counts_emitted`, `cell_counts_emitted`,
  `calibration_metrics_computed`, `inter_rater_agreement_computed`,
  `inter_rater_agreement_measured`, `agreement_metric_values_emitted`,
  `confidence_intervals_computed`, `confidence_interval_values_emitted`,
  `public_release_gate_passed`, `d5_unblocked`,
  `true_e_s_calibration_claimed`, `private_input_path_emitted`,
  `private_output_path_emitted`, `task_ids_emitted`, `repo_ids_emitted`,
  `paths_or_spans_emitted`, `snippets_emitted`, `content_sha_emitted`,
  `query_or_candidate_text_emitted`, `rater_ids_emitted`,
  `model_or_llm_labeling_performed`, `model_assisted_labels_allowed`.
- No-claim / no-runtime-change flags (all false): `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `model_calls_changed`,
  `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`, `promotion_ready`,
  `default_should_change`, `downstream_agent_value_proven`,
  `runtime_clean_general_algorithm_claimed`, `ood_temporal_supported`,
  `quiver_systems_supported`.
- Harness/control true flags (exactly these, all true):
  `bundle_validation_harness_available`, `private_cli_guard_validated`,
  `tmp_output_resolved_guard_validated`, `sanitized_error_guard_validated`,
  `d4b_bundle_schema_contract_defined`, `gate_check_contract_defined`,
  `min_n_gate_referenced`, `k_min_gate_referenced`,
  `agreement_availability_gate_referenced`, `ci_availability_gate_referenced`.
- Diagnostic flags (all true): `aggregate_only_public_artifact`,
  `diagnostic_only`, `not_evidence`.
- `d4b_bundle_schema_contract`: `schema`, `required_label_source`,
  `bundle_allowed_keys`, `label_object_allowed_keys`, `e_score_levels`,
  `s_score_levels`, `bucket_names`, `rejects_unknown_keys=true`,
  `rejects_packet_refs_paths_snippets_raters=true`.
- `gate_check_contract`: `min_total_labels_gate_referenced=true`,
  `k_min_gate_referenced=true`,
  `agreement_availability_gate_referenced=true`,
  `ci_availability_gate_referenced=true`,
  `min_rater_count_gate_referenced=true`, `min_rater_count=2`,
  `min_total_labels_gate=50`, `k_min_cell_gate=5`,
  `gate_band_values=[met, not_met, not_evaluated]`,
  `small_cell_suppression_required=true`,
  `exact_counts_never_emitted=true`, `metrics_never_computed=true`,
  `validator_not_run_by_default=true`.
- `d4d_runbook_contract`: `protocol`, `required_attestation_fields`,
  `attestation_must_be_all_true=true`,
  `no_llm_or_model_labels_required=true`,
  `no_proxy_labels_as_true_labels_required=true`,
  `local_only_storage_required=true`.
- `d4e_converter_contract`: `converter_source`, `target_bundle_schema`,
  `private_only=true`, `output_location=tmp_only_local_private`,
  `committed=false`.
- `validation_harness_info`: `available=true`, `opt_in_required=true`,
  `output_location=tmp_only_local_private`, `committed=false`,
  `validates_d4b_bundle_schema=true`, `runs_gate_checks_only=true`,
  `rejects_packet_refs_paths_snippets_raters=true`,
  `rejects_model_proxy_llm_labels=true`, `claims_calibration=false`,
  `computes_agreement_or_ci=false`.
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys (`task_id`, `repo_id`, `repo`,
`path`, `span`, `line_range`, `start_line`, `end_line`, `content_sha`,
`snippet`, `candidate_text`, `query`, `query_text`, `prompt`,
`response`, `model_output`, `label`, `labels`, `raw_label`,
`annotation_row`, `rater_id`, `annotator_id`, `packet_ref`,
`packet_id`, `private_record_ref`, `candidate_ref`, `label_slots`,
`annotation_instructions`, `e_score`, `s_score`, `bucket`,
`source_packet_schema`, `d4d_runbook_attestation`, `packets`,
`provider_payload`, `api_key`, `agreement_metric`, `kappa`,
`confidence_interval`, `ci_value`, `ci_lower`, `ci_upper`, etc.)
anywhere, and rejects value patterns: ANY URL (no URL allowlist),
32/40/64-char hex digests, secret-like strings, path-like `src/foo.rs`
and `/private/foo.jsonl`, multiline strings, raw JSON fragments, raw
line ranges `12-34`, and the self-test sentinel.

Contract containers (`d4b_bundle_schema_contract`, `gate_check_contract`,
`d4d_runbook_contract`, `d4e_converter_contract`) are **exact string
allowlists**: only approved schema/protocol identifiers, E/S levels,
bucket names, label-slot field names, attestation field names, the
human-manual label source, the D4e converter source identifier, the
private report schema identifier, the approved D4b bundle field-name
tokens, the gate band values, and the approved category strings
(e.g. `tmp_only_local_private`) may appear there. Arbitrary short
strings such as implementation symbols or private text are rejected
**even inside** contract containers (no over-broad container exemption).
Sensitive field names (`content_sha`, `query_text`, `packet_ref`,
`source_packet_schema`, `d4d_runbook_attestation`, `packets`) remain
rejected as keys anywhere and as values outside contracts.

## Private output guard (different from public scanner)

The private D4f gate report output guard is different from the public
scanner AND from the private bundle INPUT guard:

- allow gate booleans / bands (the report is a gate-check report, not a
  bundle);
- allow schema/category names (e.g. `tmp_only_local_private`,
  `d4f_bundle_validation_gate_private_report.v1`, `met`/`not_met`/
  `not_evaluated`);
- reject labels list / label rows;
- reject exact counts (`total_labels`, `label_count`, `bucket_count`,
  `cell_count`, `n`, `count`, etc.);
- reject agreement / CI numeric values;
- reject task/repo/path/snippet/hash/query/rater fields;
- reject input/output paths/basenames;
- verify schema_version exactly
  `d4f_bundle_validation_gate_private_report.v1`;
- verify `private_validation_report=true`, `public_artifact=false`,
  `do_not_commit=true`, `small_cell_suppression_required=true`;
- verify `public_release_gate_passed=false`, `d5_unblocked=false`;
- verify `*_emitted=false` flags (exact counts / buckets / cells /
  agreement values / CI values);
- verify synthetic/real flags are truthful (synthetic => harness-only
  and no real validation; real => not synthetic-marked).

## Self-tests

- All default false/true flags (default artifact no D4b bundle read, no
  validation, no labels, no counts, no metrics, no claims; the
  harness/control flags true; diagnostic flags true).
- No private read by default.
- CLI guard matrix (input without allow, allow without input, allow
  without `--out`, committed artifact path, non-`/tmp` output, synthetic
  without allow, traversal).
- Validate-before-read (no input access on invalid out / committed out
  / non-`/tmp` out / synthetic without allow / input without allow /
  allow without input).
- Resolved `/tmp` symlink escape rejection (parent symlink escape,
  existing output symlink escape, valid `/tmp` guard passes).
- Sanitized malformed input and unknown/private-looking argument errors
  (no sentinel, basename, or private path leak).
- D4b bundle INPUT guard (valid synthetic bundle validates; non-dict /
  unknown schema / wrong label_source / extra top-level key / path /
  snippet / content_sha / query_text / candidate_text / rater_id /
  task_id / packet_ref / provider_payload / api_key / model_output /
  agreement_metric / confidence_interval / per_row_hash / unknown label
  key / invalid e_score / invalid bucket / non-bool citation_valid /
  rater_count below min / non-bool agreement_available / synthetic but
  local_conversion=true rejected).
- Gate-check logic (valid bundle: schema/label_source/rater_count/
  agreement/CI gates pass, bands emitted; small bundle min-N not_met;
  large bundle min-N met; k-min met when all buckets >= k_min; k-min
  not_met when a bucket has 1 <= count < k_min; invalid bundle: all
  gates not_evaluated; missing agreement/CI flags fail gates; no exact
  count keys emitted).
- Real-mode flag-path decision logic (synthetic CLI false; bundle
  synthetic false; real passes true; non-human label source false;
  D4e not-real-conversion false; invalid schema false; tmp guard failed
  false).
- Valid synthetic D4b bundle accepted in `/tmp` private mode.
- Synthetic report marked harness-only and no real validation claim.
- Valid real-mode flag-path over synthetic fixture sets local validation
  true only locally when not synthetic flag, label source is human
  manual, D4e real-conversion flags are true; docs mark this as
  flag-path test, not evidence of real labels.
- Private report OUTPUT guard rejects: labels key, path key, snippet
  key, rater_id key, wrong schema_version, public_release_gate_passed
  true, d5_unblocked true, synthetic but local_validation true,
  agreement_metric key, confidence_interval key, total_labels key,
  invalid band value; clean report passes.
- stdout/stderr/output metadata contain no exact input/output path or
  basename.
- Public artifact scanner fail-closes (rejects forbidden keys + value
  patterns; contract containers reject unapproved strings; approved
  schema/level/bucket/slot/attestation/bundle-key token/band values
  pass).
- Self-test failure blocks public artifact generation.

## Validation

```text
python3 -m py_compile eval/d4f_bundle_validation_gate.py    => PASS
python3 eval/d4f_bundle_validation_gate.py --self-test      => PASS (352/352 checks)
python3 eval/d4f_bundle_validation_gate.py \
  --out artifacts/d4f_bundle_validation_gate/\
d4f_bundle_validation_gate_report.json                     => PASS
  (status: blocked_no_private_bundle_available_or_no_validation_run,
   forbidden_scan: pass, self_test_passed: true,
   private_bundle_read: false,
   bundle_validation_run: false,
   d5_unblocked: false,
   public_release_gate_passed: false,
   bundle_validation_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   d4b_bundle_schema_contract_defined: true,
   gate_check_contract_defined: true,
   min_n_gate_referenced: true,
   k_min_gate_referenced: true,
   agreement_availability_gate_referenced: true,
   ci_availability_gate_referenced: true,
   mode: public_harness_no_private_bundle_no_validation, phase: D4f,
   d4b_bundle_schema_source: d4b_true_label_bundle_v1,
   d4e_converter_source: d4e_filled_packet_converter_harness.v1,
   d4d_runbook_protocol: d4d_human_annotation_runbook.v1)
# Private /tmp synthetic smoke (NOT committed):
python3 eval/d4f_bundle_validation_gate.py \
  --allow-private-bundle --synthetic-harness-test \
  --input-bundle /tmp/synthetic_d4b_bundle.json \
  --out /tmp/d4f_synthetic_validation.json                      => PASS
  (synthetic_harness_test=true,
   synthetic_bundle_validated_for_harness_only=true,
   local_private_bundle_validation_run=false,
   real_human_bundle_validated=false,
   schema_gate_passed=true, public_release_gate_passed=false,
   d5_unblocked=false)
# Private /tmp real-mode flag-path smoke (NOT committed; over a synthetic
# fixture with D4e real-conversion flags set to true):
python3 eval/d4f_bundle_validation_gate.py \
  --allow-private-bundle \
  --input-bundle /tmp/real_flagpath_d4b_bundle.json \
  --out /tmp/d4f_real_flagpath_validation.json                  => PASS
  (synthetic_harness_test=false,
   local_private_bundle_validation_run=true,
   real_human_bundle_validated=true,
   public_release_gate_passed=false,
   d5_unblocked=false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## Caveats

- D4f is the D4b bundle validation / gate-check harness public
  artifact only. It is eval/diagnostic only. It does NOT change runtime,
  retriever, pack, model, backend, or default policy; it does NOT
  change EvidenceCore semantics. It is NOT a benchmark result, NOT a
  downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.
- D4f default is a harness with a blocked public artifact. The default
  committed artifact reads NO private D4b bundle, runs NO validation,
  persists NO private bundle, reads NO labels, computes NO calibration /
  agreement / CI, performs NO model/LLM labeling, and passes NO
  public-release gate. D5 remains blocked. Harness/control true flags
  are true only for the validated harness/controls, NOT for any real
  bundle validation or gate-pass claim.
- D4f is NOT real bundle validation in committed output, NOT gate-pass,
  NOT calibration, NOT agreement/CI computation, and NOT D5 unblock.
  It is the last useful harness before real labels exist: D4e proves
  filled packets can become a D4b bundle locally; D4f proves a D4b
  bundle can be validated and gate-checked locally without publishing
  labels, exact counts, or metrics.
- D4f has a private validator mode (opt-in, NOT committed). Private
  output is written to `/tmp` only and never committed. The private
  report contains gate booleans and bands ONLY (no labels, no exact
  counts, no metrics). The real-mode flag-path test over a synthetic
  fixture (which sets `local_private_bundle_validation_run=true` and
  `real_human_bundle_validated=true` locally) is a flag-path test only
  and is NOT evidence that real labels exist. Real human labels are not
  yet collected; D5 remains blocked.
- The validator consumes only the D4e D4b bundle output shape; it
  rejects packet refs / paths / snippets / content_sha / query text /
  candidate text / rater IDs / provider payloads / API secrets / model
  outputs / raw agreement/CI values / per-row hashes / unknown keys.
  D4f validates schema and gate availability only; it does not compute
  metrics.
- The min-N and k-min gates are computed internally (exact N and
  per-bucket counts) but the report emits ONLY the bands
  (`met`/`not_met`/`not_evaluated`); never exact N or cell counts.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; the harness/control true flags are the only true control
  flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was NOT updated (D4f is a
  harness/blocked-only artifact; no conclusions change).
