# D4a Dual-Rubric Execution Gate / Dry-Run (Public Gate Artifact Only)

## Scope and claim boundary

D4a is the **execution gate / dry-run** public artifact. It validates the
control plane required before any future local/private true E-score /
S-score label calibration (D4b) can run. D4a is the dry-run follow-on to
D3 (which preregistered the label protocol only).

D4a **does not** collect real labels, **does not** read private label
bundles by default, **does not** compute true calibration metrics, **does
not** measure inter-rater agreement, **does not** claim true/proxy
calibration, and **does not** change runtime behavior, retriever, pack,
model, backend, default policy, or EvidenceCore semantics.

- Claim level: `dual_rubric_execution_gate_dry_run_only`.
- Rubric version: `d3_true_dual_rubric_label_protocol_v1` (D3 protocol
  checked; D4a does not redefine the rubric).
- Status: `execution_gate_ready_no_labels_collected`; mode
  `public_gate_dry_run`; phase `D4a`; next phase
  `D4b_local_private_label_collection_smoke`.

D4a is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
downstream agent value claim, NOT a runtime-clean general algorithm
claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D4a emits no EvidenceCore records and changes none of its
  semantics.
- D4a collects no labels: `labels_collected=false`,
  `calibration_metrics_computed=false`,
  `inter_rater_agreement_measured=false`,
  `agreement_metrics_computed=false`,
  `confidence_intervals_computed=false`.
- D4a reads no private bundles by default:
  `private_label_bundle_read=false`, `private_records_read=false`,
  `raw_private_records_read=false`, `raw_labels_persisted=false`,
  `raw_label_rows_emitted=false`, `private_label_bundle_persisted=false`,
  `private_output_path_emitted=false`, `private_input_path_emitted=false`,
  `private_output_committed=false`.
- D4a claims no calibration: `true_e_s_calibration_claimed=false`,
  `proxy_calibration_claimed=false`. D4a passes no release gate:
  `public_release_gate_passed=false`,
  `real_label_bundle_gate_passed=false`.

## Core boundary: D4a is NOT D4b

- **D4a** is the execution gate / dry-run public artifact only. It
  validates CLI/privacy guards, D3 protocol constants, synthetic
  in-memory gate logic, fail-closed scanning, and documentation
  boundaries.
- **D4b** is real local/private label collection/calibration. D4a does
  NOT perform D4b. The default committed D4a artifact does NOT read
  private labels, NOT collect labels, NOT compute calibration/agreement/
  CI metrics, and NOT claim true/proxy calibration.

The private dry-run mode is a local-only harness: it may validate a
local/private label-bundle-shaped JSON only with explicit opt-in and
`/tmp` output, but its output is local-only and NEVER committed.

## CLI

```bash
python3 -m py_compile eval/d4_dual_rubric_execution_gate.py
python3 eval/d4_dual_rubric_execution_gate.py --self-test
python3 eval/d4_dual_rubric_execution_gate.py \
    --out artifacts/d4_dual_rubric_execution_gate/\
d4_dual_rubric_execution_gate_report.json
```

Default mode (no `--input`, no `--allow-private-labels`): writes the
committed public gate artifact (default out path if `--out` omitted).

Private dry-run mode is an explicit guard harness only:

```bash
# NOT committed; /tmp only:
python3 eval/d4_dual_rubric_execution_gate.py \
    --allow-private-labels --input /tmp/private_bundle.json \
    --out /tmp/d4a_gate_smoke.json
```

CLI guard matrix (all validated before any input is opened):

- `--input` without `--allow-private-labels` => exit 2 (no path/basename
  leak).
- `--allow-private-labels` without `--input` => exit 2.
- `--allow-private-labels` with `--input` but no explicit `--out` =>
  exit 2.
- `--allow-private-labels` with the committed artifact path as `--out`
  => exit 2 before read.
- `--allow-private-labels` with a non-`/tmp` `--out` => exit 2 before
  read.
- `--allow-private-labels --input <path> --out /tmp/...` => accepted
  for local-only dry-run.
