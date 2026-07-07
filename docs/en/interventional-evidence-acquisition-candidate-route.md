# Interventional Evidence Acquisition Candidate Route

Date: 2026-07-07

Status: `candidate_route_phase1_hard_source_private_pilot_complete_no_claim`

Authorization: `hard_source_local_private_pilot_confirmed_ignored_private_rows`

Route relation: `new_candidate_route_not_reopening_closed_v2_lines`

This note records a Phase 0 candidate-route design and the later minimal Phase 1 local private pilot for interventional evidence acquisition. It is not OpenLocus v3 branding and does not authorize provider/network work, training, runtime/default changes, or method-winner claims.

## Boundary

This candidate route does not reopen HAAE-A2/v2 trace-driven policy, RPM-D2/model scaling, FRK repair, LDI/static support, provider/network, runtime/default, or method-winner routes. Existing closure context remains authoritative; see [`current-route-closure.md`](./current-route-closure.md), [`state-action-trace-v2-bootstrap.md`](./state-action-trace-v2-bootstrap.md), and [`openlocus-v2-rpm-d1-learning-smoke.md`](./openlocus-v2-rpm-d1-learning-smoke.md) instead of duplicating those route histories here.

Phase 1 private pilot output still requires explicit `--confirm-private-output`. Without that flag, the runner must not write private rows. This pilot does not authorize provider/LLM plumbing, runtime/default changes, CI gates, model changes, training, source scans, or README changes.

## Phase 1 local private pilot status

The minimal local pilot runner is `eval/interventional_evidence_acquisition_phase1_local_episode_runner.py`. A confirmed low-resource local run previously wrote private rows only under ignored `runs/` storage after `--confirm-private-output`. The current public aggregate report at `artifacts/interventional_evidence_acquisition_phase1_local_episode_runner/interventional_evidence_acquisition_phase1_local_episode_runner_report.json` was regenerated as a methodology-repair `phase1_preflight` dry run with no private rows written.

The report is aggregate-only: no private row contents, task text, paths, ranges, hashes, snippets, provider payloads, or per-episode details are public. No provider/network actions were authorized or executed, no training or runtime/default change was authorized, no method-winner claim is made, and the next authorized action remains `stop/request next explicit decision`.

## Hard-source preflight status

The hard-source preflight script is `eval/interventional_evidence_acquisition_phase1_hard_source_preflight.py`. It generated `artifacts/interventional_evidence_acquisition_phase1_hard_source_preflight/interventional_evidence_acquisition_phase1_hard_source_preflight_report.json` with status `phase1_hard_source_preflight_no_private_rows`.

This is not a confirmed private capture. It checks 32 synthetic/local hard task shapes across 8 family buckets and publishes only aggregate buckets for balance, structural availability, candidate ambiguity, baseline non-saturation, EvidenceCore summary, and privacy summary. It does not write private rows and does not authorize provider/network work, training, runtime/default changes, new retrieval families, method-winner claims, or route reopening.

## Hard-source private pilot status

The same script now supports explicit `--confirm-private-output` mode. A confirmed local private pilot wrote private rows only under ignored `runs/` storage and updated the same public report to status `phase1_hard_source_private_pilot_complete_no_claim`.

The public report remains aggregate-only: task/action/family count buckets, candidate-found buckets, materialized buckets, evidence-success buckets, baseline/non-saturation buckets, privacy summary, and no-claim attestations. Retrieval-only actions may find candidates but do not count as evidence success without current-source materialization. No provider/network work, training, runtime/default changes, new retrieval families, method-winner claims, or route reopening are authorized.

## Private-row aggregate screen status

The same script now supports `--aggregate-private-rows`. It reads existing ignored hard-source private rows locally and writes `artifacts/interventional_evidence_acquisition_phase1_hard_source_private_row_aggregate_screen/interventional_evidence_acquisition_phase1_hard_source_private_row_aggregate_screen_report.json` with status `phase1_hard_source_private_row_aggregate_screen_no_claim`.

