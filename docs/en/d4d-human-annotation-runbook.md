# D4d Human Annotation Runbook / Checklist Protocol (Public Protocol-Only Artifact)

## Scope and claim boundary

D4d is the **human annotation runbook / checklist protocol** public
artifact. D4d freezes how future human raters should label D4c annotation
packets (filling the dual-rubric E/S slots) before any D4e converter or D5
aggregate release candidate. The default committed artifact is a **public
protocol-only runbook**, NOT a label collection, NOT a packet build, NOT a
filled packet, NOT a D4b bundle, NOT a converter run, and NOT a
calibration.

The D4d bridge is:

```text
D3 dual-rubric -> D4c annotation packets -> human annotation runbook (D4d) -> D4e converter -> D4b true-label bundle -> D5 aggregate release candidate
```

D4d prepares D4e by freezing the human annotation checklist: which slots
to fill, which rubric levels to use, which sources are prohibited, how
adjudication works, and which release gates must pass. D4e (the
packet->bundle converter) needs a filled-packet contract preceded by a
human annotation runbook/checklist; D4d provides that runbook.

D4d **does not** read private packets, **does not** read private packet
output, **does not** read private source records, **does not** generate
or persist annotation packets, **does not** recruit or identify raters,
**does not** emit rater IDs, **does not** collect labels, **does not**
create filled packets, **does not** create a D4b true-label bundle,
**does not** run the packet->bundle converter, **does not** validate a
D4b bundle, **does not** compute calibration metrics, **does not**
measure inter-rater agreement, **does not** compute confidence intervals,
**does not** pass any public-release gate, **does not** unblock D5,
**does not** claim true E/S calibration, **does not** perform model/LLM
labeling, **does not** allow model-assisted labels, **does not** emit
private paths/snippets, **does not** emit packet/task/repo IDs or content
hashes, **does not** emit query/candidate text, and **does not** change
runtime behavior, retriever, pack, model, backend, default policy, or
EvidenceCore semantics.

- Claim level: `human_annotation_runbook_protocol_only`.
- D3 rubric version: `d3_true_dual_rubric_label_protocol_v1`.
- D4c packet schema target: `d4c_annotation_packet_v1`.
- D4b bundle schema target: `d4b_true_label_bundle_v1`.
- Status: `protocol_ready_no_raters_no_labels_no_packets`; mode
  `public_runbook_protocol_only`; phase `D4d`.

D4d is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
downstream agent value claim, NOT a runtime-clean general algorithm
claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D4d emits no EvidenceCore records and changes none of its
  semantics.
- D4d reads no private packets and collects no labels:
  `private_packets_read=false`,
  `private_packet_output_read=false`,
  `private_source_records_read=false`,
  `annotation_packets_generated=false`,
  `annotation_packets_persisted=false`,
  `raters_recruited=false`, `raters_identified=false`,
  `rater_ids_emitted=false`, `labels_collected=false`,
  `filled_packets_created=false`, `private_paths_or_snippets_emitted=false`,
  `packet_ids_emitted=false`, `task_ids_emitted=false`,
  `repo_ids_emitted=false`, `content_sha_emitted=false`,
  `query_or_candidate_text_emitted=false`.
- D4d creates no bundle, runs no converter, computes no metrics, performs
  no model labeling, and passes no release gate:
  `d4b_true_label_bundle_created=false`,
  `d4b_bundle_converter_run=false`,
  `d4b_true_label_bundle_validated=false`,
  `calibration_metrics_computed=false`,
  `inter_rater_agreement_measured=false`,
  `confidence_intervals_computed=false`,
  `model_or_llm_labeling_performed=false`,
  `model_assisted_labels_allowed=false`,
  `true_e_s_calibration_claimed=false`,
  `public_release_gate_passed=false`, `d5_unblocked=false`.

## Core boundary: D4d is protocol-only

- The **default committed D4d artifact** is a public protocol-only
  runbook. Its status is
  `protocol_ready_no_raters_no_labels_no_packets`. It reads NO private
  packets, generates NO packets, recruits/identifies NO raters, collects
  NO labels, creates NO filled packets, creates NO D4b bundle, runs NO
  converter, computes NO calibration, measures NO agreement/CI, performs
  NO model/LLM labeling, and passes NO public-release gate. D5 remains
  blocked.
- D4d has NO private mode, NO `--input`, and NO private packet/source
  reads. There is no opt-in private builder (unlike D4c).
