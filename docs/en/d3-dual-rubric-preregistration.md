# D3 Dual-Rubric Label Protocol Preregistration (Protocol Only)

## Scope and claim boundary

D3 is the **protocol-only** preregistration of the future true E-score /
S-score label collection and calibration protocol. It is the bridge
between D1 (deterministic dual-rubric relevance scaffold) and D2 (proxy
mappability), and a later D4 local/private true E/S calibration run.

D3 **preregisters** the protocol. It does NOT collect labels, does NOT
read private records, does NOT compute calibration metrics, does NOT
measure inter-rater agreement, does NOT claim true E/S calibration, does
NOT claim proxy calibration, and does NOT collect model-assisted labels.

- Claim level: `dual_rubric_label_protocol_preregistration_only`.
- Rubric version: `d3_true_dual_rubric_label_protocol_v1`.
- Status: `protocol_ready_no_labels_collected`; mode `protocol_only`.

D3 is **eval/diagnostic protocol only**. It does NOT change runtime
behavior, retriever ranking, pack construction, model calls, backend
storage, default policy, or EvidenceCore semantics. It is NOT a benchmark
result, NOT a downstream agent value claim, NOT a runtime-clean general
algorithm claim, NOT an OOD temporal claim, and NOT a QuIVer systems
claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D3 emits no EvidenceCore records and changes none of its
  semantics.
- D3 collects no labels: `labels_collected=false`,
  `calibration_metrics_computed=false`,
  `inter_rater_agreement_measured=false`.
- D3 reads no private records: `private_records_read=false`,
  `raw_private_records_read=false`,
  `private_records_persisted=false`.
- D3 claims no calibration: `true_e_s_calibration_claimed=false`,
  `proxy_calibration_claimed=false`,
  `model_assisted_labels_collected=false`.

## CLI

D3 is protocol-only and accepts no private input. There is **no**
`--input` argument and no `--allow-private-records` flag.

```bash
python3 -m py_compile eval/d3_dual_rubric_preregistration.py
python3 eval/d3_dual_rubric_preregistration.py --self-test
python3 eval/d3_dual_rubric_preregistration.py \
    --out artifacts/d3_dual_rubric_preregistration/\
d3_dual_rubric_preregistration_report.json
```

## Artifact sections (all category-only, aggregate/protocol only)

The committed artifact at
`artifacts/d3_dual_rubric_preregistration/d3_dual_rubric_preregistration_report.json`
is protocol-only. Identity / boundary fields:

- `schema_version` = `d3_dual_rubric_preregistration.v1`
- `generated_by`, `generated_at`, `claim_level`, `rubric_version`,
  `status`, `mode`
- Label-protocol false flags (all false): `labels_collected`,
  `private_records_read`, `raw_private_records_read`,
  `private_records_persisted`, `true_e_s_calibration_claimed`,
  `proxy_calibration_claimed`, `model_assisted_labels_collected`,
  `inter_rater_agreement_measured`, `calibration_metrics_computed`.
- No-claim / no-runtime-change flags (all false): `promotion_ready`,
  `default_should_change`, `downstream_agent_value_proven`,
  `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`,
  `model_calls_changed`, `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`,
  `runtime_clean_general_algorithm_claimed`, `ood_temporal_supported`,
  `quiver_systems_supported`.
- Diagnostic flags (all true): `aggregate_only_public_artifact`,
  `diagnostic_only`, `not_evidence`.

### sampling_frame_protocol

- `eligible_record_sources` = `["local_private_p21_records",
  "local_private_d2b_proxy_smoke_candidates"]` (category labels only; no
  filesystem paths).
- `sampling_axes` = `["proxy_bucket", "proxy_e_band", "proxy_s_band",
  "abstain_or_unmappable_status"]`.
- `stratification_required=true`.
- `max_records_per_batch_local_only=50`.
- `raw_record_material_private_only=true`.

### annotation_rubric

- `e_score_levels`: `E0` (no semantic/direct-answer evidence), `E1`
  (weak or partial), `E2` (strong, valid citation).
- `s_score_levels`: `S0` (no dependency/support-structure evidence),
  `S1` (weak or partial), `S2` (strong).
- `definitions`: abstention gate (citation validity/staleness/uncited/
  no-evidence fires before E/S bucket assignment), E/S ordinal scales.
- `bucket_mapping`: `primary_evidence` (E2 with valid citation),
  `dependency_support` (S2 with E below E2), `weak_candidates`
  (nonzero E or S below high thresholds), `abstained` (no evidence or
  abstention gate fired).
- `abstract_examples`: approved abstract category strings ONLY —
  `direct_definition_of_requested_symbol`,
  `caller_import_relation_without_answer_bearing_text`,
  `same_module_but_insufficient_evidence`. No concrete repo/path/snippet
  content. The self-test enforces that examples EXACTLY match this
  approved enum; unapproved concrete/path-like examples fail validation
  AND the forbidden scanner.

### future_execution_gates

D4 is a separate gated phase. To execute true E/S label collection, all
gates must hold:

- `explicit_private_opt_in_required=true`.
- `local_output_path_required=true`; `output_location_category=
  tmp_only_local_private`.
- `no_committed_raw_labels=true`.
- `k_min=5`.
- `min_total_labels=50`.
- `inter_rater_agreement_required=true`.
- `agreement_metrics_aggregate_only=["cohens_kappa",
  "krippendorff_alpha"]` (aggregate-only metrics).
- `confidence_intervals_required=true`.

### public_release_thresholds

- `min_total_n=50`.
- `k_min_per_cell=5`.
- `small_cell_policy="suppress_or_merge_to_other"`.
- `confidence_intervals_required=true`.
- `per_row_raw_label_outputs=false`.

### privacy_contract

- `no_task_ids=true`, `no_repo_ids_or_names=true`, `no_file_paths=true`,
  `no_spans_or_line_ranges=true`, `no_snippets_or_excerpts=true`,
  `no_content_hashes=true`, `no_prompts_or_responses=true`,
  `no_model_outputs=true`, `no_private_labels=true`,
  `no_raw_annotation_rows=true`, `no_per_row_hashes=true`,
  `no_local_filesystem_paths=true`.
- `forbidden_field_categories` lists the forbidden field names
  (`task_id`, `repo_id`, `repo`, `path`, `span`, `line_range`,
  `start_line`, `end_line`, `content_sha`, `snippet`, `excerpt`,
  `candidate_text`, `query`, `prompt`, `response`, `model_output`,
  `label`, `raw_label`, `annotation_row`, `per_row_hash`,
  `local_filesystem_path`).

### phase_graph

D1..D6 as category strings only (no execution data):

- D1 `dual_rubric_relevance_scaffold`
- D2 `dual_rubric_proxy_aggregate_calibration`
- D3 `dual_rubric_label_protocol_preregistration`
- D4 `local_private_true_e_s_calibration_execution_gated`
- D5 `aggregate_calibration_release_candidate_gated`
- D6 `runtime_integration_decision_gated`

### forbidden_scan summary

A strict forbidden-output scanner runs fail-closed before the JSON
artifact is written. It rejects forbidden dict keys (path/span/
content_sha/snippet/query/task_id/repo_id/repo/label/raw_label/
annotation_row/per_row_hash/model_output/etc.) anywhere, and rejects
value patterns: ANY URL (no URL allowlist), 32/40/64-char hex digests,
secret-like strings, path-like `src/foo.py` and `/private/foo.jsonl`,
multiline strings, raw JSON fragments, and raw line ranges `12-34`. It
allows safe protocol strings (`local_private_p21_records`,
`proxy_bucket`, `E0`, etc.).

## No-claim / safety flags

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
- `labels_collected=false`, `private_records_read=false`,
  `raw_private_records_read=false`, `private_records_persisted=false`,
  `true_e_s_calibration_claimed=false`, `proxy_calibration_claimed=false`,
  `model_assisted_labels_collected=false`,
  `inter_rater_agreement_measured=false`,
  `calibration_metrics_computed=false`.

## Validation

```text
python3 -m py_compile eval/d3_dual_rubric_preregistration.py           => PASS
python3 eval/d3_dual_rubric_preregistration.py --self-test            => PASS (96/96 checks)
python3 eval/d3_dual_rubric_preregistration.py \
  --out artifacts/d3_dual_rubric_preregistration/\
d3_dual_rubric_preregistration_report.json                            => PASS
  (status: protocol_ready_no_labels_collected,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, private_records_read: false,
   true_e_s_calibration_claimed: false, proxy_calibration_claimed: false,
   calibration_metrics_computed: false,
   inter_rater_agreement_measured: false,
   model_assisted_labels_collected: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

## Caveats

- D3 is protocol-only preregistration. It is eval/diagnostic only. It
  does NOT change runtime, retriever, pack, model, backend, or default
  policy; it does NOT change EvidenceCore semantics. It is NOT a
  benchmark result, NOT a downstream agent value claim, NOT a
  runtime-clean general algorithm claim, NOT an OOD temporal claim, and
  NOT a QuIVer systems claim.
- D3 collects NO labels, reads NO private records, computes NO
  calibration metrics, measures NO inter-rater agreement, claims NO
  true E/S calibration, claims NO proxy calibration, and collects NO
  model-assisted labels. D3 is a *preregistration* of the protocol
  only.
- D4 is the first phase that MAY execute local/private true E/S
  calibration, and only if all `future_execution_gates` hold. D3 does
  not gate or trigger D4 automatically; D4 requires a separate explicit
  decision.
- Public release of any future calibration output requires
  `min_total_n=50`, `k_min_per_cell=5`, small-cell suppression
  (`suppress_or_merge_to_other`), confidence intervals, and
  `per_row_raw_label_outputs=false`.
- Any examples in D3 are approved abstract category strings only; no
  concrete repo/path/snippet content is or will be emitted.
- Existing mode-only dirty files (`eval/ci_clone_and_lock_repo.py`,
  `eval/ci_make_repo_matrix.py`,
  `eval/p59_contrastive_pack_coverage_counterfactual.py`) were NOT
  touched.