- Private-mode success stdout must NOT print the exact `/tmp` output
  path.
- Private-mode errors must NOT print raw exceptions, input path/basename,
  raw JSON, or label text.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d4_dual_rubric_execution_gate/d4_dual_rubric_execution_gate_report.json`
is the public gate dry-run. Identity / boundary fields:

- `schema_version` = `d4_dual_rubric_execution_gate.v1`
- `generated_by`, `generated_at`, `claim_level`, `rubric_version`,
  `status`, `mode`, `phase`, `next_phase`
- `d3_protocol_checked=true`, `d3_protocol_version=
  d3_true_dual_rubric_label_protocol_v1`, `d3_required_gates_present=true`
- Default false flags (all false): `labels_collected`,
  `private_label_bundle_read`, `private_label_bundle_persisted`,
  `private_records_read`, `raw_private_records_read`,
  `raw_labels_persisted`, `raw_label_rows_emitted`,
  `private_output_path_emitted`, `private_input_path_emitted`,
  `private_output_committed`, `calibration_metrics_computed`,
  `inter_rater_agreement_measured`, `agreement_metrics_computed`,
  `confidence_intervals_computed`, `true_e_s_calibration_claimed`,
  `proxy_calibration_claimed`, `public_release_gate_passed`,
  `real_label_bundle_gate_passed`.
- Execution-control flags (true only for validated dry-run controls):
  `execution_controls_validated`, `private_cli_guard_validated`,
  `tmp_output_guard_validated`, `validate_before_read_guard_validated`,
  `sanitized_error_guard_validated`,
  `small_cell_suppression_gate_validated`, `min_total_n_gate_validated`,
  `agreement_required_gate_validated`,
  `confidence_interval_gate_validated`.
- No-claim / no-runtime-change flags (all false): `promotion_ready`,
  `default_should_change`, `downstream_agent_value_proven`,
  `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`,
  `model_calls_changed`, `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`,
  `runtime_clean_general_algorithm_claimed`, `ood_temporal_supported`,
  `quiver_systems_supported`.
- Diagnostic flags (all true): `aggregate_only_public_artifact`,
  `diagnostic_only`, `not_evidence`.
- `gate_thresholds`: `k_min=5`, `min_total_labels=50`,
  `agreement_required=true`, `confidence_intervals_required=true`.
- `gate_category_names`: `primary_evidence`, `dependency_support`,
  `weak_candidates`, `abstained`.
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Gate logic (synthetic, in-memory)

D4a evaluates gate thresholds over synthetic in-memory aggregate
summaries only. It does NOT compute calibration metrics, inter-rater
agreement, or confidence intervals. Gates (constants from D3):

- min-N: `total_labels >= 50` (`min_total_labels`).
- small-cell suppression: every release cell `n >= k_min` (5); any cell
  below 5 fails/suppresses the public release gate.
- agreement required: a second rater is present AND agreement is
  available (unavailable => fail).
- confidence intervals required: CIs are available (missing => fail).
- all conditions satisfied => private dry-run gate status pass.

The public artifact may include only gate category names, thresholds,
booleans, and synthetic self-test aggregate pass/fail counts. It must
NOT include real private sample sizes from any private input.

## Private dry-run bundle schema (local-only, sanitized)

The private dry-run mode accepts a synthetic/private-shaped AGGREGATE
summary (counts and booleans), NOT raw rows. It does NOT require real
labels. Allowed keys only:

- `schema` = `d4_private_label_bundle_dry_run_v1`
- `total_labels` (int >= 0)
- `cells` (list of `{category, n}` where `category` is a fixed gate
  category name and `n` is an int >= 0)
- `second_rater_present`, `agreement_available`,
  `confidence_intervals_available` (booleans)
- `min_cell_n` (optional int >= 0)

Any key outside this allowlist (e.g. `rater_id`, `raw_label`,
`annotation_row`, `path`) fails fail-closed. If malformed, the fixed
sanitized error is:
`error: failed to load private labels (schema/privacy/parse error;
details suppressed)`.

Private dry-run output JSON must NOT contain: input/output paths,
basenames, raw labels, rater IDs, annotation rows, row hashes, or exact
real private sample sizes. It contains only gate pass/fail booleans,
fixed thresholds, fixed gate category names, and sanitized flags.

## Forbidden scanner (fail-closed)

A strict forbidden-output scanner runs fail-closed before writing any
JSON. Rejects forbidden dict keys (`task_id`, `repo_id`, `repo`, `path`,
`span`, `line_range`, `start_line`, `end_line`, `content_sha`, `snippet`,
`candidate_text`, `query`, `prompt`, `response`, `model_output`,
`label`, `raw_label`, `annotation_row`, `rater_id`, `annotator_id`,
`disagreement_example`, `per_row_hash`, etc.) anywhere, and rejects
value patterns: ANY URL (no URL allowlist), 32/40/64-char hex digests,
secret-like strings, path-like `src/foo.py` and `/private/foo.jsonl`,
multiline strings, raw JSON fragments, raw line ranges `12-34`, and the
self-test sentinel. Allows safe gate/protocol strings (`primary_evidence`,
`k_min`, `D4a`, `d3_true_dual_rubric_label_protocol_v1`, etc.).

## Self-tests

- All default false/true flags as above.
- D3 protocol constants/gates checked (`k_min=5`,
  `min_total_labels=50`, agreement/CI required).
- CLI guard matrix including validate-before-read, committed-out
  rejected before read, non-`/tmp` rejected before read.
- Sanitized error with sensitive basename + `SECRET_LABEL_SENTINEL`:
  no leak in stdout/stderr/output.
- Private output path not serialized.
- Forbidden scanner rejects sensitive keys/values and fail-closes.
- Gate logic tests for min-N, small-cell, agreement, CI, and pass case.
- Artifact generation refuses success if self-test fails.

## Validation

```text
python3 -m py_compile eval/d4_dual_rubric_execution_gate.py    => PASS
python3 eval/d4_dual_rubric_execution_gate.py --self-test      => PASS (153/153 checks)
python3 eval/d4_dual_rubric_execution_gate.py \
  --out artifacts/d4_dual_rubric_execution_gate/\
