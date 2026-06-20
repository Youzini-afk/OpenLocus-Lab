# D4-series Harness Rollup / D5 Blocked Status (Public Rollup-Only Artifact)

## Scope and claim boundary

The D4-series rollup is the **D4-series harness rollup / D5 blocked
status** public artifact. It is a **rollup-only** artifact, NOT a new
research phase. It aggregates ONLY the committed D4a-D4f public
statuses / claim levels and the D5 blockers. It performs NO private
reads, NO probes, NO `/tmp` outputs, NO label collection, NO metrics,
and NO D5 calibration.

The D4-series control-plane bridge is:

```text
D4a execution gate (dry-run) -> D4b true-label bundle harness -> D4c annotation packet builder harness -> D4d human annotation runbook -> D4e filled-packet converter harness -> D4f bundle validation gate harness -> (D5 blocked: no real human manual labels)
```

The rollup **does not** read private records, packets, labels, or
bundles, **does not** emit labels / raw label rows / exact counts /
agreement / CI values, **does not** accept packet refs / task IDs /
repo IDs / paths / spans / snippets / content hashes / query /
candidate text / rater IDs / model outputs / provider payloads in any
committed artifact, **does not** compute calibration / inter-rater
agreement / confidence intervals, **does not** pass any public-release
gate, **does not** unblock D5, **does not** claim true E/S calibration,
**does not** perform model/LLM labeling, and **does not** change
runtime behavior, retriever, pack, model, backend, default policy, or
EvidenceCore semantics.

- Schema version: `d4_series_rollup.v1`.
- Claim level: `d4_series_harness_rollup_only`.
- Status: `d5_blocked_no_real_human_manual_labels`; mode
  `public_rollup_no_private_reads`; phase `D4-rollup`.

The rollup is **eval/diagnostic only**. It is NOT a benchmark result,
NOT a downstream agent value claim, NOT a runtime-clean general
algorithm claim, NOT an OOD temporal claim, and NOT a QuIVer systems
claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; the rollup emits no EvidenceCore records and changes none
  of its semantics.
- The rollup reads no private records / packets / labels / bundles and
  collects no labels: `private_records_read=false`,
  `private_packets_read=false`, `private_labels_read=false`,
  `private_bundles_read=false`, `labels_collected=false`.
- The rollup computes no metrics and claims no calibration:
  `calibration_metrics_computed=false`,
  `agreement_metrics_computed=false`,
  `confidence_intervals_computed=false`,
  `true_e_s_calibration_claimed=false`.
- The rollup passes no release gate and does not unblock D5:
  `d5_public_aggregate_candidate_allowed=false`.
- No-claim / no-runtime-change flags (all false):
  `promotion_ready=false`, `default_should_change=false`,
  `downstream_agent_value_proven=false`,
  `runtime_behavior_changed=false`, `retriever_changed=false`,
  `pack_builder_changed=false`, `model_calls_changed=false`,
  `backend_changed=false`, `default_policy_changed=false`,
  `evidencecore_semantics_changed=false`,
  `runtime_clean_general_algorithm_claimed=false`,
  `ood_temporal_supported=false`, `quiver_systems_supported=false`.

## Core boundary: rollup-only, D5 remains blocked

- The **default committed rollup artifact** is a public rollup-only
  artifact. Its status is `d5_blocked_no_real_human_manual_labels`. It
  reads NO private records / packets / labels / bundles, collects NO
  labels, emits NO labels / counts / metrics / paths / IDs / snippets /
  rater IDs, computes NO calibration / agreement / CI, performs NO
  model/LLM labeling, and passes NO public-release gate. D5 remains
  blocked.
- The rollup has NO private mode. It has NO `/tmp` output path. It has
  NO CLI guard for private input. It is purely a public aggregate of
  the six committed D4 harness artifacts.
- Real human manual labels are NOT yet collected. D5 is NOT unblocked.
  No D5 public-aggregate candidate is allowed.

### D5 prerequisites (all false)

The artifact carries these values both as flat booleans and as a
`d5_prerequisites` object for readability; both representations must match.

```text
real_human_manual_labels_available=false
d4e_real_local_conversion_over_real_labels_run=false
d4f_real_local_validation_over_real_labels_run=false
min_n_gate_passed_for_real_labels=false
k_min_gate_passed_for_real_labels=false
agreement_gate_passed_for_real_labels=false
ci_gate_passed_for_real_labels=false
d5_public_aggregate_candidate_allowed=false
```

## D4 phases aggregated (exactly six, each exactly once)

The rollup lists EXACTLY the six D4 phases (D4a-D4f), each exactly
once, with their committed short-form commit ID, `artifact_status`,
and `claim_level`. No private paths, no counts, no metrics, no
packet/bundle contents, no task/repo IDs, no rater IDs.