- The runbook/checklist content is category-only and abstract: no packet
  examples, snippets, paths, task IDs, repo names, rater IDs/names, URLs,
  or private examples.

### D4d -> D4e -> D4b relation

D4d freezes the human annotation runbook/checklist that D4e will use.
D4e (the packet->bundle converter, future) maps filled D4c packets (with
human-filled E/S slots) to a `d4b_true_label_bundle_v1`. D4d **does not**
run that converter, **does not** create the bundle, and **does not**
collect or claim labels. D4d prepares D4e by freezing the human checklist
before any conversion.

## CLI

```bash
python3 -m py_compile eval/d4d_human_annotation_runbook.py
python3 eval/d4d_human_annotation_runbook.py --self-test
python3 eval/d4d_human_annotation_runbook.py \
    --out artifacts/d4d_human_annotation_runbook/\
d4d_human_annotation_runbook_report.json
```

Default mode (the only mode): writes the committed public protocol-only
runbook artifact (default out path if `--out` omitted).

CLI arguments: `--self-test`, `--out`. There is **no** `--input` and
**no** `--allow-private-source-records`; D4d is protocol-only and never
reads private packets or source records. Unknown/private-looking arguments are
rejected with a generic `invalid arguments` message that does not echo private
paths or basenames.

## Runbook / checklist sections

The runbook content is category-only and abstract. Seven required
sections, each with a checklist of approved abstract category tokens:

1. **Preconditions** — D3 rubric only; D4c packet schema is the packet
   input source; D4b bundle schema is the output target; packets stay
   local/private; no public packet contents; D4d collects no labels.
2. **Rater setup** — at least two independent human raters; independent
   work before adjudication; no rater IDs in public artifacts; local
   rater identity mapping private-only; training uses abstract examples
   only.
3. **Labeling rules** — fill only `e_score`, `s_score`, `bucket`,
   `citation_valid`, `rater_pair_present`, `adjudicated`; D3 E0/E1/E2
   and S0/S1/S2 definitions; primary evidence requires citation validity;
   dependency support is structural/supportive, not direct-answer
   evidence; abstain on invalid/stale/insufficient evidence.
4. **Prohibited labeling sources** — no LLM/model-generated labels; no
   proxy labels as true labels; no model-name-based rules; no
   benchmark-private buckets as runtime policy; no downstream value
   claims.
5. **Local storage / privacy** — packets and filled packets local-only;
   no packet IDs/task IDs/repo IDs/paths/snippets/content hashes/query/
   candidate text in public artifacts; local outputs under `/tmp` or
   approved private workspace; no committed packets or labels.
6. **Adjudication** — disagreement categories are local-only; adjudication
   happens after independent labels; public output may only include
   aggregate disagreement counts if D5 gates pass; no disagreement
   examples in public artifact.
7. **Release gates** — min total labels `N >= 50`; k-min per public cell
   `k >= 5`; agreement metric required; confidence intervals required;
   small cells suppressed/merged; aggregate-only public release
   candidate; D5 remains blocked until all gates pass.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/d4d_human_annotation_runbook/d4d_human_annotation_runbook_report.json`
is the public protocol-only runbook artifact. Identity / boundary fields:

- `schema_version` = `d4d_human_annotation_runbook.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `d3_rubric_version`, `d4c_packet_schema_target`,
  `d4b_bundle_schema_target`
- Default false flags (all false): `private_packets_read`,
  `private_packet_output_read`, `private_source_records_read`,
  `annotation_packets_generated`, `annotation_packets_persisted`,
  `raters_recruited`, `raters_identified`, `rater_ids_emitted`,
  `labels_collected`, `filled_packets_created`,
  `d4b_true_label_bundle_created`, `d4b_bundle_converter_run`,
  `d4b_true_label_bundle_validated`, `calibration_metrics_computed`,
  `inter_rater_agreement_measured`, `confidence_intervals_computed`,
  `public_release_gate_passed`, `d5_unblocked`,
  `true_e_s_calibration_claimed`, `model_or_llm_labeling_performed`,
  `model_assisted_labels_allowed`, `private_paths_or_snippets_emitted`,
  `packet_ids_emitted`, `task_ids_emitted`, `repo_ids_emitted`,
  `content_sha_emitted`, `query_or_candidate_text_emitted`.
