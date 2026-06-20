# D4c Annotation Packet Builder Harness (Public Harness / No-Packets Artifact)

## Scope and claim boundary

D4c is the **annotation packet builder harness** public artifact. It
bridges private source records to future human annotations by building
local/private annotation packets with blank label slots. The **default
committed artifact is a public harness / no-packets artifact**, NOT a
real packet build. D4c is the follow-on to D4b (which froze the
true-label bundle input contract). The D4c bridge is:

```text
private records -> human annotation packets -> D4b true-label bundle -> D5 aggregate release candidate
```

D4c **does not** collect labels, **does not** fill label slots, **does
not** create a D4b true-label bundle, **does not** run the packet->bundle
converter, **does not** compute calibration metrics, **does not**
perform model/LLM labeling, **does not** read private source records by
default, **does not** emit provider payloads/API keys/secrets/model
outputs, and **does not** change runtime behavior, retriever, pack,
model, backend, default policy, or EvidenceCore semantics.

- Claim level: `annotation_packet_builder_harness_only`.
- D4b bundle schema target: `d4b_true_label_bundle_v1` (target only;
  D4c does not run the converter).
- Status: `blocked_no_private_source_records_available_or_no_packets_built`;
  mode `public_harness_no_packets`; phase `D4c`.

D4c is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
downstream agent value claim, NOT a runtime-clean general algorithm
claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D4c emits no EvidenceCore records and changes none of its
  semantics.
- D4c reads no private source records by default:
  `private_source_records_read=false`,
  `private_source_records_persisted=false`,
  `annotation_packets_built=false`,
  `annotation_packets_persisted=false`,
  `private_packet_output_written=false`,
  `private_input_path_emitted=false`,
  `packet_output_path_emitted=false`, `packet_ids_emitted=false`,
  `task_ids_emitted=false`, `repo_ids_emitted=false`,
  `paths_or_spans_emitted=false`, `snippets_emitted=false`,
  `content_sha_emitted=false`, `query_text_emitted=false`,
  `candidate_text_emitted=false`,
  `private_packet_output_contains_sensitive_context=false`.
- D4c fills no labels and creates no bundle:
  `private_packet_schema_validated=false`,
  `private_packet_labels_filled=false`, `labels_collected=false`,
  `true_label_bundle_created=false`,
  `d4b_true_label_bundle_validated=false`,
  `d4b_bundle_converter_run=false`,
  `calibration_metrics_computed=false`,
  `model_or_llm_labeling_performed=false`,
  `provider_payloads_emitted=false`,
  `annotation_instructions_emitted=false`. D4c passes no release gate:
  `true_e_s_calibration_claimed=false`,
  `public_release_gate_passed=false`.

## Core boundary: D4c default is blocked / no-packets

- The **default committed D4c artifact** is a public harness / no-packets
  artifact. Its status is
  `blocked_no_private_source_records_available_or_no_packets_built`. It
  reads NO private source records, builds NO packets, persists NO
  packets, fills NO labels, creates NO D4b bundle, runs NO converter,
  computes NO calibration, performs NO model/LLM labeling, and passes
  NO public-release gate.
- D4c must NOT claim annotation packets were built unless private source
  records are explicitly supplied and run locally under `/tmp`.
- The optional private packet builder mode is local-only and `/tmp` only;
  no private output is ever committed.

### D4c -> human annotation -> D4b bundle relation

D4c builds annotation packets (with blank label slots) from private
source records. Human raters then fill the blank slots. A separate
D4b converter (manual transcription or local converter) maps filled
packets to a `d4b_true_label_bundle_v1`. D4c **does not** run that
converter, **does not** create the bundle, and **does not** collect or
claim labels. The `d4b_mapping_contract` records that the converter is
not run and no true-label bundle is created.

## CLI

```bash
python3 -m py_compile eval/d4c_annotation_packet_builder.py
python3 eval/d4c_annotation_packet_builder.py --self-test
python3 eval/d4c_annotation_packet_builder.py \
    --out artifacts/d4c_annotation_packet_builder/\
d4c_annotation_packet_builder_report.json
```

Default mode (no `--input`, no `--allow-private-source-records`): writes
the committed public harness / no-packets artifact (default out path if
`--out` omitted).

Private packet builder mode is an explicit guard harness only (`/tmp`
only, never committed):

```bash
# NOT committed; /tmp only (private packet builder):
python3 eval/d4c_annotation_packet_builder.py \
    --allow-private-source-records \
    --input /tmp/private_source_records.json \
    --out /tmp/d4c_annotation_packets.json
```

CLI arguments: `--self-test`, `--out`,
`--allow-private-source-records`, `--input`.

CLI guard matrix (all validated before any input is opened):