| Phase | Commit | artifact_status | claim_level |
|---|---|---|---|
| D4a | `d62c13b` | `execution_gate_ready_no_labels_collected` | `dual_rubric_execution_gate_dry_run_only` |
| D4b | `6dd4024` | `blocked_no_true_label_bundle_available` | `true_label_bundle_execution_harness_only` |
| D4c | `3458716` | `blocked_no_annotation_packets_created` | `annotation_packet_builder_harness_only` |
| D4d | `55c9850` | `protocol_ready_no_raters_no_labels_no_packets` | `human_annotation_runbook_protocol_only` |
| D4e | `280d8bb` | `blocked_no_filled_packets_available_or_no_conversion_run` | `filled_packet_to_d4b_bundle_converter_harness_only` |
| D4f | `fea76d3` | `blocked_no_private_bundle_available_or_no_validation_run` | `d4b_bundle_validation_gate_harness_only` |

### Safe booleans true (control-plane chain + harness completeness)

```text
control_plane_chain_complete=true
d4a_execution_gate_complete=true
d4b_true_label_bundle_harness_complete=true
d4c_annotation_packet_builder_harness_complete=true
d4d_human_annotation_runbook_complete=true
d4e_converter_harness_complete=true
d4f_bundle_validation_gate_harness_complete=true
aggregate_only_public_artifact=true
diagnostic_only=true
not_evidence=true
```

These safe-true flags express ONLY that the control-plane chain and
each D4 harness artifact exist and are committed. They are NOT claims
of real label collection, real conversion, real validation, gate-pass,
calibration, agreement, CI, or D5 unblock.

## CLI

```bash
python3 -m py_compile eval/d4_series_rollup.py
python3 eval/d4_series_rollup.py --self-test
python3 eval/d4_series_rollup.py \
    --out artifacts/d4_series_rollup/d4_series_rollup_report.json
```

Default mode: writes the committed public rollup-only artifact
(default out path if `--out` omitted).

CLI arguments: `--self-test`, `--out`. Unknown/private-looking
arguments are rejected with a generic `invalid arguments` message that
does not echo private paths or basenames (SafeArgumentParser pattern).
The rollup has NO `--allow-private-*`, NO `--input-*`, and NO
`--synthetic-*` flags: it is rollup-only and reads no private input.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d4_series_rollup/d4_series_rollup_report.json` is the
public rollup-only artifact. Identity / boundary fields:

- `schema_version` = `d4_series_rollup.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- `d4_phases`: list of exactly six entries; each entry has exactly the
  four keys `phase`, `commit`, `artifact_status`, `claim_level`. This
  list is an EXACT contract container (see scanner below).
- Safe booleans true (exactly these, all true):
  `control_plane_chain_complete`, `d4a_execution_gate_complete`,
  `d4b_true_label_bundle_harness_complete`,
  `d4c_annotation_packet_builder_harness_complete`,
  `d4d_human_annotation_runbook_complete`,
  `d4e_converter_harness_complete`,
  `d4f_bundle_validation_gate_harness_complete`,
  `aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`.
- D5 prerequisite flags (all false): see above.
- No-read / no-claim / no-runtime-change flags (all false): see above.
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
`confidence_interval`, `ci_value`, `ci_lower`, `ci_upper`,
`total_labels`, `label_count`, `bucket_count`, `cell_count`, etc.)
anywhere, and rejects value patterns: ANY URL (no URL allowlist),
32/40/64-char hex digests, secret-like strings, path-like `src/foo.rs`
and `/private/foo.jsonl`, multiline strings, raw JSON fragments, raw
line ranges `12-34` and `12:34`, and the self-test sentinel.

The `d4_phases` list is an **exact string allowlist** contract
container: only approved phase IDs (`D4a`-`D4f`, `D4-rollup`), the six
short commit IDs, the six per-phase `artifact_status` strings, and the
six per-phase `claim_level` strings may appear as VALUES inside it.
Arbitrary short strings (e.g. implementation symbols, `compute_loss`,
private text) are rejected EVEN inside the contract container (no
over-broad container exemption). Sensitive field names (`content_sha`,
`query_text`, `packet_ref`, `source_packet_schema`,
`d4d_runbook_attestation`, `packets`) are rejected even inside the
contract container (they are not in the approved allowlist) and as keys
anywhere. No URLs are allowed anywhere.

## Self-tests

- Artifact identity fields (`schema_version`, `claim_level`, `status`,
  `mode`, `phase`, `generated_by`).
- All safe-true flags are true (control-plane chain + each D4 harness
  complete + aggregate-only / diagnostic / not-evidence).
