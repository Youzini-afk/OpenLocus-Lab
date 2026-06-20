# D5-A0 Automated E/S Calibration Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

D5-A0 is the **first empirical, post-control-plane smoke** of the Step 6
dual-rubric pipeline. It uses the **existing committed r14 sanity
fixtures** (`fixtures/r14/tasks/sanity.jsonl` +
`fixtures/r14/labels/sanity.jsonl`) and **real OpenLocus retrieval
outputs** produced transiently into `/tmp` (never committed) to compute
**automated E/S calibration smoke** aggregate metrics over the four
fixed retrieval methods (regex, bm25, symbol, rrf).

D5-A0 is the empirical pivot after the D4-series control-plane harnesses
were blocked on missing real human/manual true E/S labels. The previous
trajectory over-required new manual labels as a global blocker; D5-A0
stops the control-plane-only stages and produces empirical results by
deriving **automated E labels** and **deterministic S-proxy labels**
from the existing committed span labels (gold spans + hard negatives)
already in the r14 sanity fixture. No new human labels are collected.

The D5-A automated/programmatic empirical path is active (this smoke).
The D5-H / human-reference / human-calibrated path remains out of scope
until human labels exist; D5-A0 does not unlock default, policy,
public-release, or human-calibrated claims.

D5-A0 **does not** collect new human/manual labels, **does not** claim
true E/S calibration, **does not** audit human reference labels, **does
not** pass any public-release gate, **does not** promote any candidate,
**does not** unblock D5-H / human-reference / human-calibrated claims,
**does not** unblock default/policy/public-release or human-calibrated
claims, **does not** change runtime behavior, retriever, pack, model,
backend, default policy, or EvidenceCore semantics. D5-A0 **does not**
commit raw predictions, raw retrieval outputs, per-candidate rows,
paths, spans, snippets, content hashes, queries, gold labels,
hard-negative labels, repo IDs, task IDs, or any row-level data.

- Claim level: `automated_e_s_calibration_smoke_only`.
- Status: `automated_es_calibration_smoke_pass` on success; mode
  `public_aggregate_r14_retrieval_smoke`; phase `D5-A0`.
- D5-A0 is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  a downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

### D4-series -> D5-A0 relation

```text
D4-series control-plane harnesses (D4a-D4f + D4-rollup)
-> D5-H / human-reference / human-calibrated path out of scope until human labels
-> D5-A0 automated E/S calibration smoke over existing r14 sanity labels
   (D5-A automated empirical path active; uses existing committed labels;
    no new human labels; no true E/S calibration claim;
    does NOT unlock default/policy/public-release/human-calibrated claims)
```

D5-A0 is NOT D5-H. The D5-H / human-reference / human-calibrated audit
remains out of scope/unavailable until real human/manual true E/S labels
are collected; the D5-A automated/programmatic empirical path is active
and continues. D5-A0 only produces the first empirical smoke by
deriving automated E/S labels from the existing committed span labels
(which were originally collected for span-recall metrics, not for true
E/S rubric scoring). D5-A0 is therefore a smoke, not a calibration,
and does not unlock default/policy/public-release or human-calibrated
claims.

## Automated E label procedure

The automated E label is derived deterministically from the existing
committed r14 sanity span labels (gold spans + hard negatives). It is
NOT a true human E-score and is NOT the D3 dual-rubric E-score.

Procedure per candidate (candidate = one EvidenceCore row from a real
OpenLocus retrieval output):

1. **invalid / source-missing** candidate (no `path`, or no valid
   `1 <= start_line <= end_line`) -> `e_uncertain`.
2. **overlap hard-negative AND gold** (same path AND line overlap with
   both a hard-negative span and a gold span) -> `conflict_uncertain`.
3. **overlap hard-negative only** -> `e_hard_negative`.
4. **overlap gold** -> `e_positive`.
5. **same gold file but no gold overlap** (candidate path matches a
   gold file path but the candidate lines do not overlap any gold
   span) -> `e_wrong_span_gold_file`.
