# D4e Filled-Packet to D4b Bundle Converter Harness (Public Harness / No-Conversion Artifact)

## Scope and claim boundary

D4e is the **filled-packet -> D4b true-label bundle converter harness**
public artifact. D4e hardens the conversion control plane between D4d
human annotation and D4b bundle validation, before any real human labels
exist. The default committed artifact is a **public harness /
no-conversion artifact**, NOT a real filled-packet -> D4b bundle
conversion run, NOT calibration, NOT agreement/CI computation, and NOT
a D5 unblock.

The D4e bridge is:

```text
D3 dual-rubric -> D4c annotation packets -> human annotation runbook (D4d) -> D4e converter -> D4b true-label bundle -> D5 aggregate release candidate
```

D4e **does not** read private filled packets by default, **does not**
convert filled packets to a D4b bundle by default, **does not** write
or commit a D4b bundle by default, **does not** accept D4c source
context fields, **does not** accept model/proxy/LLM labels as
human/manual labels, **does not** emit packet refs / task IDs / repo
IDs / paths / spans / snippets / content hashes / query / candidate
text / rater IDs in any committed artifact, **does not** compute
calibration / inter-rater agreement / confidence intervals, **does
not** pass any public-release gate, **does not** unblock D5, **does
not** claim true E/S calibration, **does not** perform model/LLM
labeling, and **does not** change runtime behavior, retriever, pack,
model, backend, default policy, or EvidenceCore semantics.

- Claim level: `filled_packet_to_d4b_bundle_converter_harness_only`.
- D4c packet schema source: `d4c_annotation_packet_v1`.
- D4d runbook protocol: `d4d_human_annotation_runbook.v1`.
- D4b bundle schema target: `d4b_true_label_bundle_v1`.
- Status: `blocked_no_filled_packets_available_or_no_conversion_run`;
  mode `public_harness_no_filled_packets_no_conversion`; phase `D4e`.

D4e is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
downstream agent value claim, NOT a runtime-clean general algorithm
claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D4e emits no EvidenceCore records and changes none of its
  semantics.
- D4e default reads no filled packets and runs no conversion:
  `private_filled_packets_read=false`,
  `filled_packets_validated=false`,
  `filled_packets_persisted=false`,
  `conversion_run=false`,
  `d4b_true_label_bundle_created=false`,
  `d4b_true_label_bundle_written=false`,
  `d4b_true_label_bundle_validated=false`,
  `labels_collected=false`, `labels_converted=false`,
  `raw_label_rows_emitted=false`,
  `packet_ids_emitted=false`, `task_ids_emitted=false`,
  `repo_ids_emitted=false`, `paths_or_spans_emitted=false`,
  `snippets_emitted=false`, `content_sha_emitted=false`,
  `query_or_candidate_text_emitted=false`, `rater_ids_emitted=false`,
  `private_input_path_emitted=false`,
  `private_output_path_emitted=false`,
  `exact_private_counts_emitted=false`.
- D4e computes no metrics, performs no model labeling, and passes no
  release gate:
  `calibration_metrics_computed=false`,
  `inter_rater_agreement_measured=false`,
  `confidence_intervals_computed=false`,
  `model_or_llm_labeling_performed=false`,
  `model_assisted_labels_allowed=false`,
  `true_e_s_calibration_claimed=false`,
  `public_release_gate_passed=false`, `d5_unblocked=false`.

## Core boundary: D4e is a converter harness with a blocked public artifact

- The **default committed D4e artifact** is a public harness /
  no-conversion artifact. Its status is
  `blocked_no_filled_packets_available_or_no_conversion_run`. It reads
  NO private filled packets, validates NO filled packets, runs NO
  conversion, creates/writes/validates NO D4b bundle, collects/converts
  NO labels, emits NO packet refs / paths / snippets / IDs / rater
  IDs, computes NO calibration / agreement / CI, performs NO model/LLM
  labeling, and passes NO public-release gate. D5 remains blocked.
- D4e has a private converter mode (opt-in, NOT committed) for
  local-only `/tmp` runs. Private output is never committed.