- No-claim / no-runtime-change flags (all false): `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `model_calls_changed`,
  `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`, `promotion_ready`,
  `default_should_change`, `downstream_agent_value_proven`,
  `runtime_clean_general_algorithm_claimed`, `ood_temporal_supported`,
  `quiver_systems_supported`.
- Protocol true flags (exactly these, all true):
  `runbook_protocol_defined`, `checklist_schema_defined`,
  `rater_independence_required`, `d3_rubric_required`,
  `d4c_packet_schema_referenced`, `d4b_bundle_schema_referenced`,
  `local_only_storage_required`, `no_llm_labeling_required`,
  `adjudication_policy_defined`, `disagreement_handling_defined`,
  `min_n_gate_referenced`, `k_min_gate_referenced`,
  `agreement_gate_referenced`, `ci_gate_referenced`,
  `aggregate_only_public_release_required`.
- Diagnostic flags (all true): `aggregate_only_public_artifact`,
  `diagnostic_only`, `not_evidence`.
- `runbook_protocol_contract`: the seven sections with category-only
  checklists; `d3_rubric_version`, `d4c_packet_schema_target`,
  `d4b_bundle_schema_target`.
- `rubric_contract`: `d3_rubric_version`, `e_score_levels=[E0,E1,E2]`,
  `s_score_levels=[S0,S1,S2]`, `bucket_names=[primary_evidence,
  dependency_support, weak_candidates, abstained]`,
  `required_label_slots=[e_score,s_score,bucket,citation_valid,
  rater_pair_present,adjudicated]`.
- `label_slot_contract`: `required_label_slots` (the six slots),
  `target_packet_schema=d4c_annotation_packet_v1`,
  `target_bundle_schema=d4b_true_label_bundle_v1`,
  `no_filled_packets_created=true`.
- `release_gate_contract`: `gate_names=[min_total_labels,k_min,
  agreement_metric,confidence_intervals,small_cell_suppression]`,
  `min_total_labels=50`, `k_min=5`, `min_rater_count=2`,
  `agreement_required=true`, `confidence_intervals_required=true`,
  `small_cell_suppression_required=true`,
  `aggregate_only_public_release_required=true`,
  `d5_blocked_until_all_gates_pass=true`, `public_release_gate_passed=false`.
- `prohibited_labeling_sources_contract`: `prohibited_sources` (no
  LLM/model labels, no proxy labels as true, no model-name rules, no
  benchmark-private buckets as runtime policy, no downstream value
  claims), `model_or_llm_labeling_performed=false`,
  `model_assisted_labels_allowed=false`.
- `rater_setup_contract`: `min_rater_count=2`,
  `rater_independence_required=true`, `rater_independence_rules`,
  `local_rater_mapping_private_only=true`, `rater_ids_emitted=false`,
  `raters_recruited=false`, `raters_identified=false`.
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
`provider_payload`, `api_key`, etc.) anywhere, and rejects value
patterns: ANY URL (no URL allowlist), 32/40/64-char hex digests,
secret-like strings, path-like `src/foo.rs` and `/private/foo.jsonl`,
multiline strings, raw JSON fragments, raw line ranges `12-34`, and the
self-test sentinel.

Contract containers (`checklist`, `e_score_levels`, `s_score_levels`,
`bucket_names`, `required_label_slots`, `gate_names`,
`prohibited_sources`, `rater_independence_rules`) are **exact string
allowlists**: only approved schema identifiers, E/S levels, bucket names,
label-slot field names, gate names, and approved abstract runbook
category tokens may appear there. Arbitrary short strings such as
implementation symbols or private text are rejected **even inside**
contract containers (no over-broad container exemption). Field names
remain rejected as keys anywhere and as values outside contracts.

## Self-tests

- All default false/true flags (default artifact no packets read, no
  raters, no labels, no metrics, no claims; the protocol flags true;
  diagnostic flags true).
- Artifact identity fields (`schema_version`, `claim_level`, `status`,
  `mode`, `phase`, `d3_rubric_version`, `d4c_packet_schema_target`,
  `d4b_bundle_schema_target`).
- Required runbook sections present (seven sections with exact ids and
  non-empty checklists of approved category tokens).
- Rubric / label-slot / gate contracts exact (E0/E1/E2, S0/S1/S2, bucket
  names, label slots, gate names, schema references).
- Release gate constants (`min_total_labels >= 50`, `k_min >= 5`,
  `min_rater_count >= 2`); `d5_unblocked=false`,
  `public_release_gate_passed=false`.
- Prohibited labeling sources (no LLM/proxy/model labels; no model-name
  rules; no benchmark-private buckets as runtime policy; no downstream
  value claims); `model_or_llm_labeling_performed=false`,
  `model_assisted_labels_allowed=false`.
- No private reads / no packets / no labels / no raters (all false
  flags) and no sensitive keys anywhere in the public report.
- Public scanner fail-closes: rejects forbidden keys + value patterns
  (path/snippet/content_sha/query/rater_id/packet_ref/raw_label/
  model_output/provider payload/local path/URL/hash/multiline/raw JSON/
  line range); contract containers reject unapproved strings (including
  `content_sha`, `query_text`, `packet_ref` even inside containers);
  approved abstract category strings pass.
- Fail-closed generation raises on scanner leak; clean public report does
  not raise; generation refuses success if self-test fails.
- CLI option surface: exactly `--self-test` and `--out`; no `--input`,
  no `--allow-private-source-records`.

## Validation

```text
python3 -m py_compile eval/d4d_human_annotation_runbook.py    => PASS
python3 eval/d4d_human_annotation_runbook.py --self-test      => PASS (274/274 checks)
python3 eval/d4d_human_annotation_runbook.py \
  --out artifacts/d4d_human_annotation_runbook/\