- `--input` without `--allow-private-source-records` => exit 2 (no
  path/basename leak).
- `--allow-private-source-records` without `--input` => exit 2.
- `--allow-private-source-records` with `--input` but no explicit `--out`
  => exit 2.
- `--allow-private-source-records` with the committed artifact path as
  `--out` => exit 2 before read.
- `--allow-private-source-records` with a non-`/tmp` `--out` => exit 2
  before read.
- `--allow-private-source-records --input <path> --out /tmp/...` =>
  accepted for local-only packet building.
- Strong resolved `/tmp` guard: resolve `/tmp`; resolve the output
  parent before private input read; reject a parent symlink escaping
  `/tmp` (e.g. `/tmp/link_to_repo/out.json`); reject an existing output
  file symlink; reject a resolved target escaping `/tmp`. All output
  guards run before the input is opened or stat'd (validate-before-read).
- Private-mode success stdout must NOT print the exact `/tmp` output
  path.
- Private-mode errors must NOT print raw exceptions, input/output
  path/basename, raw JSON, or private text. The fixed sanitized error is:
  `error: failed to load private source records (schema/privacy/parse
  error; details suppressed)`.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d4c_annotation_packet_builder/d4c_annotation_packet_builder_report.json`
is the public harness / no-packets artifact. Identity / boundary fields:

- `schema_version` = `d4c_annotation_packet_builder_harness.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `d4b_bundle_schema_target`
- Default false flags (all false): `private_source_records_read`,
  `private_source_records_persisted`, `annotation_packets_built`,
  `annotation_packets_persisted`, `private_packet_output_written`,
  `packet_output_path_emitted`, `private_input_path_emitted`,
  `packet_ids_emitted`, `task_ids_emitted`, `repo_ids_emitted`,
  `paths_or_spans_emitted`, `snippets_emitted`, `content_sha_emitted`,
  `query_text_emitted`, `candidate_text_emitted`,
  `private_packet_output_contains_sensitive_context`,
  `private_packet_schema_validated`, `private_packet_labels_filled`,
  `labels_collected`, `true_label_bundle_created`,
  `d4b_true_label_bundle_validated`, `d4b_bundle_converter_run`,
  `calibration_metrics_computed`, `model_or_llm_labeling_performed`,
  `provider_payloads_emitted`, `annotation_instructions_emitted`,
  `true_e_s_calibration_claimed`, `public_release_gate_passed`.
- Harness/control flags (exactly these six, all true):
  `private_packet_builder_harness_available`, `private_cli_guard_validated`,
  `tmp_output_resolved_guard_validated`, `sanitized_error_guard_validated`,
  `packet_schema_contract_defined`, `d4b_mapping_contract_defined`.
- No-claim / no-runtime-change flags (all false): `promotion_ready`,
  `default_should_change`, `downstream_agent_value_proven`,
  `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`,
  `model_calls_changed`, `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`,
  `runtime_clean_general_algorithm_claimed`, `ood_temporal_supported`,
  `quiver_systems_supported`.
- Diagnostic flags (all true): `aggregate_only_public_artifact`,
  `diagnostic_only`, `not_evidence`.
- `private_source_record_schema_contract`: category-only contract
  (schema `d4c_private_source_records_v1`, `private_only=true`,
  `may_contain_sensitive_context=true`).
- `packet_schema_contract`: schema `d4c_annotation_packet_v1`,
  `private_only=true`, `may_contain_sensitive_context=true`,
  `required_label_slots` = `[e_score, s_score, bucket, citation_valid,
  rater_pair_present, adjudicated]`, `target_bundle_schema=
  d4b_true_label_bundle_v1`.
- `d4b_mapping_contract`: `target_bundle_schema=d4b_true_label_bundle_v1`,
  `packet_label_slots` = the same six slots,
  `packet_to_bundle_requires_manual_transcription_or_local_converter=true`,
  `converter_not_run=true`, `true_label_bundle_created=false`.
- `private_packet_builder_harness`: `/tmp`-only, opt-in, not committed,
  fills no labels, creates no D4b bundle, runs no converter, claims no
  calibration.
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Private source-records contract (local-only)

Private source records are a JSON object with schema
`d4c_private_source_records_v1` and a `records` list. Each record
requires exactly: `private_record_ref`, `candidate_ref`, `query_text`,
`candidate_text`, `candidate_bucket_hint`, `evidence`. `evidence` entries
require exactly: `path`, `start_line`, `end_line`, `content_sha`,
`snippet`. `candidate_bucket_hint` must be one of
`primary_evidence`/`dependency_support`/`weak_candidates`/`abstained`/
`unknown`. `start_line`/`end_line` are positive ints with
`start_line <= end_line`. `content_sha` is 32/40/64-char hex. The loader
rejects unknown keys (e.g. `provider_payload`, `api_key`, `secret`,
`model_output`, `prompt_response`, labels/label rows) rather than
supporting and stripping them. If malformed, the fixed sanitized error
is: `error: failed to load private source records (schema/privacy/parse
error; details suppressed)`.