- The converter consumes only the filled label slots and the D4d
  attestation; it rejects D4c source context fields (paths, spans,
  snippets, content_sha, query text, candidate text, packet source
  context). It does not need source context and should not accept it.

### D4d -> D4e -> D4b relation

D4d freezes the human annotation runbook/checklist that D4e uses. D4e
maps filled D4c packets (with human-filled E/S slots and a D4d
attestation) to a `d4b_true_label_bundle_v1`-shaped bundle. D4e is a
converter harness with a blocked public artifact: by default it runs NO
conversion and creates NO bundle. A private local-only run (under
`/tmp`, never committed) may convert filled packets to a D4b bundle
when the D4d attestation passes (no model/proxy labels, schema passes,
/tmp guard passes).

## CLI

```bash
python3 -m py_compile eval/d4e_filled_packet_converter.py
python3 eval/d4e_filled_packet_converter.py --self-test
python3 eval/d4e_filled_packet_converter.py \
    --out artifacts/d4e_filled_packet_converter/\
d4e_filled_packet_converter_report.json
# D4e private converter (NOT committed; /tmp only):
python3 eval/d4e_filled_packet_converter.py \
    --allow-private-filled-packets \
    --input-filled-packets /local/private/filled_packets.json \
    --out /tmp/d4b_true_label_bundle.json
# D4e synthetic harness self-test (NOT committed; /tmp only):
python3 eval/d4e_filled_packet_converter.py \
    --allow-private-filled-packets --synthetic-harness-test \
    --input-filled-packets /tmp/synthetic_filled_packets.json \
    --out /tmp/d4e_synthetic_bundle.json
```

Default mode: writes the committed public harness / no-conversion
artifact (default out path if `--out` omitted).

CLI arguments: `--self-test`, `--out`,
`--allow-private-filled-packets`, `--input-filled-packets`,
`--synthetic-harness-test`. Unknown/private-looking arguments are
rejected with a generic `invalid arguments` message that does not echo
private paths or basenames (SafeArgumentParser pattern).

### Guard requirements

1. No private read by default.
2. `--input-filled-packets` without `--allow-private-filled-packets`
   exits 2.
3. `--allow-private-filled-packets` without
   `--input-filled-packets` exits 2.
4. Private mode requires explicit `--out`.
5. Committed artifact path rejected before any private input read.
6. Non-`/tmp` private `--out` rejected before any private input read.
7. Resolved `/tmp` guard: parent symlink escape rejected; existing
   output symlink rejected; resolved target must stay under `/tmp`.
8. Validate CLI/output guards before opening/stat'ing input.
9. Sanitized load/parse/schema/privacy errors:
   `error: failed to load private filled packets (schema/privacy/parse error; details suppressed)`.
10. Success stdout must not include exact input path, output path,
    basename, or label text.
11. Private output is never committed.

## Private filled-packet input contract

D4e consumes a minimal label-only filled packet batch with a D4d
attestation. D4e should not need D4c source context and should reject
it.

Required batch schema:

```json
{
  "schema": "d4e_filled_annotation_packets_v1",
  "source_packet_schema": "d4c_annotation_packet_v1",
  "d4d_runbook_attestation": {
    "protocol": "d4d_human_annotation_runbook.v1",
    "two_independent_human_raters": true,
    "independent_before_adjudication": true,
    "no_llm_or_model_labels": true,
    "no_proxy_labels_as_true_labels": true,
    "local_only_storage": true
  },
  "packets": [
    {
      "packet_ref": "local-only opaque",
      "label_slots": {
        "e_score": "E0|E1|E2",
        "s_score": "S0|S1|S2",
        "bucket": "primary_evidence|dependency_support|weak_candidates|abstained",
        "citation_valid": true,
        "rater_pair_present": true,
        "adjudicated": true
      }
    }
  ]
}
```

Allowed input keys:

- batch: `schema`, `source_packet_schema`, `d4d_runbook_attestation`,
  `packets`.
- attestation: `protocol`, `two_independent_human_raters`,
  `independent_before_adjudication`, `no_llm_or_model_labels`,
  `no_proxy_labels_as_true_labels`, `local_only_storage`.