6. **non-gold file with valid span** -> `e_negative_non_gold_file`.
7. **missing labels** are NEVER treated as negatives; a candidate with
   no labels for its task falls through to the path-based cases above
   (or `e_uncertain` if invalid).

E label categories: `e_positive`, `e_hard_negative`,
`conflict_uncertain`, `e_wrong_span_gold_file`,
`e_negative_non_gold_file`, `e_uncertain`.

## S-proxy label procedure

The S-proxy label is a **deterministic support-shape signal**, NOT a
true human S-score and NOT the D3 dual-rubric S-score. It is conservative:
positive only for deterministic support-shape signals.

Procedure per candidate:

1. **E-positive** -> `s_proxy_not_evaluated_for_e_positive` (do not
   conflate E-positive with S-positive support).
2. **E-hard-negative / conflict-uncertain / e-uncertain** ->
   `s_proxy_none` (do not conflate hard-negative or invalid shape with
   positive support).
3. **e_wrong_span_gold_file** -> `s_proxy_positive` (same gold file
   support shape).
4. **adjacency to a gold span on the same gold file** (within +/-5
   lines of a gold span boundary, no overlap) -> `s_proxy_positive`
   (deterministic adjacency support shape; no distances emitted).
5. **otherwise** -> `s_proxy_none`.

S-proxy categories: `s_proxy_positive`, `s_proxy_none`,
`s_proxy_uncertain`, `s_proxy_not_evaluated_for_e_positive`.
`s_proxy_uncertain` is defined for completeness; the conservative
procedure does not emit it in the current smoke.

## CLI

```bash
python3 -m py_compile eval/d5a_automated_es_calibration.py
python3 eval/d5a_automated_es_calibration.py --self-test
python3 eval/d5a_automated_es_calibration.py \
    --out artifacts/d5a_automated_es_calibration/\
d5a_automated_es_calibration_report.json
# CLI overrides (defaults: committed r14 sanity fixtures + target/debug/openlocus):
python3 eval/d5a_automated_es_calibration.py \
    --tasks fixtures/r14/tasks/sanity.jsonl \
    --labels fixtures/r14/labels/sanity.jsonl \
    --openlocus target/debug/openlocus \
    --cwd . \
    --candidate-limit 50 \
    --out /tmp/d5a_smoke_report.json
```

Default mode: writes the committed public aggregate-only artifact
(default out path if `--out` omitted). The default mode invokes
`eval/run_retrieval.py` per method into a transient `/tmp/d5a_retrieval_*`
directory and reads those transient outputs (never committed).

CLI arguments: `--self-test`, `--out`, `--tasks`, `--labels`,
`--openlocus`, `--cwd`, `--candidate-limit`. Unknown/private-looking
arguments are rejected with a generic `invalid arguments` message that
does not echo private paths or basenames (SafeArgumentParser pattern).

`--self-test` runs synthetic in-memory predictions/labels with no
external openlocus required; it covers all span overlap cases, the
conflict case, S-proxy cases, the forbidden scanner (rejects + allows),
no-claim flag invariants, and aggregate denominator consistency.

### Guard requirements

1. Default mode reads the committed r14 sanity fixtures (existing
   committed labels; no new human labels collected).
2. Retrieval outputs are produced transiently under `/tmp` only and
   are never committed (`raw_retrieval_outputs_committed=false`,
   `transient_retrieval_outputs_only=true`).
3. The committed artifact contains ONLY aggregate counts/rates; no
   per-candidate rows, no paths, no spans, no snippets, no content_sha,
   no queries, no gold labels, no hard-negative labels, no task/repo
   IDs, no row-level data.
4. Strict fail-closed forbidden scanner runs immediately before writing
   the JSON artifact (`_enforce_no_forbidden`).
