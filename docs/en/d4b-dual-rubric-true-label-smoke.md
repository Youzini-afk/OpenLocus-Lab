# D4b Dual-Rubric True-Label Smoke Harness (Public Harness / No-Labels Artifact)

## Scope and claim boundary

D4b is the **true-label smoke harness** public artifact. It freezes the
local/private true E-score / S-score label-bundle input contract and
hardens the execution controls. The **default committed artifact is a
public harness / no-labels artifact**, NOT a real true-label smoke
result. D4b is the follow-on to D4a (which validated the execution gate
/ dry-run control plane).

D4b **does not** fabricate labels, **does not** accept proxy/synthetic/
LLM labels as true labels, **does not** read private true-label bundles
by default, **does not** compute true calibration metrics, **does not**
measure inter-rater agreement, **does not** claim true/proxy calibration,
and **does not** change runtime behavior, retriever, pack, model,
backend, default policy, or EvidenceCore semantics.

- Claim level: `true_label_bundle_execution_harness_only`.
- Rubric version: `d3_true_dual_rubric_label_protocol_v1` (D3 protocol
  checked; D4b does not redefine the rubric).
- Status: `blocked_no_true_label_bundle_available`; mode
  `public_harness_no_labels`; phase `D4b`.

D4b is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
downstream agent value claim, NOT a runtime-clean general algorithm
claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D4b emits no EvidenceCore records and changes none of its
  semantics.
- D4b collects no labels: `labels_collected=false`,
  `calibration_metrics_computed=false`,
  `inter_rater_agreement_measured=false`,
  `confidence_intervals_computed=false`.
- D4b reads no true-label bundles by default:
  `true_label_bundle_read=false`,
  `true_label_bundle_validated=false`,
  `true_label_bundle_persisted=false`, `raw_label_rows_emitted=false`,
  `private_input_path_emitted=false`, `private_output_path_emitted=false`,
  `private_output_committed=false`, `exact_private_counts_emitted=false`.
- D4b claims no calibration: `true_e_s_calibration_claimed=false`,
  `local_private_true_label_smoke_executed=false`,
  `synthetic_labels_accepted_as_true=false`,
  `proxy_labels_accepted_as_true=false`,
  `llm_labels_accepted_as_true=false`,
  `model_assisted_labels_allowed=false`. D4b passes no release gate:
  `public_release_gate_passed=false`,
  `real_label_bundle_gate_passed=false`.

## Core boundary: D4b default is blocked / no-labels

- The **default committed D4b artifact** is a public harness / no-labels
  artifact. Its status is `blocked_no_true_label_bundle_available`. It
  collects NO labels, reads NO true-label bundles, validates NO bundle
  as true labels, computes NO calibration metrics, measures NO
  inter-rater agreement, claims NO true/proxy calibration, and passes NO
  public-release / real-bundle gate.
- D4b must NOT claim a true-label smoke was executed unless a real
  human/manual true E/S label bundle is explicitly supplied and run
  locally under `/tmp`. **Synthetic, proxy, and LLM labels are NOT
  accepted as true labels.** They may appear only in self-tests and
  optional private-mode harness tests, with
  `local_private_true_label_smoke_executed=false`.
- The optional private smoke mode is local-only and `/tmp` only; no
  private output is ever committed.

### Minimum real input before `local_private_true_label_smoke_executed` may be true

`local_private_true_label_smoke_executed` may be set `true` **only** in a
local private run (never committed) when ALL of the following hold:

- human/manual true E/S labels (bundle `label_source` is exactly
  `human_manual_true_e_s`);
- the D3 dual-rubric protocol (`d3_true_dual_rubric_label_protocol_v1`)
  is the rubric;
- `rater_count >= 2` with adjudication;
- the bundle passes the D4b schema contract (no IDs/paths/snippets/rater
  IDs/raw row metadata/unknown keys);
- the run is local-only under `/tmp` with no rows emitted.

If any condition fails, or the run uses `--synthetic-harness-test`, the
flag is `false`. **Synthetic/proxy/LLM labels are not accepted as true
labels under any flag.**

## CLI

```bash
python3 -m py_compile eval/d4b_dual_rubric_true_label_smoke.py
python3 eval/d4b_dual_rubric_true_label_smoke.py --self-test
python3 eval/d4b_dual_rubric_true_label_smoke.py \
    --out artifacts/d4b_dual_rubric_true_label_smoke/\
d4b_dual_rubric_true_label_smoke_report.json
```