- packet: `packet_ref`, `label_slots`.
- label slots: `e_score`, `s_score`, `bucket`, `citation_valid`,
  `rater_pair_present`, `adjudicated`.

Rejected input keys/values: paths/spans/snippets/content hashes;
query/candidate text; task/repo IDs; rater IDs/names;
prompts/responses/model outputs/provider payloads/API keys; source
context fields. D4e consumes filled labels and attestation only.

## Private D4b bundle output contract

Private output under `/tmp` may contain labels because it is local-only
and never committed.

Recommended output:

```json
{
  "schema": "d4b_true_label_bundle_v1",
  "label_source": "human_manual_true_e_s",
  "rater_count": 2,
  "agreement_available": true,
  "confidence_intervals_available": false,
  "synthetic_harness_test": false,
  "synthetic_labels_converted_for_harness_only": false,
  "local_private_conversion_executed": true,
  "real_human_labels_converted": true,
  "labels": [
    {
      "e_score": "E0",
      "s_score": "S1",
      "bucket": "dependency_support",
      "citation_valid": true,
      "rater_pair_present": true,
      "adjudicated": true
    }
  ]
}
```

For `--synthetic-harness-test`, output must clearly mark:

- `synthetic_harness_test=true`
- `synthetic_labels_converted_for_harness_only=true`
- `local_private_conversion_executed=false`
- `real_human_labels_converted=false`

For real local private runs, `local_private_conversion_executed=true`
and `real_human_labels_converted=true` may be true only if not
synthetic, D4d attestation passes, no model/proxy labels, input schema
passes, and `/tmp` guard passes. Docs must say a local real-mode
flag-path test over a synthetic fixture is not evidence that real
labels exist.

Private output must not include packet refs, task/repo IDs, paths/spans,
snippets, content_sha, query/candidate text, rater IDs, provider
payloads, API secrets, model outputs, exact input/output paths, or
basenames.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d4e_filled_packet_converter/d4e_filled_packet_converter_report.json`
is the public harness / no-conversion artifact. Identity / boundary
fields:

- `schema_version` = `d4e_filled_packet_converter_harness.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `d4c_packet_schema_source`, `d4d_runbook_protocol`,
  `d4b_bundle_schema_target`
- Default false flags (all false): `private_filled_packets_read`,
  `filled_packets_validated`, `filled_packets_persisted`,
  `conversion_run`, `d4b_true_label_bundle_created`,
  `d4b_true_label_bundle_written`, `d4b_true_label_bundle_validated`,
  `labels_collected`, `labels_converted`, `raw_label_rows_emitted`,
  `packet_ids_emitted`, `task_ids_emitted`, `repo_ids_emitted`,
  `paths_or_spans_emitted`, `snippets_emitted`, `content_sha_emitted`,
  `query_or_candidate_text_emitted`, `rater_ids_emitted`,
  `private_input_path_emitted`, `private_output_path_emitted`,
  `exact_private_counts_emitted`, `calibration_metrics_computed`,
  `inter_rater_agreement_measured`, `confidence_intervals_computed`,
  `public_release_gate_passed`, `d5_unblocked`,
  `true_e_s_calibration_claimed`, `model_or_llm_labeling_performed`,
  `model_assisted_labels_allowed`.