This screen is public aggregate-only and diagnostic. It publishes buckets for row/action/family coverage, candidate-found, materialized, evidence-success, materialized-but-not-success, baseline/randomized screen, and conservative recommendation `maybe_expand_with_new_explicit_decision`. It publishes no raw rows, private paths, symbols, queries, ranges, snippets, hashes, run paths, prompts, responses, provider payloads, or labels, and it makes no method-winner or signal claim.

## Phase 1B micro-policy status

The same script now supports `--run-phase1b-micro-policy --confirm-private-output`. It ran a tiny local micro-policy collection over the existing hard synthetic task source and wrote private rows only under ignored `runs/`. The public report is `artifacts/interventional_evidence_acquisition_phase1b_micro_policy_tiny_collection/interventional_evidence_acquisition_phase1b_micro_policy_tiny_collection_report.json` with status `phase1b_micro_policy_tiny_collection_synthetic_preflight_no_real_evidencecore_no_claim`.

Phase 1B uses only the seven local micro-policy/control labels: `bm25_then_read_top1`, `bm25_then_read_next_unique_file`, `symbol_regex_then_read_top1`, `symbol_regex_then_read_next_unique_file`, `read_related_test_when_available`, `stop`, and `abstain`. Standalone retrieval is not a top-level Phase 1B policy. Because the source still simulates materialization instead of reading real current files/ranges/content, this is synthetic preflight only, not real EvidenceCore evidence. Public output uses buckets for synthetic success labels only, recommendation `maybe_expand_with_new_explicit_decision`, and no method-winner or signal claim.

## Phase 1C real current-source feasibility status

The same script now supports `--run-phase1c-real-source --confirm-private-output --phase1c-private-manifest <ignored-local-path>`. It ran a tiny local feasibility pilot over 8 current repository-file tasks and all seven existing Phase 1B micro-policy/control labels, with exact task paths/ranges read from an ignored private manifest. Private rows are under ignored `runs/`; the public report is `artifacts/interventional_evidence_acquisition_phase1c_tiny_real_current_source_pilot/interventional_evidence_acquisition_phase1c_tiny_real_current_source_pilot_report.json` with status `phase1c_tiny_real_current_source_pilot_evidencecore_feasibility_no_claim`.

This only checks whether the local micro-policy framework can safely perform real current-source materialization. Counted success requires private path/range/content bytes, SHA-256, re-read/currentness match, and range/content match. Public output is aggregate buckets only with recommendation `maybe_expand_with_new_explicit_decision`. It makes no method-winner, lift, or signal claim and does not change provider/network, training/model, runtime/default, or retrieval-family boundaries.

## Phase 1D real-source coverage robustness status

The same script now supports `--run-phase1d-real-source --confirm-private-output --phase1d-private-manifest <ignored-local-path>`. It ran a modest local robustness pilot over up to 16 current repository-file tasks and all seven existing micro-policy/control labels, with exact task paths/ranges read from an ignored private manifest. Private rows are under ignored `runs/`; the public report is `artifacts/interventional_evidence_acquisition_phase1d_real_source_coverage_robustness/interventional_evidence_acquisition_phase1d_real_source_coverage_robustness_report.json` with status `phase1d_real_source_coverage_robustness_no_claim`.

This tests coverage robustness only, not policy efficacy. Counted success requires real current-source materialization with private hash and currentness checks. Public output is aggregate buckets only with recommendation `maybe_expand_with_new_explicit_decision`; it makes no method-winner, lift, or signal claim.

## Candidate question

Can a tiny, local, randomized intervention over existing evidence-acquisition actions produce clearer product-workflow evidence than passive trace review, while preserving EvidenceCore and privacy invariants?

The intended evidence is decision-quality, not branding: whether controlled action choice helps find current, rematerializable evidence sooner on hard product-workflow episodes.

## Phase 1 local pilot shape