Default mode (no `--input`, no `--allow-private-labels`): writes the
committed public harness / no-labels artifact (default out path if
`--out` omitted).

Private smoke mode is an explicit guard harness only (`/tmp` only, never
committed):

```bash
# NOT committed; /tmp only (real local private smoke):
python3 eval/d4b_dual_rubric_true_label_smoke.py \
    --allow-private-labels --input /tmp/private_bundle.json \
    --out /tmp/d4b_smoke.json
# NOT committed; /tmp only (synthetic harness self-test):
python3 eval/d4b_dual_rubric_true_label_smoke.py \
    --allow-private-labels --synthetic-harness-test \
    --input /tmp/harness_bundle.json --out /tmp/d4b_harness.json
```

CLI arguments: `--self-test`, `--out`, `--allow-private-labels`,
`--input`, `--synthetic-harness-test` (defaults false).

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
- `--synthetic-harness-test` without `--allow-private-labels` => exit 2.
- `--allow-private-labels --input <path> --out /tmp/...` => accepted
  for local-only smoke.
- Strong resolved `/tmp` guard: resolve `/tmp`; resolve the output
  parent before private input read; reject a parent symlink escaping
  `/tmp` (e.g. `/tmp/link_to_repo/out.json`); reject an existing output
  file symlink; reject a resolved target escaping `/tmp`. All output
  guards run before the input is opened or stat'd.
- Private-mode success stdout must NOT print the exact `/tmp` output
  path.
- Private-mode errors must NOT print raw exceptions, input/output
  path/basename, raw JSON, or label text. The fixed sanitized error is:
  `error: failed to load private true labels (schema/privacy/parse
  error; details suppressed)`.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d4b_dual_rubric_true_label_smoke/d4b_dual_rubric_true_label_smoke_report.json`
is the public harness / no-labels artifact. Identity / boundary fields:

- `schema_version` = `d4b_dual_rubric_true_label_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `rubric_version`,
  `status`, `mode`, `phase`
- `d3_protocol_checked=true`, `d3_protocol_version=
  d3_true_dual_rubric_label_protocol_v1`, `d3_required_gates_present=true`
- Default false flags (all false): `labels_collected`,
  `true_label_bundle_read`, `true_label_bundle_validated`,
  `true_label_bundle_persisted`,
  `local_private_true_label_smoke_executed`,
  `calibration_metrics_computed`, `inter_rater_agreement_measured`,
  `confidence_intervals_computed`, `true_e_s_calibration_claimed`,
  `public_release_gate_passed`, `real_label_bundle_gate_passed`,
  `raw_label_rows_emitted`, `private_input_path_emitted`,
  `private_output_path_emitted`, `private_output_committed`,
  `exact_private_counts_emitted`, `synthetic_labels_accepted_as_true`,
  `proxy_labels_accepted_as_true`, `llm_labels_accepted_as_true`,
  `model_assisted_labels_allowed`.
- Harness/control flags (exactly these five, all true):
  `private_execution_harness_available`, `private_cli_guard_validated`,
  `tmp_output_resolved_guard_validated`, `sanitized_error_guard_validated`,
  `bundle_schema_contract_defined`.
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
  `min_rater_count=2`, `agreement_required=true`,
  `confidence_intervals_required=true`.
- `gate_category_names`: `primary_evidence`, `dependency_support`,
  `weak_candidates`, `abstained`.
- `bundle_schema_contract`: the local-only true-label bundle contract
  (schema `d4b_true_label_bundle_v1`, required
  `label_source=human_manual_true_e_s`, rejected sources
  `proxy`/`synthetic`/`llm`/`model_assisted`, allowed bundle/label keys,
  E/S levels, bucket names).
- `private_execution_harness`: `/tmp`-only, opt-in, not committed, no
  calibration claim.
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Private true-label bundle contract (local-only)

A real local private true-label bundle is a JSON object whose `labels`
are human/manual true E/S annotations. The loader rejects IDs/paths/
snippets/rater IDs/raw row metadata/unknown keys rather than supporting
and stripping them. Allowed bundle keys only:

- `schema` = `d4b_true_label_bundle_v1`
- `label_source` = `human_manual_true_e_s` (exactly; `proxy`/`synthetic`/
  `llm`/`model_assisted` are rejected as true labels)
- `rater_count` (int >= 2)
- `agreement_available`, `confidence_intervals_available` (booleans)
- `labels` (list of label objects)

Each label object must have ONLY these six keys:

- `e_score` in `E0`/`E1`/`E2`
- `s_score` in `S0`/`S1`/`S2`
- `bucket` in `primary_evidence`/`dependency_support`/`weak_candidates`/
  `abstained`
- `citation_valid`, `rater_pair_present`, `adjudicated` (booleans)

Any key outside these allowlists (e.g. `rater_id`, `raw_label`,
`annotation_row`, `path`, `task_id`, `snippet`) fails fail-closed. If
malformed, the fixed sanitized error is:
`error: failed to load private true labels (schema/privacy/parse error;
details suppressed)`.

## Private output rules (bands only, never exact counts)

Private smoke output JSON is `/tmp` only and never committed. It must
NOT contain: input/output paths or basenames, label rows, IDs, paths,
snippets, raw E/S rows, rater IDs, annotation rows, row hashes,
prompts/responses/model outputs, or exact real private counts. Because
the bundle INPUT contract uses a `labels` key, no OUTPUT may emit a
`labels` key (the forbidden scanner rejects it).

Instead of exact counts, the private output emits bands and gate
booleans only:

- `label_count_band`: `min_n_met` (>= 50 labels) / `below_min_n` (< 50).
- `bucket_count_bands`: per fixed bucket, `k_met` (count >= k_min=5) /
  `below_k` (0 < count < k_min, small cell suppressed) / `suppressed`
  (count == 0, empty cell suppressed).
- `gate_results`: booleans for min-N / bucket-cell / second-rater /
  agreement / CI / overall.
- `input_attestation_required=true`.
- `synthetic_harness_test=true` and
  `local_private_true_label_smoke_executed=false` for synthetic /
  in-memory harness self-tests (even if the bundle is human-manual-
  shaped). A real local private run (no synthetic flag,
  `label_source=human_manual_true_e_s`, valid schema) may set
  `local_private_true_label_smoke_executed=true` locally only (never
  committed).

## Gate logic (over a validated human-manual bundle)

D4b evaluates gate thresholds over a validated human-manual bundle. It
does NOT compute calibration metrics, inter-rater agreement, or
confidence intervals. Gates (constants from D3):

- min-N: `len(labels) >= 50` (`min_total_labels`).
- small-cell suppression: every fixed bucket cell `n >= k_min` (5); any
  cell below 5 fails/suppresses (band `below_k`); an empty cell is
  `suppressed`.
- second rater required: `rater_count >= 2`.
- agreement required: `agreement_available` is true.
- confidence intervals required: `confidence_intervals_available` is
  true.
- all conditions satisfied => overall gate pass.

The public artifact may include only gate category names, thresholds,
booleans, bands, and synthetic self-test aggregate pass/fail counts. It
must NOT include real private sample sizes or label rows from any
private input.

## Forbidden scanner (fail-closed)

A strict forbidden-output scanner runs fail-closed before writing any
JSON. Rejects forbidden dict keys (`task_id`, `repo_id`, `repo`, `path`,
`span`, `line_range`, `start_line`, `end_line`, `content_sha`, `snippet`,
`candidate_text`, `query`, `prompt`, `response`, `model_output`,
`label`, `labels`, `raw_label`, `annotation_row`, `rater_id`,
`annotator_id`, `disagreement_example`, `per_row_hash`, etc.) anywhere,
and rejects value patterns: ANY URL (no URL allowlist), 32/40/64-char
hex digests, secret-like strings, path-like `src/foo.py` and
`/private/foo.jsonl`, multiline strings, raw JSON fragments, raw line
ranges `12-34`, and the self-test sentinel. Allows safe gate/protocol/
band strings (`primary_evidence`, `k_min`, `D4b`, `min_n_met`,
`d3_true_dual_rubric_label_protocol_v1`, etc.).

## Self-tests

- All default false/true flags as above (default artifact no labels, no
  read, no metrics, no claims; the five harness flags true).
- D3 protocol constants/gates checked (`k_min=5`,
  `min_total_labels=50`, `min_rater_count=2`, agreement/CI required).
- Bundle schema contract defined; proxy/synthetic/llm/model_assisted
  label sources rejected as true labels.
- CLI guard matrix including validate-before-read, committed-out
  rejected before read, non-`/tmp` rejected before read,
  `--synthetic-harness-test` without allow rejected.
- Resolved `/tmp` symlink-escape rejection (parent symlink escape and
  existing output file symlink).
- Sanitized error with sensitive basename + `SECRET_LABEL_SENTINEL`:
  no leak in stdout/stderr/output.