- No-claim / no-runtime-change flags (all false): `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `model_calls_changed`,
  `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`, `promotion_ready`,
  `default_should_change`, `downstream_agent_value_proven`,
  `runtime_clean_general_algorithm_claimed`, `ood_temporal_supported`,
  `quiver_systems_supported`.
- Harness/control true flags (exactly these, all true):
  `converter_harness_available`, `private_cli_guard_validated`,
  `tmp_output_resolved_guard_validated`, `sanitized_error_guard_validated`,
  `filled_packet_schema_contract_defined`, `d4d_attestation_required`,
  `d4b_bundle_schema_contract_defined`, `d4b_mapping_contract_defined`.
- Diagnostic flags (all true): `aggregate_only_public_artifact`,
  `diagnostic_only`, `not_evidence`.
- Attestation scope fields: `default_public_mode_input_attestation_evaluated=false`
  because default public mode reads no input, and
  `private_conversion_d4d_attestation_required=true` because any private
  filled-packet conversion must carry D4d attestation.
- `filled_packet_schema_contract`: `schema`, `source_packet_schema_ref`,
  `private_only=true`, `may_contain_filled_label_slots=true`,
  `required_label_slots`, `required_attestation_fields`,
  `rejects_source_context_fields=true`.
- `d4d_runbook_contract`: `protocol`, `required_attestation_fields`,
  `attestation_must_be_all_true=true`,
  `no_llm_or_model_labels_required=true`,
  `no_proxy_labels_as_true_labels_required=true`,
  `local_only_storage_required=true`.
- `d4b_bundle_schema_contract`: `schema`, `required_label_source`,
  `bundle_allowed_keys`, `label_object_allowed_keys`, `e_score_levels`,
  `s_score_levels`, `bucket_names`, `rejects_unknown_keys=true`,
  `rejects_packet_refs_paths_snippets_raters=true`.
- `d4b_mapping_contract`: `target_bundle_schema`, `packet_label_slots`,
  `source_packet_schema_ref`, `runbook_protocol`,
  `packet_to_bundle_requires_human_or_local_converter=true`,
  `converter_not_run_by_default=true`, `d4b_true_label_bundle_created=false`.
- `converter_harness_info`: `available=true`, `opt_in_required=true`,
  `output_location=tmp_only_local_private`, `committed=false`,
  `converts_filled_packets_to_d4b_bundle=true`,
  `rejects_source_context_fields=true`,
  `rejects_model_proxy_llm_labels=true`, `claims_calibration=false`.
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
`provider_payload`, `api_key`, etc.) anywhere, and rejects value
patterns: ANY URL (no URL allowlist), 32/40/64-char hex digests,
secret-like strings, path-like `src/foo.rs` and `/private/foo.jsonl`,
multiline strings, raw JSON fragments, raw line ranges `12-34`, and
the self-test sentinel.

Contract containers (`filled_packet_schema_contract`,
`d4d_runbook_contract`, `d4b_bundle_schema_contract`,
`d4b_mapping_contract`) are **exact string allowlists**: only approved
schema/protocol identifiers, E/S levels, bucket names, label-slot field
names, attestation field names, the human-manual label source, and the
approved D4b bundle field-name tokens may appear there. Arbitrary short
strings such as implementation symbols or private text are rejected
**even inside** contract containers (no over-broad container exemption).
Sensitive field names (`content_sha`, `query_text`, `packet_ref`,
`source_packet_schema`, `d4d_runbook_attestation`, `packets`) remain
rejected as keys anywhere and as values outside contracts.

## Private output guard (different from public scanner)

The private D4b bundle output guard is different from the public
scanner:

- allow label fields and E/S values (the bundle is a real D4b bundle
  that may contain labels locally);
- reject paths/snippets/content_sha/query/candidate text;
- reject packet refs in final D4b bundle;
- reject rater IDs;
- reject provider payload/API secrets/model outputs;
- verify schema exactly `d4b_true_label_bundle_v1`;
- verify `label_source` exactly `human_manual_true_e_s`;
- verify synthetic harness metadata or real local flags are truthful
  (synthetic => harness-only and no real conversion; real => not
  synthetic-marked);
- verify no exact input/output path or basename in output metadata.

## Self-tests

- All default false/true flags (default artifact no filled packets read,
  no conversion, no bundle, no labels, no metrics, no claims; the
  harness/control flags true; diagnostic flags true).
- No private read by default.
- CLI guard matrix (input without allow, allow without input, allow
  without --out, committed artifact path, non-`/tmp` output, synthetic
  without allow, traversal).
- Validate-before-read (no input access on invalid out / committed out
  / non-`/tmp` out / synthetic without allow / input without allow /
  allow without input).
- Resolved `/tmp` symlink escape rejection (parent symlink escape,
  existing output symlink escape, valid `/tmp` guard passes).
- Sanitized malformed input and unknown/private-looking argument errors
  (no sentinel, basename, or private path leak).
- D4d attestation required (valid attestation validates; missing
  attestation rejected; missing field rejected; extra field rejected;
  wrong protocol rejected; `no_llm_or_model_labels=false` rejected;
  `no_proxy_labels_as_true_labels=false` rejected;
  `local_only_storage=false` rejected;
  `two_independent_human_raters=false` rejected;
  `independent_before_adjudication=false` rejected).
- Filled packet with path/snippet/content_sha/query/candidate/rater_id/
  task_id/provider_payload/api_key/model_output/annotation_instructions
  rejected.
- Valid synthetic filled packet batch converts to D4b bundle in `/tmp`.
- Synthetic output marked harness-only and no real conversion claim.
- Valid real-mode flag path over synthetic fixture can set local
  conversion true only locally when not synthetic flag and attestation
  passes; docs mark this as flag-path test, not evidence of real labels.
- Output bundle contains no packet refs / paths / snippets / query /
  candidate text.
- stdout/stderr/output metadata contain no exact input/output path or
  basename.
- Public artifact scanner fail-closes (rejects forbidden keys + value
  patterns; contract containers reject unapproved strings; approved
  schema/level/bucket/slot/attestation/bundle-key tokens pass).
- Self-test failure blocks public artifact generation.

## Validation

```text
python3 -m py_compile eval/d4e_filled_packet_converter.py    => PASS
python3 eval/d4e_filled_packet_converter.py --self-test      => PASS (307/307 checks)
python3 eval/d4e_filled_packet_converter.py \
  --out artifacts/d4e_filled_packet_converter/\