5. Self-test failure refuses successful artifact generation
   (`_refuse_on_self_test_failure`).

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d5a_automated_es_calibration/d5a_automated_es_calibration_report.json`
is the public aggregate-only smoke artifact. Identity / boundary
fields:

- `schema_version` = `d5a_automated_es_calibration.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- Safe true flags (exactly these, all true):
  `aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`,
  `automated_e_s_calibration_smoke_claimed`,
  `automated_d5a_path_active`, `uses_existing_committed_labels`,
  `self_test_executed`, `transient_retrieval_outputs_only`.
- No-claim / no-runtime-change flags (all false):
  `automated_e_s_calibration_claimed`,
  `human_e_s_calibration_claimed`, `new_human_labels_collected`,
  `human_reference_audit_claimed`, `promotion_ready`,
  `default_should_change`, `evidencecore_semantics_changed`,
  `runtime_clean_general_algorithm_claimed`,
  `downstream_agent_value_proven`,
  `external_benchmark_performance_claimed`,
  `runtime_behavior_changed`, `retriever_changed`,
  `pack_builder_changed`, `model_calls_changed`, `backend_changed`,
  `default_policy_changed`, `true_e_s_calibration_claimed`,
  `raw_predictions_committed`, `raw_retrieval_outputs_committed`,
  `per_candidate_rows_emitted`, `public_release_gate_passed`,
  `d5_human_reference_calibration_unblocked`, `ood_temporal_supported`,
  `quiver_systems_supported`.
- `input_summary`: `fixture_name` (`r14_sanity`), `task_count`,
  `label_source_category_counts` (aggregate counts by
  `label_quality`), `methods_evaluated` (`[regex, bm25, symbol, rrf]`).
  Label-source category keys are explicit buckets only:
  `human_reviewed`, `mined`, `mined_high_confidence`, `unknown`, and
  the collapsed fallback `other_unapproved_label_source_category`.
  Unapproved row-derived category strings are never emitted as public
  artifact keys.
- `retrieval_summary`: `methods_attempted`, `methods_succeeded`,
  `candidate_count_total`, `retrieval_invocation`
  (`run_retrieval_subprocess`), `retrieval_output_location`
  (`tmp_only_transient`), `raw_retrieval_outputs_committed=false`.
- `automated_label_summary`: `candidates_labeled_total`,
  `candidates_unlabeled_total` (always 0), `e_label_categories`,
  `s_proxy_label_categories`, `e_label_category_counts`,
  `s_proxy_label_category_counts`, aggregate E label rates, and
  S-proxy rates.
- `method_aggregate_metrics`: per-method list of dicts with
  `candidates_seen`, per-category counts, per-category rates, and a
  `denominators` object (`candidate_total`, `e_label_denominator`,
  `s_label_denominator`). No per-candidate rows, no paths, no spans.
- `e_label_categories` and `s_proxy_label_categories` are EXACT
  contract containers (short-token allowlists only).
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys (`task_id`, `repo_id`, `repo`,
`path`, `file`, `span`, `start_line`, `end_line`, `content_sha`,
`snippet`, `candidate_text`, `query`, `query_text`, `prompt`,
`response`, `model_output`, `label`, `labels`, `raw_label`,
`annotation_row`, `rater_id`, `annotator_id`, `packet_ref`,
`packet_id`, `private_record_ref`, `candidate_ref`, `candidate`,
`per_row_hash`, `row_hash`, `provider_payload`, `api_key`,
`agreement_metric`, `kappa`, `confidence_interval`, `ci_value`,
`ci_lower`, `ci_upper`, `gold`, `gold_span`, `gold_spans`,
`hard_negative`, `hard_negatives`, `evidence`, `candidate_row`,
`predictions`, `retrieval_output`, `retrieval_outputs`, etc.) anywhere,
and rejects value patterns: ANY URL (no URL allowlist), 32/40/64-char
hex digests, secret-like strings, path-like `src/foo.rs` and
`/private/foo.jsonl`, multiline strings, raw JSON fragments, raw line
ranges `12-34`, and the self-test sentinel.