d4_dual_rubric_execution_gate_report.json                     => PASS
  (status: execution_gate_ready_no_labels_collected,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, private_label_bundle_read: false,
   private_output_committed: false,
   calibration_metrics_computed: false,
   true_e_s_calibration_claimed: false, proxy_calibration_claimed: false,
   public_release_gate_passed: false,
   execution_controls_validated: true,
   mode: public_gate_dry_run, phase: D4a,
   next_phase: D4b_local_private_label_collection_smoke,
   rubric_version: d3_true_dual_rubric_label_protocol_v1)
/tmp private dry-run smoke (synthetic bundle)                => PASS
  (no input/output path, basename, raw label, sentinel, or
   exact private sample size in output/stdout/stderr)
CLI guard matrix (missing allow/input/out, committed out,
  non-/tmp out)                                                => PASS (all exit 2)
python3 scripts/validate_docs_i18n.py                          => PASS
git diff --check                                                => PASS
```

## Caveats

- D4a is the execution gate / dry-run public artifact only. It is
  eval/diagnostic only. It does NOT change runtime, retriever, pack,
  model, backend, or default policy; it does NOT change EvidenceCore
  semantics. It is NOT a benchmark result, NOT a downstream agent value
  claim, NOT a runtime-clean general algorithm claim, NOT an OOD
  temporal claim, and NOT a QuIVer systems claim.
- D4a is NOT D4b. The default committed artifact collects NO labels,
  reads NO private label bundles, computes NO calibration metrics,
  measures NO inter-rater agreement, claims NO true/proxy calibration,
  and passes NO public-release gate.
- The private dry-run mode is `/tmp` only and NEVER committed. It
  validates a local/private label-bundle-shaped JSON only to validate
  shape/gates; it does NOT compute or claim true calibration metrics.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; execution-control flags are true only for the validated
  dry-run controls.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was NOT updated (D4a is a
  gate/dry-run; no conclusions change).