Phase 1 was run as a private randomized local pilot only:

- 24-40 hard product-workflow episodes.
- Maximum 7 existing local actions: `retrieve_bm25`, `retrieve_symbol_regex`, `read_top1`, `read_next_unique_file`, `read_related_test`, `stop`, `abstain`.
- No LLM/provider/network actions.
- No model training or model scaling.
- No new retrieval channel families.
- No runtime/default changes.
- No method-winner, scale, default, or product-readiness claim.

## Private row schema

The confirmed run used a small fail-closed private row shape with:

- `schema_version`: fixed candidate schema id.
- `episode_id`, `step_index`, `randomization_block_id`: private identifiers.
- `task_bucket`: coarse product-workflow task family, not raw prompt text.
- `state`: label-blind pre-action fields such as remaining budget bucket, seen file count bucket, candidate count bucket, ambiguity bucket, and evidence coverage bucket.
- `action`: one of the 7 local actions above.
- `randomization`: eligible action set, assignment policy id, probability bucket, and seed/reference kept private.
- `observation`: cost bucket, file/read result bucket, abstain/stop marker, and failure-safe reason bucket.
- `evidence_core`: private source path, range, content/currentness check result, and rematerialization status.
- `outcome`: post-action success/failure-safe label and reason bucket, filled only after action/offline review.
- `privacy`: private-only markers for prompt/response/snippet/gold/provider/path/range/hash/reference containment.

Private rows stay under ignored `runs/` storage and are not public artifacts.

## Aggregate-only public report shape

The public report is aggregate/sanitized only and contains:

- route/status/authorization fields;
- episode-count and step-count buckets;
- action coverage and randomization health buckets;
- EvidenceCore rematerialization pass/fail buckets;
- success/failure-safe aggregate buckets by action family;
- stop/abstain and budget buckets;
- privacy scan summary;
- stop/go recommendation with no private rows.

The public report must not include private traces, prompts, responses, snippets, gold labels, provider payloads, exact paths, exact ranges, hashes, private refs, raw task text, raw row values, or per-episode details.

## EvidenceCore and privacy invariants

- Counted evidence must rematerialize current source path/range/content/currentness.
- Candidate evidence is not fact until it passes the currentness and content checks.
- Public outputs are aggregate/sanitized only.
- Private traces, prompts, responses, snippets, gold, provider payloads, exact paths, exact ranges, hashes, and private refs stay private.
- State/action fields must remain label-blind; labels/outcomes are post-action or offline-only.

## Phase 0 to Phase 1 decision record

Phase 1 was allowed only after these conditions were met:

1. A separate explicit route decision names this candidate route and authorizes the tiny private pilot.
2. The episode source is bounded to 24-40 hard product-workflow episodes.
3. The action set remains limited to the 7 existing local actions listed above.
4. The private row schema and aggregate-only report contract are accepted before any capture.
5. EvidenceCore rematerialization and privacy checks are required from the first row.
6. The decision explicitly preserves all closed-route boundaries listed in this note.

## Phase 1 stop/go status

Phase 1 completed as a no-claim pilot. It must stop unless a separate later decision is made, because the public report deliberately makes no signal or method-winner claim. Future continuation would require all of:

1. Schema-valid private rows with no label leakage into state/action fields.
2. EvidenceCore rematerialization meets the predeclared minimum needed for counted evidence to be trusted.
3. No public/private privacy boundary failures.
4. Randomization health meets predeclared checks for the tiny pilot's aggregate comparison.
5. Predeclared aggregate stop/go thresholds are met, including a practical aggregate signal that randomized existing-local-action choice improves hard product-workflow evidence acquisition versus the best fixed local-action baseline under the same 7-action, same-budget setup, not merely versus stop/abstain.

Even if all criteria pass, the only possible next step is another explicit route decision. Phase 1 would not authorize runtime/default changes, provider/network work, training, new retrieval families, or method-winner claims.