Contract containers (`methods_evaluated`, `methods_attempted`,
`methods_succeeded`, `e_label_categories`, `s_proxy_label_categories`)
are **exact string allowlists**: only approved short tokens (method
names `regex`/`bm25`/`symbol`/`rrf`, the fixture category `r14_sanity`,
E label category tokens, S-proxy category tokens, and the retrieval
category tokens `run_retrieval_subprocess`/`tmp_only_transient`) may
appear there. Arbitrary short strings (e.g. `compute_loss` or private
text) are rejected **even inside** contract containers (no over-broad
container exemption); sensitive field names (`content_sha`,
`query_text`, `candidate`, `gold`, `hard_negative`, `evidence`,
`predictions`, `retrieval_output`, etc.) are rejected even inside
contract containers and as keys anywhere.

`label_source_category_counts` is also key-allowlisted: approved
committed fixture metadata categories may be counted as keys, while any
unapproved category collapses to `other_unapproved_label_source_category`
before public artifact emission. The scanner rejects unapproved dynamic
keys under that count container.

The scanner runs ONLY against the final public aggregate artifact. The
internal raw predictions (which contain `path`/`start_line`/`end_line`/
`content_sha`/`query`/etc.) are read transiently into memory, never
scanned, and never committed.

## Self-tests

- Artifact identity fields (schema, claim, status, mode, phase,
  generated_by).
- Safe true flags (all true); no-claim / no-runtime-change false flags
  (all false).
- Automated E label procedure: gold overlap -> `e_positive`;
  hard-negative overlap -> `e_hard_negative`; conflict overlap (gold AND
  hard-negative) -> `conflict_uncertain`; same-gold-file wrong span ->
  `e_wrong_span_gold_file`; non-gold file -> `e_negative_non_gold_file`;
  invalid / source-missing / bad line range -> `e_uncertain`; missing
  labels never treated as negatives.
- S-proxy label procedure: E-positive ->
  `s_proxy_not_evaluated_for_e_positive`; `e_wrong_span_gold_file` ->
  `s_proxy_positive`; adjacency to gold span -> `s_proxy_positive`;
  `e_hard_negative`/`conflict_uncertain`/`e_uncertain` ->
  `s_proxy_none`; non-gold file far from gold -> `s_proxy_none`.
- Aggregate denominator consistency: E label rates sum to 1.0 (modulo
  float rounding) when denom > 0; E counts sum to `candidates_seen`; S
  counts sum to `candidates_seen`; `candidates_seen` matches all three
  denominators.
- Forbidden scanner rejects: all forbidden dict keys; URL value;
  32/40/64-char hex digest values; secret sentinel value; secret-like
  value; path-like value; leading-slash path value; jsonl path value;
  multiline value; raw JSON fragment value; line range value; colon
  line range value; unapproved string in contract container; sensitive
  field name in contract container; URL in contract container.
- Forbidden scanner allows: approved method tokens inside
  `methods_evaluated`; approved E label tokens inside
  `e_label_categories`; approved S-proxy tokens inside
  `s_proxy_label_categories`.
- Label-source key hardening: approved `mined` is preserved;
  unapproved label-quality sentinels collapse to a fixed fallback and
  are not emitted; scanner rejects unapproved dynamic keys under
  `label_source_category_counts`.
- Fail-closed generation: clean public report does not raise; leaked
  public report raises SystemExit; self-test failure refuses artifact
  generation (raises when failed, does not raise when passed); failed
  self-test does not carry success status.
- Public artifact self-scan is clean (no forbidden key anywhere).
- CLI argument surface: `--self-test`, `--out`, `--tasks`, `--labels`,
  `--openlocus`, `--cwd`, `--candidate-limit` are the only options
  (plus `-h`/`--help`).

## Validation