d4d_human_annotation_runbook_report.json                     => PASS
  (status: protocol_ready_no_raters_no_labels_no_packets,
   forbidden_scan: pass, self_test_passed: true,
   private_packets_read: false,
   annotation_packets_generated: false,
   labels_collected: false,
   filled_packets_created: false,
   d4b_true_label_bundle_created: false,
   d4b_bundle_converter_run: false,
   calibration_metrics_computed: false,
   inter_rater_agreement_measured: false,
   confidence_intervals_computed: false,
   model_or_llm_labeling_performed: false,
   model_assisted_labels_allowed: false,
   raters_recruited: false, raters_identified: false,
   rater_ids_emitted: false,
   public_release_gate_passed: false, d5_unblocked: false,
   runbook_protocol_defined: true,
   checklist_schema_defined: true,
   rater_independence_required: true,
   d3_rubric_required: true,
   d4c_packet_schema_referenced: true,
   d4b_bundle_schema_referenced: true,
   local_only_storage_required: true,
   no_llm_labeling_required: true,
   adjudication_policy_defined: true,
   disagreement_handling_defined: true,
   min_n_gate_referenced: true,
   k_min_gate_referenced: true,
   agreement_gate_referenced: true,
   ci_gate_referenced: true,
   aggregate_only_public_release_required: true,
   mode: public_runbook_protocol_only, phase: D4d,
   d3_rubric_version: d3_true_dual_rubric_label_protocol_v1,
   d4c_packet_schema_target: d4c_annotation_packet_v1,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## Caveats

- D4d is the human annotation runbook / checklist protocol public
  artifact only. It is eval/diagnostic only. It does NOT change runtime,
  retriever, pack, model, backend, or default policy; it does NOT change
  EvidenceCore semantics. It is NOT a benchmark result, NOT a downstream
  agent value claim, NOT a runtime-clean general algorithm claim, NOT an
  OOD temporal claim, and NOT a QuIVer systems claim.
- D4d default is protocol-only. The default committed artifact reads NO
  private packets, generates NO packets, recruits/identifies NO raters,
  collects NO labels, creates NO filled packets, creates NO D4b bundle,
  runs NO converter, computes NO calibration, measures NO agreement/CI,
  performs NO model/LLM labeling, and passes NO public-release gate.
  D5 remains blocked. Protocol true flags are true only for the defined
  protocol controls, NOT for any real label collection or bundle claim.
- D4d is NOT label collection, NOT packet generation, NOT filled-packet
  creation, NOT D4b true-label bundle creation, NOT converter, NOT
  calibration, NOT agreement measurement, and NOT D5 unblocked. It
  freezes the human annotation runbook/checklist that prepares D4e.
- D4d has NO private mode, NO `--input`, and NO private packet/source
  reads. Unlike D4c, there is no opt-in private builder. The runbook
  content is category-only and abstract; no packet examples, snippets,
  paths, IDs, rater names, or URLs appear in the public artifact.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`, `not_evidence`)
  remain true; the protocol true flags are the only true control flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. `current-research-conclusions` was NOT updated (D4d is a
  protocol-only artifact; no conclusions change).