d4e_filled_packet_converter_report.json                     => PASS
  (status: blocked_no_filled_packets_available_or_no_conversion_run,
   forbidden_scan: pass, self_test_passed: true,
   private_filled_packets_read: false,
   conversion_run: false,
   d4b_true_label_bundle_created: false,
   d4b_true_label_bundle_written: false,
   labels_converted: false,
   d5_unblocked: false,
   converter_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   filled_packet_schema_contract_defined: true,
   d4d_attestation_required: true,
   d4b_bundle_schema_contract_defined: true,
   d4b_mapping_contract_defined: true,
   mode: public_harness_no_filled_packets_no_conversion, phase: D4e,
   d4c_packet_schema_source: d4c_annotation_packet_v1,
   d4d_runbook_protocol: d4d_human_annotation_runbook.v1,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## Caveats

- D4e is the filled-packet -> D4b bundle converter harness public
  artifact only. It is eval/diagnostic only. It does NOT change runtime,
  retriever, pack, model, backend, or default policy; it does NOT
  change EvidenceCore semantics. It is NOT a benchmark result, NOT a
  downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.
- D4e default is a harness with a blocked public artifact. The default
  committed artifact reads NO private filled packets, runs NO
  conversion, creates/writes/validates NO D4b bundle, collects/converts
  NO labels, computes NO calibration / agreement / CI, performs NO
  model/LLM labeling, and passes NO public-release gate. D5 remains
  blocked. Harness/control true flags are true only for the validated
  harness/controls, NOT for any real label conversion or bundle claim.
- D4e is NOT real label conversion in committed output, NOT
  calibration, NOT agreement/CI computation, and NOT D5 unblock. It
  hardens the converter control plane between D4d human annotation and
  D4b bundle validation, before any real human labels exist.
- D4e has a private converter mode (opt-in, NOT committed). Private
  output is written to `/tmp` only and never committed. The real-mode
  flag-path test over a synthetic fixture (which sets
  `local_private_conversion_executed=true` and
  `real_human_labels_converted=true` locally) is a flag-path test only
  and is NOT evidence that real labels exist. Real human labels are
  not yet collected; D5 remains blocked.
- The converter consumes only the filled label slots and the D4d
  attestation; it rejects D4c source context fields (paths, spans,
  snippets, content_sha, query text, candidate text, packet source
  context). The D4d attestation must be exactly
  `d4d_human_annotation_runbook.v1` with all six required flags true
  (two independent human raters, independence before adjudication, no
  LLM/model labels, no proxy labels as true labels, local-only storage);
  model/proxy/LLM labels are rejected as human/manual labels.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; the harness/control true flags are the only true control
  flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was NOT updated (D4e is a
  harness/blocked-only artifact; no conclusions change).