```text
python3 -m py_compile eval/d5a_automated_es_calibration.py    => PASS
python3 eval/d5a_automated_es_calibration.py --self-test      => PASS (157/157 checks)
python3 eval/d5a_automated_es_calibration.py \
  --out artifacts/d5a_automated_es_calibration/\
d5a_automated_es_calibration_report.json                     => PASS
  (status: automated_es_calibration_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_r14_retrieval_smoke, phase: D5-A0,
   methods_succeeded: [regex, bm25, symbol, rrf],
   candidate_count_total: 3152,
   uses_existing_committed_labels: true,
   automated_d5a_path_active: true,
   new_human_labels_collected: false,
   human_e_s_calibration_claimed: false,
   automated_e_s_calibration_claimed: false,
   raw_retrieval_outputs_committed: false,
   per_candidate_rows_emitted: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   model_calls_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   runtime_clean_general_algorithm_claimed: false,
   downstream_agent_value_proven: false,
   external_benchmark_performance_claimed: false,
   d5_human_reference_calibration_unblocked: false,
   public_release_gate_passed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## Caveats

- D5-A0 is the public aggregate-only smoke artifact. It is
  eval/diagnostic only. It does NOT change runtime, retriever, pack,
  model, backend, or default policy; it does NOT change EvidenceCore
  semantics. It is NOT a benchmark result, NOT a downstream agent value
  claim, NOT a runtime-clean general algorithm claim, NOT an OOD
  temporal claim, and NOT a QuIVer systems claim.
- D5-A0 uses the existing committed r14 sanity labels (gold spans +
  hard negatives) to derive **automated E labels** and **deterministic
  S-proxy labels**. These are NOT true human/manual E/S scores and are
  NOT the D3 dual-rubric E/S scores. They are smoke-only aggregate
  signals derived from existing committed span labels.
- D5-A0 does NOT collect new human/manual labels, does NOT audit human
  reference labels, does NOT claim true E/S calibration, does NOT pass
  any public-release gate, and does NOT unblock D5-H / human-reference
  / human-calibrated claims or default/policy/public-release claims.
  The D5-H / human-reference / human-calibrated audit remains out of
  scope/unavailable until real human/manual true E/S labels are
  collected; the D5-A automated empirical path is active and continues.
- D5-A0 invokes `eval/run_retrieval.py` per method into transient
  `/tmp/d5a_retrieval_*` directories and reads those transient outputs
  (never committed). The committed artifact contains ONLY aggregate
  counts/rates; no per-candidate rows, no paths, no spans, no snippets,
  no content_sha, no queries, no gold labels, no hard-negative labels,
  no task/repo IDs, no row-level data.
- The aggregate metrics are smoke-only and depend on (a) the existing
  committed r14 sanity fixture shape (gold spans + hard negatives), (b)
  the four fixed retrieval methods (regex, bm25, symbol, rrf), and (c)
  the deterministic E/S label procedures documented above. They are NOT
  comparable across different fixtures, label sets, methods, or
  procedures, and they are NOT benchmark performance claims.
- `e_uncertain` is emitted only for invalid/source-missing candidates;
  in the current r14 sanity smoke, all retrieval outputs are
  structurally valid, so `e_uncertain_count=0` is expected. This does
  NOT mean every candidate is correct; it means every candidate has a
  valid path and line range.
- `s_proxy_uncertain` is defined for completeness but is not emitted by
  the conservative procedure in the current smoke.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; the smoke-claimed / uses-existing-labels /
  D5-A-path-active flags
  (`automated_e_s_calibration_smoke_claimed`,
  `automated_d5a_path_active`, `uses_existing_committed_labels`,
  `self_test_executed`, `transient_retrieval_outputs_only`) are the
  only additional true flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was updated to clarify that
  D5-H / human-reference / human-calibrated calibration remains out of
  scope until human labels while the D5-A automated empirical path is
  active; no promotion/default/runtime claims change.