## Private packet output contract (sensitive context, /tmp only)

Private annotation packets MAY contain sensitive context necessary for
human labeling:

- local packet refs / local private refs;
- query/candidate text;
- paths, line spans, snippets, content hashes;
- annotation instructions;
- blank label slots for `e_score`, `s_score`, `bucket`,
  `citation_valid`, `rater_pair_present`, `adjudicated`.

Rules:

- explicit `/tmp` output only, never committed;
- success stdout must not print exact path;
- no labels filled automatically by the builder; label slots must be
  null/blank;
- no D4b bundle creation;
- no calibration/agreement/CI metrics;
- no model/LLM labeling;
- no provider/API secrets or provider payloads;
- no exact input/output path or basename in packet metadata/stdout/
  stderr.
- safe local guardrail flags: `private_packet_output=true`,
  `public_artifact=false`, `do_not_commit=true`,
  `labels_filled_by_builder=false`, `d4b_bundle_created=false`,
  `d4b_bundle_converter_run=false`,
  `true_label_bundle_created=false`,
  `calibration_metrics_computed=false`,
  `model_or_llm_labeling_performed=false`.

Bucket hints can appear only as source `candidate_bucket_hint` or
guidance, never as a filled `bucket` label slot.

## Scanner split (two scanners)

1. **Public artifact scanner**: strict, fail-closed. Rejects task/repo
   IDs, packet IDs/refs, paths, spans, snippets, content SHA,
   query/candidate text, labels, local paths, hashes, raw JSON fragments,
   multiline strings, URLs, and the self-test sentinel. Contract
   containers (`packet_schema_contract`, `d4b_mapping_contract`,
   `private_source_record_schema_contract`) are exact string allowlists:
   only approved schema identifiers and approved label-slot field names
   may appear there. Arbitrary short strings such as implementation
   symbols or private text are rejected. The scanner is not weakened to
   make private packets pass.
2. **Private packet guard**: different. Allows paths/snippets/content
   hashes/query/candidate text/annotation instructions/blank label slots
   in private packets only; enforces private-mode `/tmp` location,
   packet schema (`d4c_annotation_packet_v1`), blank label slots, no
   filled E0/E1/E2/S0/S1/S2 values, no D4b bundle, no converter, no
   calibration, no model labeling, and rejects provider secrets/API
   keys/provider payloads/model outputs.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys (`task_id`, `repo_id`, `repo`,
`path`, `span`, `line_range`, `start_line`, `end_line`, `content_sha`,
`snippet`, `candidate_text`, `query`, `query_text`, `prompt`,
`response`, `model_output`, `label`, `labels`, `raw_label`,
`annotation_row`, `rater_id`, `annotator_id`, `packet_ref`,
`packet_id`, `private_record_ref`, `candidate_ref`, `label_slots`,
`annotation_instructions`, `e_score`, `s_score`, `bucket`,
`provider_payload`, `api_key`, etc.) anywhere, and rejects value
patterns: ANY URL (no URL allowlist), 32/40/64-char hex digests,
secret-like strings, path-like `src/foo.rs` and `/private/foo.jsonl`,
multiline strings, raw JSON fragments, raw line ranges `12-34`, and
the self-test sentinel. Allows safe protocol/identity/band strings only
(`d4c_annotation_packet_builder_harness.v1`, `D4c`,
`d4b_true_label_bundle_v1`, etc.). Contract field-name containers use
an exact string allowlist, not a generic schema-container exemption.

## Self-tests

- All default false/true flags as above (default artifact no packets, no
  read, no labels, no metrics, no claims; the six harness flags true;
  diagnostic flags true).
- Artifact identity fields (`schema_version`, `claim_level`, `status`,
  `mode`, `phase`, `d4b_bundle_schema_target`).
- Public contracts defined (`private_source_record_schema_contract`,
  `packet_schema_contract`, `d4b_mapping_contract`).
- Public scanner fail-closes (forbidden keys + value patterns).
- Contract allowlist: approved schema identifiers and label-slot tokens
  are allowed only as values inside explicit contract containers
  (`packet_schema_contract.required_label_slots`); arbitrary strings
  such as `compute_loss` or private text are rejected even inside
  contract containers; field names remain rejected as keys outside
  contracts (`{"e_score":"E2"}`, `{"content_sha":"abc"}`,
  `{"query_text":"..."}`, `{"packet_ref":"..."}`) and rejected as
  values outside contracts.