- All D5 prerequisite flags are false.
- All no-read / no-claim / no-runtime-change false flags are false.
- `d4_phases` has exactly six entries; each of D4a-D4f appears exactly
  once; no duplicates; no extra or missing phase IDs.
- Each `d4_phases` entry has exactly the four keys `phase`, `commit`,
  `artifact_status`, `claim_level`.
- Per-phase `commit`, `artifact_status`, `claim_level` match the exact
  expected strings.
- `control_plane_chain_complete=true`.
- Public artifact forbidden scanner:
  - rejects forbidden dict keys (`task_id`, `repo_id`, `repo`, `path`,
    `span`, `start_line`, `end_line`, `content_sha`, `snippet`,
    `candidate_text`, `query`, `query_text`, `prompt`, `response`,
    `model_output`, `label`, `raw_label`, `annotation_row`,
    `rater_id`, `annotator_id`, `packet_ref`, `packet_id`,
    `private_record_ref`, `candidate_ref`, `per_row_hash`, `row_hash`,
    `provider_payload`, `api_key`, `agreement_metric`,
    `confidence_interval`, `ci_value`, `ci_lower`, `ci_upper`, `kappa`,
    `total_labels`, `label_count`, `bucket_count`, `cell_count`);
  - rejects value patterns (URL, 32/40/64-char hex digests,
    secret-like, path-like, leading-slash path, `.jsonl` path,
    multiline, raw JSON fragment, line range `12-34`, line range
    `12:34`, self-test sentinel);
  - rejects unapproved strings inside the `d4_phases` contract
    container (no over-broad container exemption);
  - rejects sensitive field names as VALUES inside the contract
    container;
  - rejects URLs inside the contract container (no URL allowlist);
  - allows approved phase / commit / status / claim_level strings
    inside the contract container.
- Fail-closed generation: clean public report does not raise; leaked
  report raises; refuse on self-test failure raises when failed and
  does not raise when passed; failed self-test does not carry success
  status; passed self-test carries success status.
- Public report self-scan is clean; no forbidden key anywhere.
- CLI argument surface: `--self-test`, `--out`; no other arguments.

## Validation

```text
python3 -m py_compile eval/d4_series_rollup.py    => PASS
python3 eval/d4_series_rollup.py --self-test     => PASS (147/147 checks)
python3 eval/d4_series_rollup.py \
  --out artifacts/d4_series_rollup/d4_series_rollup_report.json  => PASS
  (status: d5_blocked_no_real_human_manual_labels,
   forbidden_scan: pass, self_test_passed: true,
   control_plane_chain_complete: true,
   d5_public_aggregate_candidate_allowed: false,
   real_human_manual_labels_available: false,
   mode: public_rollup_no_private_reads, phase: D4-rollup,
   d4_phases: [D4a d62c13b, D4b 6dd4024, D4c 3458716,
               D4d 55c9850, D4e 280d8bb, D4f fea76d3])
python3 scripts/validate_docs_i18n.py             => PASS
git diff --check                                 => PASS
```

## Caveats

- The D4-series rollup is a public rollup-only artifact. It is
  eval/diagnostic only. It does NOT change runtime, retriever, pack,
  model, backend, or default policy; it does NOT change EvidenceCore
  semantics. It is NOT a benchmark result, NOT a downstream agent
  value claim, NOT a runtime-clean general algorithm claim, NOT an OOD
  temporal claim, and NOT a QuIVer systems claim.
- The rollup aggregates ONLY the committed D4a-D4f public statuses /
  claim levels. It does NOT re-run any D4 harness, NOT collect labels,
  NOT compute calibration / agreement / CI, NOT validate any bundle,
  and NOT unblock D5. D5 remains blocked because real human manual
  labels are NOT yet collected.
- The `d4_phases` `artifact_status` strings in this rollup are the
  rollup summary forms specified by the D4-series rollup contract.
  The D4c rollup summary status is
  `blocked_no_annotation_packets_created`; the underlying committed D4c
  artifact at `artifacts/d4c_annotation_packet_builder/` reports the
  fuller status
  `blocked_no_private_source_records_available_or_no_packets_built`
  (same blocked semantics, fuller wording). The D4a, D4b, D4d, D4e, and
  D4f rollup statuses match the underlying committed artifacts
  verbatim. All six `claim_level` values and all six short commit IDs
  match the underlying committed artifacts verbatim.
- The safe-true flags express ONLY that the control-plane chain and
  each D4 harness artifact exist and are committed. They are NOT claims
  of real label collection, real conversion, real validation,
  gate-pass, calibration, agreement, CI, or D5 unblock.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; the safe-true flags are the only true flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was NOT updated (the rollup
  is a rollup-only / D5-blocked artifact; no conclusions change).