- Valid synthetic human-manual-shaped bundle accepted only as a harness
  test (`synthetic_harness_test=true`,
  `local_private_true_label_smoke_executed=false`).
- Proxy/synthetic/LLM source rejected as true-label smoke.
- Invalid bundle with task_id/path/snippet/rater_id/raw_label/unknown
  keys rejected.
- Missing second rater fails; N<50 fails; bucket cell<5 fails/suppresses
  (band `below_k`); empty bucket suppressed (band `suppressed`);
  missing CI/agreement fails; all gates pass for a valid synthetic
  human-manual-shaped bundle.
- Private output has no label rows, IDs, paths, basenames, raw E/S rows,
  exact counts, or `labels` key.
- Forbidden scanner fail-closes and generation refuses success if
  self-test fails.

## Validation

```text
python3 -m py_compile eval/d4b_dual_rubric_true_label_smoke.py    => PASS
python3 eval/d4b_dual_rubric_true_label_smoke.py --self-test      => PASS (206/206 checks)
python3 eval/d4b_dual_rubric_true_label_smoke.py \
  --out artifacts/d4b_dual_rubric_true_label_smoke/\
d4b_dual_rubric_true_label_smoke_report.json                     => PASS
  (status: blocked_no_true_label_bundle_available,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, true_label_bundle_read: false,
   true_label_bundle_validated: false,
   local_private_true_label_smoke_executed: false,
   private_output_committed: false,
   calibration_metrics_computed: false,
   true_e_s_calibration_claimed: false,
   synthetic_labels_accepted_as_true: false,
   proxy_labels_accepted_as_true: false,
   llm_labels_accepted_as_true: false,
   model_assisted_labels_allowed: false,
   public_release_gate_passed: false,
   real_label_bundle_gate_passed: false,
   private_execution_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   bundle_schema_contract_defined: true,
   mode: public_harness_no_labels, phase: D4b,
   rubric_version: d3_true_dual_rubric_label_protocol_v1)
/tmp private smoke (synthetic human-manual-shaped bundle)       => PASS
  (synthetic_harness_test=true,
   local_private_true_label_smoke_executed=false,
   no input/output path, basename, raw label, sentinel, exact
   counts, or labels key in output/stdout/stderr)
/tmp private smoke (real-mode flag-path test over synthetic fixture)
                                                                 => PASS
  (synthetic_harness_test=false,
   local_private_true_label_smoke_executed=true locally only,
   true_label_bundle_read=true, true_label_bundle_validated=true,
   NOT committed)
CLI guard matrix (missing allow/input/out, committed out,
  non-/tmp out, synthetic without allow)                        => PASS (all exit 2)
Resolved /tmp symlink-escape guard (parent symlink,
  existing output file symlink)                                 => PASS (exit 2)
python3 scripts/validate_docs_i18n.py                            => PASS
git diff --check                                                 => PASS
```

## Caveats

- D4b is the true-label smoke harness public artifact only. It is
  eval/diagnostic only. It does NOT change runtime, retriever, pack,
  model, backend, or default policy; it does NOT change EvidenceCore
  semantics. It is NOT a benchmark result, NOT a downstream agent value
  claim, NOT a runtime-clean general algorithm claim, NOT an OOD
  temporal claim, and NOT a QuIVer systems claim.
- D4b default is blocked / no-labels. The default committed artifact
  collects NO labels, reads NO true-label bundles, validates NO bundle
  as true labels, computes NO calibration metrics, measures NO
  inter-rater agreement, claims NO true/proxy calibration, and passes NO
  public-release / real-bundle gate. Harness/control flags are true only
  for the validated harness/controls, NOT for any real calibration.
- Synthetic/proxy/LLM labels are NOT accepted as true labels. They may
  appear only in self-tests and optional private-mode harness tests,
  with `local_private_true_label_smoke_executed=false`.
- The private smoke mode is `/tmp` only and NEVER committed. It
  validates a local/private true-label-bundle-shaped JSON only to
  validate shape/gates; it does NOT compute or claim true calibration
  metrics. A real local private run may set
  `local_private_true_label_smoke_executed=true` locally only, and then
  truthfully records `true_label_bundle_read=true` and
  `true_label_bundle_validated=true` in that local-only output. The
  validation command above uses a synthetic fixture to test this flag
  path; it is NOT public evidence that real human labels exist.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; the five harness/control flags are the only true control
  flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was NOT updated (D4b is a
  harness/blocked artifact; no conclusions change).