- Private source-records schema validation: valid records validate;
  unknown schema/keys, provider_payload/api_key/secret/model_output/
  prompt_response/labels, missing fields, invalid bucket hint, empty
  query_text, start_line>end_line, non-positive lines, invalid
  content_sha, extra evidence keys, empty evidence rejected.
- CLI guard matrix including validate-before-read, committed-out
  rejected before read, non-`/tmp` rejected before read, input-without-
  allow rejected before read.
- Resolved `/tmp` symlink-escape rejection (parent symlink escape and
  existing output file symlink).
- Sanitized error with sensitive basename + sentinel (no leak in
  stdout/stderr/output).
- Synthetic private input with path/snippet/content_sha writes a
  `/tmp` packet with sensitive context present, label slots blank, no
  filled E/S values, no D4b bundle, no calibration, no model labeling,
  no exact input/output path/basename in metadata/stdout, and output
  not committed.
- Private packet output contains sensitive context only in `/tmp`
  private mode, never in the public artifact.
- Private packet guard rejects filled label slots, provider payload
  keys, and secret-like values; passes clean packets.
- Forbidden scanner fail-closes and generation refuses success if
  self-test fails.

## Validation

```text
python3 -m py_compile eval/d4c_annotation_packet_builder.py    => PASS
python3 eval/d4c_annotation_packet_builder.py --self-test      => PASS (233/233 checks)
python3 eval/d4c_annotation_packet_builder.py \
  --out artifacts/d4c_annotation_packet_builder/\
d4c_annotation_packet_builder_report.json                     => PASS
  (status: blocked_no_private_source_records_available_or_no_packets_built,
   forbidden_scan: pass, self_test_passed: true,
   private_source_records_read: false,
   annotation_packets_built: false,
   private_packet_output_written: false,
   private_packet_output_contains_sensitive_context: false,
   labels_collected: false,
   true_label_bundle_created: false,
   d4b_bundle_converter_run: false,
   calibration_metrics_computed: false,
   model_or_llm_labeling_performed: false,
   provider_payloads_emitted: false,
   public_release_gate_passed: false,
   private_packet_builder_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   packet_schema_contract_defined: true,
   d4b_mapping_contract_defined: true,
   mode: public_harness_no_packets, phase: D4c,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
/tmp private packet builder (synthetic source records)         => PASS
  (annotation_packets_built=true,
   private_packet_output_contains_sensitive_context=true,
   private_packet_guard: pass, label_slots all null,
   sensitive context (path/snippet/content_sha/query_text/
   candidate_text/annotation_instructions/packet_ref) present in
   /tmp output but NOT in public artifact,
   no input/output path or basename in metadata/stdout/stderr,
   no provider secrets, no D4b bundle, no converter, no
   calibration, no model labeling, NOT committed)
CLI guard matrix (input without allow, allow without input,
  no explicit out, committed out, non-/tmp out)                => PASS (all exit 2)
Resolved /tmp symlink-escape guard (parent symlink,
  existing output file symlink)                                => PASS (exit 2)
Malformed private input sanitized error                         => PASS (exit 2, no leak)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## Caveats

- D4c is the annotation packet builder harness public artifact only. It
  is eval/diagnostic only. It does NOT change runtime, retriever, pack,
  model, backend, or default policy; it does NOT change EvidenceCore
  semantics. It is NOT a benchmark result, NOT a downstream agent value
  claim, NOT a runtime-clean general algorithm claim, NOT an OOD
  temporal claim, and NOT a QuIVer systems claim.
- D4c default is blocked / no-packets. The default committed artifact
  reads NO private source records, builds NO packets, persists NO
  packets, fills NO labels, creates NO D4b bundle, runs NO converter,
  computes NO calibration, performs NO model/LLM labeling, and passes
  NO public-release gate. Harness/control flags are true only for the
  validated harness/controls, NOT for any real packet build or label
  claim.
- D4c is NOT label collection, NOT D4b true-label bundle creation, NOT
  calibration, and NOT release readiness. It builds packets with blank
  label slots for human raters; it does not run the packet->bundle
  converter.
- The private packet builder mode is `/tmp` only and NEVER committed.
  Unlike D4b, the D4c private packet output MAY intentionally contain
  sensitive context required for human labeling (local packet refs,
  query/candidate text, evidence path/spans/snippet/content_sha,
  annotation instructions, blank label slots), but ONLY under `/tmp`.
  The default public artifact never reads private records and contains
  no packet/private content.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; the six harness/control flags are the only true control
  flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was NOT updated (D4c is a
  harness/blocked artifact; no conclusions change).
